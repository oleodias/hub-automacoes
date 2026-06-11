"""adiciona o prefixo padrao da empresa (cm_hub_aut_) a todas as tabelas

Padroniza os nomes das 17 tabelas com o prefixo 'cm_hub_aut_', exigido
pela TI e valido em TODOS os ambientes (Postgres no dev, Oracle em
homolog/prod), para que o codigo seja unico.

No PostgreSQL, ALTER TABLE ... RENAME TO mantem automaticamente as chaves
estrangeiras e os indices ligados a tabela (eles continuam funcionando e
apenas conservam o nome antigo, o que e cosmetico). Por isso a ordem dos
renames nao importa e nada precisa ser recriado.

Observacao: no Oracle as tabelas ja nascem com o prefixo, a partir do DDL
em docs/BANCO_DE_DADOS_ORACLE.md — o Alembic NAO roda no Oracle.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Prefixo padrao da empresa.
PREFIXO = 'cm_hub_aut_'

# As 17 tabelas, com o nome SIMPLES (como estao hoje no banco).
TABELAS = [
    'usuarios',
    'submissoes',
    'links_ficha',
    'execucoes',
    'fila_execucao',
    'lancamentos_notas',
    'centros_custo',
    'operacoes_nota',
    'notas_categorias',
    'notas_unidades',
    'notas_fornecedores',
    'notas',
    'chamados',
    'chamados_anexos',
    'chamados_historico',
    'notificacoes',
    'faq_perguntas',
]


def upgrade() -> None:
    """Renomeia 'tabela' -> 'cm_hub_aut_tabela'."""
    for nome in TABELAS:
        op.rename_table(nome, f'{PREFIXO}{nome}')


def downgrade() -> None:
    """Desfaz: 'cm_hub_aut_tabela' -> 'tabela'."""
    for nome in TABELAS:
        op.rename_table(f'{PREFIXO}{nome}', nome)
