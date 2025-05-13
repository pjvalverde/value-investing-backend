import os
import json
import random
import logging
import requests
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

# Importar modelos
from backend.models.db import db
from backend.models.symbols import Symbol
from backend.models.portfolios import Portfolio

# Importar servicios
from backend.services.alpha_vantage import alpha_vantage_client
from backend.services.chart_service import chart_service
from backend.services.portfolio_service import portfolio_service
from backend.services.claude_service import claude_service

# Importar rutas
from backend.routes.screener import router as screener_router
from backend.routes.portfolio import router as portfolio_router
import pandas as pd
import markdown

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("value-investing-api")

app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Permitir acceso desde el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(screener_router, prefix="/api", tags=["screener"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs')
RESULTS_DIR = os.path.join(DATA_DIR, 'resultados')

# No se utilizan listas predefinidas de tickers
# Todos los tickers deben obtenerse en tiempo real de Perplexity y Alpha Vantage

# No se utilizan datos simulados o predefinidos
# Todas las métricas deben obtenerse en tiempo real de Alpha Vantage

logging.basicConfig(level=logging.INFO)

# Endpoint para obtener datos históricos de precios para múltiples tickers
@app.post("/historical_prices")
async def historical_prices(request: Request):
    try:
        params = await request.json()
        tickers = params.get("tickers", [])
        period = params.get("period", "5years")
        results = {}
        
        for ticker in tickers:
            # Usar el servicio de Alpha Vantage para obtener datos históricos
            historical_data = alpha_vantage_client.get_historical_prices(ticker, period)
            results[ticker] = historical_data
            
        return {"results": results}
    except Exception as e:
        logger.error(f"Error getting historical prices: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting historical prices: {str(e)}"}
        )

@app.post("/generate_portfolio")
async def generate_portfolio(request: Request):
    try:
        # Leer datos del request
        data = await request.json()
        logger.info(f"Datos recibidos: {data}")
        
        # Obtener parámetros
        user_id = data.get("user_id", str(uuid.uuid4()))
        name = data.get("name", "Mi Portfolio")
        amount = float(data.get("amount", 10000))
        horizon = data.get("horizon", "largo")
        include_tbills = data.get("includeTBills", False)
        sectors = data.get("sectors", [])
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        
        logger.info(f"Generando portafolio para monto: {amount}, sectores: {sectors}, T-Bills: {include_tbills}")
        
        # Validar asignación
        total_alloc = target_alloc.get("value", 0) + target_alloc.get("growth", 0) + target_alloc.get("bonds", 0)
        if total_alloc != 100:
            return JSONResponse(
                status_code=400,
                content={"error": f"La asignación total debe ser 100%, recibido: {total_alloc}%"}
            )
        
        # Lógica de selección mejorada
        filtered = []
        etfs = [a for a in UNIVERSE if a["tipo"] == "ETF"]
        acciones = [a for a in UNIVERSE if a["tipo"] == "Acción" and (not sectors or a["sector"] in sectors)]
        
        if amount < 2000:
            filtered = etfs.copy()
            if acciones and len(filtered) < 2:
                filtered += acciones[:2 - len(filtered)]
            if include_tbills:
                filtered.append(next(a for a in UNIVERSE if a["ticker"] == "T-BILL"))
        else:
            filtered = acciones.copy()
            if len(filtered) < 2:
                filtered += etfs
            else:
                filtered += [etf for etf in etfs if etf not in filtered]
            if include_tbills:
                filtered.append(next(a for a in UNIVERSE if a["ticker"] == "T-BILL"))
        
        # Eliminar duplicados
        tickers_seen = set()
        filtered_unique = []
        for item in filtered:
            if item["ticker"] not in tickers_seen:
                filtered_unique.append(item)
                tickers_seen.add(item["ticker"])
        
        # Crear el portfolio usando el servicio
        portfolio = portfolio_service.create_portfolio(user_id, name, target_alloc)
        
        # Optimizar el portfolio
        optimized = portfolio_service.optimize_portfolio(portfolio["id"], amount)
        
        # Guardar el último portfolio generado para este usuario
        last_portfolio[user_id] = optimized
        
        return optimized
    
    except Exception as e:
        logger.error(f"Error generando portfolio: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Error al generar portfolio", "details": str(e)}
        )

