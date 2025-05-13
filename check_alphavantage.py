import os
import requests
import json
from datetime import datetime

# Función para verificar la API key de Alpha Vantage
def check_alpha_vantage_key():
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    
    if not api_key:
        print("ERROR: No se encontró la API key de Alpha Vantage en las variables de entorno.")
        print("Asegúrate de configurar ALPHAVANTAGE_API_KEY en las variables de entorno de Railway.")
        return False
    
    # Ocultar parte de la clave para mostrarla de forma segura
    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
    print(f"API key encontrada: {masked_key}")
    
    # Probar la API key con una solicitud simple
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey={api_key}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "Global Quote" in data and data["Global Quote"]:
            price = data["Global Quote"].get("05. price")
            print(f"API key válida. Precio actual de AAPL: ${price}")
            return True
        elif "Note" in data and "API call frequency" in data["Note"]:
            print(f"ADVERTENCIA: Límite de frecuencia de API alcanzado. Mensaje: {data['Note']}")
            print("Estás usando el plan gratuito que tiene limitaciones (5 llamadas por minuto, 500 por día).")
            print("Considera actualizar a un plan pagado para más solicitudes: https://www.alphavantage.co/premium/")
            return True
        else:
            print(f"ERROR: La API key parece no ser válida o hay un problema con Alpha Vantage.")
            print(f"Respuesta: {json.dumps(data, indent=2)}")
            return False
    except Exception as e:
        print(f"ERROR al probar la API key: {str(e)}")
        return False

# Función para verificar el servicio de Alpha Vantage
def check_alpha_vantage_service():
    print("\n=== Verificando servicio de Alpha Vantage ===")
    
    # Verificar la API key
    if not check_alpha_vantage_key():
        return
    
    # Verificar límites de la API
    print("\n=== Información sobre límites de Alpha Vantage ===")
    print("Plan gratuito: 5 llamadas por minuto, 500 por día")
    print("Si necesitas más llamadas, considera actualizar a un plan pagado.")
    
    # Verificar si hay un archivo de caché para Alpha Vantage
    print("\n=== Verificando implementación de caché ===")
    try:
        import app_railway
        if hasattr(app_railway, 'alpha_client') and hasattr(app_railway.alpha_client, 'cache'):
            cache_size = len(app_railway.alpha_client.cache)
            print(f"Caché implementada. Elementos en caché: {cache_size}")
            
            # Mostrar elementos en caché
            if cache_size > 0:
                print("\nElementos en caché:")
                for ticker, data in app_railway.alpha_client.cache.items():
                    timestamp = data.get("timestamp")
                    if timestamp:
                        age = (datetime.now() - timestamp).seconds
                        print(f"- {ticker}: {age} segundos de antigüedad")
        else:
            print("No se pudo verificar la implementación de caché.")
    except Exception as e:
        print(f"Error al verificar la caché: {str(e)}")

if __name__ == "__main__":
    print("=== Verificador de configuración de Alpha Vantage ===")
    check_alpha_vantage_service()
