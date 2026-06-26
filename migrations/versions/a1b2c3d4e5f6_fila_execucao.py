"""cria tabela fila_execucao (fila persistente um-robo-por-vez)

Resolve A-01: a fila sai da memoria de um processo e passa para o banco,
funcionando com varios workers/containers.

Revision ID: a1b2c3d4e5f6
Revises: fdeee52be543
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fdeee52be543'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'fila_execucao',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('token', sa.String(length=36), nullable=False),
        sa.Column('recurso', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('resume_url', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('iniciado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index(
        'ix_fila_execucao_recurso_status',
        'fila_execucao',
        ['recurso', 'status'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_fila_execucao_recurso_status', table_name='fila_execucao')
    op.drop_table('fila_execucao')
