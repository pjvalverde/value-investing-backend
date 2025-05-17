import os
import sys
import uvicorn

# Agregar el directorio actual al path de Python para permitir importaciones absolutas
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Crear un archivo .env si no existe
env_file = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_file):
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write('# Variables de entorno para la aplicación\n')
        f.write('DATABASE_URL=\n')

if __name__ == "__main__":
    # Ejecutar la aplicación FastAPI
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
