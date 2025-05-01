@echo off
echo Iniciando Value Investing Application...

echo.
echo [1/3] Verificando entorno virtual de Python...
IF NOT EXIST venv (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate
    echo Instalando dependencias...
    pip install -r requirements.txt
) ELSE (
    echo Activando entorno virtual existente...
    call venv\Scripts\activate
)

echo.
echo [2/3] Iniciando backend en segundo plano...
start cmd /k "echo Iniciando servidor FastAPI... && uvicorn backend.main:app --reload --port 8000"

echo.
echo [3/3] Esperando 5 segundos para que el backend inicie...
timeout /t 5 /nobreak > nul

echo.
echo Abriendo documentación de la API...
start http://localhost:8000/docs

echo.
echo Value Investing Application iniciada correctamente.
echo - Backend: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo.
echo Presiona Ctrl+C para detener la aplicación.

pause
