# -*- coding: utf-8 -*-
"""
limpar_fila.py — Esvazia (destrava) a fila de execução de um robô.

Uso:
    python scripts/limpar_fila.py <recurso>

Recursos:
    relatorios   robô de relatórios aos laboratórios (n8n)
    cadastro     fluxo de cadastro de clientes (n8n)
    rpa          robôs de itens / MDF / fornecedor
    all          limpa TODAS as filas acima

⚠️ Destrutivo: remove TODOS os itens do recurso, inclusive um que esteja
   executando. Use quando a fila travar. Lê o DATABASE_URL do .env do projeto,
   então pode rodar de qualquer pasta (desde que o banco seja alcançável).
"""
import os
import sys

# Garante que o projeto (pasta-pai de scripts/) esteja no path e que o .env
# do projeto seja carregado, rode de onde rodar.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:  # evita travar com acentos/emoji no console do Windows (cp1252)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from utils.fila import (
    fila_cadastro_reset,
    fila_cadastro_status_dict,
    RECURSO_RPA,
    RECURSO_CADASTRO,
    RECURSO_RELATORIOS,
)

RECURSOS = {
    "relatorios": RECURSO_RELATORIOS,
    "cadastro": RECURSO_CADASTRO,
    "rpa": RECURSO_RPA,
}


def _uso():
    print("Uso: python scripts/limpar_fila.py <recurso>")
    print("  recurso: relatorios | cadastro | rpa | all")


def main():
    args = sys.argv[1:]
    if not args:
        _uso()
        return 1

    alvo = args[0].strip().lower()
    if alvo == "all":
        recursos = list(RECURSOS.values())
    elif alvo in RECURSOS:
        recursos = [RECURSOS[alvo]]
    else:
        print(f"❌ Recurso desconhecido: {alvo!r}")
        _uso()
        return 1

    total = 0
    for r in recursos:
        antes = fila_cadastro_status_dict(r)
        qtd = fila_cadastro_reset(r)
        total += qtd
        print(f"🧹 [{r}] aguardando={antes['tamanho_fila']} | "
              f"em_execucao={antes['em_execucao']} → removidos {qtd}")
    print(f"✅ Total removido: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
