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
#
# NOTA: o seed de centros de custo / operações lê os arquivos
# scripts/dados/lista_cc.txt e scripts/dados/lista_operacoes.txt.
# Essa pasta é ignorada pelo Git (dados internos), então copie-a do
# PC antigo. Se os arquivos não existirem, esse passo é PULADO com
# um aviso — os demais seeds rodam normalmente.
# ══════════════════════════════════════════════════════════════

import os
import sys

# Raiz do projeto no path (este arquivo vive em scripts/)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# Importa os seeds já existentes (reaproveitando a lógica de cada um)
import seed_notas
from scripts import seed_dados_notas, seed_faq


def main():
    print("\n══════════════════════════════════════════════════")
    print("  SEED COMPLETO — populando dados-base do Hub")
    print("══════════════════════════════════════════════════")

    # 1) Unidades e categorias de notas
    print("\n[1/3] Unidades e categorias...")
    seed_notas.run()

    # 2) Centros de custo e operações (dependem de arquivos .txt internos)
    print("\n[2/3] Centros de custo e operações...")
    if os.path.exists(seed_dados_notas.ARQUIVO_CC) and os.path.exists(seed_dados_notas.ARQUIVO_OP):
        seed_dados_notas.executar()
    else:
        print("   ⚠️  Pulado: arquivos não encontrados em scripts/dados/")
        print(f"      Esperado: {seed_dados_notas.ARQUIVO_CC}")
        print(f"                {seed_dados_notas.ARQUIVO_OP}")
        print("      Copie a pasta scripts/dados/ do PC antigo e rode de novo.")

    # 3) FAQ da Central de Suporte
    print("\n[3/3] FAQ da Central de Suporte...")
    seed_faq.seed()

    print("\n✅ Seed completo finalizado.\n")


if __name__ == '__main__':
    main()
