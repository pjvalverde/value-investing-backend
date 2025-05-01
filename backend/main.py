import os
import json
import random
import logging
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Importar modelos
from backend.models.db import db
from backend.models.symbols import Symbol
from backend.models.portfolios import Portfolio

# Importar rutas
from backend.routes.screener import router as screener_router
from backend.routes.portfolio import router as portfolio_router
import pandas as pd
import markdown
import os
import requests
import json

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

# Memoria temporal para guardar el último portafolio generado por usuario (simulación)
last_portfolio = {}

# Ejemplo de universo de acciones, ETFs y T-Bills por sector (puedes expandirlo)
UNIVERSE = [
    {"ticker": "AAPL", "sector": "Tecnología", "tipo": "Acción"},
    {"ticker": "MSFT", "sector": "Tecnología", "tipo": "Acción"},
    {"ticker": "JNJ", "sector": "Salud", "tipo": "Acción"},
    {"ticker": "V", "sector": "Finanzas", "tipo": "Acción"},
    {"ticker": "JPM", "sector": "Finanzas", "tipo": "Acción"},
    {"ticker": "VOO", "sector": "ETF", "tipo": "ETF"},
    {"ticker": "QQQ", "sector": "ETF", "tipo": "ETF"},
    {"ticker": "SPY", "sector": "ETF", "tipo": "ETF"},
    {"ticker": "T-BILL", "sector": "Gobierno", "tipo": "Bono"},
]

# Simulación de métricas de value investing (en producción, usar Alpha Vantage y DeepSeek)
METRICAS = {
    "AAPL": {"ROE": 30, "P/E": 28, "Margen de Beneficio": 23, "Ratio de Deuda": 0.5, "Crecimiento de FCF": 10, "Moat Cualitativo": "Alto"},
    "MSFT": {"ROE": 35, "P/E": 32, "Margen de Beneficio": 31, "Ratio de Deuda": 0.4, "Crecimiento de FCF": 12, "Moat Cualitativo": "Alto"},
    "JNJ": {"ROE": 25, "P/E": 18, "Margen de Beneficio": 20, "Ratio de Deuda": 0.3, "Crecimiento de FCF": 8, "Moat Cualitativo": "Medio"},
    "V": {"ROE": 40, "P/E": 34, "Margen de Beneficio": 51, "Ratio de Deuda": 0.5, "Crecimiento de FCF": 15, "Moat Cualitativo": "Alto"},
    "JPM": {"ROE": 18, "P/E": 12, "Margen de Beneficio": 25, "Ratio de Deuda": 0.8, "Crecimiento de FCF": 5, "Moat Cualitativo": "Medio"},
    "VOO": {"ROE": 16, "P/E": 22, "Margen de Beneficio": 18, "Ratio de Deuda": 0.4, "Crecimiento de FCF": 7, "Moat Cualitativo": "Diversificado"},
    "QQQ": {"ROE": 18, "P/E": 25, "Margen de Beneficio": 20, "Ratio de Deuda": 0.5, "Crecimiento de FCF": 8, "Moat Cualitativo": "Diversificado"},
    "SPY": {"ROE": 15, "P/E": 21, "Margen de Beneficio": 17, "Ratio de Deuda": 0.4, "Crecimiento de FCF": 6, "Moat Cualitativo": "Diversificado"},
    "T-BILL": {"ROE": None, "P/E": None, "Margen de Beneficio": None, "Ratio de Deuda": None, "Crecimiento de FCF": None, "Moat Cualitativo": None},
}

logging.basicConfig(level=logging.INFO)

# Endpoint para generar el portafolio
@app.post("/historical_prices")
async def historical_prices(request: Request):
    params = await request.json()
    tickers = params.get("tickers", [])
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    results = {}
    for ticker in tickers:
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
            resp = requests.get(url)
            data = resp.json()
            series = data.get("Monthly Time Series", {})
            # Tomar los últimos 60 meses (5 años)
            prices = [
                {"date": k, "close": float(v["4. close"])}
                for k, v in sorted(series.items(), reverse=False)[-60:]
            ]
            results[ticker] = prices
        except Exception as e:
            logging.error(f"Error obteniendo históricos para {ticker}: {e}")
            results[ticker] = []
    return {"historical": results}

