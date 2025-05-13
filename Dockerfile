FROM python:3.11-slim

WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el cu00f3digo de la aplicaciu00f3n
COPY . .

# Dar permisos de ejecuciu00f3n al script de inicio
RUN chmod +x start.sh

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicaciu00f3n
CMD ["/bin/bash", "start.sh"]
