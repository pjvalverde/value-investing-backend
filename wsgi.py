# Archivo WSGI para despliegue en producciu00f3n
import os
import sys

# Obtener el directorio actual
base_dir = os.path.dirname(os.path.abspath(__file__))

# Agregar el directorio al path de Python
sys.path.insert(0, base_dir)

# Importar la aplicaciu00f3n desde backend/main.py
from backend.main import app as application

# Para ejecutar localmente con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("wsgi:application", host="0.0.0.0", port=8000, reload=True)
