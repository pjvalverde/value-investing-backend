from fastapi import FastAPI
import os

app = FastAPI(title="Value Investing API Railway Edition")

@app.get("/api/env/perplexity")
def check_perplexity_key():
    """
    Endpoint de diagnóstico: muestra si PERPLEXITY_API_KEY está cargada (sin exponer el valor)
    """
    key = os.getenv("PERPLEXITY_API_KEY")
    if key:
        return {"perplexity_api_key_loaded": True, "length": len(key)}
    else:
        return {"perplexity_api_key_loaded": False}

@app.get("/")
def root():
    return {"message": "API Railway funcionando"}
