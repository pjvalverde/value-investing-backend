import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("claude_service")

class ClaudeService:
    """Service for interacting with Claude API for investment analysis"""
    
    def __init__(self):
        self.api_key = os.getenv("CLAUDE_API_KEY")
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.cache = {}  # Simple cache for responses
        self.model = "claude-3-opus-20240229"  # Default model
    
    def _make_request(self, prompt: str, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """Make a request to Claude API with caching"""
        # Check cache first if cache_key provided
        if cache_key and cache_key in self.cache:
            logger.info(f"Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        if not self.api_key:
            logger.error("Claude API key not configured")
            raise ValueError("Claude API key not configured")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": self.model,
            "max_tokens": 4000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            logger.info("Making request to Claude API")
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Extract the response content
            if "content" in result and len(result["content"]) > 0:
                response_content = result["content"][0]["text"]
                
                # Cache the result if cache_key provided
                if cache_key:
                    self.cache[cache_key] = response_content
                    logger.info(f"Cached response for {cache_key}")
                
                return response_content
            else:
                raise ValueError("No content in Claude API response")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"Value error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
    
    def analyze_stock(self, ticker: str, fundamentals: Dict[str, Any]) -> str:
        """Get Claude's analysis of a stock based on fundamentals"""
        try:
            # Create a cache key
            metrics_str = json.dumps(fundamentals["metrics"])
            cache_key = f"stock_analysis_{ticker}_{hash(metrics_str)}"
            
            # Prepare the prompt
            prompt = f"""You are an expert value investing analyst. Please analyze this stock and provide your assessment:

Ticker: {ticker}
Name: {fundamentals.get('name', '')}
Sector: {fundamentals.get('sector', '')}
Industry: {fundamentals.get('industry', '')}

Key Metrics:
- ROE: {fundamentals['metrics'].get('ROE')}
- P/E Ratio: {fundamentals['metrics'].get('P/E')}
- Profit Margin: {fundamentals['metrics'].get('Margen de Beneficio')}
- Debt Ratio: {fundamentals['metrics'].get('Ratio de Deuda')}
- FCF Growth: {fundamentals['metrics'].get('Crecimiento de FCF')}
- Competitive Moat: {fundamentals['metrics'].get('Moat Cualitativo')}

Additional Information:
- Market Cap: {fundamentals.get('additional', {}).get('MarketCap')}
- Beta: {fundamentals.get('additional', {}).get('Beta')}
- Dividend Yield: {fundamentals.get('additional', {}).get('DividendYield')}
- EPS: {fundamentals.get('additional', {}).get('EPS')}
- 52-Week High: {fundamentals.get('additional', {}).get('52WeekHigh')}
- 52-Week Low: {fundamentals.get('additional', {}).get('52WeekLow')}

Please provide:
1. A brief overview of the company
2. Assessment of valuation (is it undervalued, fairly valued, or overvalued?)
3. Analysis of financial health and competitive position
4. Growth prospects
5. Risks to consider
6. Overall investment recommendation (Strong Buy, Buy, Hold, Sell, Strong Sell)

Format your analysis in a clear, structured way with headers and bullet points where appropriate.
"""
            
            # Make the request
            analysis = self._make_request(prompt, cache_key)
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing stock {ticker}: {str(e)}")
            return f"Error analyzing {ticker}: {str(e)}"
    
    def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> str:
        """Get Claude's analysis of a portfolio"""
        try:
            # Create a cache key based on portfolio composition
            portfolio_hash = hash(json.dumps(portfolio_data, sort_keys=True))
            cache_key = f"portfolio_analysis_{portfolio_hash}"
            
            # Extract portfolio composition
            value_stocks = portfolio_data.get("allocation", {}).get("value", [])
            growth_stocks = portfolio_data.get("allocation", {}).get("growth", [])
            bonds = portfolio_data.get("allocation", {}).get("bonds", [])
            metrics = portfolio_data.get("metrics", {})
            
            # Prepare the prompt
            prompt = f"""You are an expert portfolio manager specializing in value investing. Please analyze this investment portfolio and provide your assessment:

Portfolio Composition:

Value Stocks ({len(value_stocks)}):
"""
            
            for stock in value_stocks:
                prompt += f"- {stock['ticker']} ({stock['name']}): ${stock['price']:.2f}, Weight: {stock['weight']*100:.1f}%, Amount: ${stock['amount']:.2f}\n"
            
            prompt += f"\nGrowth Stocks ({len(growth_stocks)}):\n"
            
            for stock in growth_stocks:
                prompt += f"- {stock['ticker']} ({stock['name']}): ${stock['price']:.2f}, Weight: {stock['weight']*100:.1f}%, Amount: ${stock['amount']:.2f}\n"
            
            prompt += f"\nBonds ({len(bonds)}):\n"
            
            for bond in bonds:
                prompt += f"- {bond['ticker']} ({bond['name']}): ${bond['price']:.2f}, Weight: {bond['weight']*100:.1f}%, Amount: ${bond['amount']:.2f}\n"
            
            prompt += f"\nPortfolio Metrics:\n"
            prompt += f"- Expected Return: {metrics.get('expected_return', 'N/A')}%\n"
            prompt += f"- Volatility: {metrics.get('volatility', 'N/A')}%\n"
            prompt += f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}\n"
            
            prompt += """\nPlease provide:
1. Overall assessment of the portfolio composition and diversification
2. Analysis of the risk-return profile
3. Strengths and weaknesses of the current allocation
4. Suggestions for potential improvements or rebalancing
5. Long-term outlook for this portfolio

Format your analysis in a clear, structured way with headers and bullet points where appropriate.
"""
            
            # Make the request
            analysis = self._make_request(prompt, cache_key)
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {str(e)}")
            return f"Error analyzing portfolio: {str(e)}"
    
    def compare_stocks(self, tickers: List[str], metrics_data: Dict[str, Dict]) -> str:
        """Get Claude's comparative analysis of multiple stocks"""
        try:
            # Create a cache key
            tickers_str = ",".join(sorted(tickers))
            metrics_hash = hash(json.dumps(metrics_data, sort_keys=True))
            cache_key = f"compare_stocks_{tickers_str}_{metrics_hash}"
            
            # Prepare the prompt
            prompt = f"""You are an expert value investing analyst. Please compare these stocks and provide your assessment:

Stocks to Compare:\n"""
            
            # Add metrics for each ticker
            for ticker in tickers:
                metrics = metrics_data.get(ticker, {})
                prompt += f"\n{ticker}:\n"
                prompt += f"- ROE: {metrics.get('ROE')}\n"
                prompt += f"- P/E Ratio: {metrics.get('P/E')}\n"
                prompt += f"- Profit Margin: {metrics.get('Margen de Beneficio')}\n"
                prompt += f"- Debt Ratio: {metrics.get('Ratio de Deuda')}\n"
                prompt += f"- FCF Growth: {metrics.get('Crecimiento de FCF')}\n"
                prompt += f"- Competitive Moat: {metrics.get('Moat Cualitativo')}\n"
            
            prompt += """\nPlease provide:
1. A comparative analysis of these stocks across key metrics
2. Relative valuation assessment
3. Relative financial health and competitive position
4. Growth prospects comparison
5. Risk comparison
6. Overall ranking from most to least attractive investment

Format your analysis in a clear, structured way with headers, tables, and bullet points where appropriate.
"""
            
            # Make the request
            analysis = self._make_request(prompt, cache_key)
            return analysis
            
        except Exception as e:
            logger.error(f"Error comparing stocks {tickers}: {str(e)}")
            return f"Error comparing stocks: {str(e)}"
    
    def generate_investment_thesis(self, ticker: str, fundamentals: Dict[str, Any]) -> str:
        """Generate an investment thesis for a stock"""
        try:
            # Create a cache key
            metrics_str = json.dumps(fundamentals["metrics"])
            cache_key = f"investment_thesis_{ticker}_{hash(metrics_str)}"
            
            # Prepare the prompt
            prompt = f"""You are an expert value investor. Please write a comprehensive investment thesis for this stock:

Ticker: {ticker}
Name: {fundamentals.get('name', '')}
Sector: {fundamentals.get('sector', '')}
Industry: {fundamentals.get('industry', '')}

Key Metrics:
- ROE: {fundamentals['metrics'].get('ROE')}
- P/E Ratio: {fundamentals['metrics'].get('P/E')}
- Profit Margin: {fundamentals['metrics'].get('Margen de Beneficio')}
- Debt Ratio: {fundamentals['metrics'].get('Ratio de Deuda')}
- FCF Growth: {fundamentals['metrics'].get('Crecimiento de FCF')}
- Competitive Moat: {fundamentals['metrics'].get('Moat Cualitativo')}

Additional Information:
- Market Cap: {fundamentals.get('additional', {}).get('MarketCap')}
- Beta: {fundamentals.get('additional', {}).get('Beta')}
- Dividend Yield: {fundamentals.get('additional', {}).get('DividendYield')}
- EPS: {fundamentals.get('additional', {}).get('EPS')}
- 52-Week High: {fundamentals.get('additional', {}).get('52WeekHigh')}
- 52-Week Low: {fundamentals.get('additional', {}).get('52WeekLow')}

Please write a detailed investment thesis that includes:
1. Company Overview and Business Model
2. Competitive Advantages and Market Position
3. Financial Analysis and Valuation
4. Growth Catalysts and Opportunities
5. Risks and Challenges
6. Investment Recommendation and Price Target
7. Conclusion

Make it thorough and professional, as if it would be presented to investment committee members.
"""
            
            # Make the request
            thesis = self._make_request(prompt, cache_key)
            return thesis
            
        except Exception as e:
            logger.error(f"Error generating investment thesis for {ticker}: {str(e)}")
            return f"Error generating investment thesis for {ticker}: {str(e)}"

# Create a singleton instance
claude_service = ClaudeService()
