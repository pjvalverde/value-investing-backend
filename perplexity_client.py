import os
import requests
import logging
import json
import re

logger = logging.getLogger("perplexity-client")


class PerplexityClient:
    """Perplexity AI client – prompts enriched with Damodaran metrics."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is not set in environment variables.")
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-pro"

    def _call_perplexity(self, system_prompt, user_prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            if response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                raise Exception(f"Perplexity API error: {response.status_code}")
            response_data = response.json()
            response_text = response_data["choices"][0]["message"]["content"]

            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]")
            if start_idx == -1 or end_idx == -1:
                logger.error("No JSON array found in Perplexity response")
                raise Exception("No JSON array found in Perplexity response")

            json_str = response_text[start_idx:end_idx + 1]
            # Sanitize: remove numeric underscores (e.g., 1_000_000 -> 1000000)
            json_str_clean = re.sub(r'(?<=\d)_(?=\d)', '', json_str)
            try:
                parsed = json.loads(json_str_clean)
            except json.JSONDecodeError:
                # Fix single-quote keys/values
                json_str_fixed = re.sub(r"(?<=[:,\[\{])\s*'([^']*)'\s*:", r'"\1":', json_str_clean)
                json_str_fixed = re.sub(r":\s*'([^']*)'", r':"\1"', json_str_fixed)
                parsed = json.loads(json_str_fixed)

            logger.info(f"Perplexity returned {len(parsed)} items")
            return parsed
        except Exception as e:
            logger.error(f"Error querying Perplexity API: {str(e)}")
            raise

    # ─────────────────────────────────────────────
    # VALUE STOCKS (Buffett/Munger + Damodaran)
    # ─────────────────────────────────────────────
    def get_value_portfolio(self, amount, min_marketcap_eur=1_000_000_000,
                            max_marketcap_eur=100_000_000_000,
                            min_roe=12, max_per=18, max_debt=0.6,
                            n_stocks=10, region="EU,US"):
        system_prompt = (
            "Eres un asistente experto en value investing (Buffett/Munger) y análisis cuantitativo "
            "(Aswath Damodaran). Devuelve ÚNICAMENTE un array JSON de acciones value (large/mega cap) "
            "con los siguientes criterios:\n"
            f"- Capitalización: €{min_marketcap_eur:,} – €{max_marketcap_eur:,}\n"
            f"- ROE ≥ {min_roe}% | PER ≤ {max_per} | Deuda/Equity ≤ {max_debt}\n"
            "- Moat cualitativo fuerte (ventaja competitiva duradera)\n"
            "- ROIC > WACC (creación de valor real, idealmente ROIC ≥ 15%)\n"
            "- Solo datos REALES y actuales. Diversifica sectores y países.\n\n"
            "Cada elemento del array JSON debe tener EXACTAMENTE estos campos:\n"
            "ticker, nombre, sector, país, marketcap (número), PER (número), ROE (número%), "
            "deuda (ratio decimal), margen (ratio decimal), moat (string breve), "
            "peso (número 0-100, suma=100), price (precio actual USD/EUR), "
            "metrics: { ev_ebitda (número), roic (número%), fcf_yield (número%), "
            "revenue_cagr_5y (número%), intrinsic_value (precio DCF estimado), "
            "margin_of_safety (% descuento al valor intrínseco, puede ser negativo) }\n\n"
            f"Devuelve exactamente {n_stocks} acciones. Solo el array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Portafolio value óptimo para €{amount:,.0f} invertidos en empresas europeas y "
            f"estadounidenses de gran capitalización, con moat fuerte, ROIC > WACC y margen de "
            f"seguridad positivo según criterios Damodaran."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    # ─────────────────────────────────────────────
    # GROWTH STOCKS
    # ─────────────────────────────────────────────
    def get_growth_portfolio(self, amount, min_marketcap_eur=300_000_000,
                             max_marketcap_eur=2_000_000_000,
                             min_beta=1.2, max_beta=1.4, n_stocks=10, region="EU,US"):
        system_prompt = (
            "Eres un asistente experto en finanzas cuantitativas y growth investing con enfoque Damodaran. "
            "Devuelve ÚNICAMENTE un array JSON de acciones growth (small/micro cap) con:\n"
            f"- Capitalización: €{min_marketcap_eur:,} – €{max_marketcap_eur:,}\n"
            f"- Beta: {min_beta} – {max_beta}\n"
            "- Crecimiento de ingresos acelerado (CAGR ≥ 15% los últimos 3 años)\n"
            "- TAM (mercado total direccionable) grande y en expansión\n"
            "- Solo datos REALES y actuales. Diversifica sectores y países.\n\n"
            "Cada elemento debe tener EXACTAMENTE:\n"
            "ticker, nombre, sector, país, marketcap (número), beta (número), "
            "peso (número 0-100, suma=100), price (precio actual USD/EUR), "
            "metrics: { roic (número%), ev_ebitda (número), fcf_yield (número%), "
            "revenue_cagr_5y (número%), revenue_cagr_3y (número%), "
            "intrinsic_value (DCF estimado), margin_of_safety (%), "
            "gross_margin (%), tam_estimate (string breve) }\n\n"
            f"Devuelve exactamente {n_stocks} acciones. Solo el array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Portafolio growth óptimo para €{amount:,.0f} en small/micro caps europeas y "
            f"estadounidenses con alto crecimiento de ingresos y beta entre {min_beta}-{max_beta}. "
            f"Incluye métricas Damodaran de valoración y crecimiento."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    # ─────────────────────────────────────────────
    # DISRUPTIVE PORTFOLIO
    # ─────────────────────────────────────────────
    def get_disruptive_portfolio(self, amount, n_instruments=5, region="EU,US", n_stocks=None):
        if n_stocks is not None:
            n_instruments = n_stocks
        system_prompt = (
            "Eres un experto en inversión disruptiva y tecnología. "
            "Devuelve ÚNICAMENTE un array JSON de instrumentos reales en categorías:\n"
            "- Private Equity / Venture Capital (fondos VC, PE, startups IA, biotech)\n"
            "- ETFs temáticos disruptivos (IA, robótica, semiconductores, ciberseguridad)\n"
            "- Acciones disruptivas de alto potencial\n"
            "Solo instrumentos REALES y actuales. Nunca inventados.\n\n"
            "Cada elemento debe tener:\n"
            "ticker, nombre, categoría, sector, país, "
            "peso (número 0-100, suma=100), price (número actual), "
            "metrics: { expected_cagr (%), max_drawdown (%), "
            "liquidity (alta/media/baja), ev_ebitda (número o null), "
            "roic (número% o null), revenue_cagr_5y (número% o null) }\n\n"
            f"Devuelve exactamente {n_instruments} instrumentos. Solo el array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Portafolio disruptivo global para €{amount:,.0f} en private equity, "
            f"ETFs temáticos y acciones disruptivas. Región: {region}."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    # ─────────────────────────────────────────────
    # DISRUPTIVE ETFs
    # ─────────────────────────────────────────────
    def get_disruptive_etfs(self, amount, n_etfs=3, region="Global"):
        system_prompt = (
            "Eres un experto en ETFs de tecnología disruptiva. "
            "Devuelve ÚNICAMENTE un array JSON con los mejores ETFs en innovación, IA, robótica, "
            "semiconductores y tecnologías emergentes. Solo datos reales y actualizados.\n\n"
            "Cada ETF debe tener:\n"
            "ticker (ej. 'ARKK'), name (nombre completo), sector, country,\n"
            "price (precio actual USD, número real),\n"
            "weight (peso sugerido 0.0–1.0, suma=1.0),\n"
            "metrics: { expense_ratio (%), holdings (número), ytd_return (%), "
            "3y_return (%), aum_billion (número USD), "
            "top_holdings (string: 3 principales posiciones) }\n\n"
            f"Devuelve exactamente {n_etfs} ETFs. Solo el array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Los {n_etfs} mejores ETFs de tecnología disruptiva para una cartera de "
            f"${amount:,.2f}. Incluye ETFs de IA, robótica e innovación. Región: {region}."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    # ─────────────────────────────────────────────
    # BOND ETFs
    # ─────────────────────────────────────────────
    def get_bond_etfs(self, amount, n_etfs=3, region="Global"):
        system_prompt = (
            "Eres un experto en ETFs de renta fija y gestión de riesgo de portafolios. "
            "Devuelve ÚNICAMENTE un array JSON con los mejores ETFs de bonos (gubernamentales, "
            "corporativos, high yield, globales) líquidos y diversificados. "
            "Solo datos reales y actualizados.\n\n"
            "Cada ETF debe tener:\n"
            "ticker (ej. 'BND'), name, sector, country,\n"
            "price (precio actual USD, número real),\n"
            "weight (peso sugerido 0.0–1.0, suma=1.0),\n"
            "metrics: { duration_years (número), yield_to_maturity (%), "
            "expense_ratio (%), aum_billion (número USD), "
            "credit_quality (string: AAA/AA/A/BBB mix), "
            "correlation_equity (número -1 a 1) }\n\n"
            f"Devuelve exactamente {n_etfs} ETFs. Solo el array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Los {n_etfs} mejores ETFs de bonos para diversificar y proteger una cartera "
            f"de ${amount:,.2f}. Incluye gubernamentales, corporativos y globales. Región: {region}."
        )
        return self._call_perplexity(system_prompt, user_prompt)
