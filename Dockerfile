FROM python:3.11-slim

WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el cu00f3digo de la aplicaciu00f3n
COPY . .

# Configurar variables de entorno
ENV PORT=8000

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicaciu00f3n
CMD ["uvicorn", "app_direct:app", "--host", "0.0.0.0", "--port", "8000"]