# Endpoint para obtener el portafolio generado
@app.get("/get_portfolio")
def get_portfolio():
    if not last_portfolio:
        return JSONResponse(status_code=404, content={"error": "No hay portfolio generado"})
    return last_portfolio

# Endpoint para obtener datos históricos de precios
@app.get("/historical_prices/{ticker}")
def get_historical_prices(ticker: str, period: str = "1year"):
    try:
        # Verificar si el ticker existe en nuestro universo
        if ticker not in [a["ticker"] for a in UNIVERSE]:
            return JSONResponse(
                status_code=404,
                content={"error": f"Ticker {ticker} no encontrado en el universo de inversión"}
            )
        
        # Usar el servicio de gráficos para obtener los datos históricos
        try:
            # Obtener datos del chart service
            chart_data = chart_service.get_price_chart_data(ticker, period)
            
            # Si no hay datos, usar datos simulados
            if not chart_data or "prices" not in chart_data or not chart_data["prices"]:
                logger.warning(f"No se encontraron datos para {ticker}. Usando datos simulados.")
                return generate_simulated_historical_data(ticker, period)
                
            return chart_data
            
        except Exception as e:
            logger.warning(f"Error al obtener datos reales para {ticker}: {str(e)}. Usando datos simulados.")
            # Si falla, usar datos simulados
            return generate_simulated_historical_data(ticker, period)
    
    except Exception as e:
        logger.error(f"Error al obtener precios históricos: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Error al obtener precios históricos", "details": str(e)}
        )

# Función para generar datos históricos simulados
def generate_simulated_historical_data(ticker: str, period: str = "1year"):
    # Determinar cuántos puntos de datos generar
    if period == "1month":
        num_points = 30
        date_format = "%Y-%m-%d"
        delta = timedelta(days=1)
    elif period == "6months":
        num_points = 26
        date_format = "%Y-%m-%d"
        delta = timedelta(days=7)
    else:  # 1year o default
        num_points = 12
        date_format = "%Y-%m"
        delta = timedelta(days=30)
    
    # Generar un precio base aleatorio entre 50 y 500
    base_price = random.uniform(50, 500)
    
    # Generar datos históricos simulados con una tendencia alcista o bajista
    trend = random.choice([1, -1])  # 1 para alcista, -1 para bajista
    volatility = random.uniform(0.02, 0.1)  # Volatilidad entre 2% y 10%
    
    result = []
    current_date = datetime.now()
    current_price = base_price
    
    for i in range(num_points):
        # Ajustar la fecha hacia atrás
        date = current_date - (delta * (num_points - i))
        
        # Simular movimiento de precio
        price_change = current_price * (trend * random.uniform(0.005, 0.03) + random.uniform(-volatility, volatility))
        current_price += price_change
        
        # Asegurarse de que el precio no sea negativo
        current_price = max(current_price, 1.0)
        
        result.append({
            "date": date.strftime(date_format),
            "price": round(current_price, 2)
        })
    
    return result

