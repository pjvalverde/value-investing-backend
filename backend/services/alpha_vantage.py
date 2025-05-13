import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alpha_vantage_service")

class AlphaVantageClient:
    """Client for Alpha Vantage API with caching, rate limiting and error handling"""
    
    def __init__(self):
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
        self.cache = {}
        self.cache_expiry = {}
        self.last_request_time = 0
        self.rate_limit_delay = 12  # Seconds between requests (Alpha Vantage free tier: 5 requests per minute)
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed API rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            logger.info(f"Rate limiting: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if it exists and is not expired"""
        if cache_key in self.cache and cache_key in self.cache_expiry:
            if datetime.now() < self.cache_expiry[cache_key]:
                logger.info(f"Cache hit for {cache_key}")
                return self.cache[cache_key]
            else:
                logger.info(f"Cache expired for {cache_key}")
                del self.cache[cache_key]
                del self.cache_expiry[cache_key]
        
        return None
    
    def _store_in_cache(self, cache_key: str, data: Dict, expiry_minutes: int = 60):
        """Store data in cache with expiration time"""
        self.cache[cache_key] = data
        self.cache_expiry[cache_key] = datetime.now() + timedelta(minutes=expiry_minutes)
        logger.info(f"Cached data for {cache_key} (expires in {expiry_minutes} minutes)")
    
    def _make_request(self, params: Dict[str, str], cache_key: str = None, expiry_minutes: int = 60) -> Dict:
        """Make a request to Alpha Vantage API with caching and error handling"""
        if not self.api_key:
            logger.error("Alpha Vantage API key not configured")
            raise ValueError("Alpha Vantage API key not configured. Please set the ALPHAVANTAGE_API_KEY environment variable.")
        
        # Check cache first if cache_key provided
        if cache_key:
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Add API key to params
        params["apikey"] = self.api_key
        
        # Respect rate limits
        self._respect_rate_limit()
        
        try:
            logger.info(f"Making request to Alpha Vantage: {params}")
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Check for API error messages
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                raise ValueError(f"Alpha Vantage API error: {data['Error Message']}")
            
            if "Note" in data and "API call frequency" in data["Note"]:
                logger.warning(f"Alpha Vantage rate limit warning: {data['Note']}")
            
            # Cache the result if cache_key provided
            if cache_key:
                self._store_in_cache(cache_key, data, expiry_minutes)
            
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Value error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
    
    def get_real_time_price(self, ticker: str) -> Dict[str, Any]:
        """Get real-time price for a ticker without fallback to simulated data"""
        cache_key = f"price_{ticker}"
        
        # Try to get from cache first (short expiry for prices)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Try different endpoints
        for attempt, (function, result_key, price_key) in enumerate([
            ("GLOBAL_QUOTE", "Global Quote", "05. price"),
            ("TIME_SERIES_DAILY", "Time Series (Daily)", "4. close")
        ]):
            try:
                if attempt > 0:
                    # Add delay between attempts
                    time.sleep(1)
                
                params = {"function": function, "symbol": ticker}
                data = self._make_request(params)
                
                if function == "GLOBAL_QUOTE" and result_key in data and price_key in data[result_key]:
                    price = float(data[result_key][price_key])
                    result = {"ticker": ticker, "price": price, "source": "GLOBAL_QUOTE"}
                    self._store_in_cache(cache_key, result, expiry_minutes=15)  # Short cache for prices
                    return result
                
                elif function == "TIME_SERIES_DAILY" and result_key in data:
                    # Get the most recent date
                    latest_date = list(data[result_key].keys())[0]
                    price = float(data[result_key][latest_date][price_key])
                    result = {"ticker": ticker, "price": price, "source": "TIME_SERIES_DAILY"}
                    self._store_in_cache(cache_key, result, expiry_minutes=15)
                    return result
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for {ticker}: {str(e)}")
        
        # If we reach here, no valid data was found
        error_msg = f"Could not retrieve real-time price data for {ticker} from Alpha Vantage API"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def get_historical_prices(self, ticker: str, period: str = "1year") -> Dict[str, Any]:
        """Get historical price data for a ticker without fallback to simulated data"""
        cache_key = f"historical_{ticker}_{period}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Map period to appropriate function and parameters
        if period == "5years":
            function = "TIME_SERIES_MONTHLY"
            output_size = "full"
            result_key = "Monthly Time Series"
        elif period == "1year":
            function = "TIME_SERIES_WEEKLY"
            output_size = "compact"
            result_key = "Weekly Time Series"
        elif period == "3months":
            function = "TIME_SERIES_DAILY"
            output_size = "compact"
            result_key = "Time Series (Daily)"
        else:
            function = "TIME_SERIES_DAILY"
            output_size = "compact"
            result_key = "Time Series (Daily)"
        
        params = {
            "function": function,
            "symbol": ticker,
            "outputsize": output_size
        }
        
        data = self._make_request(params)
        
        if result_key in data:
            # Process the time series data
            time_series = data[result_key]
            processed_data = []
            
            for date, values in time_series.items():
                processed_data.append({
                    "date": date,
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0))
                })
            
            # Sort by date
            processed_data.sort(key=lambda x: x["date"])
            
            result = {
                "ticker": ticker,
                "period": period,
                "data": processed_data
            }
            
            # Cache for longer period since historical data doesn't change frequently
            self._store_in_cache(cache_key, result, expiry_minutes=240)  # 4 hours
            return result
        
        error_msg = f"No {result_key} data found in response for {ticker}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def get_stock_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental data for a stock without fallback to simulated data"""
        cache_key = f"fundamentals_{ticker}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Try to get overview data
        params = {
            "function": "OVERVIEW",
            "symbol": ticker
        }
        
        data = self._make_request(params)
        
        if "Symbol" in data and data["Symbol"] == ticker:
            # Process the fundamental data
            fundamentals = {
                "ticker": ticker,
                "name": data.get("Name", ""),
                "sector": data.get("Sector", ""),
                "industry": data.get("Industry", ""),
                "metrics": {
                    "ROE": self._parse_percentage(data.get("ReturnOnEquityTTM", "0")),
                    "P/E": float(data.get("PERatio", 0)) if data.get("PERatio") else None,
                    "Margen de Beneficio": self._parse_percentage(data.get("ProfitMargin", "0")),
                    "Ratio de Deuda": float(data.get("DebtToEquity", "0")) / 100 if data.get("DebtToEquity") else None,
                    "Crecimiento de FCF": None,  # Not directly available
                    "Moat Cualitativo": self._determine_moat(data)
                },
                "additional": {
                    "MarketCap": data.get("MarketCapitalization"),
                    "Beta": data.get("Beta"),
                    "DividendYield": data.get("DividendYield"),
                    "EPS": data.get("EPS"),
                    "52WeekHigh": data.get("52WeekHigh"),
                    "52WeekLow": data.get("52WeekLow")
                }
            }
            
            # Cache for a longer period since fundamentals don't change frequently
            self._store_in_cache(cache_key, fundamentals, expiry_minutes=1440)  # 24 hours
            return fundamentals
        
        error_msg = f"No fundamental data found for {ticker}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def _parse_percentage(self, value_str: str) -> Optional[float]:
        """Parse percentage values from Alpha Vantage"""
        try:
            if value_str and value_str != "None":
                return float(value_str) * 100  # Convert to percentage
            return None
        except (ValueError, TypeError):
            return None
    
    def _determine_moat(self, data: Dict[str, Any]) -> str:
        """Determine qualitative moat based on fundamental data"""
        try:
            profit_margin = float(data.get("ProfitMargin", 0)) if data.get("ProfitMargin") else 0
            roe = float(data.get("ReturnOnEquityTTM", 0)) if data.get("ReturnOnEquityTTM") else 0
            gross_margin = float(data.get("GrossProfitTTM", 0)) / float(data.get("RevenueTTM", 1)) if data.get("GrossProfitTTM") and data.get("RevenueTTM") else 0
            
            if profit_margin > 0.2 and roe > 0.2 and gross_margin > 0.4:
                return "Alto"
            elif profit_margin > 0.1 and roe > 0.15 and gross_margin > 0.3:
                return "Medio"
            else:
                return "Bajo"
        except Exception:
            return "Desconocido"

# Create a singleton instance
alpha_vantage_client = AlphaVantageClient()
