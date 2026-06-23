# ══════════════════════════════════════════════════════════════
# testar_endpoint.py — testa o POST /relatorios/iniciar do Hub
# ──────────────────────────────────────────────────────────────
# Sobe o robô VIA HTTP (como o n8n faria), validando token + rota.
# O Hub precisa estar RODANDO e nesta máquina (Selenium/Chrome).
#
# Uso (PowerShell):
#   $env:N8N_HUB_TOKEN="seu_token"      # o mesmo do .env do Hub
#   python -m automacoes.relatorios.testar_endpoint automacoes/relatorios/job_teste.json
#
# Opcional: HUB_URL (default http://localhost:5000)
#   $env:HUB_URL="http://localhost:5000"
# ══════════════════════════════════════════════════════════════
import os
import sys
import json

import requests  # já é dependência do projeto


def main():
    arq = sys.argv[1] if len(sys.argv) > 1 else "automacoes/relatorios/job_teste.json"
    hub = os.getenv("HUB_URL", "http://localhost:5000").rstrip("/")
    token = os.getenv("N8N_HUB_TOKEN", "")

    with open(arq, "r", encoding="utf-8") as f:
        job = json.load(f)

    url = f"{hub}/relatorios/iniciar"
    print(f"> POST {url}  (envios: {len(job.get('envios', []))})")
    if not token:
        print("> ⚠️  N8N_HUB_TOKEN vazio — se o Hub exigir token, vai dar 401.")

    resp = requests.post(
        url,
        headers={"X-Hub-Token": token, "Content-Type": "application/json"},
        json=job,
        timeout=900,  # robô é síncrono e pode demorar
    )
    print(f"> HTTP {resp.status_code}")
    try:
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    except Exception:  # noqa: BLE001
        print(resp.text[:2000])


if __name__ == "__main__":
    main()