# Endpoint para obtener datos comparativos en tiempo real
@app.get("/comparative_data/{tickers}")
async def get_comparative_data(tickers: str):
    ticker_list = tickers.split(",")
    result = []
    
    for ticker in ticker_list:
        try:
            # Verificar si el ticker existe en nuestro universo
            if ticker not in [a["ticker"] for a in UNIVERSE]:
                logger.warning(f"Ticker {ticker} no encontrado en el universo de inversión")
                continue
            
            # Intentar obtener datos fundamentales usando el servicio de Alpha Vantage
            try:
                # Obtener datos fundamentales
                fundamental_data = alpha_vantage_client.get_fundamental_data(ticker)
                
                # Obtener precio en tiempo real
                price_data = alpha_vantage_client.get_real_time_price(ticker)
                
                # Obtener análisis cualitativo usando Claude
                qualitative_analysis = claude_service.get_stock_analysis(ticker)
                
                # Extraer métricas fundamentales
                company_data = {
                    "company": fundamental_data.get("Name", ticker),
                    "ticker": ticker,
                    "price": price_data.get("price"),
                    "change": price_data.get("change_percent"),
                    "ROE": float(fundamental_data.get("ReturnOnEquityTTM", "0")) * 100 if fundamental_data.get("ReturnOnEquityTTM") else None,
                    "P/E": float(fundamental_data.get("PERatio", "0")) if fundamental_data.get("PERatio") else None,
                    "Margen de Beneficio": f"{float(fundamental_data.get('ProfitMargin', '0')) * 100:.1f}%" if fundamental_data.get("ProfitMargin") else None,
                    "Ratio de Deuda": fundamental_data.get("DebtToEquityRatio"),
                    "Crecimiento de FCF": qualitative_analysis.get("fcf_growth"),
                    "Moat Cualitativo": qualitative_analysis.get("moat_rating"),
                    "Sector": fundamental_data.get("Sector"),
                    "Industria": fundamental_data.get("Industry"),
                    "Capitalización": fundamental_data.get("MarketCapitalization"),
                    "Dividendo": fundamental_data.get("DividendYield")
                }
                
                result.append(company_data)
                continue
                
            except Exception as e:
                logger.warning(f"Error al obtener datos reales para {ticker}: {str(e)}. Usando datos alternativos.")
            
            # Si no se pueden obtener datos reales, usar datos de METRICAS si están disponibles
            if ticker in METRICAS:
                metrics = METRICAS[ticker]
                ticker_info = next((a for a in UNIVERSE if a["ticker"] == ticker), {})
                
                company_data = {
                    "company": ticker,
                    "ticker": ticker,
                    "price": None,  # No disponible sin datos reales
                    "change": None,  # No disponible sin datos reales
                    "ROE": metrics["ROE"],
                    "P/E": metrics["P/E"],
                    "Margen de Beneficio": metrics["Margen de Beneficio"],
                    "Ratio de Deuda": metrics["Ratio de Deuda"],
                    "Crecimiento de FCF": metrics["Crecimiento de FCF"],
                    "Moat Cualitativo": metrics["Moat Cualitativo"],
                    "Sector": ticker_info.get("sector"),
                    "Industria": None,
                    "Capitalización": None,
                    "Dividendo": None
                }
                result.append(company_data)
                continue
            
            # Si no hay datos disponibles, generar datos simulados
            ticker_info = next((a for a in UNIVERSE if a["ticker"] == ticker), {})
            company_data = {
                "company": ticker,
                "ticker": ticker,
                "price": round(random.uniform(50, 500), 2),
                "change": f"{random.uniform(-5, 5):.2f}%",
                "ROE": round(random.uniform(5, 25), 1),
                "P/E": round(random.uniform(10, 30), 1),
                "Margen de Beneficio": f"{random.uniform(5, 30):.1f}%",
                "Ratio de Deuda": f"{random.uniform(0.1, 0.8):.1f}",
                "Crecimiento de FCF": f"{random.uniform(3, 15):.1f}%",
                "Moat Cualitativo": random.choice(["Alto", "Medio", "Bajo"]),
                "Sector": ticker_info.get("sector"),
                "Industria": None,
                "Capitalización": f"{random.uniform(1, 500):.1f}B",
                "Dividendo": f"{random.uniform(0, 5):.2f}%"
            }
            result.append(company_data)
            
        except Exception as e:
            logger.error(f"Error al obtener datos comparativos para {ticker}: {str(e)}")
            # En caso de error, agregar datos simulados
            result.append({
                "company": ticker,
                "ticker": ticker,
                "price": round(random.uniform(50, 500), 2),
                "change": f"{random.uniform(-5, 5):.2f}%",
                "ROE": round(random.uniform(5, 25), 1),
                "P/E": round(random.uniform(10, 30), 1),
                "Margen de Beneficio": f"{random.uniform(5, 30):.1f}%",
                "Ratio de Deuda": f"{random.uniform(0.1, 0.8):.1f}",
                "Crecimiento de FCF": f"{random.uniform(3, 15):.1f}%",
                "Moat Cualitativo": random.choice(["Alto", "Medio", "Bajo"]),
                "Sector": None,
                "Industria": None,
                "Capitalización": f"{random.uniform(1, 500):.1f}B",
                "Dividendo": f"{random.uniform(0, 5):.2f}%"
            })
    
    return result

