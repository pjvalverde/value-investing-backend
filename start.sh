#!/bin/bash

echo "Starting Value Investing API on Railway (FULL VERSION)..."
echo "Environment variables:"
echo "PORT: $PORT"

# Verificar API keys necesarias
if [ -z "$PERPLEXITY_API_KEY" ]; then
  echo "ERROR: PERPLEXITY_API_KEY no está configurada"
  echo "No se usarán datos simulados ni predefinidos. Se requiere configurar PERPLEXITY_API_KEY."
  exit 1
else
  echo "PERPLEXITY_API_KEY: ${PERPLEXITY_API_KEY:0:3}..."
fi

if [ -z "$CLAUDE_API_KEY" ]; then
  echo "ERROR: CLAUDE_API_KEY no está configurada"
  exit 1
else
  echo "CLAUDE_API_KEY: ${CLAUDE_API_KEY:0:3}..."
fi

# Iniciar la aplicación
python app_railway.py
