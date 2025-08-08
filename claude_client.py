import os
import logging
import requests
from typing import Optional

logger = logging.getLogger("claude-client")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL_DEFAULT = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")


class ClaudeClient:
    """Minimal client that calls Anthropic's HTTP API directly.
    Accepts ANTHROPIC_API_KEY or CLAUDE_API_KEY.
    """

    def __init__(self, api_key=None, model: str = MODEL_DEFAULT):
        self.api_key = (
            api_key
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("CLAUDE_API_KEY")
        )
        if not self.api_key:
            raise ValueError("Set ANTHROPIC_API_KEY (or CLAUDE_API_KEY) in environment variables.")
        self.model = model

    def generate_analysis(self, portfolio, strategy_description=None, language="es"):
        """Generate a detailed qualitative analysis for a portfolio using Claude."""
        # Build prompt
        header = (
            "Eres un analista financiero experto en inversión cuantitativa y value investing. "
            "Te entrego la composición de un portafolio optimizado. "
            "Primero, presenta una tabla en formato Markdown con las siguientes columnas: "
            "Ticker, Estrategia, Sector, País, Peso (%), Precio, Acciones, Valor, Métricas clave. "
            "Usa los datos que te proporciono abajo. Después de la tabla, redacta un análisis profesional, "
            "recomendaciones y alertas visuales si detectas riesgos o concentraciones. "
            f"El análisis debe estar en {language}.\n"
        )
        if strategy_description:
            header += f"\nDescripción de la estrategia: {strategy_description}\n"
        table = [
            "\nComposición del portafolio:",
            "| Ticker | Estrategia | Sector | País | Peso (%) | Precio | Acciones | Valor | Métricas clave |",
            "|--------|------------|--------|------|----------|--------|----------|-------|----------------|",
        ]
        for stock in portfolio or []:
            peso = stock.get("peso", stock.get("weight"))
            try:
                peso_str = f"{float(peso):.2f}%" if peso is not None else "-"
            except Exception:
                peso_str = "-"
            metrics = stock.get("metrics", {}) or {}
            metrics_str = ", ".join([f"{k}: {v}" for k, v in metrics.items()]) if metrics else "-"
            table.append(
                f"| {stock.get('ticker', stock.get('symbol','-'))} | "
                f"{stock.get('estrategia', stock.get('strategy','-'))} | "
                f"{stock.get('sector','-')} | {stock.get('country','-')} | {peso_str} | "
                f"{stock.get('price','-')} | {stock.get('shares','-')} | {stock.get('amount','-')} | {metrics_str} |"
            )
        footer = (
            "\nAhora, debajo de la tabla, presenta un análisis profesional, recomendaciones y alertas visuales "
            "si detectas riesgos o concentraciones."
        )
        user_content = "\n".join([header] + table + [footer])

        payload = {
            "model": self.model,
            "max_tokens": 800,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": user_content}
            ],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            resp = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200:
                logger.error("Claude API error %s: %s", resp.status_code, resp.text[:500])
                raise RuntimeError(f"Claude API error {resp.status_code}")
            data = resp.json()
            # messages API returns a list of content blocks
            blocks = data.get("content") or []
            if not blocks:
                return "[Sin respuesta de Claude]"
            parts = []
            for b in blocks:
                # text blocks have type "text"
                if isinstance(b, dict) and b.get("type") == "text":
                    parts.append(b.get("text", ""))
            return ("\n".join(parts)).strip() or "[Sin contenido]"
        except Exception as e:
            logger.error("Error al llamar a Claude: %s", e)
            raise

    def generate_decision(self, analysis_text: str, portfolio_hint: Optional[dict] = None, language: str = "es"):
        """Ask Claude to return a strict JSON decision to invest or not.
        Returns dict with keys: decision (invertir|no_invertir), score (0-100), reasons (list[str]), alerts (list[str]).
        """
        instruction = (
            "Eres un CIO con filosofía de Value Investing (Buffett y Munger). "
            "Con base en el análisis anterior, devuelve SOLO un objeto JSON estricto con: "
            "decision ('invertir' o 'no_invertir'), score (0-100), reasons (lista corta), alerts (lista corta). "
            "No incluyas texto adicional."
        )
        context = portfolio_hint or {}
        user_content = (
            f"{instruction}\n\nANÁLISIS:\n{analysis_text}\n\nPISTAS_PORTAFOLIO(JSON opcional):\n{context}"
        )
        payload = {
            "model": self.model,
            "max_tokens": 400,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": user_content}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            resp = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=45)
            if resp.status_code != 200:
                logger.error("Claude decision API error %s: %s", resp.status_code, resp.text[:500])
                raise RuntimeError(f"Claude API error {resp.status_code}")
            data = resp.json()
            blocks = data.get("content") or []
            text = "".join([b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]).strip()
            import json as _json
            # Try parse as JSON
            try:
                parsed = _json.loads(text)
            except Exception:
                # Attempt to extract JSON object substring
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = _json.loads(text[start:end+1])
                else:
                    raise RuntimeError("Claude did not return JSON")
            # Normalize
            decision = (parsed.get("decision") or "").lower()
            if decision not in ("invertir", "no_invertir"):
                decision = "no_invertir"
            score = int(float(parsed.get("score", 0)))
            reasons = parsed.get("reasons") or parsed.get("razones") or []
            alerts = parsed.get("alerts") or parsed.get("alertas") or []
            return {"decision": decision, "score": score, "reasons": reasons, "alerts": alerts}
        except Exception as e:
            logger.error("Error al obtener decisión de Claude: %s", e)
            raise
