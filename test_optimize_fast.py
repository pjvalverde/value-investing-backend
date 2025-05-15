import requests
import json

# Cambia la URL si tu backend corre en otro puerto o dominio
def test_optimize():
    url = "http://localhost:8000/api/portfolio/optimize"
    payload = {
        "amount": 1000,  # Monto pequeño para que Perplexity responda rápido
        "target_alloc": {"growth": 100}
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("\nPortfolio generado (resumido):")
            print(json.dumps(data["allocation"], indent=2) if "allocation" in data else data)
        else:
            print("\nRespuesta de error:")
            print(resp.text)
    except Exception as e:
        print(f"Error en la petición: {e}")

if __name__ == "__main__":
    test_optimize()
