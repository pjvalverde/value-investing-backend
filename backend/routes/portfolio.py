from fastapi import APIRouter, Request, HTTPException
from backend.models.portfolios import Portfolio
import logging
import json
import uuid

# Para usar Claude necesitamos NodeJS, así que usaremos subprocess
import subprocess
import os

router = APIRouter()

@router.post("/portfolio/optimize")
async def optimize_portfolio(request: Request):
    """Endpoint para optimizar un portfolio
    
    Body:
    - amount: Monto total a invertir
    - target: Asignación objetivo {"bonds": 25, "value": 50, "growth": 25}
    
    Returns:
    - Lista de acciones y cantidades optimizadas
    """
    try:
        data = await request.json()
        amount = data.get("amount")
        target = data.get("target")
        
        if not amount or not target:
            raise HTTPException(status_code=400, detail="Se requiere amount y target")
        
        # Usar el optimizador de portfolio
        result = Portfolio.optimize(amount, target)
        
        # Calcular métricas del portfolio
        total_invested = sum(item["usd"] for item in result)
        cash = amount - total_invested
        
        # Calcular rendimiento esperado y volatilidad (simulado)
        expected_return = 8.5  # Simulado: 8.5% anual
        volatility = 12.0     # Simulado: 12% volatilidad anual
        
        return {
            "portfolio": result,
            "metrics": {
                "total_invested": total_invested,
                "cash": cash,
                "expected_return": expected_return,
                "volatility": volatility
            }
        }
    except Exception as e:
        logging.error(f"Error al optimizar portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portfolio/optimize-claude")
async def optimize_portfolio_claude(request: Request):
    """Endpoint para optimizar un portfolio usando Claude
    
    Body:
    - amount: Monto total a invertir
    - target: Asignación objetivo {"bonds": 25, "value": 50, "growth": 25}
    
    Returns:
    - Plan de inversión generado por Claude
    """
    try:
        data = await request.json()
        amount = data.get("amount")
        target = data.get("target")
        
        if not amount or not target:
            raise HTTPException(status_code=400, detail="Se requiere amount y target")
        
        # Obtener acciones value y growth
        value_stocks = Portfolio.optimize(amount * target.get("value", 0) / 100, {"value": 100})
        growth_stocks = Portfolio.optimize(amount * target.get("growth", 0) / 100, {"growth": 100})
        
        # Preparar prompt para Claude
        claude_prompt = f"""
        Eres un portfolio optimizer. Necesito asignar ${amount} con esta distribución objetivo:
        {json.dumps(target)}
        
        Acciones value disponibles:
        {json.dumps(value_stocks)}
        
        Acciones growth disponibles:
        {json.dumps(growth_stocks)}
        
        Bonos ETF "SHY" precio 100
        
        Por favor, genera un plan de inversión JSON con esta estructura:
        {{"portfolio": [{{
            "ticker": "AAPL",
            "shares": 10,
            "price": 175.50,
            "usd": 1755.00,
            "bucket": "value"
        }}, ...],
        "metrics": {{
            "total_invested": 9500,
            "cash": 500,
            "expected_return": 8.5,
            "volatility": 12.0
        }}}}
        
        Respeta exactamente la asignación objetivo. Responde SOLO con el JSON, sin texto adicional.
        """
        
        # Llamar a Claude usando Node.js (asumiendo que tenemos un wrapper en lib/claude.js)
        # Este enfoque requiere que Node.js esté instalado y que el script claude.js exista
        script_path = os.path.join(os.path.dirname(__file__), "../lib/claude_runner.js")
        
        # Crear un script temporal para ejecutar Claude
        with open(script_path, "w") as f:
            f.write("""
            const { runClaude } = require('./claude.js');
            
            async function main() {
                const prompt = process.argv[2];
                const result = await runClaude(prompt);
                console.log(result);
            }
            
            main().catch(console.error);
            """)
        
        # Ejecutar el script con Node.js
        result = subprocess.run(
            ["node", script_path, claude_prompt],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        if result.returncode != 0:
            logging.error(f"Error al ejecutar Claude: {result.stderr}")
            raise HTTPException(status_code=500, detail="Error al ejecutar Claude")
        
        # Parsear la respuesta de Claude
        try:
            claude_response = result.stdout.strip()
            # Extraer solo el JSON si hay texto adicional
            if "{{" in claude_response:
                claude_response = claude_response[claude_response.find("{{"): claude_response.rfind("}}") + 2]
            
            plan = json.loads(claude_response)
            return plan
        except json.JSONDecodeError:
            logging.error(f"Error al parsear respuesta de Claude: {claude_response}")
            # Si no podemos parsear la respuesta, usamos el optimizador normal
            return await optimize_portfolio(request)
    
    except Exception as e:
        logging.error(f"Error al optimizar portfolio con Claude: {str(e)}")
        # En caso de error, usar el optimizador normal como fallback
        return await optimize_portfolio(request)

@router.get("/portfolio/performance")
async def get_performance(portfolio_id: str = None, start_date: str = None, end_date: str = None):
    """Endpoint para obtener el rendimiento histórico de un portfolio
    
    Query params:
    - portfolio_id: ID del portfolio (opcional)
    - start_date: Fecha de inicio (YYYY-MM-DD) (opcional)
    - end_date: Fecha de fin (YYYY-MM-DD) (opcional)
    
    Returns:
    - Datos de rendimiento {"portfolio": [...], "benchmark": [...]}
    """
    try:
        # Si no se proporciona portfolio_id, usamos uno simulado
        if not portfolio_id:
            portfolio_id = str(uuid.uuid4())
        
        performance = Portfolio.calculate_performance(portfolio_id, start_date, end_date)
        return performance
    except Exception as e:
        logging.error(f"Error al obtener rendimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portfolio/create")
async def create_portfolio(request: Request):
    """Endpoint para crear un nuevo portfolio
    
    Body:
    - user_id: ID del usuario (opcional)
    - name: Nombre del portfolio
    - target_alloc: Asignación objetivo {"bonds": 25, "value": 50, "growth": 25}
    
    Returns:
    - ID del portfolio creado
    """
    try:
        data = await request.json()
        user_id = data.get("user_id", str(uuid.uuid4()))  # Si no hay user_id, generamos uno
        name = data.get("name")
        target_alloc = data.get("target_alloc")
        
        if not name or not target_alloc:
            raise HTTPException(status_code=400, detail="Se requiere name y target_alloc")
        
        portfolio_id = Portfolio.create(user_id, name, target_alloc)
        
        if not portfolio_id:
            raise HTTPException(status_code=500, detail="Error al crear portfolio")
        
        return {"id": portfolio_id}
    except Exception as e:
        logging.error(f"Error al crear portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{portfolio_id}")
async def get_portfolio(portfolio_id: str):
    """Endpoint para obtener un portfolio por ID
    
    Path params:
    - portfolio_id: ID del portfolio
    
    Returns:
    - Datos del portfolio
    """
    try:
        portfolio = Portfolio.get_by_id(portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio no encontrado")
        
        return portfolio
    except Exception as e:
        logging.error(f"Error al obtener portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/user/{user_id}")
async def get_user_portfolios(user_id: str):
    """Endpoint para obtener todos los portfolios de un usuario
    
    Path params:
    - user_id: ID del usuario
    
    Returns:
    - Lista de portfolios del usuario
    """
    try:
        portfolios = Portfolio.get_by_user(user_id)
        return portfolios
    except Exception as e:
        logging.error(f"Error al obtener portfolios del usuario: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
