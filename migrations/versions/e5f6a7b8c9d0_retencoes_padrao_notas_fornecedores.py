"""adicionar coluna retencoes_padrao em notas_fornecedores

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-16 12:00:00.000000

A coluna retencoes_padrao (lista JSON de tipos de retenção) é usada em
routes/notas.py (serialização, criação, edição e geração de notas do mês),
mas nunca chegou a ser criada no banco — a migration anterior
('a0773d001063 adicionar retencoes') ficou vazia. Esta migration corrige isso.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('notas_fornecedores') as batch_op:
        batch_op.add_column(sa.Column('retencoes_padrao', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('notas_fornecedores') as batch_op:
        batch_op.drop_column('retencoes_padrao')
