# Archivo de punto de entrada para Render
# Importa la aplicación desde main.py
from main import app

# Esta variable es necesaria para que gunicorn pueda encontrar la aplicación
# Render busca una variable llamada 'app' por defecto
app = app
