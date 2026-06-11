# ══════════════════════════════════════════════════════════════
# seed_notas.py — Dados iniciais do módulo Controle de Notas
# ══════════════════════════════════════════════════════════════
# Popula as tabelas notas_unidades e notas_categorias com os
# valores iniciais que o React app espera (matriz/f2/f3/f4 e
# as 11 categorias do mock.js).
#
# Como rodar (a partir da raiz do projeto, depois do upgrade do
# Alembic):
#     python scripts/seed_notas.py
#
# Idempotente: rodar várias vezes NÃO duplica registros — só
# adiciona o que ainda não existe.
# ══════════════════════════════════════════════════════════════

import sys
import os

# Garante que conseguimos importar o app mesmo rodando de fora.
# Este arquivo vive em scripts/, então a raiz fica DOIS níveis acima.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models import NotasCategoria, NotasUnidade


# ── Dados iniciais ────────────────────────────────────────────
# Os IDs (slugs) batem exatamente com os do mock.js do React,
# pra evitar atrito quando conectarmos a API ao Kanban.

UNIDADES = [
    # (id,       nome,             short,    ordem)
    ('matriz', 'Matriz (1)',     'MTZ',     1),
    ('f2',     'Filial 2',       'F2',      2),
    ('f3',     'Filial 3 (SC)',  'F3 SC',   3),
    ('f4',     'Filial 4',       'F4',      4),
]

CATEGORIAS = [
    # (id,         nome,                         ordem)
    ('energia',    'Energia elétrica',            1),
    ('agua',       'Água e esgoto',               2),
    ('internet',   'Internet/Telefonia',          3),
    ('movel',      'Telefonia móvel',             4),
    ('assinatura', 'Assinatura digital',          5),
    ('juridica',   'Assessoria jurídica',         6),
    ('contabil',   'Assessoria contábil',         7),
    ('aluguel',    'Aluguel',                     8),
    ('manutencao', 'Manutenção',                  9),
    ('escritorio', 'Material de escritório',     10),
    ('outros',     'Outros',                     11),
]


def run():
    """Insere unidades e categorias que ainda não existem."""
    with app.app_context():
        # ── Unidades ───────────────────────────────────────────
        criadas_u = 0
        for uid, nome, short, ordem in UNIDADES:
            existente = db.session.get(NotasUnidade, uid)
            if not existente:
                db.session.add(NotasUnidade(
                    id=uid, nome=nome, short=short, ordem=ordem, ativa=True
                ))
                criadas_u += 1

        # ── Categorias ─────────────────────────────────────────
        criadas_c = 0
        for cid, nome, ordem in CATEGORIAS:
            existente = db.session.get(NotasCategoria, cid)
            if not existente:
                db.session.add(NotasCategoria(
                    id=cid, nome=nome, ordem=ordem, ativa=True
                ))
                criadas_c += 1

        db.session.commit()

        # ── Resumo ─────────────────────────────────────────────
        total_u = NotasUnidade.query.count()
        total_c = NotasCategoria.query.count()

        print()
        print("═══════════════════════════════════════════════════")
        print("  Seed de Controle de Notas — concluído")
        print("═══════════════════════════════════════════════════")
        print(f"  Unidades:    {criadas_u} novas inseridas  ·  {total_u} no total")
        print(f"  Categorias:  {criadas_c} novas inseridas  ·  {total_c} no total")
        print("═══════════════════════════════════════════════════")
        print()


if __name__ == '__main__':
    run()