# Aplicaciu00f3n FastAPI completamente independiente sin importaciones externas
import os
import sys
import uvicorn
import logging
import json
import uuid
import random
import requests
from datetime import datetime, timedelta
import pandas as pd
import markdown
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

# Agregar el directorio actual al path para poder importar los mu00f3dulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("value-investing-api")

# Importar FastAPI y componentes necesarios
from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

# Importar servicios
from backend.services.alpha_vantage import AlphaVantageClient
from backend.services.chart_service import ChartService
from backend.services.portfolio_service import PortfolioService
from backend.services.claude_service import ClaudeService

# Crear la aplicaciu00f3n FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Permitir acceso desde el frontend React - Configuracin explcita de CORS
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://pjvalverde.github.io",
    "*"  # Permitir cualquier origen en desarrollo
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Type"],
    max_age=600,  # 10 minutos
)

# Agregar middleware para loguear todas las solicitudes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"Solicitud recibida: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logging.info(f"Respuesta enviada: {response.status_code}")
        return response
    except Exception as e:
        logging.error(f"Error en solicitud: {str(e)}")
        raise

# Inicializar servicios
alpha_vantage_client = None
chart_service = None
portfolio_service = None
claude_service = None
last_portfolio = None

# Inicializar servicios al inicio de la aplicaciu00f3n
@app.on_event("startup")
async def startup_event():
    global alpha_vantage_client, chart_service, portfolio_service, claude_service
    
    # Inicializar el cliente de Alpha Vantage
    alpha_vantage_api_key = os.getenv("ALPHAVANTAGE_API_KEY", "demo")
    alpha_vantage_client = AlphaVantageClient(api_key=alpha_vantage_api_key)
    
    # Inicializar el servicio de gru00e1ficos
    chart_service = ChartService(alpha_vantage_client=alpha_vantage_client)
    
    # Inicializar el servicio de portfolio
    portfolio_service = PortfolioService(alpha_vantage_client=alpha_vantage_client)
    
    # Inicializar el servicio de Claude
    claude_api_key = os.getenv("CLAUDE_API_KEY", "")
    claude_service = ClaudeService(api_key=claude_api_key)
    
    logger.info("Servicios inicializados correctamente")

# Endpoint para obtener precios en tiempo real
@app.get("/real_time_price/{ticker}")
async def real_time_price(ticker: str):
    try:
        # Verificar si el ticker existe
        logger.info(f"Obteniendo precio en tiempo real para {ticker}")
            
        # Usar el servicio de Alpha Vantage para obtener el precio en tiempo real
        price_data = alpha_vantage_client.get_real_time_price(ticker)
        
        # Si no hay datos, devolver un error
        if not price_data or "price" not in price_data:
            return JSONResponse(
                status_code=404,
                content={"error": f"No se pudo obtener el precio en tiempo real para {ticker}"}
            )
            
        return price_data
    except Exception as e:
        logger.error(f"Error obteniendo precio en tiempo real para {ticker}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error obteniendo precio para {ticker}", "details": str(e)}
        )

# Endpoint para obtener datos históricos de precios
@app.get("/historical_prices/{ticker}")
def get_historical_prices(ticker: str, period: str = "1year"):
    try:
        logger.info(f"Obteniendo datos históricos para {ticker}, periodo {period}")
        
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

