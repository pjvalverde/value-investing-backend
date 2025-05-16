import os
import logging
from anthropic import Anthropic, AsyncAnthropic, HUMAN_PROMPT, AI_PROMPT

logger = logging.getLogger("claude-client")

class ClaudeClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY is not set in environment variables.")
        self.client = Anthropic(api_key=self.api_key)

    def generate_analysis(self, portfolio, strategy_description=None, language="es"):
        """
        Generate a detailed qualitative analysis for a portfolio using Claude.
        Args:
            portfolio (list): List of dicts with stock info (ticker, sector, metrics, allocation, etc.).
            strategy_description (str): Optional description of the investment strategy.
            language (str): Output language ('es' for Spanish, 'en' for English).
        Returns:
            str: Claude's analysis.
        """
        prompt = (
            f"{HUMAN_PROMPT} Eres un analista financiero experto en inversión cuantitativa y value investing. "
            f"Te entrego la composición de un portafolio optimizado, junto con métricas relevantes de cada acción. "
            f"Redacta un análisis profesional y detallado justificando la selección, riesgos, oportunidades y diversificación. "
            f"Incluye referencias a la filosofía de Buffett y Graham, y sugiere mejoras si es relevante. "
            f"El análisis debe estar en {language}.\n"
        )
        if strategy_description:
            prompt += f"\nDescripción de la estrategia: {strategy_description}\n"
        prompt += f"\nComposición del portafolio:\n"
        for stock in portfolio:
            # Asegurar que el peso sea float para evitar errores de formato
            peso = stock.get('peso')
            if peso is None:
                peso = stock.get('weight')
            try:
                peso_float = float(peso)
                peso_str = f"{peso_float:.2f}%"
            except (TypeError, ValueError):
                peso_str = "-"
            prompt += f"- {stock.get('ticker')} | Sector: {stock.get('sector')} | Peso: {peso_str} | Métricas: {stock.get('metrics', {})}\n"
        prompt += f"{AI_PROMPT}"
        try:
            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=800,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            # El contenido viene como una lista de bloques, usualmente uno solo
            return response.content[0].text.strip() if response.content else "[Sin respuesta de Claude]"
        except Exception as e:
            logger.error(f"Error al llamar a Claude: {str(e)}")
            return f"[Error al generar análisis con Claude: {e}]"
