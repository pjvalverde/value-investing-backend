# Aplicación FastAPI completamente independiente sin importaciones externas
import os
import uvicorn
import logging
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
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
    Preserves all original Perplexity fields (metrics, sector, PER, ROE, etc.).
    Uses fractional shares so every position has a meaningful dollar allocation.
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
            if w > 1.5:  # interpret as percent (0-100 scale)
                w = w / 100.0
            if w <= 0:
                w = 1.0 / max(1, len(items))
        except Exception:
            w = 1.0 / max(1, len(items))
        try:
            px = float(price)
            if px <= 0:
                px = 100.0
        except Exception:
            px = 100.0

        allocated = round(amount * w, 2)
        # Use fractional shares so high-price stocks still show a real allocation
        shares = round(allocated / px, 4)

        allocation.append({
            # Core position fields
            "symbol": symbol,
            "name": name,
            "price": round(px, 2),
            "shares": shares,
            "amount": allocated,
            # Fundamental data forwarded from Perplexity
            "sector":   it.get("sector")   or it.get("Sector")   or "",
            "country":  it.get("país")     or it.get("country")  or it.get("Country") or "",
            "per":      it.get("PER")      or it.get("per")      or it.get("pe_ratio") or None,
            "roe":      it.get("ROE")      or it.get("roe")      or None,
            "deuda":    it.get("deuda")    or it.get("debt_equity") or None,
            "margen":   it.get("margen")   or it.get("margin")   or None,
            "moat":     it.get("moat")     or it.get("Moat")     or "",
            "beta":     it.get("beta")     or it.get("Beta")     or None,
            "marketcap":it.get("marketcap")or it.get("MarketCap")or None,
            "categoria":it.get("categoría")or it.get("categoria")or it.get("category") or "",
            # Damodaran metrics object (ev_ebitda, roic, fcf_yield, etc.)
            "metrics":  it.get("metrics") or {},
        })
    return allocation


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
        return JSONResponse(status_code=500, content={"error": f"Claude error: {e}"})

# Provide an alias path that won't be captured by the category route
@app.post("/api/analysis/claude")
async def portfolio_claude_analysis_alias(request: Request):
    return await portfolio_claude_analysis(request)


