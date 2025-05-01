# Este archivo simplifica la ejecuciu00f3n de la aplicaciu00f3n FastAPI
import os
import sys
import uvicorn

# Agregar el directorio actual al path de Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importar la aplicaciu00f3n FastAPI desde el mu00f3dulo backend
from backend.main import app

# Ejecutar la aplicaciu00f3n si se ejecuta este archivo directamente
if __name__ == "__main__":
    # Cargar variables de entorno si existe un archivo .env
    from dotenv import load_dotenv
    load_dotenv()
    
    # Ejecutar la aplicaciu00f3n FastAPI
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
