# Archivo independiente para ejecutar la aplicaciu00f3n FastAPI sin problemas de importaciu00f3n
import os
import sys
import uvicorn
import logging
import json
import uuid
from datetime import datetime, timedelta
import pandas as pd
import markdown
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

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

# Clase Database simplificada
class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            # Obtener la URL de conexiu00f3n de las variables de entorno
            db_url = os.getenv('DATABASE_URL')
            
            if not db_url:
                logging.warning("DATABASE_URL no estu00e1 configurada. Usando base de datos en memoria.")
                # Si no hay URL de base de datos, usamos una simulaciu00f3n en memoria
                self.conn = None
                return
            
            # Aquu00ed iru00eda la conexiu00f3n real a la base de datos
            logging.info("Conexiu00f3n a la base de datos establecida correctamente")
            
        except Exception as e:
            logging.error(f"Error al conectar a la base de datos: {str(e)}")
            self.conn = None
    
    def query(self, sql, params=None):
        if not self.conn:
            # Simulaciu00f3n en memoria para desarrollo
            if "symbols" in sql.lower() and "strategy" in sql.lower():
                return self.mock_symbols_query(sql)
            return {"rows": []}
        
        # Aquu00ed iru00eda la consulta real a la base de datos
        return {"rows": []}
    
    def mock_symbols_query(self, sql):
        # Datos simulados para desarrollo sin base de datos
        if "strategy = 'value'" in sql.lower():
            return {
                "rows": [
                    {"ticker": "AAPL", "name": "Apple Inc.", "price": 175.50, "forward_pe": 25.3, "yoy_rev_growth": 0.12},
                    {"ticker": "MSFT", "name": "Microsoft Corp.", "price": 325.20, "forward_pe": 28.1, "yoy_rev_growth": 0.15},
                    {"ticker": "JNJ", "name": "Johnson & Johnson", "price": 152.75, "forward_pe": 15.2, "yoy_rev_growth": 0.08},
                    {"ticker": "PG", "name": "Procter & Gamble", "price": 145.30, "forward_pe": 22.5, "yoy_rev_growth": 0.05},
                    {"ticker": "JPM", "name": "JPMorgan Chase", "price": 138.40, "forward_pe": 12.3, "yoy_rev_growth": 0.10}
                ]
            }
        elif "strategy = 'growth'" in sql.lower():
            return {
                "rows": [
                    {"ticker": "NVDA", "name": "NVIDIA Corp.", "price": 450.80, "forward_pe": 45.2, "yoy_rev_growth": 0.35},
                    {"ticker": "TSLA", "name": "Tesla Inc.", "price": 220.50, "forward_pe": 60.5, "yoy_rev_growth": 0.28},
                    {"ticker": "AMZN", "name": "Amazon.com Inc.", "price": 178.30, "forward_pe": 38.7, "yoy_rev_growth": 0.22},
                    {"ticker": "GOOGL", "name": "Alphabet Inc.", "price": 142.60, "forward_pe": 22.1, "yoy_rev_growth": 0.18},
                    {"ticker": "META", "name": "Meta Platforms", "price": 480.25, "forward_pe": 24.3, "yoy_rev_growth": 0.25}
                ]
            }
        else:
            return {"rows": []}

# Instancia global de la base de datos
db = Database()

# Clase Symbol simplificada
class Symbol:
    @staticmethod
    def get_value_screener(min_pe=0, max_pe=15, region="US,EU"):
        try:
            query = "SELECT * FROM fundamentals f JOIN symbols s ON f.ticker = s.ticker WHERE s.strategy = 'value'"
            result = db.query(query)
            return result["rows"]
        except Exception as e:
            logging.error(f"Error en get_value_screener: {str(e)}")
            return []
    
    @staticmethod
    def get_growth_screener(min_growth=0.20, region="US,EU"):
        try:
            query = "SELECT * FROM fundamentals f JOIN symbols s ON f.ticker = s.ticker WHERE s.strategy = 'growth'"
            result = db.query(query)
            return result["rows"]
        except Exception as e:
            logging.error(f"Error en get_growth_screener: {str(e)}")
            return []

# Clase Portfolio simplificada
class Portfolio:
    @staticmethod
    def create_portfolio(user_id, name, target_alloc):
        try:
            portfolio_id = str(uuid.uuid4())
            # Aquu00ed iru00eda la creaciu00f3n real del portfolio en la base de datos
            return {"id": portfolio_id, "name": name, "user_id": user_id, "target_alloc": target_alloc}
        except Exception as e:
            logging.error(f"Error en create_portfolio: {str(e)}")
            return None
    
    @staticmethod
    def optimize_portfolio(portfolio_id, target_alloc):
        try:
            # Simulaciu00f3n de optimizaciu00f3n de portfolio
            value_stocks = Symbol.get_value_screener()
            growth_stocks = Symbol.get_growth_screener()
            
            # Seleccionar stocks para cada categoru00eda
            value_allocation = target_alloc.get("value", 0)
            growth_allocation = target_alloc.get("growth", 0)
            bonds_allocation = target_alloc.get("bonds", 0)
            
            # Crear portfolio optimizado
            optimized = {
                "id": portfolio_id,
                "allocation": {
                    "value": [
                        {"ticker": stock["ticker"], "name": stock["name"], "weight": value_allocation / len(value_stocks) if value_stocks else 0}
                        for stock in value_stocks[:3]  # Limitar a 3 stocks para simplificar
                    ],
                    "growth": [
                        {"ticker": stock["ticker"], "name": stock["name"], "weight": growth_allocation / len(growth_stocks) if growth_stocks else 0}
                        for stock in growth_stocks[:3]  # Limitar a 3 stocks para simplificar
                    ],
                    "bonds": [
                        {"ticker": "AGG", "name": "iShares Core U.S. Aggregate Bond ETF", "weight": bonds_allocation}
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
            logging.error(f"Error en optimize_portfolio: {str(e)}")
            return None

# Rutas para el screener
@app.get("/api/screener/value")
async def get_value_screener(min_pe: float = 0, max_pe: float = 15, region: str = "US,EU"):
    try:
        stocks = Symbol.get_value_screener(min_pe, max_pe, region)
        return {"stocks": stocks}
    except Exception as e:
        logging.error(f"Error en endpoint /api/screener/value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/screener/growth")
async def get_growth_screener(min_growth: float = 0.20, region: str = "US,EU"):
    try:
        stocks = Symbol.get_growth_screener(min_growth, region)
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
        
        portfolio = Portfolio.create_portfolio(user_id, name, target_alloc)
        if not portfolio:
            raise HTTPException(status_code=500, detail="Error al crear el portfolio")
        
        return portfolio
    except Exception as e:
        logging.error(f"Error en endpoint /api/portfolio/create: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: Request):
    try:
        data = await request.json()
        portfolio_id = data.get("portfolio_id", str(uuid.uuid4()))
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        
        optimized = Portfolio.optimize_portfolio(portfolio_id, target_alloc)
        if not optimized:
            raise HTTPException(status_code=500, detail="Error al optimizar el portfolio")
        
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
    uvicorn.run("app_standalone:app", host="0.0.0.0", port=8000, reload=True)