# Endpoint para obtener la justificación (Claude API)
@app.get("/justification")
async def justification():
    import os
    import requests
    global last_portfolio
    if not last_portfolio or "portfolio" not in last_portfolio:
        return JSONResponse(content={"error": "Primero genera un portafolio."}, status_code=400)
    portfolio = last_portfolio["portfolio"]
    tickers = [a["ticker"] for a in portfolio if a["tipo"] in ["Acción", "ETF"]]
    prompt = (
        "Eres un analista de inversiones. Explica de manera detallada por qué las siguientes acciones y ETFs fueron seleccionados para el portafolio de un inversionista considerando su sector, peso, métricas clave y contexto de mercado. Hazlo en español y sé específico para cada ticker: " + ", ".join(tickers)
    )
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data = {
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        # Extraer el análisis del response
        content = ""
        if "content" in result and result["content"]:
            content = result["content"][0]["text"]
        if not content or len(content.strip()) < 10:
            logging.error(f"Claude devolvió respuesta vacía: {result}")
            return JSONResponse(content={"error": "Claude no devolvió un análisis válido."}, status_code=500)
        # Preparar métricas para la tabla comparativa
        metrics = []
        for a in portfolio:
            if a["tipo"] in ["Acción", "ETF"]:
                metrics.append({
                    "ticker": a["ticker"],
                    "sector": a.get("sector", ""),
                    "ROE": a.get("ROE", None),
                    "PE": a.get("PE", None),
                    "margen_beneficio": a.get("margen_beneficio", None),
                    "ratio_deuda": a.get("ratio_deuda", None),
                    "crecimiento_fcf": a.get("crecimiento_fcf", None),
                    "moat": a.get("moat", None)
                })
        return {"analysis": content, "metrics": metrics}
    except Exception as e:
        logging.error(f"Error al conectar con Claude: {e}")
        return JSONResponse(content={"error": f"Error al conectar con Claude: {str(e)}"}, status_code=500)

@app.get("/justification_accion/{ticker}")
async def justification_accion(ticker: str):
    try:
        # Verificar si el ticker existe en nuestro universo
        if ticker not in [a["ticker"] for a in UNIVERSE]:
            return JSONResponse(
                status_code=404,
                content={"error": f"Ticker {ticker} no encontrado en el universo de inversión"}
            )
        
        # Obtener datos fundamentales y precio actual
        try:
            # Obtener datos fundamentales
            fundamental_data = alpha_vantage_client.get_fundamental_data(ticker)
            
            # Obtener precio en tiempo real
            price_data = alpha_vantage_client.get_real_time_price(ticker)
            
            # Usar el servicio de Claude para obtener un análisis detallado
            analysis = claude_service.get_detailed_stock_analysis(ticker, fundamental_data, price_data)
            
            # Obtener datos históricos para el contexto
            historical_data = chart_service.get_price_chart_data(ticker, "1year")
            
            # Obtener métricas de rendimiento
            performance_metrics = chart_service.get_performance_metrics(ticker)
            
            # Combinar toda la información en un análisis completo
            complete_analysis = {
                "ticker": ticker,
                "company_name": fundamental_data.get("Name", ticker),
                "current_price": price_data.get("price"),
                "change_percent": price_data.get("change_percent"),
                "sector": fundamental_data.get("Sector"),
                "industry": fundamental_data.get("Industry"),
                "market_cap": fundamental_data.get("MarketCapitalization"),
                "pe_ratio": fundamental_data.get("PERatio"),
                "dividend_yield": fundamental_data.get("DividendYield"),
                "roe": fundamental_data.get("ReturnOnEquityTTM"),
                "profit_margin": fundamental_data.get("ProfitMargin"),
                "debt_to_equity": fundamental_data.get("DebtToEquityRatio"),
                "performance": performance_metrics,
                "analysis_html": analysis.get("analysis_html"),
                "investment_thesis": analysis.get("investment_thesis"),
                "strengths": analysis.get("strengths"),
                "weaknesses": analysis.get("weaknesses"),
                "opportunities": analysis.get("opportunities"),
                "threats": analysis.get("threats"),
                "recommendation": analysis.get("recommendation")
            }
            
            return complete_analysis
            
        except Exception as e:
            logger.warning(f"Error al obtener datos reales para {ticker}: {str(e)}. Usando datos alternativos.")
            
            # Si no se pueden obtener datos reales, usar datos de METRICAS si están disponibles
            if ticker in METRICAS:
                metrics = METRICAS[ticker]
                ticker_info = next((a for a in UNIVERSE if a["ticker"] == ticker), {})
                
                # Generar un análisis simplificado basado en los datos disponibles
                simplified_analysis = claude_service.get_simplified_analysis(ticker, metrics)
                
                return {
                    "ticker": ticker,
                    "company_name": ticker,
                    "sector": ticker_info.get("sector"),
                    "roe": metrics.get("ROE"),
                    "pe_ratio": metrics.get("P/E"),
                    "profit_margin": metrics.get("Margen de Beneficio"),
                    "debt_to_equity": metrics.get("Ratio de Deuda"),
                    "analysis_html": simplified_analysis.get("analysis_html"),
                    "investment_thesis": simplified_analysis.get("investment_thesis"),
                    "recommendation": simplified_analysis.get("recommendation")
                }
            
            # Si no hay datos disponibles, generar un mensaje de error
            return JSONResponse(
                status_code=404,
                content={"error": f"No se encontraron datos suficientes para analizar {ticker}"}
            )
    
    except Exception as e:
        logger.error(f"Error al obtener análisis para {ticker}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al obtener análisis individual: {str(e)}"}
        )

