import os
import sys
import uvicorn

# Agregar el directorio actual al path de Python para permitir importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importar FastAPI y componentes necesarios
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Crear la aplicación FastAPI
app = FastAPI(title="Value Investing API", description="API para el sistema de Value Investing")

# Permitir acceso desde el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar directamente desde el directorio actual
import backend.models.db as db_module
import backend.routes.screener as screener_module
import backend.routes.portfolio as portfolio_module

# Obtener los routers
screener_router = screener_module.router
portfolio_router = portfolio_module.router

# Registrar routers
app.include_router(screener_router, prefix="/api", tags=["screener"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["portfolio"])

# Ruta raíz
@app.get("/")
def root():
    return {"message": "Value Investing API - Versión 2.0"}

# Ejecutar la aplicación si se llama directamente
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
