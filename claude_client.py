import os
import logging
import requests
from typing import Optional

logger = logging.getLogger("claude-client")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL_DEFAULT = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")


class ClaudeClient:
    """Client for Anthropic Claude – integrates Damodaran + Buffett/Munger framework."""

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
        """Generate elite-level portfolio analysis combining Damodaran + Buffett/Munger."""

        system_prompt = (
            "Eres un analista financiero de élite que integra dos frameworks complementarios:\n\n"
            "1. VALUE INVESTING (Warren Buffett & Charlie Munger):\n"
            "   - Moat competitivo duradero (brand, network effects, switching costs, cost advantages)\n"
            "   - Calidad excepcional del management y cultura de asignación racional de capital\n"
            "   - Margen de seguridad explícito sobre el valor intrínseco\n"
            "   - Empresas que puedas entender y predecir a 10+ años\n"
            "   - ROIC consistentemente superior al coste de capital (>15% sostenido)\n\n"
            "2. ANÁLISIS CUANTITATIVO (Aswath Damodaran):\n"
            "   - Valoración por DCF: el precio justo es el PV de los FCF futuros descontados al WACC\n"
            "   - Creación de valor SOLO si ROIC > WACC (spread positivo)\n"
            "   - EV/EBITDA para comparaciones sectoriales robustas\n"
            "   - FCF Yield como indicador de generación real de caja para el inversor\n"
            "   - CAGR de ingresos sostenible a 5 años como motor del valor terminal\n"
            "   - Margen de seguridad explícito: precio mercado vs valor intrínseco DCF\n\n"
            "Tu análisis debe ser RIGUROSO, CUANTITATIVO donde sea posible, y orientado a la "
            "DECISIÓN DE INVERSIÓN del inversor particular. Identifica fortalezas, riesgos reales "
            "y red flags. Usa lenguaje profesional pero accesible. Sé directo y opinativo."
        )

        header = (
            f"Analiza el siguiente portafolio de inversión usando el framework combinado "
            f"Damodaran + Buffett/Munger. Idioma de respuesta: {language}.\n\n"
        )
        if strategy_description:
            header += f"Estrategia declarada: {strategy_description}\n\n"

        table_lines = [
            "COMPOSICIÓN DEL PORTAFOLIO:",
            "| Ticker | Categoría | Sector | País | Peso% | Precio | Acciones | Valor | ROIC | EV/EBITDA | FCF Yield | Margen Seg. | Métricas |",
            "|--------|-----------|--------|------|-------|--------|----------|-------|------|-----------|-----------|-------------|----------|",
        ]
        for stock in portfolio or []:
            peso = stock.get("peso", stock.get("weight"))
            try:
                peso_str = f"{float(peso):.1f}%" if peso is not None else "-"
            except Exception:
                peso_str = "-"
            metrics = stock.get("metrics", {}) or {}
            roic = metrics.get("roic", metrics.get("ROIC", "-"))
            ev_ebitda = metrics.get("ev_ebitda", metrics.get("EV_EBITDA", "-"))
            fcf_yield = metrics.get("fcf_yield", "-")
            margin_safety = metrics.get("margin_of_safety", "-")
            other_metrics = {k: v for k, v in metrics.items()
                            if k not in ("roic", "ROIC", "ev_ebitda", "EV_EBITDA",
                                         "fcf_yield", "margin_of_safety", "intrinsic_value",
                                         "revenue_cagr_5y")}
            metrics_str = ", ".join([f"{k}: {v}" for k, v in list(other_metrics.items())[:3]]) or "-"
            category = stock.get("category", stock.get("estrategia", stock.get("strategy", "-")))
            table_lines.append(
                f"| {stock.get('ticker', stock.get('symbol', '-'))} | "
                f"{category} | "
                f"{stock.get('sector', '-')} | {stock.get('country', stock.get('país', '-'))} | {peso_str} | "
                f"{stock.get('price', '-')} | {stock.get('shares', '-')} | {stock.get('amount', '-')} | "
                f"{roic} | {ev_ebitda} | {fcf_yield} | {margin_safety} | {metrics_str} |"
            )

        analysis_request = (
            "\n\nAhora proporciona un análisis profesional estructurado así:\n\n"
            "## 📊 Visión General del Portafolio\n"
            "Evaluación de la composición, diversificación y alineación con principios de value investing.\n\n"
            "## 🏰 Análisis de Moats (Buffett/Munger)\n"
            "Para las posiciones más relevantes, evalúa la solidez del moat competitivo. "
            "¿Cuáles tienen ventajas duraderas? ¿Cuáles son vulnerables?\n\n"
            "## 📐 Análisis Cuantitativo (Damodaran)\n"
            "Evalúa el ROIC vs WACC para el portafolio agregado. "
            "¿Las valoraciones EV/EBITDA son razonables vs sector? "
            "¿El FCF Yield promedio es atractivo? "
            "¿Existe margen de seguridad real en las posiciones principales?\n\n"
            "## ⚠️ Riesgos y Alertas\n"
            "Identifica concentraciones sectoriales/geográficas, valoraciones excesivas, "
            "deuda elevada o red flags cualitativas. Sé específico.\n\n"
            "## 💡 Recomendaciones Concretas\n"
            "3-5 acciones concretas que el inversor debería considerar (ajustes, añadir, reducir). "
            "Con justificación basada en ambos frameworks.\n\n"
            "Mantén el análisis en máximo 600 palabras. Directo, opinativo, accionable."
        )

        user_content = header + "\n".join(table_lines) + analysis_request

        payload = {
            "model": self.model,
            "max_tokens": 700,
            "temperature": 0.65,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            resp = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=90)
            if resp.status_code != 200:
                logger.error("Claude API error %s: %s", resp.status_code, resp.text[:500])
                raise RuntimeError(f"Claude API error {resp.status_code}")
            data = resp.json()
            blocks = data.get("content") or []
            if not blocks:
                return "[Sin respuesta de Claude]"
            parts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
            return ("\n".join(parts)).strip() or "[Sin contenido]"
        except Exception as e:
            logger.error("Error al llamar a Claude: %s", e)
            raise

    def generate_decision(self, analysis_text: str, portfolio_hint: Optional[dict] = None, language: str = "es"):
        """Ask Claude (as a CIO using Damodaran + Buffett/Munger) for a strict JSON invest decision."""
        system_prompt = (
            "Eres un Chief Investment Officer con 30 años de experiencia, formado en la filosofía "
            "combinada de Buffett/Munger (calidad + moat + margen de seguridad) y Damodaran "
            "(rigor cuantitativo: ROIC > WACC, FCF Yield, EV/EBITDA, valor intrínseco DCF). "
            "Tu decisión es BINARIA: invertir o no invertir, basada en el análisis previo. "
            "Devuelve ÚNICAMENTE un objeto JSON válido, sin texto adicional, con esta estructura exacta:\n"
            '{"decision": "invertir" | "no_invertir", "score": 0-100, '
            '"reasons": ["razón 1", "razón 2", "razón 3"], '
            '"alerts": ["alerta 1", "alerta 2"], '
            '"damodaran_verdict": "ROIC > WACC: Sí/No. Margen de seguridad: X%. FCF Yield: X%.", '
            '"buffett_verdict": "Moat: Fuerte/Moderado/Débil. Management: Excelente/Bueno/Regular."}'
        )
        context = portfolio_hint or {}
        user_content = (
            f"Con base en este análisis del portafolio, emite tu decisión de inversión como CIO.\n\n"
            f"ANÁLISIS:\n{analysis_text}\n\n"
            f"DATOS DEL PORTAFOLIO (referencia):\n{context}"
        )
        payload = {
            "model": self.model,
            "max_tokens": 500,
            "temperature": 0.15,
            "system": system_prompt,
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
            try:
                parsed = _json.loads(text)
            except Exception:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = _json.loads(text[start:end + 1])
                else:
                    raise RuntimeError("Claude did not return valid JSON")

            decision = (parsed.get("decision") or "").lower()
            if decision not in ("invertir", "no_invertir"):
                decision = "no_invertir"
            score = min(100, max(0, int(float(parsed.get("score", 0)))))
            reasons = parsed.get("reasons") or parsed.get("razones") or []
            alerts = parsed.get("alerts") or parsed.get("alertas") or []
            damodaran_verdict = parsed.get("damodaran_verdict", "")
            buffett_verdict = parsed.get("buffett_verdict", "")
            return {
                "decision": decision,
                "score": score,
                "reasons": reasons,
                "alerts": alerts,
                "damodaran_verdict": damodaran_verdict,
                "buffett_verdict": buffett_verdict,
            }
        except Exception as e:
            logger.error("Error al obtener decisión de Claude: %s", e)
            raise
