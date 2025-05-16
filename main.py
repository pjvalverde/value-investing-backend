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

# Verificar y loguear si las API keys están presentes
perplexity_key = os.getenv("PERPLEXITY_API_KEY")
claude_key = os.getenv("CLAUDE_API_KEY")
logging.basicConfig(level=logging.INFO)
logging.info(f"PERPLEXITY_API_KEY: {'OK (' + perplexity_key[:5] + '...)' if perplexity_key else 'NO CONFIGURADA'}")
logging.info(f"CLAUDE_API_KEY: {'OK (' + claude_key[:5] + '...)' if claude_key else 'NO CONFIGURADA'}")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("value-investing-api")

from improved_alpha_service import ImprovedAlphaVantageClient
alpha_client = ImprovedAlphaVantageClient()

# Crear la aplicación FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Importar ClaudeClient para análisis cualitativo
from claude_client import ClaudeClient
claude_client = ClaudeClient()


@app.get("/api/env/perplexity")
def check_perplexity_key():
    import os
    key = os.getenv("PERPLEXITY_API_KEY")
    if key:
        return {"perplexity_api_key_loaded": True, "length": len(key)}
    else:
        return {"perplexity_api_key_loaded": False}


# Permitir acceso desde el frontend React - Configuración explícita de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pjvalverde.github.io"],  # Solo permite el frontend de GitHub Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.post("/api/portfolio/analysis")
async def portfolio_analysis(request: Request):
    """
    Endpoint que recibe la composición de un portafolio y devuelve un análisis detallado generado por Claude.
    Body:
    - portfolio: lista de dicts con info de cada acción (ticker, sector, peso, metrics, etc.)
    - strategy_description: descripción opcional de la estrategia
    - language: idioma de salida ('es' o 'en')
    Returns:
    - analysis: texto generado por Claude
    """
    try:
        data = await request.json()
        portfolio = data.get("portfolio")
        strategy_description = data.get("strategy_description")
        language = data.get("language", "es")
        # Permitir tanto lista como objeto con allocation
        if isinstance(portfolio, dict) and "allocation" in portfolio:
            portfolio = portfolio["allocation"]
        if not portfolio or not isinstance(portfolio, list):
            raise ValueError("Debes proporcionar un portafolio real (lista de acciones)")
        # Validar que no hay campos simulados
        for stock in portfolio:
            if stock.get("simulated"):
                raise ValueError("No se permiten datos simulados en el análisis de portafolio")
        analysis = claude_client.generate_analysis(portfolio, strategy_description, language)
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/analysis: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "No se pudo generar el análisis con Claude", "details": str(e)}
        )

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
        logger.error(f"Error al crear portafolio: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Error al crear portafolio", "details": str(e)}
        )