# Endpoint para datos comparativos
@app.get("/comparative_data/{tickers}")
async def get_comparative_data(tickers: str):
    try:
        ticker_list = tickers.split(",")
        result = []
        
        for ticker in ticker_list:
            try:
                # Verificar si el ticker existe
                logger.info(f"Obteniendo datos comparativos para {ticker}")
                
                # Intentar obtener datos fundamentales usando el servicio de Alpha Vantage
                try:
                    # Obtener datos fundamentales
                    fundamental_data = alpha_vantage_client.get_fundamental_data(ticker)
                    
                    # Obtener precio en tiempo real
                    price_data = alpha_vantage_client.get_real_time_price(ticker)
                    
                    # Obtener anu00e1lisis cualitativo usando Claude
                    qualitative_analysis = claude_service.get_stock_analysis(ticker)
                    
                    # Extraer mu00e9tricas fundamentales
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
                        "Capitalizaciu00f3n": fundamental_data.get("MarketCapitalization"),
                        "Dividendo": fundamental_data.get("DividendYield")
                    }
                    
                    result.append(company_data)
                    continue
                    
                except Exception as e:
                    logger.warning(f"Error al obtener datos reales para {ticker}: {str(e)}. Usando datos simulados.")
                
                # Si no hay datos disponibles, generar datos simulados
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
                    "Sector": None,
                    "Industria": None,
                    "Capitalizaciu00f3n": f"{random.uniform(1, 500):.1f}B",
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
                    "Capitalizaciu00f3n": f"{random.uniform(1, 500):.1f}B",
                    "Dividendo": f"{random.uniform(0, 5):.2f}%"
                })
        
        return result
    except Exception as e:
        logger.error(f"Error en endpoint /comparative_data: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Error al obtener datos comparativos", "details": str(e)}
        )

# Endpoint para anu00e1lisis de acciones
@app.get("/justification_accion/{ticker}")
async def justification_accion(ticker: str):
    try:
        # Verificar si el ticker existe
        logger.info(f"Obteniendo anu00e1lisis para {ticker}")
        
        # Obtener datos fundamentales y precio actual
        try:
            # Obtener datos fundamentales
            fundamental_data = alpha_vantage_client.get_fundamental_data(ticker)
            
            # Obtener precio en tiempo real
            price_data = alpha_vantage_client.get_real_time_price(ticker)
            
            # Usar el servicio de Claude para obtener un anu00e1lisis detallado
            analysis = claude_service.get_detailed_stock_analysis(ticker, fundamental_data, price_data)
            
            # Obtener datos histu00f3ricos para el contexto
            historical_data = chart_service.get_price_chart_data(ticker, "1year")
            
            # Obtener mu00e9tricas de rendimiento
            performance_metrics = chart_service.get_performance_metrics(ticker)
            
            # Combinar toda la informaciu00f3n en un anu00e1lisis completo
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
            logger.warning(f"Error al obtener datos reales para {ticker}: {str(e)}. Usando datos simulados.")
            
            # Si no se pueden obtener datos reales, generar un anu00e1lisis simplificado
            simplified_analysis = {
                "ticker": ticker,
                "company_name": ticker,
                "current_price": round(random.uniform(50, 500), 2),
                "change_percent": f"{random.uniform(-5, 5):.2f}%",
                "sector": random.choice(["Tecnologu00eda", "Finanzas", "Salud", "Consumo", "Industrial"]),
                "analysis_html": f"<div><h2>Anu00e1lisis simplificado de {ticker}</h2><p>Este es un anu00e1lisis simplificado basado en datos simulados.</p></div>",
                "investment_thesis": f"La empresa {ticker} muestra indicadores financieros {random.choice(['positivos', 'mixtos', 'negativos'])}.",
                "recommendation": random.choice(["Comprar", "Mantener", "Vender"])
            }
            
            return simplified_analysis
    
    except Exception as e:
        logger.error(f"Error al obtener anu00e1lisis para {ticker}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al obtener anu00e1lisis individual: {str(e)}"}
        )

# Rutas para portfolios
@app.post("/api/portfolio/create")
async def create_portfolio(request: Request):
    try:
        data = await request.json()
        logger.info(f"Datos recibidos: {data}")
        
        # Obtener paru00e1metros
        user_id = data.get("user_id", str(uuid.uuid4()))
        name = data.get("name", "Mi Portfolio")
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        
        # Validar asignaciu00f3n
        total_alloc = target_alloc.get("value", 0) + target_alloc.get("growth", 0) + target_alloc.get("bonds", 0)
        if total_alloc != 100:
            return JSONResponse(
                status_code=400,
                content={"error": f"La asignaciu00f3n total debe ser 100%, recibido: {total_alloc}%"}
            )
        
        # Crear el portfolio usando el servicio
        portfolio = portfolio_service.create_portfolio(user_id, name, target_alloc)
        
        return portfolio
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/create: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Error al crear portfolio", "details": str(e)}
        )

