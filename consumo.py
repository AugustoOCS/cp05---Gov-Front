"""Script de consumo (requests) dos endpoints da Sensor Monitoring API.

Uso: python consumo.py [TAG]      (API_URL padrão: http://localhost:8000)
"""
import json
import os
import sys
import uuid

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
SESSION_ID = f"script-{uuid.uuid4().hex[:6]}"


def get(caminho: str, feature: str, params: dict | None = None) -> dict:
    headers = {"X-Session-Id": SESSION_ID, "X-Feature": feature}
    r = requests.get(f"{API_URL}{caminho}", headers=headers, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "MTR-001-TEMP"

    print(f"== Leitura atual: {tag}")
    print(json.dumps(get(f"/v1/sensores/{tag}/leitura-atual", "leitura-atual"), indent=2, ensure_ascii=False))

    print(f"\n== Histórico: {tag} (últimos 5 pontos)")
    hist = get(f"/v1/sensores/{tag}/historico", "historico", {"limite": 50})
    for p in hist["pontos"][-5:]:
        print(p)

    print("\n== Observabilidade (resumo)")
    obs = get("/v1/observabilidade", "observabilidade-script", {"session_id": SESSION_ID})
    print(json.dumps(obs["resumo"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
