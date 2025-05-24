import os
import requests
import logging
import json

logger = logging.getLogger("perplexity-client")

class PerplexityClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is not set in environment variables.")
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-pro"

    def get_growth_portfolio(self, amount, min_marketcap_eur=300_000_000, max_marketcap_eur=2_000_000_000, min_beta=1.2, max_beta=1.4, n_stocks=10, region="EU,US"):
        """
        Llama a Perplexity para obtener una lista óptima de acciones growth (small/micro cap) según los criterios dados.
        Devuelve una lista de acciones con pesos sugeridos y métricas clave.
        """
        system_prompt = (
            "Eres un asistente experto en finanzas cuantitativas. Devuelve únicamente un array JSON de acciones growth (small/micro cap) que cumplan:\n"
            f"- Capitalización entre €{min_marketcap_eur:,} y €{max_marketcap_eur:,}\n"
            f"- Beta entre {min_beta} y {max_beta}\n"
            f"- Solo datos reales y actuales\n"
            "- Incluye: ticker, nombre, sector, país, marketcap, beta, peso (%), métricas clave (ROE, P/E, crecimiento FCF, etc.)\n"
            f"- Diversifica sectores y países.\n- Devuelve exactamente {n_stocks} acciones.\n- Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Quiero invertir €{amount:,} en acciones growth europeas y estadounidenses de pequeña capitalización. Dame la lista óptima según los criterios."
        )
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
            # Extraer el array JSON de la respuesta
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1]
                try:
                    # Sanitizar: eliminar guiones bajos en los números antes de parsear
                    json_str_clean = json_str.replace('_', '')
                    stocks_data = json.loads(json_str_clean)
                    logger.info(f"Portafolio growth obtenido con {len(stocks_data)} acciones")
                    return stocks_data
                except Exception as e:
                    logger.error(f"Error parsing JSON from Perplexity: {str(e)} | JSON: {json_str}")
                    raise
            else:
                logger.error("No se encontró un array JSON en la respuesta de Perplexity")
                raise Exception("No JSON array found in Perplexity response")
        except Exception as e:
            logger.error(f"Error al consultar Perplexity API: {str(e)}")
            raise

    def get_disruptive_portfolio(self, amount, n_stocks=10, region="US,EU,Global"):
        """
        Llama a Perplexity para obtener una lista óptima de acciones, ETFs o fondos disruptivos (private equity, tecnología especializada, IA, robótica, semiconductores, ciberseguridad, biotecnología, etc).
        Devuelve una lista de instrumentos con pesos sugeridos y métricas clave.
        """
        system_prompt = (
            "Eres un asistente experto en asset allocation y selección de instrumentos disruptivos. Devuelve únicamente un array JSON de instrumentos (acciones, ETFs o fondos) que cumplan:\n"
            "- Categoría: Private Equity, Tecnología Especializada, Innovación Disruptiva, IA, Robótica, Semiconductores, Ciberseguridad, Biotecnología, Energía limpia, Fintech, Blockchain.\n"
            "- Incluye ejemplos como: ARK Innovation ETF (ARKK), Global X Robotics & AI ETF (BOTZ), VanEck Semiconductor ETF (SMH), ETFMG Prime Cyber Security ETF (HACK), Nvidia (NVDA), fondos de private equity como Sequoia Capital, Andreessen Horowitz, T. Rowe Price Global Technology Equity Fund (PRGTX).\n"
            "- Diversifica entre subsectores disruptivos y regiones.\n"
            "- Solo datos reales y actuales.\n"
            "- Incluye: ticker, nombre, tipo (ETF, acción, fondo), sector, país, rentabilidad histórica anualizada, riesgo (volatilidad), peso (%), métricas clave.\n"
            f"- Devuelve exactamente {n_stocks} instrumentos.\n- Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Quiero invertir €{amount:,} en una cartera disruptiva diversificada entre private equity, tecnología especializada y sectores innovadores. Dame la lista óptima de instrumentos según los criterios."
        )
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
            # Extraer el array JSON de la respuesta
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1]
                try:
                    json_str_clean = json_str.replace('_', '')
                    instruments_data = json.loads(json_str_clean)
                    logger.info(f"Portafolio disruptivo obtenido con {len(instruments_data)} instrumentos")
                    return instruments_data
                except Exception as e:
                    logger.error(f"Error parsing JSON from Perplexity: {str(e)} | JSON: {json_str}")
                    raise
            else:
                logger.error("No se encontró un array JSON en la respuesta de Perplexity")
                raise Exception("No JSON array found in Perplexity response")
        except Exception as e:
            logger.error(f"Error al consultar Perplexity API: {str(e)}")
            raise

    def get_value_portfolio(self, amount, min_marketcap_eur=1_000_000_000, max_marketcap_eur=100_000_000_000, min_roe=12, max_per=18, max_debt=0.6, n_stocks=10, region="EU,US"):
        """
        Llama a Perplexity para obtener una lista óptima de acciones value (large cap, bajo PER, alto ROE, margen alto, deuda baja, moat cualitativo, etc).
        Devuelve una lista de acciones con pesos sugeridos y métricas clave.
        """
        system_prompt = (
            "Eres un asistente experto en value investing y análisis fundamental. Devuelve únicamente un array JSON de acciones value (large/mega cap) que cumplan:\n"
            f"- Capitalización entre €{min_marketcap_eur:,} y €{max_marketcap_eur:,}\n"
            f"- ROE mínimo {min_roe}%\n"
            f"- PER máximo {max_per}\n"
            f"- Deuda/Equity máxima {max_debt}\n"
            "- Margen de beneficio alto, moat cualitativo fuerte (ventaja competitiva),\n"
            "- Solo datos reales y actuales\n"
            "- Incluye: ticker, nombre, sector, país, marketcap, PER, ROE, deuda, margen, moat, peso (%), métricas clave\n"
            f"- Diversifica sectores y países.\n- Devuelve exactamente {n_stocks} acciones.\n- Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Quiero invertir €{amount:,} en acciones value europeas y estadounidenses de gran capitalización. Dame la lista óptima según los criterios."
        )
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
            # Extraer el array JSON de la respuesta
            start_idx = response_text.find("[")
            end_idx = response_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1]
                try:
                    # Sanitizar: eliminar guiones bajos en los números antes de parsear
                    json_str_clean = json_str.replace('_', '')
                    stocks_data = json.loads(json_str_clean)
                    logger.info(f"Portafolio value obtenido con {len(stocks_data)} acciones")
                    return stocks_data
                except Exception as e:
                    logger.error(f"Error parsing JSON from Perplexity: {str(e)} | JSON: {json_str}")
                    raise
            else:
                logger.error("No se encontró un array JSON en la respuesta de Perplexity")
                raise Exception("No JSON array found in Perplexity response")
        except Exception as e:
            logger.error(f"Error al consultar Perplexity API: {str(e)}")
            raise