@app.post("/generate_portfolio")
async def generate_portfolio(request: Request):
    params = await request.json()
    amount = float(params.get("amount", 0))
    horizon = params.get("horizon", "largo")
    include_tbills = params.get("includeTBills", False)
    sectors = params.get("sectors", [])
    logging.info(f"Generando portafolio para monto: {amount}, sectores: {sectors}, T-Bills: {include_tbills}")
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
    for a in filtered:
        if a["ticker"] not in tickers_seen:
            filtered_unique.append(a)
            tickers_seen.add(a["ticker"])
    filtered = filtered_unique
    portfolio = []
    warnings = []
    
    # Obtener ETFs seleccionados por el usuario
    selected_etfs = params.get("etfs", [])
    
    # Filtrar por sectores seleccionados
    filtered_universe = [item for item in UNIVERSE if item["sector"] in sectors or not sectors]
    
    # Agregar ETFs específicos seleccionados por el usuario
    if selected_etfs:
        # Filtrar los ETFs que ya están en el universo filtrado
        existing_tickers = [item["ticker"] for item in filtered_universe]
        
        # Agregar los ETFs seleccionados que no estén ya en el universo
        for etf in selected_etfs:
            if etf not in existing_tickers:
                # Buscar el ETF en el universo completo
                etf_item = next((item for item in UNIVERSE if item["ticker"] == etf), None)
                
                # Si no existe en el universo, agregarlo como nuevo ETF
                if not etf_item:
                    etf_item = {"ticker": etf, "sector": "ETF", "tipo": "ETF"}
                    
                filtered_universe.append(etf_item)
                logging.info(f"ETF específico agregado: {etf}")
    
    # Incluir T-Bills si se solicita
    if include_tbills:
        tbills = [item for item in UNIVERSE if item["tipo"] == "Bono"]
        if tbills:
            filtered_universe.extend(tbills)
    
    # Si no hay suficientes opciones, advertir
    if len(filtered_universe) < 3:
        warnings.append("No hay suficientes opciones disponibles para los sectores seleccionados.")
        # Añadir algunas opciones adicionales
        additional = [item for item in UNIVERSE if item not in filtered_universe][:3]
        filtered_universe.extend(additional)
    
    # Distribuir el monto según el horizonte y tipo de activos
    if horizon == "corto":
        # Corto plazo: más conservador, más bonos
        weights = {"Acción": 0.3, "ETF": 0.3, "Bono": 0.4}
    elif horizon == "intermedio":
        # Intermedio: balanceado
        weights = {"Acción": 0.4, "ETF": 0.4, "Bono": 0.2}
    else:  # largo
        # Largo plazo: más agresivo, más acciones
        weights = {"Acción": 0.5, "ETF": 0.4, "Bono": 0.1}
    
    # Si no se incluyen bonos, redistribuir
    if not include_tbills:
        weights["Acción"] += weights["Bono"] / 2
        weights["ETF"] += weights["Bono"] / 2
        weights["Bono"] = 0
    
    # Calcular montos por tipo de activo
    amounts = {tipo: amount * weight for tipo, weight in weights.items()}
    
    # Obtener API key de Alpha Vantage
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    
    # Seleccionar activos por tipo
    for tipo, tipo_amount in amounts.items():
        if tipo_amount <= 0:
            continue
        
        # Filtrar por tipo
        tipo_assets = [item for item in filtered_universe if item["tipo"] == tipo]
        
        if not tipo_assets:
            continue
        
        # Determinar cuántos activos seleccionar
        num_assets = min(len(tipo_assets), 3 if tipo == "Acción" else 3 if tipo == "ETF" else 1)
        
        # Para ETFs, dar prioridad a los seleccionados por el usuario
        if tipo == "ETF" and selected_etfs:
            # Filtrar ETFs seleccionados por el usuario que estén en tipo_assets
            user_selected_etfs = [item for item in tipo_assets if item["ticker"] in selected_etfs]
            
            # Si hay ETFs seleccionados por el usuario, usarlos primero
            if user_selected_etfs:
                # Si hay suficientes ETFs seleccionados, usar solo esos
                if len(user_selected_etfs) >= num_assets:
                    selected = user_selected_etfs[:num_assets]
                # Si no hay suficientes, usar los seleccionados y completar con aleatorios
                else:
                    remaining = [item for item in tipo_assets if item not in user_selected_etfs]
                    remaining_needed = num_assets - len(user_selected_etfs)
                    
                    if remaining and remaining_needed > 0:
                        import random
                        selected = user_selected_etfs + random.sample(remaining, min(remaining_needed, len(remaining)))
                    else:
                        selected = user_selected_etfs
            # Si no hay ETFs seleccionados por el usuario en tipo_assets, seleccionar aleatoriamente
            else:
                import random
                selected = random.sample(tipo_assets, num_assets)
        # Para otros tipos de activos, seleccionar aleatoriamente
        else:
            import random
            selected = random.sample(tipo_assets, num_assets)
        
        # Distribuir el monto equitativamente
        asset_amount = tipo_amount / len(selected)
        
        for asset in selected:
            # Intentar obtener precio real de Alpha Vantage con reintentos
            price = None
            if ALPHAVANTAGE_API_KEY and asset["ticker"] != "T-BILL":
                # Intentar hasta 3 veces con diferentes endpoints
                for attempt in range(3):
                    try:
                        # Primer intento: GLOBAL_QUOTE
                        if attempt == 0:
                            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={asset['ticker']}&apikey={ALPHAVANTAGE_API_KEY}"
                            resp = requests.get(url, timeout=15)
                            data = resp.json()
                            
                            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                                price = float(data["Global Quote"]["05. price"])
                                logging.info(f"Precio real obtenido para {asset['ticker']} (GLOBAL_QUOTE): ${price}")
                                break
                        
                        # Segundo intento: TIME_SERIES_DAILY
                        elif attempt == 1:
                            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={asset['ticker']}&apikey={ALPHAVANTAGE_API_KEY}"
                            resp = requests.get(url, timeout=15)
                            data = resp.json()
                            
                            if "Time Series (Daily)" in data:
                                # Obtener la fecha más reciente
                                latest_date = list(data["Time Series (Daily)"].keys())[0]
                                price = float(data["Time Series (Daily)"][latest_date]["4. close"])
                                logging.info(f"Precio real obtenido para {asset['ticker']} (TIME_SERIES_DAILY): ${price}")
                                break
                        
                        # Tercer intento: Usar precios predefinidos para acciones comunes
                        else:
                            common_prices = {
                                "AAPL": 175.34,
                                "MSFT": 402.78,
                                "JNJ": 147.56,
                                "V": 275.96,
                                "JPM": 198.47,
                                "VOO": 470.15,
                                "QQQ": 438.27,
                                "SPY": 468.32
                            }
                            
                            if asset["ticker"] in common_prices:
                                price = common_prices[asset["ticker"]]
                                logging.info(f"Usando precio predefinido para {asset['ticker']}: ${price}")
                                break
                            
                        # Esperar un poco entre intentos para no sobrecargar la API
                        if attempt < 2:
                            import time
                            time.sleep(1)
                            
                    except Exception as e:
                        logging.error(f"Error en intento {attempt+1} al obtener precio para {asset['ticker']}: {e}")
                        if attempt == 2:
                            warnings.append(f"No se pudo obtener el precio de {asset['ticker']}.")
            
            # Si no se pudo obtener el precio real, usar simulación
            if price is None:
                if asset["ticker"] == "T-BILL":
                    price = 100  # Precio fijo para T-Bills
                else:
                    # Simulación más realista basada en el tipo de activo
                    if asset["tipo"] == "Acción":
                        price = random.uniform(100, 400)  # Precio más realista para acciones
                    elif asset["tipo"] == "ETF":
                        price = random.uniform(200, 500)  # Precio más realista para ETFs
                    else:
                        price = random.uniform(50, 200)
                    
                    logging.warning(f"Usando precio simulado para {asset['ticker']}: ${price:.2f}")
                    warnings.append(f"No se pudo obtener el precio de {asset['ticker']}.")
            
            cantidad = asset_amount / price
            
            # Añadir al portafolio
            portfolio_item = {
                "ticker": asset["ticker"],
                "sector": asset["sector"],
                "tipo": asset["tipo"],
                "peso": round(asset_amount / amount * 100, 2),
                "price": round(price, 2),
                "cantidad": round(cantidad, 2),
                "inversion": round(asset_amount, 2),
                "recomendacion": "Comprar"
            }
            
            # Añadir métricas de value investing si están disponibles
            if asset["ticker"] in METRICAS:
                metrics = METRICAS[asset["ticker"]]
                portfolio_item.update({
                    "ROE": metrics["ROE"],
                    "PE": metrics["P/E"],
                    "margen_beneficio": metrics["Margen de Beneficio"],
                    "ratio_deuda": metrics["Ratio de Deuda"],
                    "crecimiento_fcf": metrics["Crecimiento de FCF"],
                    "moat": metrics["Moat Cualitativo"]
                })
            
            portfolio.append(portfolio_item)
    global last_portfolio
    last_portfolio = {"portfolio": portfolio, "amount": amount, "params": params}
    logging.info(f"Portafolio generado: {portfolio}")
    result = {"status": "ok"}
    if warnings:
        result["warnings"] = warnings
    return result

