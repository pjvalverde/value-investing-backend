FROM python:3.9-slim

WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el cu00f3digo de la aplicaciu00f3n
COPY . .

# Configurar variables de entorno
ENV PORT=${PORT}

# Exponer el puerto
EXPOSE $PORT

# Comando para ejecutar la aplicaciu00f3n
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
