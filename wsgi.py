# Archivo WSGI para despliegue en producciu00f3n - Versiu00f3n independiente
import os
import sys

# Importar la aplicaciu00f3n desde main.py (que ahora es independiente)
from main import app as application

# Para ejecutar localmente con uvicorn
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("wsgi:application", host="0.0.0.0", port=port)