# Endpoint para obtener el portafolio generado
@app.get("/portfolio")
def get_portfolio():
    if not last_portfolio:
        return JSONResponse(content={"error": "No se ha generado un portafolio aún."}, status_code=404)
    return JSONResponse(content=last_portfolio["portfolio"])

# Endpoint para obtener datos históricos de precios
@app.get("/historical_prices")
async def get_historical_prices(ticker: str, period: str = "1year"):
    if not ALPHAVANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="API key no configurada")
    
    try:
        # Determinar la función y el intervalo según el período solicitado
        if period == "1month":
            function = "TIME_SERIES_DAILY"
            key = "Time Series (Daily)"
            limit = 30  # Últimos 30 días
        elif period == "6months":
            function = "TIME_SERIES_WEEKLY"
            key = "Weekly Time Series"
            limit = 26  # Últimas 26 semanas
        else:  # 1year o default
            function = "TIME_SERIES_MONTHLY"
            key = "Monthly Time Series"
            limit = 12  # Últimos 12 meses
        
        url = f"https://www.alphavantage.co/query?function={function}&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if key not in data:
            # Intentar con datos simulados si no hay datos reales
            return generate_simulated_historical_data(ticker, period)
        
        time_series = data[key]
        dates = sorted(time_series.keys())[-limit:]  # Obtener las últimas fechas según el límite
        
        result = []
        for date in dates:
            close_price = float(time_series[date]["4. close"])
            result.append({
                "date": date,
                "price": close_price
            })
        
        return result
    
    except Exception as e:
        logging.error(f"Error al obtener datos históricos para {ticker}: {str(e)}")
        # Si hay un error, devolver datos simulados
        return generate_simulated_historical_data(ticker, period)

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
@app.get("/comparative_data")
async def get_comparative_data(tickers: str):
    ticker_list = tickers.split(",")
    result = []
    
    for ticker in ticker_list:
        try:
            # Intentar obtener datos fundamentales de Alpha Vantage
            if ALPHAVANTAGE_API_KEY:
                url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
                response = requests.get(url, timeout=15)
                data = response.json()
                
                if "Symbol" in data:
                    # Extraer métricas fundamentales
                    company_data = {
                        "company": data.get("Name", ticker),
                        "ROE": float(data.get("ReturnOnEquityTTM", "0")) * 100 if data.get("ReturnOnEquityTTM") else None,
                        "P/E": float(data.get("PERatio", "0")) if data.get("PERatio") else None,
                        "Margen de Beneficio": f"{float(data.get('ProfitMargin', '0')) * 100:.1f}%" if data.get("ProfitMargin") else None,
                        "Ratio de Deuda": data.get("DebtToEquityRatio", None),
                        "Crecimiento de FCF": None,  # No disponible directamente en Alpha Vantage
                        "Moat Cualitativo": None  # Requiere análisis cualitativo
                    }
                    
                    result.append(company_data)
                    continue
            
            # Si no se pueden obtener datos reales, usar datos de METRICAS si están disponibles
            if ticker in METRICAS:
                metrics = METRICAS[ticker]
                company_data = {
                    "company": ticker,
                    "ROE": metrics["ROE"],
                    "P/E": metrics["P/E"],
                    "Margen de Beneficio": metrics["Margen de Beneficio"],
                    "Ratio de Deuda": metrics["Ratio de Deuda"],
                    "Crecimiento de FCF": metrics["Crecimiento de FCF"],
                    "Moat Cualitativo": metrics["Moat Cualitativo"]
                }
                result.append(company_data)
                continue
            
            # Si no hay datos disponibles, generar datos simulados
            company_data = {
                "company": ticker,
                "ROE": round(random.uniform(5, 25), 1),
                "P/E": round(random.uniform(10, 30), 1),
                "Margen de Beneficio": f"{random.uniform(5, 30):.1f}%",
                "Ratio de Deuda": f"{random.uniform(0.1, 0.8):.1f}",
                "Crecimiento de FCF": f"{random.uniform(3, 15):.1f}%",
                "Moat Cualitativo": random.choice(["Alto", "Medio", "Bajo"])
            }
            result.append(company_data)
            
        except Exception as e:
            logging.error(f"Error al obtener datos comparativos para {ticker}: {str(e)}")
            # En caso de error, agregar datos simulados
            result.append({
                "company": ticker,
                "ROE": round(random.uniform(5, 25), 1),
                "P/E": round(random.uniform(10, 30), 1),
                "Margen de Beneficio": f"{random.uniform(5, 30):.1f}%",
                "Ratio de Deuda": f"{random.uniform(0.1, 0.8):.1f}",
                "Crecimiento de FCF": f"{random.uniform(3, 15):.1f}%",
                "Moat Cualitativo": random.choice(["Alto", "Medio", "Bajo"])
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

@app.get("/justification/accion")
async def justification_accion(ticker: str):
    import os
    import requests
    global last_portfolio
    if not last_portfolio or "portfolio" not in last_portfolio:
        return JSONResponse(content={"error": "Primero genera un portafolio."}, status_code=400)
    portfolio = last_portfolio["portfolio"]
    tickers = [a["ticker"] for a in portfolio if a["tipo"] in ["Acción", "ETF"]]
    # Obtener el análisis general primero
    prompt_general = (
        "Eres un analista de inversiones. Explica de manera detallada por qué las siguientes acciones y ETFs fueron seleccionados para el portafolio de un inversionista considerando su sector, peso, métricas clave y contexto de mercado. Hazlo en español y sé específico para cada ticker: " + ", ".join(tickers)
    )
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    data_general = {
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 1200,
        "temperature": 0.7,
        "messages": [
            {"role": "user", "content": prompt_general}
        ]
    }
    try:
        resp_general = requests.post(url, headers=headers, json=data_general, timeout=60)
        resp_general.raise_for_status()
        result_general = resp_general.json()
        analysis_general = ""
        if "content" in result_general and result_general["content"]:
            analysis_general = result_general["content"][0]["text"]
        if not analysis_general or len(analysis_general.strip()) < 10:
            return JSONResponse(content={"error": "Claude no devolvió análisis general."}, status_code=500)
        # Ahora pedirle a Claude que extraiga SOLO el fragmento para el ticker
        prompt_extract = (
            f"Del siguiente análisis de portafolio, extrae y devuelve únicamente el análisis detallado correspondiente a la acción o ETF con ticker '{ticker}'. Si no existe, responde 'No hay análisis para este ticker'.\n\nAnálisis completo:\n" + analysis_general + f"\n\nDevuelve solo el análisis de {ticker}, en HTML resaltando en amarillo el bloque principal."
        )
        data_extract = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 600,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": prompt_extract}
            ]
        }
        resp_extract = requests.post(url, headers=headers, json=data_extract, timeout=60)
        resp_extract.raise_for_status()
        result_extract = resp_extract.json()
        fragment = ""
        if "content" in result_extract and result_extract["content"]:
            fragment = result_extract["content"][0]["text"]
        if not fragment or len(fragment.strip()) < 10:
            return JSONResponse(content={"error": "Claude no devolvió análisis individual."}, status_code=500)
        return {"analysis": fragment}
    except Exception as e:
        logging.error(f"Error al obtener análisis individual de Claude: {e}")
        return JSONResponse(content={"error": f"Error al obtener análisis individual: {str(e)}"}, status_code=500)

