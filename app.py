# Aplicación FastAPI completamente independiente sin importaciones externas
import os
import uvicorn
import logging
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# External AI clients
try:
    from perplexity_client import PerplexityClient
except Exception:
    PerplexityClient = None  # type: ignore
try:
    from claude_client import ClaudeClient
except Exception:
    ClaudeClient = None  # type: ignore

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Crear la aplicación FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Fallback datasets (avoid NameError if not imported elsewhere)
VALUE_STOCKS: list = []
GROWTH_STOCKS: list = []

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

# --- Static files (React build) ---
# Serve assets built into backend/public
# public/index.html must exist (copied from frontend build)
try:
    app.mount("/static", StaticFiles(directory="public/static"), name="static")
except Exception:
    # Ignore if already mounted
    pass

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
        logging.info("Iniciando optimización de portfolio")
        # Intentar leer el cuerpo de la solicitud
        try:
            body = await request.body()
            logging.info(f"Cuerpo de la solicitud: {body}")
            data = await request.json()
            logging.info(f"Datos recibidos: {data}")
        except Exception as e:
            logging.error(f"Error al leer el cuerpo de la solicitud: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": "Error al leer el cuerpo de la solicitud", "details": str(e)}
            )
        
        portfolio_id = data.get("portfolio_id", str(uuid.uuid4()))
        target_alloc = data.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
        amount = data.get("amount", 10000)
        
        logging.info(f"Optimizando portfolio {portfolio_id} con asignación {target_alloc} y monto {amount}")

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
        
        logging.info(f"Portfolio optimizado: {optimized}")
        return optimized
    except Exception as e:
        logging.error(f"Error en endpoint /api/portfolio/optimize: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Error al optimizar portfolio", "details": str(e)}
        )

# --- Real-time portfolio from Perplexity ---
def _compute_allocation(items: list, amount: float):
    """Convert Perplexity items into allocation list with shares and amounts.
    Expected fields in item: ticker (or symbol), name, price, weight (0-1 or 0-100).
    """
    allocation = []
    if not items:
        return allocation
    for it in items:
        symbol = it.get("ticker") or it.get("symbol") or it.get("Ticker") or "N/A"
        name = it.get("name") or it.get("Name") or it.get("nombre") or symbol
        price = it.get("price") or it.get("Price") or it.get("precio") or 100
        # weight could be 0-1, 0-100, or missing
        weight = it.get("weight") or it.get("peso") or it.get("Weight") or 0
        try:
            w = float(weight)
            if w > 1.5:  # interpret as percent
                w = w / 100.0
            if w <= 0:
                w = 1.0 / max(1, len(items))
        except Exception:
            w = 1.0 / max(1, len(items))
        try:
            px = float(price)
        except Exception:
            px = 100.0
        allocated = amount * w
        shares = int(max(0, allocated // px))
        allocation.append({
            "symbol": symbol,
            "name": name,
            "price": px,
            "shares": shares,
            "amount": round(shares * px, 2),
        })
    return allocation


@app.post("/api/portfolio/{category}")
async def build_portfolio_category(category: str, request: Request):
    """Build a portfolio slice using Perplexity for a given category.
    Supported categories: value, growth, bonds, disruptive.
    Body: { amount: number }
    """
    try:
        body = await request.json()
        amount = float(body.get("amount", 0))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not PerplexityClient:
        return JSONResponse(status_code=500, content={"error": "Perplexity client not available on server"})
    try:
        client = PerplexityClient()
    except Exception as e:
        # Most likely missing API key
        logging.error(f"Perplexity init error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Perplexity no disponible: {e}"})

    try:
        items: list
        if category == "value":
            items = client.get_value_portfolio(amount)
        elif category == "growth":
            items = client.get_growth_portfolio(amount)
        elif category == "bonds":
            items = client.get_bond_etfs(amount)
        elif category == "disruptive":
            # Prefer ETFs for quick results
            try:
                items = client.get_disruptive_etfs(amount)
            except Exception:
                items = client.get_disruptive_portfolio(amount)
        else:
            return JSONResponse(status_code=404, content={"error": f"Categoría desconocida: {category}"})

        allocation = _compute_allocation(items, amount)
        return {"allocation": allocation, "sourceCount": len(items)}
    except Exception as e:
        logging.error(f"Error building portfolio for {category}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/portfolio/claude-analysis")
async def portfolio_claude_analysis(request: Request):
    """Generate a qualitative analysis using Claude.
    Body: { portfolio: { allocation: {category: [...] } } }
    """
    try:
        body = await request.json()
        portfolio = body.get("portfolio") or {}
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not ClaudeClient:
        return JSONResponse(status_code=500, content={"error": "Claude client not available on server"})
    try:
        claude = ClaudeClient()
    except Exception as e:
        logging.error(f"Claude init error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Claude no disponible: {e}"})

    # Flatten positions for prompt simplicity
    flat_positions = []
    try:
        allocation = (portfolio or {}).get("allocation", {})
        for _category, positions in allocation.items():
            if isinstance(positions, dict):
                positions = list(positions.values())
            if isinstance(positions, list):
                for p in positions:
                    flat_positions.append({
                        "ticker": p.get("symbol") or p.get("ticker"),
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "shares": p.get("shares"),
                        "amount": p.get("amount"),
                        "weight": p.get("weight"),
                        "metrics": p.get("metrics", {}),
                    })
    except Exception:
        pass

    try:
        analysis = claude.generate_analysis(flat_positions, language="es")
        return {"analysis": analysis}
    except Exception as e:
        logging.error(f"Claude analysis error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Status endpoint for monitoring
@app.get("/api/status")
def api_status():
    return {"status": "ok"}

# Rutas de prueba

@app.get("/test")
def test():
    logging.info("Ruta de prueba accedida")
    return {"status": "ok", "message": "API funcionando correctamente"}

@app.get("/api/test")
def api_test():
    logging.info("Ruta de prueba API accedida")
    # Manejar variables opcionales en tiempo de ejecución
    try:
        value_count = len(VALUE_STOCKS)
    except Exception:
        value_count = 0
    try:
        growth_count = len(GROWTH_STOCKS)
    except Exception:
        growth_count = 0
    return {"status": "ok", "data": {"value_stocks": value_count, "growth_stocks": growth_count}}

# --- SPA entry and catch-all (must be after API routes) ---
INDEX_FILE = Path("public") / "index.html"

@app.get("/", include_in_schema=False)
def serve_index():
    # Serve React index.html at root
    return FileResponse(INDEX_FILE)

@app.get("/{full_path:path}", include_in_schema=False)
def spa_catch_all(full_path: str):
    # Do not intercept API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    file_path = Path("public") / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(INDEX_FILE)

# Ejecutar la aplicación si se llama directamente
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
