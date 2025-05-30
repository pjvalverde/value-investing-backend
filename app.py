# Aplicación FastAPI completamente independiente sin importaciones externas
import os
import uvicorn
import logging
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Crear la aplicación FastAPI
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

# Rutas de prueba
@app.get("/")
def root():
    return {"message": "Value Investing API - Versión 2.0"}

@app.get("/test")
def test():
    logging.info("Ruta de prueba accedida")
    return {"status": "ok", "message": "API funcionando correctamente"}

@app.get("/api/test")
def api_test():
    logging.info("Ruta de prueba API accedida")
    return {"status": "ok", "data": {"value_stocks": len(VALUE_STOCKS), "growth_stocks": len(GROWTH_STOCKS)}}

# Ejecutar la aplicación si se llama directamente
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
