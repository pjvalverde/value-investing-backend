# Value Investing Application

Una aplicaciu00f3n completa para ayudar a inversionistas a construir portfolios basados en principios de Value Investing y Growth, con optimizaciu00f3n de carteras y anu00e1lisis fundamental.

## Arquitectura de la Aplicaciu00f3n

La aplicaciu00f3n estu00e1 dividida en dos componentes principales:

### Backend (FastAPI)

- **Modelos**: Definiciu00f3n de la estructura de datos y lu00f3gica de negocio
  - `db.py`: Conexiu00f3n a la base de datos PostgreSQL y definiciu00f3n de tablas
  - `symbols.py`: Modelo para manejar su00edmbolos/acciones y screeners
  - `portfolios.py`: Modelo para la gestiu00f3n y optimizaciu00f3n de portfolios

- **Rutas**: Endpoints de la API
  - `screener.py`: Endpoints para filtrar acciones por criterios de value y growth
  - `portfolio.py`: Endpoints para crear, optimizar y analizar portfolios

- **Jobs**: Tareas programadas para actualizar datos
  - `refresh_fundamentals.js`: Actualiza datos fundamentales desde Alpha Vantage
  - `refresh_prices.js`: Actualiza precios y calcula indicadores de momentum
  - `recalc_performance.js`: Recalcula el rendimiento de los portfolios

### Frontend (React)

- **Componentes Principales**:
  - Portfolio Tradicional: Permite crear portfolios basados en criterios clu00e1sicos
  - Portfolio Builder: Interfaz moderna para optimizar carteras segu00fan diferentes estrategias
  - Screeners: Filtros para encontrar acciones value y growth
  - Visualizaciones: Gru00e1ficos y tablas para analizar rendimiento

## Funcionalidades Principales

### 1. Screeners de Acciones

- **Value Screener**: Filtra acciones basadas en criterios de valor como P/E bajo, P/B bajo, dividendos, etc.
- **Growth Screener**: Identifica acciones con alto crecimiento de ingresos, buenos mu00e1rgenes y momentum positivo

### 2. Portfolio Builder

- **Asignaciu00f3n de Activos**: Distribuciu00f3n entre bonos, acciones value y acciones growth
- **Optimizaciu00f3n de Portfolio**: Utiliza la API de Claude para generar portfolios optimizados
- **Visualizaciu00f3n de Resultados**: Gru00e1ficos de distribuciu00f3n y tablas de posiciones

### 3. Anu00e1lisis y Seguimiento

- **Comparaciu00f3n con u00cdndices**: Compara el rendimiento con el S&P 500
- **Anu00e1lisis Fundamental**: Evaluaciu00f3n detallada de cada acciu00f3n en el portfolio
- **Datos Histu00f3ricos**: Visualizaciu00f3n de rendimiento histu00f3rico

## Tecnologu00edas Utilizadas

- **Backend**: FastAPI, PostgreSQL, psycopg2
- **Frontend**: React, Recharts
- **APIs Externas**: Alpha Vantage (datos de mercado), Claude (optimizaciu00f3n)
- **Despliegue**: Railway (backend y jobs programados)

## Instalaciu00f3n y Configuraciu00f3n

### Requisitos Previos

- Node.js (v14 o superior)
- PostgreSQL (v12 o superior)
- Python (v3.8 o superior)

### Variables de Entorno

Crea un archivo `.env` en la rau00edz del proyecto backend con las siguientes variables:

```
DATABASE_URL=postgresql://usuario:contraseu00f1a@localhost:5432/value_investing
ALPHAVANTAGE_API_KEY=tu_clave_de_api
CLAUDE_API_KEY=tu_clave_de_api_claude
```

### Instalaciu00f3n del Backend

1. Clona el repositorio
2. Navega al directorio del backend
3. Instala las dependencias de Python:
   ```
   pip install -r requirements.txt
   ```
4. Inicializa la base de datos:
   ```
   python -m backend.models.db
   ```
5. Inicia el servidor:
   ```
   uvicorn backend.main:app --reload
   ```

### Instalaciu00f3n del Frontend

1. Navega al directorio del frontend
2. Instala las dependencias:
   ```
   npm install
   ```
3. Crea un archivo `.env` con:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```
4. Inicia la aplicaciu00f3n:
   ```
   npm start
   ```

## Despliegue en Railway

La aplicaciu00f3n estu00e1 configurada para ser desplegada en Railway con los siguientes servicios:

1. **Servicio Backend**: Ejecuta la API FastAPI
2. **Servicio PostgreSQL**: Base de datos para almacenar informaciu00f3n de portfolios y acciones
3. **Servicio Jobs**: Ejecuta las tareas programadas para actualizar datos

Configura las mismas variables de entorno en Railway que se mencionaron anteriormente.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir los cambios importantes antes de realizar un pull request.