@app.post("/api/portfolio/claude-stream")
async def claude_stream_analysis(request: Request):
    """Stream Claude portfolio analysis as SSE — avoids Heroku H12 30-second timeout.
    Body: { portfolio: { allocation: {category: [...] } } }
    """
    import requests as _requests

    try:
        body = await request.json()
        portfolio = body.get("portfolio") or {}
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    # Flatten positions
    flat_positions = []
    try:
        allocation = (portfolio or {}).get("allocation", {})
        for _category, positions in allocation.items():
            if isinstance(positions, dict):
                positions = list(positions.values())
            if isinstance(positions, list):
                for p in positions:
                    flat_positions.append({
                        "ticker":    p.get("symbol") or p.get("ticker", "-"),
                        "name":      p.get("name", "-"),
                        "sector":    p.get("sector", "-"),
                        "country":   p.get("country") or p.get("país", "-"),
                        "category":  p.get("category") or p.get("estrategia", "-"),
                        "weight":    p.get("weight") or p.get("peso"),
                        "roe":       p.get("roe"),
                        "deuda":     p.get("deuda"),
                        "margen":    p.get("margen"),
                        "per":       p.get("per"),
                        "moat":      p.get("moat", ""),
                        "metrics":   p.get("metrics", {}),
                    })
    except Exception as e:
        logging.error(f"Error flattening portfolio for stream: {e}")

    if not flat_positions:
        return JSONResponse(status_code=400, content={"error": "No positions in portfolio"})

    api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return JSONResponse(status_code=500, content={"error": "No Claude API key configured"})

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

    system_prompt = (
        "Eres un comité de inversión de élite formado por Warren Buffett, Charlie Munger y Aswath Damodaran. "
        "Analizas portafolios con rigor usando sus metodologías combinadas y das una opinión DIRECTA y ACCIONABLE. "
        "Usa los datos reales provistos (ROIC, EV/EBITDA, FCF Yield, ROE, márgenes, deuda, margen de seguridad). "
        "Sé específico con los tickers y métricas concretas. Responde en español. Máximo 550 palabras."
    )

    # Build metrics table
    table_lines = [
        "PORTAFOLIO — DATOS REALES DE MERCADO:",
        "| Ticker | Sector | Peso% | ROIC% | EV/EBITDA | FCF Yield% | ROE% | D/E | Margen% | MoS% |",
        "|--------|--------|-------|-------|-----------|------------|------|-----|---------|------|",
    ]
    for s in flat_positions:
        m = s.get("metrics") or {}
        peso = s.get("weight")
        try:
            peso_str = f"{float(peso):.1f}" if peso is not None else "-"
        except Exception:
            peso_str = "-"
        table_lines.append(
            f"| {s['ticker']} | {s['sector']} | {peso_str}% | "
            f"{m.get('roic', '-')} | {m.get('ev_ebitda', '-')} | {m.get('fcf_yield', '-')} | "
            f"{s.get('roe', '-')} | {s.get('deuda', '-')} | {s.get('margen', '-')} | "
            f"{m.get('margin_of_safety', '-')} |"
        )

    user_content = (
        "\n".join(table_lines) + "\n\n"
        "Analiza este portafolio como el comité. Estructura tu respuesta así:\n\n"
        "## 🏛 Warren Buffett — Calidad y Moat\n"
        "Evalúa el moat, ROE, márgenes y calidad de negocio para las posiciones clave. ¿Comprarías y mantendrías 10 años?\n\n"
        "## 🧠 Charlie Munger — Modelos Mentales\n"
        "Evalúa la diversificación sectorial, calidad vs precio y red flags psicológicas. ¿Son negocios excelentes o mediocres?\n\n"
        "## 📐 Aswath Damodaran — Rigor Cuantitativo\n"
        "Analiza ROIC vs WACC estimado (8.5%), EV/EBITDA vs sector, FCF Yield y margen de seguridad DCF. ¿Los números justifican la inversión?\n\n"
        "## 📊 Veredicto del Comité\n"
        "Decisión: **INVERTIR** / **VIGILAR** / **EVITAR** — Puntuación: X/100 — 3 razones concretas basadas en métricas."
    )

    payload = {
        "model": model,
        "max_tokens": 800,
        "temperature": 0.55,
        "stream": True,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    headers_api = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    def generate():
        try:
            resp = _requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers_api,
                json=payload,
                stream=True,
                timeout=120,
            )
            if resp.status_code != 200:
                err_text = resp.text[:500]
                logging.error(f"Claude stream API error {resp.status_code}: {err_text}")
                yield f"data: {json.dumps({'error': f'Claude API error {resp.status_code}: {err_text}'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                        if event.get("type") == "content_block_delta":
                            text = event.get("delta", {}).get("text", "")
                            if text:
                                yield f"data: {json.dumps({'text': text})}\n\n"
                    except Exception:
                        pass

            yield "data: [DONE]\n\n"

        except Exception as e:
            logging.error(f"Streaming generate error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _yf_fallback(category: str, amount: float) -> list:
    """Use yfinance curated portfolios as fallback when Perplexity is unavailable."""
    try:
        from yfinance_portfolios import (
            get_value_portfolio_yf, get_growth_portfolio_yf,
            get_bond_etfs_yf, get_disruptive_etfs_yf,
        )
        if category == "value":
            return get_value_portfolio_yf(amount)
        elif category == "growth":
            return get_growth_portfolio_yf(amount)
        elif category == "bonds":
            return get_bond_etfs_yf(amount)
        elif category == "disruptive":
            return get_disruptive_etfs_yf(amount)
    except Exception as e:
        logging.error(f"yfinance fallback error for {category}: {e}")
    return []


@app.post("/api/portfolio/{category}")
async def build_portfolio_category(category: str, request: Request):
    """Build a portfolio slice. Tries Perplexity first; falls back to yfinance.
    Supported categories: value, growth, bonds, disruptive.
    Body: { amount: number }
    """
    try:
        body = await request.json()
        amount = float(body.get("amount", 0))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if category not in ("value", "growth", "bonds", "disruptive"):
        return JSONResponse(status_code=404, content={"error": f"Categoría desconocida: {category}"})

    items: list = []
    source = "perplexity"

    # ── Try Perplexity first ──────────────────────────────────────────────────
    perplexity_ok = False
    if PerplexityClient:
        try:
            client = PerplexityClient()
            if category == "value":
                items = client.get_value_portfolio(amount)
            elif category == "growth":
                items = client.get_growth_portfolio(amount)
            elif category == "bonds":
                items = client.get_bond_etfs(amount)
            elif category == "disruptive":
                try:
                    items = client.get_disruptive_etfs(amount)
                except Exception:
                    items = client.get_disruptive_portfolio(amount)
            perplexity_ok = bool(items)
        except Exception as e:
            logging.warning(f"Perplexity unavailable for {category}: {e}. Falling back to yfinance.")

    # ── Fall back to yfinance if Perplexity failed or returned empty ──────────
    if not perplexity_ok:
        logging.info(f"Using yfinance fallback for {category}")
        items = _yf_fallback(category, amount)
        source = "yfinance"

    if not items:
        return JSONResponse(status_code=500, content={"error": f"No se pudo obtener datos para {category}"})

    allocation = _compute_allocation(items, amount)
    return {"allocation": allocation, "sourceCount": len(items), "source": source}


@app.post("/api/portfolio/historical-batch")
async def historical_batch(request: Request):
    """Get normalized historical price data for multiple tickers using yfinance."""
    try:
        body = await request.json()
        tickers = body.get("tickers", [])
        period = body.get("period", "1y")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    if not tickers:
        return JSONResponse(status_code=400, content={"error": "No tickers provided"})

    valid_periods = {"1mo", "3mo", "6mo", "1y", "3y", "5y"}
    if period not in valid_periods:
        period = "1y"

    try:
        import yfinance as yf
        result = {}
        for ticker in tickers[:10]:  # Max 10 tickers
            try:
                stock = yf.Ticker(str(ticker).upper())
                hist = stock.history(period=period)
                if hist.empty:
                    logging.warning(f"No data for ticker {ticker}")
                    continue
                data = [
                    {"date": date.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
                    for date, row in hist.iterrows()
                ]
                result[ticker] = data
            except Exception as e:
                logging.warning(f"Could not fetch {ticker}: {e}")
                continue
        return result
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "yfinance not installed on server"})
    except Exception as e:
        logging.error(f"Historical batch error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/analysis/decision")
async def investment_decision(request: Request):
    """Return invest/no-invest decision based on prior Claude analysis text or portfolio.
    Body: { analysis: str, portfolio?: {...} }
    """
    try:
        body = await request.json()
        analysis_text = body.get("analysis", "")
        portfolio_hint = body.get("portfolio")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not ClaudeClient:
        return JSONResponse(status_code=500, content={"error": "Claude client not available on server"})
    try:
        claude = ClaudeClient()
        decision = claude.generate_decision(analysis_text, portfolio_hint)
        return decision
    except Exception as e:
        logging.error(f"Decision error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Claude decision error: {e}"})

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
