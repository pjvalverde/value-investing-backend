# Aplicaciu00f3n FastAPI completamente independiente sin importaciones externas
import os
import json
import random
import logging
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("value-investing-api")

# Crear la aplicaciu00f3n FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Permitir acceso desde el frontend React - Configuración explícita de CORS
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
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Solicitud recibida: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"[{request_id}] Respuesta enviada: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"[{request_id}] Error en solicitud: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# Datos simulados para desarrollo
VALUE_STOCKS = [
    {"ticker": "AAPL", "name": "Apple Inc.", "price": 175.50, "forward_pe": 25.3, "yoy_rev_growth": 0.12},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "price": 325.20, "forward_pe": 28.1, "yoy_rev_growth": 0.15},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "price": 152.75, "forward_pe": 15.2, "yoy_rev_growth": 0.08},
    {"ticker": "PG", "name": "Procter & Gamble", "price": 145.30, "forward_pe": 22.5, "yoy_rev_growth": 0.05},
    {"ticker": "JPM", "name": "JPMorgan Chase", "price": 138.40, "forward_pe": 12.3, "yoy_rev_growth": 0.10}
]

GROWTH_STOCKS = [
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "price": 450.80, "forward_pe": 45.2, "yoy_rev_growth": 0.35},
    {"ticker": "TSLA", "name": "Tesla Inc.", "price": 220.50, "forward_pe": 60.5, "yoy_rev_growth": 0.28},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "price": 178.30, "forward_pe": 38.7, "yoy_rev_growth": 0.22},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "price": 142.60, "forward_pe": 22.1, "yoy_rev_growth": 0.18},
    {"ticker": "META", "name": "Meta Platforms", "price": 480.25, "forward_pe": 24.3, "yoy_rev_growth": 0.25}
]

# Métricas simuladas para acciones
METRICAS = {
    "AAPL": {"ROE": 30, "P/E": 28, "Margen de Beneficio": 23, "Ratio de Deuda": 0.5, "Crecimiento de FCF": 10, "Moat Cualitativo": "Alto"},
    "MSFT": {"ROE": 35, "P/E": 32, "Margen de Beneficio": 31, "Ratio de Deuda": 0.4, "Crecimiento de FCF": 12, "Moat Cualitativo": "Alto"},
    "JNJ": {"ROE": 25, "P/E": 18, "Margen de Beneficio": 20, "Ratio de Deuda": 0.3, "Crecimiento de FCF": 8, "Moat Cualitativo": "Medio"},
    "NVDA": {"ROE": 42, "P/E": 45, "Margen de Beneficio": 35, "Ratio de Deuda": 0.3, "Crecimiento de FCF": 25, "Moat Cualitativo": "Alto"},
    "TSLA": {"ROE": 38, "P/E": 60, "Margen de Beneficio": 15, "Ratio de Deuda": 0.6, "Crecimiento de FCF": 30, "Moat Cualitativo": "Medio"},
}

# Rutas para el screener
@app.get("/api/screener/value")
async def get_value_screener(min_pe: float = 0, max_pe: float = 30, region: str = "US,EU"):
    try:
        # Filtrar stocks por PE si se proporciona
        stocks = [stock for stock in VALUE_STOCKS if min_pe <= stock["forward_pe"] <= max_pe]
        return {"stocks": stocks}
    except Exception as e:
        logger.error(f"Error en endpoint /api/screener/value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/growth")
