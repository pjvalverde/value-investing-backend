import os
import json
import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chart_service")

# Import the Alpha Vantage client
from backend.services.alpha_vantage import alpha_vantage_client

class ChartService:
    """Service for generating chart data for stocks and portfolios"""
    
    def __init__(self):
        self.cache = {}
    
    def get_price_chart_data(self, ticker: str, period: str = "1year") -> Dict[str, Any]:
        """Get price chart data for a ticker"""
            # Get historical prices from Alpha Vantage client
            historical_data = alpha_vantage_client.get_historical_prices(ticker, period)
            
            # Extract data for chart
            dates = [item["date"] for item in historical_data["data"]]
            prices = [item["close"] for item in historical_data["data"]]
            
            # Calculate moving averages if we have enough data
            sma_50 = self._calculate_sma(prices, 50) if len(prices) >= 50 else None
            sma_200 = self._calculate_sma(prices, 200) if len(prices) >= 200 else None
            
            # Calculate performance metrics
            performance = self._calculate_performance(prices)
            
            return {
                "ticker": ticker,
                "period": period,
                "dates": dates,
                "prices": prices,
                "sma_50": sma_50,
                "sma_200": sma_200,
            "performance": performance
            }
    
    def _calculate_sma(self, prices: List[float], window: int) -> List[Optional[float]]:
        """Calculate Simple Moving Average"""
        sma = [None] * (window - 1)  # Start with None values for the first window-1 points
        
        for i in range(window - 1, len(prices)):
            window_slice = prices[i - (window - 1):i + 1]
            sma.append(sum(window_slice) / window)
            
        return sma
    
    def _calculate_performance(self, prices: List[float]) -> Dict[str, float]:
        """Calculate performance metrics"""
        if not prices or len(prices) < 2:
            return {"total": 0, "annualized": 0, "volatility": 0}
        
        # Calculate total return
        start_price = prices[0]
        end_price = prices[-1]
        total_return = (end_price - start_price) / start_price
        
        # Calculate daily returns for volatility
        daily_returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Calculate volatility (standard deviation of returns)
        mean_return = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        volatility = variance ** 0.5
        
        # Annualize based on number of data points
        # Assuming daily data, annualize by multiplying by sqrt(252)
        annualized_volatility = volatility * (252 ** 0.5)
        
        # Annualized return (simplified)
        days = len(prices)
        annualized_return = ((1 + total_return) ** (365 / days)) - 1
        
        return {
            "total": round(total_return * 100, 2),  # as percentage
            "annualized": round(annualized_return * 100, 2),  # as percentage
            "volatility": round(annualized_volatility * 100, 2)  # as percentage
        }
    
    def get_comparative_chart_data(self, tickers: List[str], period: str = "1year") -> Dict[str, Any]:
        """Get comparative chart data for multiple tickers"""
        result = {
            "tickers": tickers,
            "period": period,
            "dates": [],
            "series": [],
            "performance": {}
        }
        
            # Get data for each ticker
            ticker_data = {}
            common_dates = None
            
            for ticker in tickers:
                chart_data = self.get_price_chart_data(ticker, period)
                ticker_data[ticker] = chart_data
                
                # Find common dates across all tickers
                if common_dates is None:
                    common_dates = set(chart_data["dates"])
                else:
                    common_dates = common_dates.intersection(set(chart_data["dates"]))
            
            # Convert back to sorted list
            common_dates = sorted(list(common_dates))
            result["dates"] = common_dates
            
            # Normalize prices to percentage change from first date
            for ticker in tickers:
                data = ticker_data[ticker]
                
                # Find indices of common dates in this ticker's data
                date_indices = [data["dates"].index(date) for date in common_dates if date in data["dates"]]
                
                # Extract prices for common dates
                prices = [data["prices"][i] for i in date_indices]
                
                # Normalize to percentage change from first price
                first_price = prices[0] if prices else 100
                normalized_prices = [((price / first_price) - 1) * 100 for price in prices]
                
                # Add to result
                result["series"].append({
                    "ticker": ticker,
                    "normalized_prices": normalized_prices,
                    "raw_prices": prices
                })
                
                # Add performance metrics
                result["performance"][ticker] = data["performance"]
        
        return result
    
    def get_portfolio_performance_chart(self, portfolio_data: Dict[str, Any], period: str = "1year") -> Dict[str, Any]:
        """Generate portfolio performance chart based on allocation"""
            # Extract tickers and weights from portfolio
            tickers = []
            weights = []
            
            # Process value stocks
            for stock in portfolio_data.get("allocation", {}).get("value", []):
                tickers.append(stock["ticker"])
                weights.append(stock["weight"])
            
            # Process growth stocks
            for stock in portfolio_data.get("allocation", {}).get("growth", []):
                tickers.append(stock["ticker"])
                weights.append(stock["weight"])
            
            # Process bonds
            for bond in portfolio_data.get("allocation", {}).get("bonds", []):
                tickers.append(bond["ticker"])
                weights.append(bond["weight"])
            
            # Get comparative data for all tickers
            comparative_data = self.get_comparative_chart_data(tickers, period)
            
            # Calculate weighted portfolio performance
            portfolio_prices = [0] * len(comparative_data["dates"])
            
            for i, series in enumerate(comparative_data["series"]):
                ticker_weight = weights[i]
                for j, price in enumerate(series["raw_prices"]):
                    # Add weighted contribution to portfolio
                    portfolio_prices[j] += price * ticker_weight
            
            # Normalize portfolio prices
            first_price = portfolio_prices[0] if portfolio_prices else 100
            normalized_portfolio = [((price / first_price) - 1) * 100 for price in portfolio_prices]
            
            # Calculate portfolio performance metrics
            portfolio_performance = self._calculate_performance(portfolio_prices)
        
        # Add portfolio to comparative data
        comparative_data["portfolio"] = {
            "prices": portfolio_prices,
            "normalized_prices": normalized_portfolio,
            "performance": portfolio_performance
        }
        
        return comparative_data

# Create a singleton instance
chart_service = ChartService()
