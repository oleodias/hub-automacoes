# ══════════════════════════════════════════════════════════════
# scripts/seed_tudo.py — Roda TODOS os seeds de dados-base em ordem
# ══════════════════════════════════════════════════════════════
# Conveniência para um banco novo: depois de `alembic upgrade head`,
# rode este script uma vez para popular os dados de configuração que
# o Hub precisa para funcionar (unidades, categorias, centros de
# custo, operações e o FAQ da Central de Suporte).
#
# Uso (a partir da raiz do projeto):
#     python scripts/seed_tudo.py
#
# Todos os seeds são idempotentes — rodar de novo NÃO duplica nada.
# ══════════════════════════════════════════════════════════════

import os
import sys

# Raiz do projeto no path (este arquivo vive em scripts/)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# Importa os seeds já existentes (reaproveitando a lógica de cada um)
import seed_notas
from scripts import seed_faq


def main():
    print("\n══════════════════════════════════════════════════")
    print("  SEED COMPLETO — populando dados-base do Hub")
    print("══════════════════════════════════════════════════")

    # 1) Unidades e categorias de notas
    print("\n[1/2] Unidades e categorias...")
    seed_notas.run()

    # 2) FAQ da Central de Suporte
    print("\n[2/2] FAQ da Central de Suporte...")
    seed_faq.seed()

    print("\n✅ Seed completo finalizado.\n")


if __name__ == '__main__':
    main()