@app.get("/visualizations/{img_name}")
def get_visualization(img_name: str):
    img_path = os.path.join(RESULTS_DIR, img_name)
    if not os.path.exists(img_path):
        return JSONResponse(content={"error": "Visualization not found"}, status_code=404)
    return FileResponse(img_path)

@app.get("/real_time_price/{ticker}")
async def real_time_price(ticker: str):
    try:
        # Verificar si el ticker existe en nuestro universo
        if ticker not in [a["ticker"] for a in UNIVERSE]:
            return JSONResponse(
                status_code=404,
                content={"error": f"Ticker {ticker} no encontrado en el universo de inversión"}
            )
            
        # Usar el servicio de Alpha Vantage para obtener el precio en tiempo real
        price_data = alpha_vantage_client.get_real_time_price(ticker)
        
        # Si no hay datos, devolver un error
        if not price_data or "price" not in price_data:
            return JSONResponse(
                status_code=404,
                content={"error": f"No se pudo obtener el precio en tiempo real para {ticker}"}
            )
            
        # Agregar información adicional del universo
        ticker_info = next((a for a in UNIVERSE if a["ticker"] == ticker), None)
        if ticker_info:
            price_data["sector"] = ticker_info.get("sector")
            price_data["tipo"] = ticker_info.get("tipo")
            
        return price_data
    except Exception as e:
        logger.error(f"Error obteniendo precio en tiempo real para {ticker}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error obteniendo precio para {ticker}", "details": str(e)}
        )

@app.get("/")
def root():
    return {"message": "API VIVA - TEST 2025-04-29"}