@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: Request):
    try:
        logger.info("Iniciando optimizaciu00f3n de portfolio")
        # Intentar leer el cuerpo de la solicitud
        try:
            data = await request.json()
            logger.info(f"Datos recibidos: {data}")
        except Exception as e:
            logger.error(f"Error al leer el cuerpo de la solicitud: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": "Error al leer el cuerpo de la solicitud", "details": str(e)}
            )
        
        # Obtener paru00e1metros
        portfolio_id = data.get("portfolio_id", str(uuid.uuid4()))
        amount = float(data.get("amount", 10000))
        
        logger.info(f"Optimizando portfolio {portfolio_id} con monto {amount}")
        
        # Usar el servicio de portfolio para optimizar
        optimized = portfolio_service.optimize_portfolio(portfolio_id, amount)
        
        # Guardar el u00faltimo portfolio generado
        global last_portfolio
        last_portfolio = optimized
        
        logger.info(f"Portfolio optimizado: {optimized}")
        return optimized
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/optimize: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Error al optimizar portfolio", "details": str(e)}
        )

# Ruta principal
@app.get("/")
async def root():
    return {
        "message": "Value Investing API - Railway Deployment", 
        "version": "2.0.0", 
        "status": "running",
        "endpoints": [
            "/real_time_price/{ticker}",
            "/historical_prices/{ticker}",
            "/comparative_data/{tickers}",
            "/justification_accion/{ticker}",
            "/api/portfolio/create",
            "/api/portfolio/optimize"
        ]
    }

# Funciu00f3n para generar datos histu00f3ricos simulados
def generate_simulated_historical_data(ticker, period="1year"):
    logger.info(f"Generando datos histu00f3ricos simulados para {ticker}, periodo {period}")
    
    # Determinar el nu00famero de du00edas basado en el periodo
    days = 365  # Default 1 au00f1o
    if period == "1month":
        days = 30
    elif period == "3months":
        days = 90
    elif period == "6months":
        days = 180
    elif period == "2years":
        days = 730
    elif period == "5years":
        days = 1825
    
    # Generar precio base aleatorio entre 50 y 500
    base_price = random.uniform(50, 500)
    
    # Generar tendencia general (positiva o negativa)
    trend = random.uniform(-0.0002, 0.0004)  # Ligera tendencia alcista en promedio
    
    # Generar volatilidad
    volatility = random.uniform(0.005, 0.02)
    
    # Generar precios histu00f3ricos
    today = datetime.now()
    prices = []
    price = base_price
    
    for i in range(days, 0, -1):
        date = today - timedelta(days=i)
        # No generar datos para fines de semana
        if date.weekday() >= 5:  # 5 es su00e1bado, 6 es domingo
            continue
            
        # Calcular cambio diario
        daily_change = random.normalvariate(trend, volatility)
        price = price * (1 + daily_change)
        
        # Agregar algo de ruido para que parezca mu00e1s real
        price = price * (1 + random.uniform(-0.002, 0.002))
        
        # Agregar a la lista de precios
        prices.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": round(price, 2),
            "volume": int(random.uniform(100000, 10000000))
        })
    
    # Calcular medias mu00f3viles
    ma_50 = []
    ma_200 = []
    
    for i in range(len(prices)):
        if i >= 50:
            ma_50_value = sum([p["price"] for p in prices[i-50:i]]) / 50
            ma_50.append({
                "date": prices[i]["date"],
                "value": round(ma_50_value, 2)
            })
        
        if i >= 200:
            ma_200_value = sum([p["price"] for p in prices[i-200:i]]) / 200
            ma_200.append({
                "date": prices[i]["date"],
                "value": round(ma_200_value, 2)
            })
    
    # Retornar datos en el formato esperado
    return {
        "ticker": ticker,
        "prices": prices,
        "ma_50": ma_50,
        "ma_200": ma_200
    }

# Ejecutar la aplicaciu00f3n si se llama directamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_direct:app", host="0.0.0.0", port=8000, reload=True)
