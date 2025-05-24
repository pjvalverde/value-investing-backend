import os
import requests
import logging
import json

logger = logging.getLogger("perplexity-client")

class PerplexityClient:
    def __init__(self, api_key=None):
        import os
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY is not set in environment variables.")
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar-pro"

    def _call_perplexity(self, system_prompt, user_prompt):
        import requests
        import logging
        import json
        import re
        logger = logging.getLogger("perplexity-client")
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
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1]
                try:
                    json_str_clean = json_str.replace('_', '')
                    try:
                        data = json.loads(json_str_clean)
                    except json.JSONDecodeError:
                        json_str_fixed = re.sub(r"(?<=[:,\[\{])\s*'([^']*)'\s*:", r'"\1":', json_str_clean)
                        json_str_fixed = re.sub(r":\s*'([^']*)'", r':"\1"', json_str_fixed)
                        data = json.loads(json_str_fixed)
                    logger.info(f"Respuesta Perplexity con {len(data)} items")
                    return data
                except Exception as e:
                    logger.error(f"Error parsing JSON from Perplexity: {str(e)} | JSON: {json_str}")
                    raise
            else:
                logger.error("No se encontró un array JSON en la respuesta de Perplexity")
                raise Exception("No JSON array found in Perplexity response")
        except Exception as e:
            logger.error(f"Error al consultar Perplexity API: {str(e)}")
            raise

    def get_growth_portfolio(self, amount, min_marketcap_eur=300_000_000, max_marketcap_eur=2_000_000_000, min_beta=1.2, max_beta=1.4, n_stocks=10, region="EU,US"):
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
        return self._call_perplexity(system_prompt, user_prompt)

    def get_value_portfolio(self, amount, min_marketcap_eur=1_000_000_000, max_marketcap_eur=100_000_000_000, min_roe=12, max_per=18, max_debt=0.6, n_stocks=10, region="EU,US"):
        system_prompt = (
            "Eres un asistente experto en value investing y análisis fundamental. Devuelve únicamente un array JSON de acciones value (large/mega cap) que cumplan:\n"
            f"- Capitalización entre €{min_marketcap_eur:,} y €{max_marketcap_eur:,}\n"
            f"- ROE mínimo {min_roe}%\n"
            f"- PER máximo {max_per}\n"
            f"- Deuda/Equity máxima {max_debt}\n"
            "- Margen de beneficio alto, moat cualitativo fuerte (ventaja competitiva),\n"
            "- Solo datos reales y actuales\n"
            "- Incluye: ticker, nombre, sector, país, marketcap, PER, ROE, deuda, margen, moat, peso (%), métricas clave\n- El campo 'metrics' debe ser un objeto JSON con métricas clave de value investing: ROC (Return on Capital), Cash Flow, P/E (Price/Earnings), Dividend Yield, Debt/Equity, Margen Operativo, Margen Neto, FCF Yield, EV/EBITDA, crecimiento de ingresos, etc. Si alguna métrica no está disponible, omítela.\n"
            f"- Diversifica sectores y países.\n- Devuelve exactamente {n_stocks} acciones.\n- Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Quiero invertir €{amount:,} en acciones value europeas y estadounidenses de gran capitalización. Dame la lista óptima según los criterios."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    def get_disruptive_portfolio(self, amount, n_instruments=5, region="EU,US", n_stocks=None):
        if n_stocks is not None:
            n_instruments = n_stocks
        system_prompt = (
            "Eres un asistente experto en inversión disruptiva y tecnología. Devuelve únicamente un array JSON de instrumentos reales y actuales en las siguientes categorías:\n"
            "- Private Equity (fondos de venture capital, private equity, startups de IA, biotecnología, etc)\n"
            "- Tecnología Especializada (ETFs temáticos, acciones disruptivas, fondos de tecnología, robótica, IA, ciberseguridad, semiconductores, etc)\n"
            "- Solo instrumentos REALES y actuales, nunca inventados ni simulados.\n"
            "- Incluye: ticker, nombre, categoría (private_equity, etf_temático, acción_disruptiva, fondo_vc, etc), sector, país, peso (%), rentabilidad esperada, métricas clave (CAGR, drawdown, liquidez, etc), comentarios.\n"
            f"- Diversifica entre private equity y tecnología avanzada. Región: {region}.\n- Devuelve exactamente {n_instruments} instrumentos.\n- Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Quiero invertir €{amount:,} en una cartera disruptiva global (private equity, tecnología, IA, biotecnología, etc). Dame la lista óptima según los criterios."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    def get_disruptive_etfs(self, amount, n_etfs=3, region="Global"):
        system_prompt = (
            "Eres un asistente experto en ETFs de tecnología disruptiva. Devuelve únicamente un array JSON con los "
            f"{n_etfs} principales ETFs que inviertan en innovación, IA, robótica, semiconductores y tecnologías emergentes.\n"
            "Cada ETF debe incluir los siguientes campos:\n"
            "- ticker (ej. 'ARKK')\n"
            "- name (nombre completo del ETF)\n"
            "- sector (ej. 'Tecnología Disruptiva', 'Robótica', 'IA')\n"
            "- country (país de origen o cobertura)\n"
            "- price (precio actual en USD, debe ser un número real y actualizado)\n"
            "- weight (peso sugerido en cartera, entre 0.1 y 0.5, la suma debe ser 1.0)\n"
            "- metrics (objeto con métricas reales como expense_ratio, holdings, ytd_return, etc.)\n"
            "Usa solo datos reales y actualizados.\n"
            "Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Dame una lista de los {n_etfs} mejores ETFs de tecnología disruptiva con sus precios actuales, "
            f"métricas clave y un peso sugerido para una cartera de ${amount:,.2f}. "
            f"Incluye ETFs que inviertan en innovación, IA, robótica y tecnologías emergentes. "
            f"La región objetivo es: {region}."
        )
        return self._call_perplexity(system_prompt, user_prompt)

    def get_bond_etfs(self, amount, n_etfs=3, region="Global"):
        system_prompt = (
            "Eres un asistente experto en ETFs de bonos y renta fija. Devuelve únicamente un array JSON con los "
            f"{n_etfs} principales ETFs de bonos (gubernamentales, corporativos, high yield, globales, etc) "
            "que sean líquidos, diversificados y adecuados para una cartera diversificada.\n"
            "Cada ETF debe incluir los siguientes campos:\n"
            "- ticker (ej. 'BND', 'TLT', 'LQD')\n"
            "- name (nombre completo del ETF)\n"
            "- sector (ej. 'Bonos Gubernamentales', 'Bonos Corporativos', etc)\n"
            "- country (país de origen o cobertura)\n"
            "- price (precio actual en USD, debe ser un número real y actualizado)\n"
            "- weight (peso sugerido en cartera, entre 0.1 y 0.5, la suma debe ser 1.0)\n"
            "- metrics (objeto con métricas reales como duration, yield, expense_ratio, aum, etc.)\n"
            "Usa solo datos reales y actualizados.\n"
            "Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Dame una lista de los {n_etfs} mejores ETFs de bonos con sus precios actuales, "
            f"métricas clave y un peso sugerido para una cartera de ${amount:,.2f}. "
            f"Incluye ETFs de bonos gubernamentales, corporativos y globales. "
            f"La región objetivo es: {region}."
        )
        return self._call_perplexity(system_prompt, user_prompt)

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

    def get_disruptive_etfs(self, amount, n_etfs=3, region="Global"):
        """
        Obtiene una lista de ETFs de tecnología disruptiva con datos reales de Perplexity.
        """
        system_prompt = (
            "Eres un asistente experto en ETFs de tecnología disruptiva. Devuelve únicamente un array JSON con los "
            f"{n_etfs} principales ETFs que inviertan en innovación, IA, robótica, semiconductores y tecnologías emergentes.\n"
            "Cada ETF debe incluir los siguientes campos:\n"
            "- ticker (ej. 'ARKK')\n"
            "- name (nombre completo del ETF)\n"
            "- sector (ej. 'Tecnología Disruptiva', 'Robótica', 'IA')\n"
            "- country (país de origen o cobertura)\n"
            "- price (precio actual en USD, debe ser un número real y actualizado)\n"
            "- weight (peso sugerido en cartera, entre 0.1 y 0.5, la suma debe ser 1.0)\n"
            "- metrics (objeto con métricas reales como expense_ratio, holdings, ytd_return, etc.)\n"
            "Usa solo datos reales y actualizados.\n"
            "Formato: array JSON, sin texto adicional."
        )
        
        user_prompt = (
            f"Dame una lista de los {n_etfs} mejores ETFs de tecnología disruptiva con sus precios actuales, "
            f"métricas clave y un peso sugerido para una cartera de ${amount:,.2f}. "
            f"Incluye ETFs que inviertan en innovación, IA, robótica y tecnologías emergentes. "
            f"La región objetivo es: {region}."
        )
        
        return self._call_perplexity(system_prompt, user_prompt)
        
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
            "- Incluye: ticker, nombre, sector, país, marketcap, PER, ROE, deuda, margen, moat, peso (%), métricas clave\n- El campo 'metrics' debe ser un objeto JSON con métricas clave de value investing: ROC (Return on Capital), Cash Flow, P/E (Price/Earnings), Dividend Yield, Debt/Equity, Margen Operativo, Margen Neto, FCF Yield, EV/EBITDA, crecimiento de ingresos, etc. Si alguna métrica no está disponible, omítela.\n"
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
                    try:
                        stocks_data = json.loads(json_str_clean)
                    except json.JSONDecodeError as e:
                        import re
                        # Intenta arreglar claves y valores con comillas simples
                        json_str_fixed = re.sub(r"(?<=[:,\[\{])\s*'([^']*)'\s*:", r'"\1":', json_str_clean)  # claves
                        json_str_fixed = re.sub(r":\s*'([^']*)'", r':"\1"', json_str_fixed)                # valores
                        stocks_data = json.loads(json_str_fixed)
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

    def get_disruptive_portfolio(self, amount, n_instruments=5, region="EU,US", n_stocks=None):
        """
        Llama a Perplexity para obtener una lista óptima de instrumentos disruptivos (Private Equity, Tecnología Especializada, ETFs temáticos, fondos de VC, acciones disruptivas reales, etc) según los criterios dados por el usuario.
        Devuelve una lista con pesos sugeridos y métricas clave.
        """
        if n_stocks is not None:
            n_instruments = n_stocks
        system_prompt = (
            "Eres un asistente experto en inversión disruptiva y tecnología. Devuelve únicamente un array JSON de instrumentos reales y actuales en las siguientes categorías:\n"
            "- Private Equity (fondos de venture capital, private equity, startups de IA, biotecnología, etc)\n"
            "- Tecnología Especializada (ETFs temáticos, acciones disruptivas, fondos de tecnología, robótica, IA, ciberseguridad, semiconductores, etc)\n"
            "- Solo instrumentos REALES y actuales, nunca inventados ni simulados.\n"
            "- Incluye: ticker, nombre, categoría (private_equity, etf_temático, acción_disruptiva, fondo_vc, etc), sector, país, peso (%), rentabilidad esperada, métricas clave (CAGR, drawdown, liquidez, etc), comentarios.\n"
            f"- Diversifica entre private equity y tecnología avanzada. Región: {region}.\n- Devuelve exactamente {n_instruments} instrumentos.\n- Formato: array JSON, sin texto adicional."
        )
        user_prompt = (
            f"Quiero invertir €{amount:,} en una cartera disruptiva global (private equity, tecnología, IA, biotecnología, etc). Dame la lista óptima según los criterios."
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
                    try:
                        disruptive_data = json.loads(json_str_clean)
                    except json.JSONDecodeError:
                        import re
                        json_str_fixed = re.sub(r"(?<=[:,\[\{])\s*'([^']*)'\s*:", r'"\1":', json_str_clean)  # claves
                        json_str_fixed = re.sub(r":\s*'([^']*)'", r':"\1"', json_str_fixed)                # valores
                        disruptive_data = json.loads(json_str_fixed)
                    logger.info(f"Portafolio disruptivo obtenido con {len(disruptive_data)} instrumentos")
                    return disruptive_data
                except Exception as e:
                    logger.error(f"Error parsing JSON from Perplexity: {str(e)} | JSON: {json_str}")
                    raise
            else:
                logger.error("No se encontró un array JSON en la respuesta de Perplexity")
                raise Exception("No JSON array found in Perplexity response")
        except Exception as e:
            logger.error(f"Error al consultar Perplexity API: {str(e)}")
            raise