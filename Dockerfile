FROM python:3.11-slim

WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el cu00f3digo de la aplicaciu00f3n
COPY app_direct.py .

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicaciu00f3n
CMD ["python", "app_direct.py"]
