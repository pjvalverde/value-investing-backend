import os
import json
import requests
from datetime import datetime

# Verificar que la API key esté configurada
api_key = os.getenv("PERPLEXITY_API_KEY")
if not api_key:
    print("ERROR: PERPLEXITY_API_KEY no está configurada en las variables de entorno")
    exit(1)

print(f"API key encontrada: {api_key[:5]}...")

# Hacer una solicitud de prueba a Perplexity API
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": "sonar-medium-online",
    "messages": [
        {
            "role": "system",
            "content": "Eres un asistente especializado en finanzas e inversiones. Responde siempre en formato JSON válido."
        },
        {
            "role": "user",
            "content": "Dame una lista de 3 acciones value que cumplan con los principios de Warren Buffett. Formato JSON."
        }
    ]
}

print("Enviando solicitud a Perplexity API...")
try:
    response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
    
    if response.status_code != 200:
        print(f"Error en Perplexity API: {response.status_code} - {response.text}")
        exit(1)
        
    response_data = response.json()
    print("Respuesta recibida de Perplexity API")
    
    # Extraer el texto de la respuesta
    response_text = response_data["choices"][0]["message"]["content"]
    print("\nRespuesta de Perplexity:")
    print(response_text)
    
    # Intentar extraer el JSON
    start_idx = response_text.find("[")
    end_idx = response_text.rfind("]")
    
    if start_idx != -1 and end_idx != -1:
        json_str = response_text[start_idx:end_idx+1]
        try:
            stocks_data = json.loads(json_str)
            print("\nJSON extraído correctamente:")
            print(json.dumps(stocks_data, indent=2))
            print(f"\nSe obtuvieron {len(stocks_data)} acciones value con Perplexity")
        except json.JSONDecodeError as e:
            print(f"Error al parsear JSON: {str(e)}\nJSON: {json_str}")
    else:
        print("No se encontró un array JSON en la respuesta")
        
except Exception as e:
    print(f"Error al consultar Perplexity API: {str(e)}")