async def get_growth_screener(min_growth: float = 0.20, region: str = "US,EU"):
    try:
        # Filtrar stocks por crecimiento si se proporciona
        stocks = [stock for stock in GROWTH_STOCKS if stock["yoy_rev_growth"] >= min_growth]
        return {"stocks": stocks}
    except Exception as e:
        logger.error(f"Error en endpoint /api/screener/growth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Rutas para portfolios
@app.post("/api/portfolio/create")
async def create_portfolio(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id", str(uuid.uuid4()))
        name = data.get("name", "Mi Portfolio")
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        
        portfolio_id = str(uuid.uuid4())
        
        return {
            "id": portfolio_id,
            "name": name,
            "user_id": user_id,
            "target_alloc": target_alloc,
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/create: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: Request):
    try:
        logger.info("Iniciando optimización de portfolio")
        # Intentar leer el cuerpo de la solicitud
        try:
            body = await request.body()
            logger.info(f"Cuerpo de la solicitud: {body}")
            data = await request.json()
            logger.info(f"Datos recibidos: {data}")
        except Exception as e:
            logger.error(f"Error al leer el cuerpo de la solicitud: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": "Error al leer el cuerpo de la solicitud", "details": str(e)}
            )
        
        portfolio_id = data.get("portfolio_id", str(uuid.uuid4()))
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        amount = data.get("amount", 10000)
        
        logger.info(f"Optimizando portfolio {portfolio_id} con asignación {target_alloc} y monto {amount}")

        # Calcular la asignación de activos
        value_allocation = target_alloc.get("value", 0) / 100
        growth_allocation = target_alloc.get("growth", 0) / 100
        bonds_allocation = target_alloc.get("bonds", 0) / 100
        
        # Seleccionar stocks para cada categoría
        value_stocks = VALUE_STOCKS[:3]  # Tomar los primeros 3 para simplificar
        growth_stocks = GROWTH_STOCKS[:3]  # Tomar los primeros 3 para simplificar
        
        # Calcular pesos y cantidades
        value_weight_per_stock = value_allocation / len(value_stocks) if value_stocks else 0
        growth_weight_per_stock = growth_allocation / len(growth_stocks) if growth_stocks else 0
        
        # Crear portfolio optimizado
        optimized = {
            "id": portfolio_id,
            "allocation": {
                "value": [
                    {
                        "ticker": stock["ticker"],
                        "name": stock["name"],
                        "weight": value_weight_per_stock,
                        "amount": round(amount * value_weight_per_stock, 2),
                        "shares": round(amount * value_weight_per_stock / stock["price"])
                    }
                    for stock in value_stocks
                ],
                "growth": [
                    {
                        "ticker": stock["ticker"],
                        "name": stock["name"],
                        "weight": growth_weight_per_stock,
                        "amount": round(amount * growth_weight_per_stock, 2),
                        "shares": round(amount * growth_weight_per_stock / stock["price"])
                    }
                    for stock in growth_stocks
                ],
                "bonds": [
                    {
                        "ticker": "AGG",
                        "name": "iShares Core U.S. Aggregate Bond ETF",
                        "weight": bonds_allocation,
                        "amount": round(amount * bonds_allocation, 2),
                        "shares": round(amount * bonds_allocation / 100)  # Precio simulado de AGG
                    }
                ]
            },
            "metrics": {
                "expected_return": 0.08,
                "volatility": 0.12,
                "sharpe_ratio": 0.67
            }
        }
        
        logger.info(f"Portfolio optimizado: {optimized}")
        return optimized
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/optimize: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Error al optimizar portfolio", "details": str(e)}
        )

@app.get("/api/portfolio/metrics/{ticker}")
async def get_stock_metrics(ticker: str):
    try:
        if ticker in METRICAS:
            return {"ticker": ticker, "metrics": METRICAS[ticker]}
        else:
            # Generar métricas aleatorias para tickers no conocidos
            random_metrics = {
                "ROE": round(random.uniform(10, 40), 1),
                "P/E": round(random.uniform(10, 50), 1),
                "Margen de Beneficio": round(random.uniform(5, 40), 1),
                "Ratio de Deuda": round(random.uniform(0.1, 0.9), 2),
                "Crecimiento de FCF": round(random.uniform(5, 30), 1),
                "Moat Cualitativo": random.choice(["Bajo", "Medio", "Alto"])
            }
            return {"ticker": ticker, "metrics": random_metrics, "simulated": True}
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/metrics/{ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/price/{ticker}")
async def get_stock_price(ticker: str):
    try:
        # Buscar en VALUE_STOCKS
        for stock in VALUE_STOCKS:
            if stock["ticker"] == ticker:
                return {"ticker": ticker, "price": stock["price"]}
        
        # Buscar en GROWTH_STOCKS
        for stock in GROWTH_STOCKS:
            if stock["ticker"] == ticker:
                return {"ticker": ticker, "price": stock["price"]}
        
        # Si no se encuentra, generar un precio aleatorio
        if ticker == "AGG":
            price = 100.0  # Precio fijo para el ETF de bonos
        else:
            price = round(random.uniform(50, 500), 2)
        
        return {"ticker": ticker, "price": price, "simulated": True}
    except Exception as e:
        logger.error(f"Error en endpoint /api/stock/price/{ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Rutas de prueba
@app.get("/")
def root():
    return {"message": "Value Investing API - Versión 2.0"}

@app.get("/test")
def test():
    logger.info("Ruta de prueba accedida")
    return {"status": "ok", "message": "API funcionando correctamente"}

@app.get("/api/test")
def api_test():
    logger.info("Ruta de prueba API accedida")
    return {"status": "ok", "data": {"value_stocks": len(VALUE_STOCKS), "growth_stocks": len(GROWTH_STOCKS)}}

# Ejecutar la aplicación si se llama directamente
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port)
