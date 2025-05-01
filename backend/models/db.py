import os
import psycopg2
import psycopg2.extras
import logging
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            # Obtener la URL de conexión de las variables de entorno
            db_url = os.getenv('DATABASE_URL')
            
            if not db_url:
                logging.warning("DATABASE_URL no está configurada. Usando base de datos en memoria.")
                # Si no hay URL de base de datos, usamos una simulación en memoria
                self.conn = None
                return
            
            self.conn = psycopg2.connect(db_url)
            self.conn.autocommit = True
            logging.info("Conexión a la base de datos establecida correctamente")
            
            # Crear tablas si no existen
            self.create_tables()
            
        except Exception as e:
            logging.error(f"Error al conectar a la base de datos: {str(e)}")
            self.conn = None
    
    def create_tables(self):
        if not self.conn:
            return
        
        try:
            cursor = self.conn.cursor()
            
            # Crear tabla de usuarios (para futuras extensiones)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Crear tabla de portfolios
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id UUID PRIMARY KEY,
                user_id UUID REFERENCES users(id),
                name TEXT NOT NULL,
                target_alloc JSONB NOT NULL, -- {"bonds":25,"value":50,"growth":25}
                current_alloc JSONB, -- cantidades actuales
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Crear tabla de símbolos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                region TEXT,
                strategy TEXT -- "value" | "growth"
            )
            """)
            
            # Crear tabla de fundamentales
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                ticker TEXT REFERENCES symbols(ticker),
                yoy_rev_growth NUMERIC,
                gross_margin NUMERIC,
                roe_ttm NUMERIC,
                forward_pe NUMERIC,
                price NUMERIC,
                asof DATE,
                PRIMARY KEY (ticker, asof)
            )
            """)
            
            # Crear tabla de momentum
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS momentum (
                ticker TEXT REFERENCES symbols(ticker),
                sma50 NUMERIC,
                sma200 NUMERIC,
                return_6m NUMERIC,
                asof DATE,
                PRIMARY KEY (ticker, asof)
            )
            """)
            
            cursor.close()
            logging.info("Tablas creadas correctamente")
            
        except Exception as e:
            logging.error(f"Error al crear tablas: {str(e)}")
    
    def query(self, sql, params=None):
        if not self.conn:
            # Simulación en memoria para desarrollo
            if "symbols" in sql.lower() and "strategy" in sql.lower():
                return self.mock_symbols_query(sql)
            return {"rows": []}
        
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(sql, params or ())
            
            if sql.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                cursor.close()
                return {"rows": result}
            else:
                affected = cursor.rowcount
                cursor.close()
                return {"affected": affected}
                
        except Exception as e:
            logging.error(f"Error en consulta SQL: {str(e)}\nSQL: {sql}")
            return {"error": str(e)}
    
    def mock_symbols_query(self, sql):
        # Datos simulados para desarrollo sin base de datos
        if "strategy = 'value'" in sql.lower():
            return {
                "rows": [
                    {"ticker": "AAPL", "price": 175.50},
                    {"ticker": "MSFT", "price": 325.20},
                    {"ticker": "JNJ", "price": 152.75},
                    {"ticker": "PG", "price": 145.30},
                    {"ticker": "JPM", "price": 138.40}
                ]
            }
        elif "strategy = 'growth'" in sql.lower():
            return {
                "rows": [
                    {"ticker": "NVDA", "price": 450.80},
                    {"ticker": "TSLA", "price": 220.50},
                    {"ticker": "AMZN", "price": 178.30},
                    {"ticker": "GOOGL", "price": 142.60},
                    {"ticker": "META", "price": 480.25}
                ]
            }
        else:
            return {"rows": []}

# Instancia global de la base de datos
db = Database()
