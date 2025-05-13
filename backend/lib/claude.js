// Wrapper para la API de Claude
const axios = require('axios');
require('dotenv').config();

/**
 * Funciu00f3n para llamar a la API de Claude
 * @param {string} prompt - El prompt para Claude
 * @returns {Promise<string>} - La respuesta de Claude
 */
async function runClaude(prompt) {
  try {
    const CLAUDE_API_KEY = process.env.CLAUDE_API_KEY;
    
    if (!CLAUDE_API_KEY) {
      console.error('CLAUDE_API_KEY no estu00e1 configurada en las variables de entorno');
      return JSON.stringify({
        error: 'Claude API no configurada',
        message: 'Por favor configure CLAUDE_API_KEY en las variables de entorno'
      });
    }
    
    const response = await axios.post(
      'https://api.anthropic.com/v1/messages',
      {
        model: 'claude-3-opus-20240229',
        max_tokens: 4000,
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.2
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': CLAUDE_API_KEY,
          'anthropic-version': '2023-06-01'
        }
      }
    );
    
    return response.data.content[0].text;
  } catch (error) {
    console.error('Error al llamar a Claude API:', error);
    return JSON.stringify({
      error: 'Error en Claude API',
      message: error.message
    });
  }
}

module.exports = { runClaude };
