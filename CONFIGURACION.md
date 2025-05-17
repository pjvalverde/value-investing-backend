# Configuraciu00f3n de Value Investing Backend

## Requisitos previos

Para que la aplicaciu00f3n funcione correctamente con datos REALES (no simulados), es necesario configurar las siguientes API keys:

### 1. Perplexity API Key

Se utiliza para obtener recomendaciones de acciones basadas en criterios especu00edficos.

1. Regu00edstrate en [Perplexity](https://www.perplexity.ai/)
2. Obtiene tu API key
3. Configura la variable de entorno `PERPLEXITY_API_KEY` con tu clave

## Cu00f3mo configurar las variables de entorno

### Desarrollo local

1. Crea un archivo `.env` en la rau00edz del proyecto con el siguiente contenido:

```
# Alpha Vantage API key
ALPHAVANTAGE_API_KEY=tu_api_key_aqui

# Perplexity API key
PERPLEXITY_API_KEY=tu_api_key_aqui
```

2. Reemplaza `tu_api_key_aqui` con tus claves reales

### Despliegue en Railway

1. Ve a tu proyecto en Railway
2. Haz clic en la pestau00f1a "Variables"
3. Agrega las variables `ALPHAVANTAGE_API_KEY` y `PERPLEXITY_API_KEY` con sus respectivos valores
4. Guarda los cambios y redespliega la aplicaciu00f3n

## Modo de simulaciu00f3n

Si no configuras las API keys, la aplicaciu00f3n funcionaru00e1 en modo de simulaciu00f3n, utilizando datos predefinidos en lugar de datos reales. Esto es u00fatil para desarrollo, pero no es recomendable para producciu00f3n.

## Verificaciu00f3n

Para verificar que las API keys estu00e1n configuradas correctamente, puedes ejecutar:

```bash
python test_perplexity_api.py  # Verifica la conexiu00f3n con Perplexity API
```

Si ves el mensaje "API key encontrada" y obtienes resultados, la configuraciu00f3n es correcta.
