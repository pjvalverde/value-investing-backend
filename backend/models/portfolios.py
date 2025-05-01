from .db import db
import logging
import uuid
from datetime import datetime

class Portfolio:
    @staticmethod
    def create(user_id, name, target_alloc):
        try:
            portfolio_id = str(uuid.uuid4())
            query = """
            INSERT INTO portfolios (id, user_id, name, target_alloc)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """
            
            result = db.query(query, [portfolio_id, user_id, name, target_alloc])
            return portfolio_id
        except Exception as e:
            logging.error(f"Error al crear portfolio: {str(e)}")
            return None
    
    @staticmethod
    def get_by_id(portfolio_id):
        try:
            query = "SELECT * FROM portfolios WHERE id = %s"
            result = db.query(query, [portfolio_id])
            rows = result.get("rows", [])
            return rows[0] if rows else None
        except Exception as e:
            logging.error(f"Error al obtener portfolio: {str(e)}")
            return None
    
    @staticmethod
    def get_by_user(user_id):
        try:
            query = "SELECT * FROM portfolios WHERE user_id = %s ORDER BY updated_at DESC"
            result = db.query(query, [user_id])
            return result.get("rows", [])
        except Exception as e:
            logging.error(f"Error al obtener portfolios del usuario: {str(e)}")
            return []
    
    @staticmethod
    def update_allocation(portfolio_id, current_alloc):
        try:
            query = """
            UPDATE portfolios 
            SET current_alloc = %s, updated_at = %s
            WHERE id = %s
            RETURNING id
            """
            
            result = db.query(query, [current_alloc, datetime.now(), portfolio_id])
            return result.get("affected", 0) > 0
        except Exception as e:
            logging.error(f"Error al actualizar asignacin de portfolio: {str(e)}")
            return False
    
    @staticmethod
    def optimize(amount, target):
        """Optimiza un portfolio basado en el monto y la asignacin objetivo
        
        Args:
            amount (float): Monto total a invertir
            target (dict): Asignacin objetivo {"bonds": 25, "value": 50, "growth": 25}
            
        Returns:
            list: Lista de acciones y cantidades optimizadas
        """
        try:
            # Calcular montos por estrategia
            strategy_amounts = {}
            for strategy, percentage in target.items():
                strategy_amounts[strategy] = amount * (percentage / 100)
            
            result = []
            
            # Obtener acciones de valor
            if "value" in strategy_amounts and strategy_amounts["value"] > 0:
                value_amount = strategy_amounts["value"]
                value_stocks = db.query("""
                    SELECT ticker, price FROM symbols s
                    JOIN fundamentals f USING(ticker)
                    WHERE strategy = 'value'
                    ORDER BY forward_pe ASC
                    LIMIT 5
                """).get("rows", [])
                
                if value_stocks:
                    per_stock = value_amount / len(value_stocks)
                    for stock in value_stocks:
                        shares = int(per_stock / stock["price"])
                        if shares > 0:
                            result.append({
                                "ticker": stock["ticker"],
                                "shares": shares,
                                "price": stock["price"],
                                "usd": shares * stock["price"],
                                "bucket": "value"
                            })
            
            # Obtener acciones de crecimiento
            if "growth" in strategy_amounts and strategy_amounts["growth"] > 0:
                growth_amount = strategy_amounts["growth"]
                growth_stocks = db.query("""
                    SELECT ticker, price FROM symbols s
                    JOIN fundamentals f USING(ticker)
                    WHERE strategy = 'growth'
                    ORDER BY yoy_rev_growth DESC
                    LIMIT 5
                """).get("rows", [])
                
                if growth_stocks:
                    per_stock = growth_amount / len(growth_stocks)
                    for stock in growth_stocks:
                        shares = int(per_stock / stock["price"])
                        if shares > 0:
                            result.append({
                                "ticker": stock["ticker"],
                                "shares": shares,
                                "price": stock["price"],
                                "usd": shares * stock["price"],
                                "bucket": "growth"
                            })
            
            # Agregar bonos si es necesario
            if "bonds" in strategy_amounts and strategy_amounts["bonds"] > 0:
                bonds_amount = strategy_amounts["bonds"]
                # Usar ETF de bonos SHY como ejemplo
                shy_price = 100  # Precio simulado para SHY
                shares = int(bonds_amount / shy_price)
                if shares > 0:
                    result.append({
                        "ticker": "SHY",
                        "shares": shares,
                        "price": shy_price,
                        "usd": shares * shy_price,
                        "bucket": "bonds"
                    })
            
            return result
            
        except Exception as e:
            logging.error(f"Error al optimizar portfolio: {str(e)}")
            return []
    
    @staticmethod
    def calculate_performance(portfolio_id, start_date=None, end_date=None):
        """Calcula el rendimiento histrico de un portfolio comparado con S&P 500
        
        Args:
            portfolio_id (str): ID del portfolio
            start_date (str, optional): Fecha de inicio (YYYY-MM-DD)
            end_date (str, optional): Fecha de fin (YYYY-MM-DD)
            
        Returns:
            dict: Datos de rendimiento {"portfolio": [...], "benchmark": [...]}
        """
        try:
            # Simulacin de rendimiento para desarrollo
            # En produccin, esto usara datos reales de precios histricos
            
            portfolio_returns = [
                {"date": "2023-01-01", "value": 100.00},
                {"date": "2023-02-01", "value": 102.50},
                {"date": "2023-03-01", "value": 105.80},
                {"date": "2023-04-01", "value": 108.20},
                {"date": "2023-05-01", "value": 107.30},
                {"date": "2023-06-01", "value": 110.50},
                {"date": "2023-07-01", "value": 114.20},
                {"date": "2023-08-01", "value": 113.40},
                {"date": "2023-09-01", "value": 116.80},
                {"date": "2023-10-01", "value": 115.20},
                {"date": "2023-11-01", "value": 119.60},
                {"date": "2023-12-01", "value": 123.40},
                {"date": "2024-01-01", "value": 125.80},
                {"date": "2024-02-01", "value": 128.50},
                {"date": "2024-03-01", "value": 130.20},
                {"date": "2024-04-01", "value": 132.90}
            ]
            
            spy_returns = [
                {"date": "2023-01-01", "value": 100.00},
                {"date": "2023-02-01", "value": 101.20},
                {"date": "2023-03-01", "value": 103.50},
                {"date": "2023-04-01", "value": 105.10},
                {"date": "2023-05-01", "value": 104.80},
                {"date": "2023-06-01", "value": 107.30},
                {"date": "2023-07-01", "value": 109.80},
                {"date": "2023-08-01", "value": 108.90},
                {"date": "2023-09-01", "value": 110.50},
                {"date": "2023-10-01", "value": 109.20},
                {"date": "2023-11-01", "value": 112.40},
                {"date": "2023-12-01", "value": 115.60},
                {"date": "2024-01-01", "value": 117.20},
                {"date": "2024-02-01", "value": 119.80},
                {"date": "2024-03-01", "value": 120.50},
                {"date": "2024-04-01", "value": 122.10}
            ]
            
            return {
                "portfolio": portfolio_returns,
                "benchmark": spy_returns
            }
            
        except Exception as e:
            logging.error(f"Error al calcular rendimiento: {str(e)}")
            return {"portfolio": [], "benchmark": []}
