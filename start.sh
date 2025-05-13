#!/bin/bash

# Obtener el puerto de la variable de entorno PORT o usar 8000 como valor predeterminado
PORT=${PORT:-8000}

# Iniciar la aplicación con uvicorn
exec uvicorn app_direct:app --host 0.0.0.0 --port $PORT
