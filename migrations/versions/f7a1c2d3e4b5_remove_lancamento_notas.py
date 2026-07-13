"""remove automacao de lancamento de notas (drop das 3 tabelas)

A automacao de Lancamento de Notas foi descontinuada — o proprio sistema
da Ciamed passou a fazer esse trabalho. Esta migration remove todo o
rastro no banco:

  - lancamentos_notas   (fila de notas p/ o robo; estava vazia)
  - centros_custo       (dados de apoio dos dropdowns)
  - operacoes_nota      (dados de apoio dos dropdowns)

Tambem apaga as perguntas de FAQ do modulo 'lancamento_notas'.

O downgrade() recria a ESTRUTURA das tabelas (inclusive o indice unico
parcial de chave de acesso), mas nao restaura os dados — eles eram
reproduziveis via os antigos seeds.

Revision ID: f7a1c2d3e4b5
Revises: e5f6a7b8c9d0
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a1c2d3e4b5'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nome do indice unico parcial criado na migration b2c3d4e5f6a7
INDICE_CHAVE_ATIVA = 'uq_lancamentos_notas_chave_ativa'
CONDICAO_CHAVE_ATIVA = "status <> 'cancelada' AND chave_acesso IS NOT NULL"


def upgrade() -> None:
    """Apaga as tabelas da automacao e as perguntas de FAQ do modulo."""
    # 1) Limpa o FAQ do modulo (a tabela faq_perguntas continua existindo,
    #    e usada pelos outros modulos).
    op.execute("DELETE FROM faq_perguntas WHERE modulo = 'lancamento_notas'")

    # 2) Dropa as tabelas. Ao dropar a tabela, o Postgres remove
    #    automaticamente os indices dependentes (inclusive o unico parcial).
    op.drop_table('lancamentos_notas')
    op.drop_table('operacoes_nota')
    op.drop_table('centros_custo')


def downgrade() -> None:
    """Recria a ESTRUTURA das tabelas (sem os dados)."""
    # ── centros_custo ──────────────────────────────────────────
    op.create_table(
        'centros_custo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=False),
        sa.Column('empresa', sa.String(length=50), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_centros_custo_codigo'), 'centros_custo', ['codigo'], unique=True
    )

    # ── operacoes_nota ─────────────────────────────────────────
    op.create_table(
        'operacoes_nota',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('descricao', sa.String(length=500), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_operacoes_nota_codigo'), 'operacoes_nota', ['codigo'], unique=True
    )

    # ── lancamentos_notas ──────────────────────────────────────
    op.create_table(
        'lancamentos_notas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chave_acesso', sa.String(length=44), nullable=True),
        sa.Column('numero_nota', sa.String(length=20), nullable=True),
        sa.Column('serie', sa.String(length=5), nullable=True),
        sa.Column('tipo_nota', sa.String(length=20), nullable=True),
        sa.Column('fornecedor_cnpj', sa.String(length=20), nullable=True),
        sa.Column('fornecedor_nome', sa.String(length=255), nullable=True),
        sa.Column('valor_total', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('xml_path', sa.String(length=500), nullable=True),
        sa.Column('dados_xml', sa.JSON(), nullable=True),
        sa.Column('dados_complementares', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('mensagem_erro', sa.Text(), nullable=True),
        sa.Column('screenshot_erro', sa.String(length=500), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('usuario_nome', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_lancamentos_notas_chave_acesso'),
        'lancamentos_notas', ['chave_acesso'], unique=False,
    )
    # Recria o indice unico parcial (Postgres) da migration b2c3d4e5f6a7
    op.create_index(
        INDICE_CHAVE_ATIVA,
        'lancamentos_notas', ['chave_acesso'], unique=True,
        postgresql_where=sa.text(CONDICAO_CHAVE_ATIVA),
    )
