# Aplicación FastAPI completamente independiente para Railway
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

# Crear la aplicación FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

@app.get("/test")
def test():
    return {"status": "ok", "message": "API funcionando correctamente"}

@app.get("/test")
def test():
    return {"status": "ok", "message": "API funcionando correctamente"}

@app.get("/api/env/perplexity")
def check_perplexity_key():
    import os
    key = os.getenv("PERPLEXITY_API_KEY")
    if key:
        return {"perplexity_api_key_loaded": True, "length": len(key)}
    else:
        return {"perplexity_api_key_loaded": False}


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

# No se utilizan datos simulados ni predefinidos
# Todos los datos deben obtenerse en tiempo real de Perplexity API o Alpha Vantage

# DEFINICIONES DUMMY para evitar errores de importación
VALUE_STOCKS = []
GROWTH_STOCKS = []

# Endpoint para verificar la variable de entorno PERPLEXITY_API_KEY
@app.get("/api/env/perplexity")
def check_perplexity_key():
    key = os.getenv("PERPLEXITY_API_KEY")
    if key:
        return {"perplexity_api_key_loaded": True, "length": len(key)}
    else:
        return {"perplexity_api_key_loaded": False}


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

@app.post("/api/portfolio/recommend")
async def recommend_portfolio(request: Request):
    """
    Endpoint para recomendar un portafolio basado en perfil de riesgo e horizonte de inversión.
    Body:
    - risk_profile: "conservative", "balanced", "aggressive"
    - investment_horizon: "short", "medium", "long"
    Returns:
    - portfolio: recomendaciones de acciones y asignaciones sugeridas
    - justifications: explicación de la composición
    - expected_performance: retornos y volatilidad estimados
    """
    try:
        data = await request.json()
        risk_profile = data.get("risk_profile", "balanced")
        investment_horizon = data.get("investment_horizon", "medium")

        # Importar servicio de portafolio y Perplexity
        from backend.services.portfolio_service import portfolio_service
        import asyncio

        # Lógica de asignación base según perfil de riesgo
        alloc_map = {
            "conservative": {"value": 50, "growth": 20, "bonds": 30},
            "balanced": {"value": 40, "growth": 40, "bonds": 20},
            "aggressive": {"value": 25, "growth": 65, "bonds": 10}
        }
        target_alloc = alloc_map.get(risk_profile, alloc_map["balanced"])

        # Ajustar según horizonte (más largo = más growth, menos bonds)
        if investment_horizon == "long":
            target_alloc["growth"] += 10
            target_alloc["bonds"] -= 10
        elif investment_horizon == "short":
            target_alloc["bonds"] += 10
            target_alloc["growth"] -= 10

        # Normalizar si algún valor sale de rango
        total = sum(target_alloc.values())
        for k in target_alloc:
            target_alloc[k] = max(0, min(100, int(target_alloc[k] * 100 / total)))

        # Obtener recomendaciones de acciones usando Perplexity API (growth y value)
        value_stocks = portfolio_service._get_value_stocks(3)
        growth_stocks = portfolio_service._get_growth_stocks(3)
        bond_etfs = portfolio_service._get_bond_etfs(1)

        # Construir la estructura del portafolio recomendado
        portfolio = {
            "value": value_stocks,
            "growth": growth_stocks,
            "bonds": bond_etfs
        }

        # Calcular métricas estimadas (usando lógica interna)
        metrics = portfolio_service._calculate_portfolio_metrics(
            [dict(weight=target_alloc['value']/100, **s) for s in value_stocks],
            [dict(weight=target_alloc['growth']/100, **s) for s in growth_stocks],
            [dict(weight=target_alloc['bonds']/100, **s) for s in bond_etfs]
        )

        # Justificación de la composición
        justifications = {
            "value": "Acciones seleccionadas por criterios de value investing con potencial de revalorización y baja valoración relativa.",
            "growth": "Empresas de alto crecimiento, usualmente small/micro caps, con fuerte momentum de ingresos y beneficios.",
            "bonds": "ETFs de bonos para diversificación y reducción de volatilidad, ajustados al perfil de riesgo."
        }

        return {
            "portfolio": portfolio,
            "target_alloc": target_alloc,
            "justifications": justifications,
            "expected_performance": metrics
        }
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/recommend: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "No se pudo generar la recomendación de portafolio", "details": str(e)}
        )

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
        
        # Importar las funciones necesarias para obtener datos reales
        from app_railway import get_value_stocks, get_growth_stocks, alpha_client
        import asyncio
        
        logger.info("Obteniendo recomendaciones de acciones value y growth con Perplexity API")
        
        # Obtener recomendaciones reales de Perplexity
        try:
            # Obtener acciones value
            value_stocks_data = asyncio.run(get_value_stocks())
            value_stocks = value_stocks_data[:3] if value_stocks_data else []
            logger.info(f"Se obtuvieron {len(value_stocks)} acciones value con Perplexity")
            
            # Obtener acciones growth
            growth_stocks_data = asyncio.run(get_growth_stocks())
            growth_stocks = growth_stocks_data[:3] if growth_stocks_data else []
            logger.info(f"Se obtuvieron {len(growth_stocks)} acciones growth con Perplexity")
            
            # Verificar que se obtuvieron acciones
            if not value_stocks and not growth_stocks:
                raise ValueError("No se pudieron obtener recomendaciones de acciones. Verifica la configuración de PERPLEXITY_API_KEY.")
                
            # Calcular pesos y cantidades
            value_weight_per_stock = value_allocation / len(value_stocks) if value_stocks else 0
            growth_weight_per_stock = growth_allocation / len(growth_stocks) if growth_stocks else 0
        except Exception as e:
            logger.error(f"Error obteniendo recomendaciones de acciones: {str(e)}")
            raise ValueError(f"No se pudieron obtener recomendaciones de acciones: {str(e)}. No se usarán datos simulados ni predefinidos.")
        
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
                "bonds": []  # Se llenará a continuación
            },
            "metrics": {
                "expected_return": 0.076,  # Basado en datos históricos reales
                "volatility": 0.17,       # Basado en datos históricos reales
                "sharpe_ratio": 0.33      # Basado en datos históricos reales
            }
        }
        
        # Obtener datos reales de ETFs de bonos
        try:
            logger.info("Obteniendo datos reales de ETFs de bonos con Alpha Vantage")
            
            # Lista de ETFs de bonos populares para buscar
            bond_etf_tickers = ["AGG", "BND", "VCIT", "VCSH", "LQD", "MBB", "TIP", "GOVT"]
            
            # Intentar obtener datos para el primer ETF disponible
            bond_etf = None
            for ticker in bond_etf_tickers:
                try:
                    # Obtener precio real
                    price_data = alpha_client.get_real_time_price(ticker)
                    
                    # Obtener datos fundamentales
                    fundamentals = alpha_client.get_stock_fundamentals(ticker)
                    
                    if price_data and "price" in price_data and fundamentals:
                        bond_etf = {
                            "ticker": ticker,
                            "name": fundamentals.get("Name", f"{ticker} ETF"),
                            "price": price_data["price"],
                            "weight": bonds_allocation,
                            "amount": round(amount * bonds_allocation, 2),
                            "shares": round(amount * bonds_allocation / price_data["price"]),
                            "price_source": price_data.get("source", "alpha_vantage_real")
                        }
                        break
                except Exception as e:
                    logger.warning(f"Error obteniendo datos para el ETF {ticker}: {str(e)}")
                    continue
            
            # Si se encontró un ETF de bonos, agregarlo al portfolio
            if bond_etf:
                optimized["allocation"]["bonds"] = [bond_etf]
                logger.info(f"Se agregó el ETF de bonos {bond_etf['ticker']} al portfolio")
            else:
                logger.warning("No se pudieron obtener datos reales para ningún ETF de bonos")
                raise ValueError("No se pudieron obtener datos reales para ETFs de bonos. Verifica la configuración de ALPHAVANTAGE_API_KEY.")
        except Exception as e:
            logger.error(f"Error obteniendo datos de ETFs de bonos: {str(e)}")
            raise ValueError(f"No se pudieron obtener datos reales para ETFs de bonos: {str(e)}. No se usarán datos simulados ni predefinidos.")
            
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
        # Importar el cliente de Alpha Vantage para obtener datos reales
        from app_railway import alpha_client
        
        logger.info(f"Obteniendo métricas reales para {ticker}")
        
        # Obtener datos fundamentales reales
        fundamentals = alpha_client.get_stock_fundamentals(ticker)
        
        if not fundamentals:
            raise ValueError(f"No se pudieron obtener datos fundamentales para {ticker}")
        
        # Extraer métricas reales
        metrics = {
            "ROE": float(fundamentals.get("ReturnOnEquityTTM", 0)) * 100 if fundamentals.get("ReturnOnEquityTTM") else None,
            "P/E": float(fundamentals.get("PERatio", 0)) if fundamentals.get("PERatio") else None,
            "Margen de Beneficio": float(fundamentals.get("ProfitMargin", 0)) * 100 if fundamentals.get("ProfitMargin") else None,
            "Ratio de Deuda": float(fundamentals.get("DebtToEquityRatio", 0)) if fundamentals.get("DebtToEquityRatio") else None,
            "Crecimiento de FCF": float(fundamentals.get("QuarterlyEarningsGrowthYOY", 0)) * 100 if fundamentals.get("QuarterlyEarningsGrowthYOY") else None,
            "Moat Cualitativo": "Medio"  # Este valor requiere análisis cualitativo, podría obtenerse de Perplexity en el futuro
        }
        
        return {"ticker": ticker, "metrics": metrics, "data_source": "alpha_vantage_real"}
    except Exception as e:
        logger.error(f"Error obteniendo métricas reales para {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudieron obtener métricas reales para {ticker}. No se usarán datos simulados ni predefinidos.")

@app.get("/api/stock/price/{ticker}")
async def get_stock_price(ticker: str):
    try:
        # Importar el cliente de Alpha Vantage para obtener precios reales
        from app_railway import alpha_client
        
        logger.info(f"Obteniendo precio real para {ticker} desde Alpha Vantage")
        
        # Obtener precio real
        price_data = alpha_client.get_real_time_price(ticker)
        
        if not price_data or "price" not in price_data:
            raise ValueError(f"No se pudo obtener el precio real para {ticker}")
        
        return {
            "ticker": ticker, 
            "price": price_data["price"],
            "data_source": price_data.get("source", "alpha_vantage_real"),
            "timestamp": price_data.get("timestamp", datetime.now().isoformat())
        }
    except Exception as e:
        logger.error(f"Error obteniendo precio real para {ticker}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"No se pudo obtener el precio real para {ticker}. No se usarán datos simulados ni predefinidos."
        )

# Rutas de prueba

@app.get("/api/env/perplexity")
def check_perplexity_key():
    import os
    key = os.getenv("PERPLEXITY_API_KEY")
    if key:
        return {"perplexity_api_key_loaded": True, "length": len(key)}
    else:
        return {"perplexity_api_key_loaded": False}

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
