import logging
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
import markdown
import os
import requests
import json

app = FastAPI()

# Permitir acceso desde el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    n = len(filtered)
    if n == 0:
        logging.error("No hay activos en los sectores seleccionados.")
        return JSONResponse(content={"error": "No hay activos en los sectores seleccionados."}, status_code=400)
    # Pesos según horizonte y T-Bills
    weights = {}
    if include_tbills and any(a["ticker"] == "T-BILL" for a in filtered):
        if horizon == "corto":
            for a in filtered:
                weights[a["ticker"]] = 0.3 if a["ticker"] == "T-BILL" else (0.7/(n-1) if n > 1 else 0.0)
        elif horizon == "intermedio":
            for a in filtered:
                weights[a["ticker"]] = 0.15 if a["ticker"] == "T-BILL" else (0.85/(n-1) if n > 1 else 0.0)
        else:
            for a in filtered:
                weights[a["ticker"]] = 1.0/n
    else:
        for a in filtered:
            weights[a["ticker"]] = 1.0/n
    # Distribuir monto: intentar que todos tengan al menos 1 unidad si el monto lo permite
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
    precios = {}
    for a in filtered:
        ticker = a["ticker"]
        if ticker != "T-BILL":
            try:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHAVANTAGE_API_KEY}"
                resp = requests.get(url)
                data = resp.json()
                price_str = data.get("Global Quote", {}).get("05. price", None)
                precios[ticker] = float(price_str) if price_str else None
            except Exception as e:
                precios[ticker] = None
        else:
            precios[ticker] = None
    # Cálculo de cantidades e inversión total
    portfolio = []
    monto_restante = amount
    for a in filtered:
        ticker = a["ticker"]
        peso = weights[ticker]
        tipo = a["tipo"]
        sector = a["sector"]
        metricas = METRICAS.get(ticker, {})
        price = precios[ticker]
        monto_asignado = amount * peso
        cantidad = 0
        inversion = 0
        if ticker != "T-BILL" and price:
            # Si el monto asignado alcanza para 1 unidad, asigna al menos 1
            if monto_asignado >= price:
                cantidad = int(monto_asignado // price)
                inversion = round(cantidad * price, 2)
                monto_restante -= inversion
            else:
                # Si el monto total restante alcanza para al menos 1, asigna 1
                if monto_restante >= price:
                    cantidad = 1
                    inversion = round(price, 2)
                    monto_restante -= price
                else:
                    cantidad = 0
                    inversion = 0
        elif ticker == "T-BILL":
            inversion = round(monto_restante, 2) if a == filtered[-1] else round(monto_asignado, 2)
            monto_restante -= inversion
        portfolio.append({
            "ticker": ticker,
            "sector": sector,
            "peso": round(peso*100, 2),
            "tipo": tipo,
            "price": price,
            "cantidad": cantidad,
            "inversion": inversion if inversion > 0 else round(monto_asignado, 2),
            "recomendacion": "Comprar" if tipo in ["Acción", "ETF"] else "Mantener",
            **metricas
        })
    global last_portfolio
    last_portfolio = {"portfolio": portfolio, "amount": amount, "params": params}
    logging.info(f"Portafolio generado: {portfolio}")
    return {"status": "ok"}

# Endpoint para obtener el portafolio generado
@app.get("/portfolio")
def get_portfolio():
    if not last_portfolio:
        return JSONResponse(content={"error": "No se ha generado un portafolio aún."}, status_code=404)
    return JSONResponse(content=last_portfolio["portfolio"])

# Endpoint para obtener la justificación (Claude API)
@app.get("/justification")
async def justification():
    import os
    import requests
    # Usar el último portafolio generado
    global last_portfolio
    if not last_portfolio or "portfolio" not in last_portfolio:
        return JSONResponse(content={"error": "Primero genera un portafolio."}, status_code=400)
    portfolio = last_portfolio["portfolio"]
    tickers = [a["ticker"] for a in portfolio if a["tipo"] in ["Acción", "ETF"]]
    # Preparar prompt para Claude
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
        "model": "claude-3-sonnet-20240229",
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
        content = result["content"][0]["text"] if "content" in result and result["content"] else ""
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

# Endpoint para obtener visualizaciones (imágenes generadas por Python)
@app.get("/visualizations/{img_name}")
def get_visualization(img_name: str):
    img_path = os.path.join(RESULTS_DIR, img_name)
    if not os.path.exists(img_path):
        return JSONResponse(content={"error": "Visualization not found"}, status_code=404)
    return FileResponse(img_path)

@app.get("/")
def root():
    return {"message": "API VIVA - TEST 2025-04-29"}
