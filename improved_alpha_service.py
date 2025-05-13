import os
import json
import logging
import requests
import time
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("alpha_vantage_service")

class ImprovedAlphaVantageClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        self.cache = {}
        self.cache_ttl = 60 * 60  # 1 hora para datos de precios
        self.cache_ttl_fundamentals = 24 * 60 * 60  # 24 horas para datos fundamentales
        self.last_request_time = 0
        self.min_request_interval = 12  # 12 segundos entre solicitudes (para plan gratuito)
        
        # Verificar API key
        if not self.api_key:
            logger.error("API key de Alpha Vantage no configurada. Se usaru00e1n datos simulados.")
            print("ERROR: ALPHAVANTAGE_API_KEY no configurada. Configurar en variables de entorno.")
        else:
            logger.info("Alpha Vantage API key configurada correctamente.")
            print("ALPHAVANTAGE_API_KEY configurada correctamente.")
        
        # Cargar cache si existe
        self._load_cache()
    
    def _load_cache(self):
        """Cargar cache desde archivo si existe"""
        try:
            cache_file = "alpha_vantage_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                    # Convertir timestamps de string a datetime
                    for ticker, data in cache_data.items():
                        if "timestamp" in data:
                            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    
                    self.cache = cache_data
                    logger.info(f"Cache cargada: {len(self.cache)} elementos")
        except Exception as e:
            logger.error(f"Error cargando cache: {str(e)}")
    
    def _save_cache(self):
        """Guardar cache a archivo"""
        try:
            # Convertir datetime a string para serializar
            serializable_cache = {}
            for ticker, data in self.cache.items():
                serializable_cache[ticker] = data.copy()
                if "timestamp" in serializable_cache[ticker]:
                    serializable_cache[ticker]["timestamp"] = serializable_cache[ticker]["timestamp"].isoformat()
            
            with open("alpha_vantage_cache.json", 'w') as f:
                json.dump(serializable_cache, f)
            logger.info(f"Cache guardada: {len(self.cache)} elementos")
        except Exception as e:
            logger.error(f"Error guardando cache: {str(e)}")
    
    def _rate_limit(self):
        """Implementar rate limiting para evitar exceder lu00edmites de API"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_real_time_price(self, ticker):
        """Obtener precio en tiempo real con manejo mejorado de cache y errores"""
        cache_key = f"price_{ticker}"
        
        # Verificar cache
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            cache_age = (datetime.now() - cache_data["timestamp"]).total_seconds()
            
            if cache_age < self.cache_ttl:
                logger.info(f"Usando precio en cachu00e9 para {ticker} (edad: {cache_age:.0f}s)")
                return cache_data["data"]
            else:
                logger.info(f"Cache expirada para price_{ticker}")
        
        # Si no hay API key, usar datos simulados
        if not self.api_key:
            simulated_price = self._get_simulated_price(ticker)
            logger.warning(f"Using simulated price for {ticker}: ${simulated_price}")
            
            result = {
                "price": simulated_price,
                "change_percent": "0.00%",
                "source": "simulated"
            }
            
            # Guardar en cache
            self.cache[cache_key] = {"data": result, "timestamp": datetime.now()}
            self._save_cache()
            
            return result
        
        # Si hay API key, intentar obtener datos reales
        try:
            # Aplicar rate limiting
            self._rate_limit()
            
            # Hacer solicitud a Alpha Vantage
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.api_key}"
            logger.info(f"Making request to Alpha Vantage: {'function': 'GLOBAL_QUOTE', 'symbol': '{ticker}', 'apikey': '{self.api_key[:4]}...'}")
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            # Verificar si hay mensaje de error por lu00edmite de API
            if "Note" in data and "API call frequency" in data["Note"]:
                logger.warning(f"Alpha Vantage API limit reached: {data['Note']}")
                
                # Si hay datos en cache (aunque expirados), usarlos
                if cache_key in self.cache:
                    logger.info(f"Usando datos expirados de cache para {ticker} debido a lu00edmite de API")
                    return self.cache[cache_key]["data"]
                
                # Si no hay cache, usar datos simulados
                simulated_price = self._get_simulated_price(ticker)
                logger.warning(f"Using simulated price for {ticker}: ${simulated_price} (API limit reached)")
                
                result = {
                    "price": simulated_price,
                    "change_percent": "0.00%",
                    "source": "simulated"
                }
                
                return result
            
            # Procesar datos reales
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                price = float(quote.get("05. price", 0))
                
                if price <= 0:
                    raise ValueError(f"Precio invu00e1lido ({price}) obtenido para {ticker}")
                
                change_percent = quote.get("10. change percent", "0%")
                
                result = {
                    "price": price,
                    "change_percent": change_percent,
                    "source": "alpha_vantage"
                }
                
                # Guardar en cache
                self.cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                self._save_cache()
                
                return result
            else:
                # Si no hay datos, intentar usar cache expirada
                if cache_key in self.cache:
                    logger.warning(f"No se encontraron datos para {ticker}, usando cache expirada")
                    return self.cache[cache_key]["data"]
                
                # Si no hay cache, usar datos simulados
                simulated_price = self._get_simulated_price(ticker)
                logger.warning(f"Using simulated price for {ticker}: ${simulated_price} (no data found)")
                
                result = {
                    "price": simulated_price,
                    "change_percent": "0.00%",
                    "source": "simulated"
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error obteniendo precio real para {ticker}: {str(e)}")
            
            # Si hay error, intentar usar cache expirada
            if cache_key in self.cache:
                logger.warning(f"Error en API, usando cache expirada para {ticker}")
                return self.cache[cache_key]["data"]
            
            # No usar datos simulados, lanzar error
            logger.error(f"No se pudo obtener el precio real para {ticker} desde Alpha Vantage")
            raise ValueError(f"No se pudo obtener el precio real para {ticker}. No se usarán datos simulados ni predefinidos.")

# Función para inicializar y probar el cliente
def test_client():
    client = ImprovedAlphaVantageClient()
    
    print("\n=== Probando cliente de Alpha Vantage mejorado ===")
    
    # Probar obtenciu00f3n de precio
    try:
        price_data = client.get_real_time_price("AAPL")
        print(f"Precio de AAPL: ${price_data['price']} (fuente: {price_data['source']})")
        
        # Probar cache
        print("\nProbando cache (segunda solicitud deberu00eda ser instantu00e1nea):")
        start_time = time.time()
        client.get_real_time_price("AAPL")
        elapsed = time.time() - start_time
        print(f"Tiempo de respuesta: {elapsed:.4f} segundos")
        
        # Mostrar estado de cache
        print(f"\nElementos en cache: {len(client.cache)}")
        for key, data in client.cache.items():
            age = (datetime.now() - data["timestamp"]).total_seconds()
            print(f"- {key}: {age:.0f} segundos de antigu00fcedad")
        
    except Exception as e:
        print(f"Error en prueba: {str(e)}")

if __name__ == "__main__":
    test_client()
