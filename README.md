# Value Investing Backend API - Updated 05/13/2025 04:11:23

Backend API for the Value Investing Portfolio application. This API provides stock data, portfolio management, and investment analysis.

## Features

- Real-time stock prices from AlphaVantage API
- Portfolio creation and optimization
- Stock screening for value and growth investments
- Investment analysis powered by Claude AI

## Deployment on Railway

The application is configured to deploy on Railway platform.

### Deployment Configuration

- **Environment Variables**:
  - `PORT`: Set automatically by Railway
  - `ALPHAVANTAGE_API_KEY`: Your Alpha Vantage API key
  - `CLAUDE_API_KEY`: Your Claude API key

- **Health Check**:
  - Path: `/test`
  - Timeout: 100 seconds

### Deployment Steps

1. Create a new project on Railway
2. Add environment variables (ALPHAVANTAGE_API_KEY, CLAUDE_API_KEY)
3. Deploy the repository
4. The application will be accessible at the generated URL

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app_railway.py

# Or use the simplified version for testing
python app_simple.py
```

## API Endpoints

- `/`: Root endpoint - API status
- `/test`: Health check endpoint
- `/real_time_price/{ticker}`: Get real-time stock prices
- `/historical_prices/{ticker}`: Get historical price data
- `/api/portfolio/create`: Create a new portfolio
- `/api/portfolio/optimize`: Optimize portfolio allocation
- `/api/screener/value`: Screen for value stocks
- `/api/screener/growth`: Screen for growth stocks

## Frontend Repository

The frontend application is available at: https://github.com/pjvalverde/value-investing-portfolio


<!-- Cambio menor para forzar redeploy automático en Heroku -->