@app.get("/visualizations/{img_name}")
def get_visualization(img_name: str):
    img_path = os.path.join(RESULTS_DIR, img_name)
    if not os.path.exists(img_path):
        return JSONResponse(content={"error": "Visualization not found"}, status_code=404)
    return FileResponse(img_path)

@app.get("/real_time_price")
async def real_time_price(ticker: str):
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    if not ALPHAVANTAGE_API_KEY:
        return JSONResponse(content={"error": "Alpha Vantage API key no configurada"}, status_code=500)
    
    # Precios predefinidos para acciones comunes (como fallback)
    common_prices = {
        "AAPL": 175.34,
        "MSFT": 402.78,
        "JNJ": 147.56,
        "V": 275.96,
        "JPM": 198.47,
        "VOO": 470.15,
        "QQQ": 438.27,
        "SPY": 468.32,
        "T-BILL": 100.00
    }
    
    # Intentar hasta 3 veces con diferentes endpoints
    for attempt in range(3):
        try:
            # Primer intento: GLOBAL_QUOTE
            if attempt == 0:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
                resp = requests.get(url, timeout=15)
                data = resp.json()
                
                if "Global Quote" in data and "05. price" in data["Global Quote"]:
                    price = float(data["Global Quote"]["05. price"])
                    logging.info(f"Precio real obtenido para {ticker} (GLOBAL_QUOTE): ${price}")
                    return {"ticker": ticker, "price": price, "source": "GLOBAL_QUOTE"}
            
            # Segundo intento: TIME_SERIES_DAILY
            elif attempt == 1:
                url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
                resp = requests.get(url, timeout=15)
                data = resp.json()
                
                if "Time Series (Daily)" in data:
                    # Obtener la fecha más reciente
                    latest_date = list(data["Time Series (Daily)"].keys())[0]
                    price = float(data["Time Series (Daily)"][latest_date]["4. close"])
                    logging.info(f"Precio real obtenido para {ticker} (TIME_SERIES_DAILY): ${price}")
                    return {"ticker": ticker, "price": price, "source": "TIME_SERIES_DAILY"}
            
            # Tercer intento: Usar precios predefinidos
            elif attempt == 2 and ticker in common_prices:
                price = common_prices[ticker]
                logging.info(f"Usando precio predefinido para {ticker}: ${price}")
                return {"ticker": ticker, "price": price, "source": "PREDEFINED"}
            
            # Esperar un poco entre intentos para no sobrecargar la API
            if attempt < 2:
                import time
                time.sleep(1)
                
        except Exception as e:
            logging.error(f"Error en intento {attempt+1} al obtener precio para {ticker}: {e}")
            if attempt == 2:
                # Si llegamos al último intento y sigue fallando, intentar usar precio predefinido
                if ticker in common_prices:
                    price = common_prices[ticker]
                    logging.warning(f"Usando precio predefinido después de errores para {ticker}: ${price}")
                    return {"ticker": ticker, "price": price, "source": "PREDEFINED_AFTER_ERROR"}
    
    # Si todo falla, usar simulación
    import random
    if ticker.startswith("T-"):
        # Para bonos del tesoro
        simulated_price = 100.00
    elif any(etf in ticker for etf in ["VOO", "SPY", "QQQ", "VTI"]):
        # Para ETFs
        simulated_price = random.uniform(200, 500)
    else:
        # Para acciones
        simulated_price = random.uniform(100, 400)
    
    logging.warning(f"Usando precio totalmente simulado para {ticker}: ${simulated_price:.2f}")
    return {"ticker": ticker, "price": round(simulated_price, 2), "simulated": True}

@app.get("/")
def root():
    return {"message": "API VIVA - TEST 2025-04-29"}
