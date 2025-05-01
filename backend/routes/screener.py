from fastapi import APIRouter, Query, Request
from backend.models.symbols import Symbol
import logging

router = APIRouter()

@router.get("/screener/value")
async def value_screener():
    """Endpoint para el screener de Value Investing
    
    Retorna acciones infravaloradas basadas en criterios de value investing:
    - P/E bajo
    - ROE alto
    - Margen de beneficio saludable
    """
    try:
        results = Symbol.get_value_screener()
        return results
    except Exception as e:
        logging.error(f"Error en value screener: {str(e)}")
        return {"error": str(e)}

@router.get("/screener/growth")
async def growth_screener(req: Request):
    """Endpoint para el screener de Growth
    
    Retorna acciones con alto potencial de crecimiento basadas en:
    - Crecimiento de ingresos YoY > minGrowth (default 20%)
    - Margen bruto > 40%
    - ROE > 15%
    - P/E forward < 40
    - Retorno 6 meses > 20%
    - SMA50 > SMA200 (tendencia alcista)
    
    Query params:
    - minGrowth: Crecimiento mu00ednimo de ingresos (default: 0.20)
    - region: Regiones separadas por coma (default: "US,EU,CN,IN")
    """
    try:
        params = req.query_params
        min_growth = float(params.get("minGrowth", "0.20"))
        region = params.get("region", "US,EU,CN,IN")
        
        results = Symbol.get_growth_screener(min_growth, region)
        return results
    except Exception as e:
        logging.error(f"Error en growth screener: {str(e)}")
        return {"error": str(e)}
