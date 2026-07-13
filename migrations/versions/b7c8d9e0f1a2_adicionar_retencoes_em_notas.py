"""adicionar coluna retencoes em notas

A coluna retencoes (lista JSON de tipos de retenção: ["inss", "iss", ...])
é usada em routes/notas.py (serializar_nota, api_criar_nota e
api_receber_nota), mas nunca chegou a ser criada no banco — a migration
'a0773d001063 adicionar retencoes' ficou vazia, e a correção posterior
(e5f6a7b8c9d0) cobriu apenas o retencoes_padrao de notas_fornecedores.

Sem esta coluna, qualquer GET /notas/api/notas quebra com AttributeError.
Esta migration fecha a lacuna.

Revision ID: b7c8d9e0f1a2
Revises: f7a1c2d3e4b5
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'f7a1c2d3e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('notas') as batch_op:
        batch_op.add_column(sa.Column('retencoes', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('notas') as batch_op:
        batch_op.drop_column('retencoes')
