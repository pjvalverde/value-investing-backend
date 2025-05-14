import os
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("env-loader")

# Cargar variables de entorno desde .env
try:
    load_dotenv()
    logger.info("Variables de entorno cargadas desde .env")
    
    # Verificar si las API keys estu00e1n configuradas
    alphavantage_key = os.getenv("ALPHAVANTAGE_API_KEY")
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    if alphavantage_key:
        logger.info("ALPHAVANTAGE_API_KEY configurada correctamente")
        print(f"ALPHAVANTAGE_API_KEY: {alphavantage_key[:5]}...")
    else:
        logger.warning("ALPHAVANTAGE_API_KEY no configurada")
        print("ALPHAVANTAGE_API_KEY: No configurada")
    
    if perplexity_key:
        logger.info("PERPLEXITY_API_KEY configurada correctamente")
        print(f"PERPLEXITY_API_KEY: {perplexity_key[:5]}...")
    else:
        logger.warning("PERPLEXITY_API_KEY no configurada")
        print("PERPLEXITY_API_KEY: No configurada")
    
except Exception as e:
    logger.error(f"Error cargando variables de entorno: {str(e)}")
    print(f"Error: {str(e)}")
