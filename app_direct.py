# Aplicaciu00f3n FastAPI completamente independiente sin importaciones externas
import os
import sys
import uvicorn
import logging
import json
import uuid
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Importar FastAPI y componentes necesarios
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Crear la aplicaciu00f3n FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Permitir acceso desde el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Rutas para el screener
@app.get("/api/screener/value")
async def get_value_screener(min_pe: float = 0, max_pe: float = 15, region: str = "US,EU"):
    try:
        # Filtrar stocks por PE si se proporciona
        stocks = [stock for stock in VALUE_STOCKS if min_pe <= stock["forward_pe"] <= max_pe]
        return {"stocks": stocks}
    except Exception as e:
        logging.error(f"Error en endpoint /api/screener/value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/growth")
async def get_growth_screener(min_growth: float = 0.20, region: str = "US,EU"):
    try:
        # Filtrar stocks por crecimiento si se proporciona
        stocks = [stock for stock in GROWTH_STOCKS if stock["yoy_rev_growth"] >= min_growth]
        return {"stocks": stocks}
    except Exception as e:
        logging.error(f"Error en endpoint /api/screener/growth: {str(e)}")
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
        logging.error(f"Error en endpoint /api/portfolio/create: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: Request):
    try:
        data = await request.json()
        portfolio_id = data.get("portfolio_id", str(uuid.uuid4()))
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        amount = data.get("amount", 10000)
        
        # Calcular la asignaciu00f3n de activos
        value_allocation = target_alloc.get("value", 0) / 100
        growth_allocation = target_alloc.get("growth", 0) / 100
        bonds_allocation = target_alloc.get("bonds", 0) / 100
        
        # Seleccionar stocks para cada categoru00eda
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
        
        return optimized
    except Exception as e:
        logging.error(f"Error en endpoint /api/portfolio/optimize: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Ruta rau00edz
@app.get("/")
def root():
    return {"message": "Value Investing API - Versiu00f3n 2.0"}

# Ejecutar la aplicaciu00f3n si se llama directamente
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app_direct:app", host="0.0.0.0", port=port)
