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
            raise ValueError("Alpha Vantage API key not configured")
        
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
        """Get real-time price for a ticker with fallback mechanisms"""
        cache_key = f"price_{ticker}"
        
        # Try to get from cache first (short expiry for prices)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Common prices as fallback
        common_prices = {
            "AAPL": 175.34, "MSFT": 402.78, "JNJ": 147.56, "V": 275.96, "JPM": 198.47,
            "VOO": 470.15, "QQQ": 438.27, "SPY": 468.32, "VTI": 252.18, "AGG": 108.45,
            "BND": 72.36, "T-BILL": 100.00
        }
        
        # Try different endpoints with fallback
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
        
        # Fallback to predefined prices
        if ticker in common_prices:
            price = common_prices[ticker]
            logger.info(f"Using predefined price for {ticker}: ${price}")
            result = {"ticker": ticker, "price": price, "source": "PREDEFINED"}
            self._store_in_cache(cache_key, result, expiry_minutes=30)  # Longer cache for fallback
            return result
        
        # Last resort: simulate a price
        if ticker.startswith("T-") or "BOND" in ticker.upper() or ticker == "AGG" or ticker == "BND":
            # For bonds and bond ETFs
            simulated_price = round(random.uniform(95, 105), 2)
        elif any(etf in ticker for etf in ["VOO", "SPY", "QQQ", "VTI", "IVV"]):
            # For major ETFs
            simulated_price = round(random.uniform(200, 500), 2)
        else:
            # For stocks
            simulated_price = round(random.uniform(100, 400), 2)
        
        logger.warning(f"Using simulated price for {ticker}: ${simulated_price}")
        result = {"ticker": ticker, "price": simulated_price, "simulated": True}
        self._store_in_cache(cache_key, result, expiry_minutes=60)  # Longer cache for simulated
        return result
    
    def get_historical_prices(self, ticker: str, period: str = "1year") -> Dict[str, Any]:
        """Get historical price data for a ticker"""
        cache_key = f"historical_{ticker}_{period}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        try:
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
            
            raise ValueError(f"No {result_key} data found in response")
            
        except Exception as e:
            logger.error(f"Error getting historical prices for {ticker}: {str(e)}")
            # Fallback to simulated data
            return self._generate_simulated_historical_data(ticker, period)
    
    def _generate_simulated_historical_data(self, ticker: str, period: str) -> Dict[str, Any]:
        """Generate simulated historical price data as a fallback"""
        logger.warning(f"Generating simulated historical data for {ticker}")
        
        # Determine number of data points based on period
        if period == "5years":
            num_points = 60  # Monthly for 5 years
            days_delta = 30
        elif period == "1year":
            num_points = 52  # Weekly for 1 year
            days_delta = 7
        elif period == "3months":
            num_points = 90  # Daily for 3 months
            days_delta = 1
        else:
            num_points = 30  # Default: daily for 1 month
            days_delta = 1
        
        # Base price depends on ticker type
        if ticker.startswith("T-") or "BOND" in ticker.upper() or ticker == "AGG" or ticker == "BND":
            base_price = 100.0
            volatility = 0.01  # Low volatility for bonds
        elif any(etf in ticker for etf in ["VOO", "SPY", "QQQ", "VTI", "IVV"]):
            base_price = 350.0
            volatility = 0.015  # Medium volatility for ETFs
        else:
            base_price = 200.0
            volatility = 0.025  # Higher volatility for stocks
        
        # Generate time series
        end_date = datetime.now()
        processed_data = []
        
        current_price = base_price
        for i in range(num_points):
            date = end_date - timedelta(days=i * days_delta)
            date_str = date.strftime("%Y-%m-%d")
            
            # Random daily change with trend
            daily_change = random.normalvariate(0.0002, volatility)  # Slight upward bias
            current_price *= (1 + daily_change)
            
            # Generate OHLC data
            daily_volatility = current_price * volatility * 0.5
            open_price = current_price * (1 + random.uniform(-0.005, 0.005))
            high_price = max(open_price, current_price) * (1 + random.uniform(0.001, 0.01))
            low_price = min(open_price, current_price) * (1 - random.uniform(0.001, 0.01))
            
            processed_data.append({
                "date": date_str,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(current_price, 2),
                "volume": int(random.uniform(1000000, 10000000))
            })
        
        # Sort by date (ascending)
        processed_data.sort(key=lambda x: x["date"])
        
        return {
            "ticker": ticker,
            "period": period,
            "data": processed_data,
            "simulated": True
        }
    
    def get_stock_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Get fundamental data for a stock"""
        cache_key = f"fundamentals_{ticker}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        try:
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
            
            raise ValueError(f"No fundamental data found for {ticker}")
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {ticker}: {str(e)}")
            # Fallback to simulated data
            return self._generate_simulated_fundamentals(ticker)
    
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
    
    def _generate_simulated_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Generate simulated fundamental data as a fallback"""
        logger.warning(f"Generating simulated fundamental data for {ticker}")
        
        # Predefined fundamentals for common stocks
        predefined = {
            "AAPL": {"name": "Apple Inc.", "sector": "Technology", "ROE": 30, "P/E": 28, "Margen de Beneficio": 23, "Ratio de Deuda": 0.5, "Moat": "Alto"},
            "MSFT": {"name": "Microsoft Corp.", "sector": "Technology", "ROE": 35, "P/E": 32, "Margen de Beneficio": 31, "Ratio de Deuda": 0.4, "Moat": "Alto"},
            "JNJ": {"name": "Johnson & Johnson", "sector": "Healthcare", "ROE": 25, "P/E": 18, "Margen de Beneficio": 20, "Ratio de Deuda": 0.3, "Moat": "Medio"},
            "V": {"name": "Visa Inc.", "sector": "Financial Services", "ROE": 40, "P/E": 34, "Margen de Beneficio": 51, "Ratio de Deuda": 0.5, "Moat": "Alto"},
            "JPM": {"name": "JPMorgan Chase", "sector": "Financial Services", "ROE": 18, "P/E": 12, "Margen de Beneficio": 25, "Ratio de Deuda": 0.8, "Moat": "Medio"},
            "VOO": {"name": "Vanguard S&P 500 ETF", "sector": "ETF", "ROE": 16, "P/E": 22, "Margen de Beneficio": 18, "Ratio de Deuda": 0.4, "Moat": "Diversificado"},
            "QQQ": {"name": "Invesco QQQ Trust", "sector": "ETF", "ROE": 18, "P/E": 25, "Margen de Beneficio": 20, "Ratio de Deuda": 0.5, "Moat": "Diversificado"},
            "SPY": {"name": "SPDR S&P 500 ETF", "sector": "ETF", "ROE": 15, "P/E": 21, "Margen de Beneficio": 17, "Ratio de Deuda": 0.4, "Moat": "Diversificado"},
            "AGG": {"name": "iShares Core U.S. Aggregate Bond ETF", "sector": "ETF", "ROE": None, "P/E": None, "Margen de Beneficio": None, "Ratio de Deuda": None, "Moat": "Diversificado"}
        }
        
        if ticker in predefined:
            data = predefined[ticker]
            fundamentals = {
                "ticker": ticker,
                "name": data["name"],
                "sector": data["sector"],
                "industry": "Simulated",
                "metrics": {
                    "ROE": data["ROE"],
                    "P/E": data["P/E"],
                    "Margen de Beneficio": data["Margen de Beneficio"],
                    "Ratio de Deuda": data["Ratio de Deuda"],
                    "Crecimiento de FCF": round(random.uniform(5, 20), 1),
                    "Moat Cualitativo": data["Moat"]
                },
                "additional": {
                    "MarketCap": str(int(random.uniform(50000000000, 2000000000000))),
                    "Beta": str(round(random.uniform(0.8, 1.5), 2)),
                    "DividendYield": str(round(random.uniform(0.5, 3.5), 2)),
                    "EPS": str(round(random.uniform(1, 15), 2)),
                    "52WeekHigh": str(round(random.uniform(100, 500), 2)),
                    "52WeekLow": str(round(random.uniform(50, 300), 2))
                },
                "simulated": True
            }
        else:
            # Generate random data for unknown tickers
            if ticker.startswith("T-") or "BOND" in ticker.upper() or ticker == "AGG" or ticker == "BND":
                # For bonds
                sector = "Fixed Income"
                metrics = {
                    "ROE": None,
                    "P/E": None,
                    "Margen de Beneficio": None,
                    "Ratio de Deuda": None,
                    "Crecimiento de FCF": None,
                    "Moat Cualitativo": None
                }
            elif any(etf in ticker for etf in ["VOO", "SPY", "QQQ", "VTI", "IVV"]):
                # For ETFs
                sector = "ETF"
                metrics = {
                    "ROE": round(random.uniform(10, 20), 1),
                    "P/E": round(random.uniform(15, 25), 1),
                    "Margen de Beneficio": round(random.uniform(10, 25), 1),
                    "Ratio de Deuda": round(random.uniform(0.3, 0.6), 2),
                    "Crecimiento de FCF": round(random.uniform(5, 15), 1),
                    "Moat Cualitativo": "Diversificado"
                }
            else:
                # For stocks
                sector = random.choice(["Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Industrials"])
                metrics = {
                    "ROE": round(random.uniform(10, 40), 1),
                    "P/E": round(random.uniform(10, 50), 1),
                    "Margen de Beneficio": round(random.uniform(5, 40), 1),
                    "Ratio de Deuda": round(random.uniform(0.1, 0.9), 2),
                    "Crecimiento de FCF": round(random.uniform(5, 30), 1),
                    "Moat Cualitativo": random.choice(["Bajo", "Medio", "Alto"])
                }
            
            fundamentals = {
                "ticker": ticker,
                "name": f"{ticker} Corporation",
                "sector": sector,
                "industry": "Simulated",
                "metrics": metrics,
                "additional": {
                    "MarketCap": str(int(random.uniform(1000000000, 500000000000))),
                    "Beta": str(round(random.uniform(0.5, 2.0), 2)),
                    "DividendYield": str(round(random.uniform(0, 5), 2)),
                    "EPS": str(round(random.uniform(0.5, 10), 2)),
                    "52WeekHigh": str(round(random.uniform(50, 400), 2)),
                    "52WeekLow": str(round(random.uniform(30, 300), 2))
                },
                "simulated": True
            }
        
        # Cache for a shorter period since it's simulated
        self._store_in_cache(f"fundamentals_{ticker}", fundamentals, expiry_minutes=720)  # 12 hours
        return fundamentals

# Create a singleton instance
alpha_vantage_client = AlphaVantageClient()
