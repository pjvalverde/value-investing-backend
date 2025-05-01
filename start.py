# Archivo de inicio simplificado para Railway
import os
import uvicorn

# Ejecutar la aplicaciu00f3n directamente
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app_standalone:app", host="0.0.0.0", port=port)
