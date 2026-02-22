"""
yfinance_portfolios.py
Fallback portfolio data source using Yahoo Finance + curated stock lists.
Used when Perplexity AI is unavailable or returns invalid data.
Provides real prices and fundamental metrics via yfinance.
"""
import logging
import time
import yfinance as yf

logger = logging.getLogger("yf-portfolios")

# ─── Curated tickers by category ──────────────────────────────────────────────

CURATED = {
    "value": [
        "AAPL", "MSFT", "BRK-B", "JNJ", "JPM",
        "V",    "MA",   "UNH",   "PG",  "KO",
    ],
    "growth": [
        "NVDA", "SHOP", "ADBE", "CRM",  "NET",
        "DDOG", "SNOW", "ABNB", "CRWD", "MELI",
    ],
    "bonds": [
        "BND", "AGG", "TLT", "HYG", "LQD",
    ],
    "disruptive": [
        "BOTZ", "ROBO", "SOXQ", "ARKK", "ICLN",
    ],
}

CATEGORY_MOATS = {
    "AAPL":  "Ecosystem lock-in, brand",
    "MSFT":  "Cloud + enterprise switching costs",
    "BRK-B": "Diversified conglomerate moat",
    "JNJ":   "Pharma IP + medical devices",
    "JPM":   "Scale + deposit franchise",
    "V":     "Network effects, global rails",
    "MA":    "Network effects, global rails",
    "UNH":   "Scale + vertical integration",
    "PG":    "Brand + distribution",
    "KO":    "Brand + global distribution",
    "NVDA":  "GPU ecosystem lock-in + CUDA",
    "SHOP":  "Merchant ecosystem + fintech",
    "ADBE":  "Creative tool switching costs",
    "CRM":   "Enterprise CRM switching costs",
    "NET":   "Network effects, edge platform",
}


def _safe_float(val, scale=1.0):
    """Return rounded float or None."""
    try:
        v = float(val)
        return round(v * scale, 2) if v else None
    except Exception:
        return None


def _fetch_ticker_data(ticker: str) -> dict | None:
    """
    Fetch live price + fundamentals from yfinance for one ticker.
    Adds a small delay to avoid Yahoo Finance rate limits.
    Returns None if data is unavailable.
    """
    time.sleep(0.4)   # gentle throttle — avoids 429 / rate-limit errors
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}

        price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("previousClose")
        )
        if not price or float(price) <= 0:
            logger.warning(f"No price for {ticker}")
            return None

        mktcap    = info.get("marketCap") or 0
        fcf_raw   = info.get("freeCashflow") or 0
        roe_raw   = info.get("returnOnEquity")      # decimal (0.25 = 25%)
        roa_raw   = info.get("returnOnAssets")
        de_raw    = info.get("debtToEquity")        # sometimes returned as %
        pe_raw    = info.get("trailingPE")
        ev_ebitda = info.get("enterpriseToEbitda")
        beta      = info.get("beta")
        rev_g     = info.get("revenueGrowth")       # decimal YoY
        sector    = info.get("sector") or ""
        country   = info.get("country") or "US"
        name      = info.get("longName") or info.get("shortName") or ticker

        # Derived metrics
        fcf_yield = _safe_float((fcf_raw / mktcap * 100) if fcf_raw and mktcap else None)
        roe_pct   = _safe_float(roe_raw, scale=100) if roe_raw is not None else None
        # yfinance sometimes returns D/E as a percentage (e.g. 150 instead of 1.5)
        de_ratio  = _safe_float(de_raw / 100 if de_raw and de_raw > 5 else de_raw)
        rev_cagr  = _safe_float(rev_g, scale=100) if rev_g is not None else None

        # ROIC approximation: ROA × (1 + D/E)
        roic = None
        if roa_raw is not None:
            roa_pct = float(roa_raw) * 100
            roic    = round(roa_pct * (1 + float(de_ratio)) if de_ratio else roa_pct, 1)

        return {
            "ticker":    ticker,
            "name":      name,
            "sector":    sector,
            "country":   country,
            "price":     round(float(price), 2),
            "marketcap": mktcap,
            "PER":       _safe_float(pe_raw),
            "ROE":       roe_pct,
            "deuda":     de_ratio,
            "beta":      _safe_float(beta),
            "moat":      CATEGORY_MOATS.get(ticker, ""),
            "metrics": {
                "ev_ebitda":        _safe_float(ev_ebitda),
                "roic":             roic,
                "fcf_yield":        fcf_yield,
                "revenue_cagr_5y":  rev_cagr,
                "intrinsic_value":  None,
                "margin_of_safety": None,
            },
        }
    except Exception as e:
        logger.warning(f"yfinance error for {ticker}: {e}")
        return None


def _equal_weight_portfolio(items: list) -> list:
    """Assign equal peso (0-100 scale, sums to 100) to each item."""
    if not items:
        return items
    w = round(100 / len(items), 2)
    for it in items:
        it["peso"] = w
    return items


def get_value_portfolio_yf(amount: float, n: int = 8) -> list:
    tickers = CURATED["value"][:n]
    logger.info(f"yfinance VALUE: {tickers}")
    results = [d for t in tickers if (d := _fetch_ticker_data(t)) is not None]
    return _equal_weight_portfolio(results)


def get_growth_portfolio_yf(amount: float, n: int = 8) -> list:
    tickers = CURATED["growth"][:n]
    logger.info(f"yfinance GROWTH: {tickers}")
    results = [d for t in tickers if (d := _fetch_ticker_data(t)) is not None]
    return _equal_weight_portfolio(results)


def get_bond_etfs_yf(amount: float, n: int = 5) -> list:
    tickers = CURATED["bonds"][:n]
    logger.info(f"yfinance BONDS: {tickers}")
    results = [d for t in tickers if (d := _fetch_ticker_data(t)) is not None]
    return _equal_weight_portfolio(results)


def get_disruptive_etfs_yf(amount: float, n: int = 5) -> list:
    tickers = CURATED["disruptive"][:n]
    logger.info(f"yfinance DISRUPTIVE: {tickers}")
    results = [d for t in tickers if (d := _fetch_ticker_data(t)) is not None]
    return _equal_weight_portfolio(results)
