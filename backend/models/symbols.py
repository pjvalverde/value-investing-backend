from backend.models.db import db
import logging

class Symbol:
    @staticmethod
    def get_all(region=None, strategy=None):
        try:
            query = "SELECT * FROM symbols"
            conditions = []
            params = []
            
            if region:
                conditions.append("region = ANY(%s)")
                params.append(region.split(','))
                
            if strategy:
                conditions.append("strategy = %s")
                params.append(strategy)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            result = db.query(query, params)
            return result.get("rows", [])
        except Exception as e:
            logging.error(f"Error al obtener su00edmbolos: {str(e)}")
            return []
    
    @staticmethod
    def get_with_fundamentals(region=None, strategy=None):
        try:
            query = """
            SELECT s.*, f.* 
            FROM symbols s 
            LEFT JOIN fundamentals f ON s.ticker = f.ticker
            """
            
            conditions = ["f.asof = (SELECT MAX(asof) FROM fundamentals)"]
            params = []
            
            if region:
                conditions.append("s.region = ANY(%s)")
                params.append(region.split(','))
                
            if strategy:
                conditions.append("s.strategy = %s")
                params.append(strategy)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            result = db.query(query, params)
            return result.get("rows", [])
        except Exception as e:
            logging.error(f"Error al obtener su00edmbolos con fundamentales: {str(e)}")
            return []
    
    @staticmethod
    def get_with_momentum(region=None, strategy=None):
        try:
            query = """
            SELECT s.*, m.* 
            FROM symbols s 
            LEFT JOIN momentum m ON s.ticker = m.ticker
            """
            
            conditions = ["m.asof = (SELECT MAX(asof) FROM momentum)"]
            params = []
            
            if region:
                conditions.append("s.region = ANY(%s)")
                params.append(region.split(','))
                
            if strategy:
                conditions.append("s.strategy = %s")
                params.append(strategy)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            result = db.query(query, params)
            return result.get("rows", [])
        except Exception as e:
            logging.error(f"Error al obtener su00edmbolos con momentum: {str(e)}")
            return []
    
    @staticmethod
    def get_growth_screener(min_growth=0.20, region="US,EU,CN,IN"):
        try:
            query = """
            SELECT * FROM fundamentals f
            JOIN momentum m USING(ticker)
            JOIN symbols s USING(ticker)
            WHERE s.region = ANY(%s)
              AND f.yoy_rev_growth >= %s
              AND f.gross_margin >= 0.40
              AND f.roe_ttm >= 0.15
              AND f.forward_pe <= 40
              AND m.return_6m >= 0.20
              AND m.sma50 > m.sma200
            ORDER BY f.yoy_rev_growth DESC
            LIMIT 30
            """
            
            result = db.query(query, [region.split(','), min_growth])
            return result.get("rows", [])
        except Exception as e:
            logging.error(f"Error en growth screener: {str(e)}")
            return []
    
    @staticmethod
    def get_value_screener():
        try:
            query = """
            SELECT * FROM fundamentals f
            JOIN symbols s USING(ticker)
            WHERE s.strategy = 'value'
              AND f.forward_pe < 15
              AND f.roe_ttm > 0.10
            ORDER BY f.forward_pe ASC
            LIMIT 30
            """
            
            result = db.query(query)
            return result.get("rows", [])
        except Exception as e:
            logging.error(f"Error en value screener: {str(e)}")
            return []
