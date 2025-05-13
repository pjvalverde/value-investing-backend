import os
import json
import logging
import random
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio_service")

# Import other services
from backend.services.alpha_vantage import alpha_vantage_client

class PortfolioService:
    """Service for portfolio analysis, optimization and management"""
    
    def __init__(self):
        self.portfolios = {}  # In-memory storage for portfolios
    
    def create_portfolio(self, user_id: str, name: str, target_alloc: Dict[str, float]) -> Dict[str, Any]:
        """Create a new portfolio"""
        try:
            # Generate a unique ID for the portfolio
            portfolio_id = str(uuid.uuid4())
            
            # Create the portfolio object
            portfolio = {
                "id": portfolio_id,
                "user_id": user_id,
                "name": name,
                "target_alloc": target_alloc,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Store in memory
            self.portfolios[portfolio_id] = portfolio
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error creating portfolio: {str(e)}")
            raise
    
    def optimize_portfolio(self, portfolio_id: str, amount: float) -> Dict[str, Any]:
        """Optimize a portfolio based on target allocation and amount"""
        try:
            # Get the portfolio
            if portfolio_id not in self.portfolios:
                portfolio_id = str(uuid.uuid4())  # Generate a new ID if not found
                self.portfolios[portfolio_id] = {
                    "id": portfolio_id,
                    "user_id": "anonymous",
                    "name": "New Portfolio",
                    "target_alloc": {"value": 40, "growth": 40, "bonds": 20},
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            portfolio = self.portfolios[portfolio_id]
            target_alloc = portfolio.get("target_alloc", {"value": 40, "growth": 40, "bonds": 20})
            
            # Calculate allocations
            value_allocation = target_alloc.get("value", 0) / 100
            growth_allocation = target_alloc.get("growth", 0) / 100
            bonds_allocation = target_alloc.get("bonds", 0) / 100
            
            # Get stocks for each category
            value_stocks = self._get_value_stocks(3)  # Get top 3 value stocks
            growth_stocks = self._get_growth_stocks(3)  # Get top 3 growth stocks
            bond_etfs = self._get_bond_etfs(1)  # Get 1 bond ETF
            
            # Calculate weights and amounts
            value_weight_per_stock = value_allocation / len(value_stocks) if value_stocks else 0
            growth_weight_per_stock = growth_allocation / len(growth_stocks) if growth_stocks else 0
            bond_weight_per_etf = bonds_allocation / len(bond_etfs) if bond_etfs else 0
            
            # Create allocation for value stocks
            value_allocation_details = []
            for stock in value_stocks:
                # Get real-time price
                price_data = alpha_vantage_client.get_real_time_price(stock["ticker"])
                price = price_data["price"]
                
                value_allocation_details.append({
                    "ticker": stock["ticker"],
                    "name": stock["name"],
                    "weight": value_weight_per_stock,
                    "amount": round(amount * value_weight_per_stock, 2),
                    "shares": round(amount * value_weight_per_stock / price),
                    "price": price,
                    "price_source": price_data.get("source", "simulated")
                })
            
            # Create allocation for growth stocks
            growth_allocation_details = []
            for stock in growth_stocks:
                # Get real-time price
                price_data = alpha_vantage_client.get_real_time_price(stock["ticker"])
                price = price_data["price"]
                
                growth_allocation_details.append({
                    "ticker": stock["ticker"],
                    "name": stock["name"],
                    "weight": growth_weight_per_stock,
                    "amount": round(amount * growth_weight_per_stock, 2),
                    "shares": round(amount * growth_weight_per_stock / price),
                    "price": price,
                    "price_source": price_data.get("source", "simulated")
                })
            
            # Create allocation for bond ETFs
            bonds_allocation_details = []
            for etf in bond_etfs:
                # Get real-time price
                price_data = alpha_vantage_client.get_real_time_price(etf["ticker"])
                price = price_data["price"]
                
                bonds_allocation_details.append({
                    "ticker": etf["ticker"],
                    "name": etf["name"],
                    "weight": bond_weight_per_etf,
                    "amount": round(amount * bond_weight_per_etf, 2),
                    "shares": round(amount * bond_weight_per_etf / price),
                    "price": price,
                    "price_source": price_data.get("source", "simulated")
                })
            
            # Calculate portfolio metrics
            metrics = self._calculate_portfolio_metrics(
                value_allocation_details, 
                growth_allocation_details, 
                bonds_allocation_details
            )
            
            # Create the optimized portfolio
            optimized = {
                "id": portfolio_id,
                "allocation": {
                    "value": value_allocation_details,
                    "growth": growth_allocation_details,
                    "bonds": bonds_allocation_details
                },
                "metrics": metrics,
                "amount": amount,
                "target_alloc": target_alloc,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update the portfolio with the optimized allocation
            self.portfolios[portfolio_id]["optimized"] = optimized
            self.portfolios[portfolio_id]["updated_at"] = datetime.now().isoformat()
            
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {str(e)}")
            raise
    
    def _get_value_stocks(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get top value stocks using Perplexity API"""
        try:
            # Import here to avoid circular imports
            from app_railway import get_value_stocks
            import asyncio
            
            # Get value stocks from Perplexity API
            logger.info("Obteniendo acciones value con Perplexity API")
            value_stocks_data = asyncio.run(get_value_stocks())
            
            # Format the data
            value_stocks = []
            for stock in value_stocks_data[:count]:
                value_stocks.append({
                    "ticker": stock["ticker"],
                    "name": stock["name"]
                })
            
            logger.info(f"Se obtuvieron {len(value_stocks)} acciones value con Perplexity")
            return value_stocks
        except Exception as e:
            logger.error(f"Error obteniendo acciones value con Perplexity: {str(e)}")
            raise ValueError("No se pudieron obtener acciones value. Verifica la configuración de PERPLEXITY_API_KEY. No se usarán datos simulados ni predefinidos.")
    
    def _get_growth_stocks(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get top growth stocks using Perplexity API"""
        try:
            # Import here to avoid circular imports
            from app_railway import get_growth_stocks
            import asyncio
            
            # Get growth stocks from Perplexity API
            logger.info("Obteniendo acciones growth con Perplexity API")
            growth_stocks_data = asyncio.run(get_growth_stocks())
            
            # Format the data
            growth_stocks = []
            for stock in growth_stocks_data[:count]:
                growth_stocks.append({
                    "ticker": stock["ticker"],
                    "name": stock["name"]
                })
            
            logger.info(f"Se obtuvieron {len(growth_stocks)} acciones growth con Perplexity")
            return growth_stocks
        except Exception as e:
            logger.error(f"Error obteniendo acciones growth con Perplexity: {str(e)}")
            raise ValueError("No se pudieron obtener acciones growth. Verifica la configuración de PERPLEXITY_API_KEY. No se usarán datos simulados ni predefinidos.")
    
    def _get_bond_etfs(self, count: int = 1) -> List[Dict[str, Any]]:
        """Get bond ETFs using Alpha Vantage API"""
        try:
            # Usar Alpha Vantage para obtener datos de ETFs de bonos
            logger.info("Obteniendo ETFs de bonos con Alpha Vantage API")
            
            # Lista de ETFs de bonos populares para buscar
            bond_etf_tickers = ["AGG", "BND", "VCIT", "VCSH", "LQD", "MBB", "TIP", "GOVT"]
            
            # Obtener datos reales para cada ETF
            bond_etfs = []
            for ticker in bond_etf_tickers[:count+2]:  # Intentar con algunos extras en caso de error
                try:
                    # Obtener datos fundamentales
                    fundamentals = alpha_vantage_client.get_stock_fundamentals(ticker)
                    
                    if fundamentals and "Name" in fundamentals:
                        bond_etfs.append({
                            "ticker": ticker,
                            "name": fundamentals.get("Name", f"{ticker} ETF")
                        })
                        
                        if len(bond_etfs) >= count:
                            break
                except Exception as e:
                    logger.warning(f"Error obteniendo datos para el ETF {ticker}: {str(e)}")
                    continue
            
            if not bond_etfs:
                raise ValueError("No se pudieron obtener datos de ETFs de bonos")
                
            logger.info(f"Se obtuvieron {len(bond_etfs)} ETFs de bonos con Alpha Vantage")
            return bond_etfs
        except Exception as e:
            logger.error(f"Error obteniendo ETFs de bonos: {str(e)}")
            raise ValueError("No se pudieron obtener datos de ETFs de bonos. Verifica la configuración de ALPHAVANTAGE_API_KEY. No se usarán datos simulados ni predefinidos.")
    
    def _calculate_portfolio_metrics(self, value_stocks, growth_stocks, bond_etfs) -> Dict[str, float]:
        """Calculate portfolio metrics based on allocations"""
        # Calculate expected return based on allocation
        # These are simplified assumptions
        value_return = 0.07  # 7% expected return for value stocks
        growth_return = 0.10  # 10% expected return for growth stocks
        bond_return = 0.04  # 4% expected return for bonds
        
        # Calculate total weights
        total_value_weight = sum(stock["weight"] for stock in value_stocks)
        total_growth_weight = sum(stock["weight"] for stock in growth_stocks)
        total_bond_weight = sum(etf["weight"] for etf in bond_etfs)
        
        # Calculate weighted expected return
        expected_return = (
            value_return * total_value_weight +
            growth_return * total_growth_weight +
            bond_return * total_bond_weight
        )
        
        # Calculate volatility (simplified)
        value_volatility = 0.15  # 15% volatility for value stocks
        growth_volatility = 0.25  # 25% volatility for growth stocks
        bond_volatility = 0.05  # 5% volatility for bonds
        
        # Simplified volatility calculation (ignoring correlations)
        volatility = (
            value_volatility * total_value_weight +
            growth_volatility * total_growth_weight +
            bond_volatility * total_bond_weight
        )
        
        # Calculate Sharpe ratio (assuming risk-free rate of 2%)
        risk_free_rate = 0.02
        sharpe_ratio = (expected_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        return {
            "expected_return": round(expected_return * 100, 2),  # as percentage
            "volatility": round(volatility * 100, 2),  # as percentage
            "sharpe_ratio": round(sharpe_ratio, 2)
        }
    
    def get_comparative_metrics(self, tickers: List[str]) -> Dict[str, Any]:
        """Get comparative metrics for a list of tickers"""
        try:
            result = {
                "tickers": tickers,
                "metrics": {}
            }
            
            for ticker in tickers:
                # Get fundamental data
                fundamentals = alpha_vantage_client.get_stock_fundamentals(ticker)
                
                # Add to result
                result["metrics"][ticker] = fundamentals["metrics"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting comparative metrics: {str(e)}")
            # Return empty metrics as fallback
            return {"tickers": tickers, "metrics": {}, "error": str(e)}
    
    def get_stock_analysis(self, ticker: str) -> Dict[str, Any]:
        """Get detailed analysis for a stock"""
        try:
            # Get fundamental data
            fundamentals = alpha_vantage_client.get_stock_fundamentals(ticker)
            
            # Get real-time price
            price_data = alpha_vantage_client.get_real_time_price(ticker)
            
            # Combine data
            analysis = {
                "ticker": ticker,
                "name": fundamentals.get("name", ""),
                "price": price_data["price"],
                "price_source": price_data.get("source", "simulated"),
                "sector": fundamentals.get("sector", ""),
                "industry": fundamentals.get("industry", ""),
                "metrics": fundamentals["metrics"],
                "additional": fundamentals.get("additional", {}),
                "timestamp": datetime.now().isoformat()
            }
            
            # Generate analysis summary
            analysis["summary"] = self._generate_analysis_summary(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting stock analysis for {ticker}: {str(e)}")
            # Return basic data as fallback
            return {
                "ticker": ticker,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_analysis_summary(self, analysis: Dict[str, Any]) -> str:
        """Generate a summary analysis based on metrics"""
        ticker = analysis["ticker"]
        name = analysis["name"]
        price = analysis["price"]
        metrics = analysis["metrics"]
        
        # Extract key metrics
        roe = metrics.get("ROE")
        pe = metrics.get("P/E")
        margin = metrics.get("Margen de Beneficio")
        debt_ratio = metrics.get("Ratio de Deuda")
        fcf_growth = metrics.get("Crecimiento de FCF")
        moat = metrics.get("Moat Cualitativo")
        
        # Generate summary
        summary = f"Análisis de {name} ({ticker}) a ${price:.2f}:\n\n"
        
        # Valuation assessment
        if pe is not None:
            if pe < 15:
                summary += "✅ Valoración: Atractiva (P/E bajo)\n"
            elif pe < 25:
                summary += "⚠️ Valoración: Razonable (P/E moderado)\n"
            else:
                summary += "❌ Valoración: Cara (P/E alto)\n"
        else:
            summary += "❓ Valoración: No disponible\n"
        
        # Profitability assessment
        if roe is not None and margin is not None:
            if roe > 20 and margin > 20:
                summary += "✅ Rentabilidad: Excelente (ROE y margen altos)\n"
            elif roe > 15 and margin > 10:
                summary += "✅ Rentabilidad: Buena (ROE y margen sólidos)\n"
            elif roe > 10 and margin > 5:
                summary += "⚠️ Rentabilidad: Aceptable (ROE y margen moderados)\n"
            else:
                summary += "❌ Rentabilidad: Débil (ROE y margen bajos)\n"
        else:
            summary += "❓ Rentabilidad: No disponible\n"
        
        # Financial health assessment
        if debt_ratio is not None:
            if debt_ratio < 0.3:
                summary += "✅ Salud Financiera: Excelente (baja deuda)\n"
            elif debt_ratio < 0.6:
                summary += "✅ Salud Financiera: Buena (deuda moderada)\n"
            elif debt_ratio < 1.0:
                summary += "⚠️ Salud Financiera: Aceptable (deuda considerable)\n"
            else:
                summary += "❌ Salud Financiera: Riesgosa (deuda alta)\n"
        else:
            summary += "❓ Salud Financiera: No disponible\n"
        
        # Growth assessment
        if fcf_growth is not None:
            if fcf_growth > 15:
                summary += "✅ Crecimiento: Fuerte (FCF en rápido crecimiento)\n"
            elif fcf_growth > 8:
                summary += "✅ Crecimiento: Bueno (FCF en crecimiento sólido)\n"
            elif fcf_growth > 3:
                summary += "⚠️ Crecimiento: Moderado (FCF en crecimiento lento)\n"
            else:
                summary += "❌ Crecimiento: Débil (FCF estancado o en declive)\n"
        else:
            summary += "❓ Crecimiento: No disponible\n"
        
        # Moat assessment
        if moat is not None:
            if moat == "Alto":
                summary += "✅ Ventaja Competitiva: Fuerte (moat significativo)\n"
            elif moat == "Medio":
                summary += "✅ Ventaja Competitiva: Moderada (moat presente)\n"
            elif moat == "Diversificado":
                summary += "✅ Ventaja Competitiva: Diversificada (ETF)\n"
            else:
                summary += "❌ Ventaja Competitiva: Débil (moat limitado)\n"
        else:
            summary += "❓ Ventaja Competitiva: No disponible\n"
        
        # Overall assessment
        positive_count = summary.count("✅")
        warning_count = summary.count("⚠️")
        negative_count = summary.count("❌")
        
        summary += "\nConclusión: "
        if positive_count >= 4:
            summary += "Excelente oportunidad de inversión con sólidos fundamentos."
        elif positive_count >= 3:
            summary += "Buena oportunidad de inversión con fundamentos sólidos en general."
        elif positive_count >= 2:
            summary += "Oportunidad de inversión aceptable con algunas fortalezas y debilidades."
        elif warning_count >= 3:
            summary += "Inversión con precaución debido a métricas mixtas."
        else:
            summary += "No recomendada como inversión principal debido a fundamentos débiles."
        
        return summary

# Create a singleton instance
portfolio_service = PortfolioService()