@app.post("/api/portfolio/optimize")
async def optimize_portfolio(request: Request):
    from perplexity_client import PerplexityClient
    try:
        logger.info("Iniciando optimización de portfolio (solo Perplexity, sin simulaciones)")
        # Leer la solicitud
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
        target_alloc = data.get("target_alloc", {"growth": 100})
        # Convertir a float para evitar errores de tipo
        amount = float(data.get("amount", 10000))
        growth_allocation = float(target_alloc.get("growth", 100)) / 100
        value_allocation = float(target_alloc.get("value", 0)) / 100

        # Llamar a Perplexity para obtener el portafolio growth
        try:
            import os
            api_key = os.getenv("PERPLEXITY_API_KEY")
            logger.info(f"[DEBUG] Usando PERPLEXITY_API_KEY: {api_key[:5]}..." if api_key else "[DEBUG] PERPLEXITY_API_KEY no está configurada")
            logger.info(f"[DEBUG] Parámetros enviados a Perplexity growth: amount={amount * growth_allocation}, min_marketcap_eur=300_000_000, max_marketcap_eur=2_000_000_000, min_beta=1.2, max_beta=1.4, n_stocks=10, region='EU,US'")
            perplexity_client = PerplexityClient()
            growth_stocks = perplexity_client.get_growth_portfolio(
                amount=amount * growth_allocation,
                min_marketcap_eur=300_000_000,
                max_marketcap_eur=2_000_000_000,
                min_beta=1.2,
                max_beta=1.4,
                n_stocks=5,
                region="EU,US"
            )
            logger.info(f"[DEBUG] Respuesta Perplexity growth: {growth_stocks}")
            if not growth_stocks or not isinstance(growth_stocks, list):
                raise ValueError("Perplexity no devolvió un portafolio válido.")
        except Exception as e:
            logger.error(f"Error obteniendo portafolio growth de Perplexity: {str(e)}")
            logger.error("[LOG] Devolviendo error al obtener portafolio growth desde Perplexity")
            return JSONResponse(
                status_code=500,
                content={"error": "No se pudo obtener el portafolio growth desde Perplexity.", "details": str(e)}
            )

        # Llamar a Perplexity para obtener el portafolio value
        try:
            value_stocks = perplexity_client.get_value_portfolio(
                amount=amount * value_allocation,
                min_marketcap_eur=300_000_000,
                max_marketcap_eur=2_000_000_000,
                n_stocks=5,
                region="EU,US"
            )
            if not value_stocks or not isinstance(value_stocks, list):
                raise ValueError("Perplexity no devolvió un portafolio válido.")
        except Exception as e:
            logger.error(f"Error obteniendo portafolio value de Perplexity: {str(e)}")
            logger.error("[LOG] Devolviendo error al obtener portafolio value desde Perplexity")
            return JSONResponse(
                status_code=500,
                content={"error": "No se pudo obtener el portafolio value desde Perplexity.", "details": str(e)}
            )

        # Asignar pesos y cantidades
        peso_total_growth = sum([float(stock.get("peso") or stock.get("weight") or 0) for stock in growth_stocks])
        peso_total_value = sum([float(stock.get("peso") or stock.get("weight") or 0) for stock in value_stocks])
        allocation = []
        for stock in growth_stocks:
            peso = float(stock.get("peso") or stock.get("weight") or 0)
            weight = peso / peso_total_growth if peso_total_growth else 1 / len(growth_stocks)
            monto = round(amount * growth_allocation * weight, 2)
            price = float(stock.get("price") or 1)  # Si Perplexity no da precio, poner 1 para evitar error
            shares = round(monto / price, 2) if price else 0
            allocation.append({
                "ticker": stock.get("ticker"),
                "name": stock.get("nombre") or stock.get("name"),
                "sector": stock.get("sector"),
                "country": stock.get("pais") or stock.get("country"),
                "weight": round(weight, 4),
                "amount": monto,
                "shares": shares,
                "metrics": stock.get("metrics", {}),
                "price": price
            })
        for stock in value_stocks:
            peso = float(stock.get("peso") or stock.get("weight") or 0)
            weight = peso / peso_total_value if peso_total_value else 1 / len(value_stocks)
            monto = round(amount * value_allocation * weight, 2)
            price = float(stock.get("price") or 1)  # Si Perplexity no da precio, poner 1 para evitar error
            shares = round(monto / price, 2) if price else 0
            allocation.append({
                "ticker": stock.get("ticker"),
                "name": stock.get("nombre") or stock.get("name"),
                "sector": stock.get("sector"),
                "country": stock.get("pais") or stock.get("country"),
                "weight": round(weight, 4),
                "amount": monto,
                "shares": shares,
                "metrics": stock.get("metrics", {}),
                "price": price
            })

        optimized = {
            "id": portfolio_id,
            "allocation": allocation,
            "metrics": {
                "expected_return": None,
                "volatility": None,
                "sharpe_ratio": None
            },
            "source": "perplexity_api"
        }
        logger.info(f"Portfolio optimizado generado solo con Perplexity: {optimized}")
        logger.info("[LOG] Devolviendo respuesta final optimizada")
        return optimized
    except Exception as e:
        logger.error(f"Error en endpoint /api/portfolio/optimize: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        logger.error("[LOG] Devolviendo error general en optimize_portfolio")
        return JSONResponse(
            status_code=500,
            content={"error": "Error al optimizar portfolio (solo Perplexity)", "details": str(e)}
        )
    finally:
        logger.info("[LOG] Finalizó ejecución de optimize_portfolio (finally)")

# ... (rest of the code remains the same)
    uvicorn.run("main:app", host="0.0.0.0", port=port)
