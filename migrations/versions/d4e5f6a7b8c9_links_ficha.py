"""cria tabela links_ficha (controle de links gerados)

Registra cada link de ficha gerado: quem gerou, para qual cliente (CNPJ),
quando, validade e se ja foi usado. Da rastreabilidade ao fluxo de fichas.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'links_ficha',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('cnpj_cliente', sa.String(length=14), nullable=False),
        sa.Column('gerado_por_id', sa.Integer(), nullable=True),
        sa.Column('gerado_por_nome', sa.String(length=150), nullable=True),
        sa.Column('vendedor', sa.String(length=255), nullable=True),
        sa.Column('representante', sa.String(length=255), nullable=True),
        sa.Column('captacao', sa.String(length=50), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=True),
        sa.Column('codigo_nl', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expira_em', sa.DateTime(), nullable=False),
        sa.Column('usado_em', sa.DateTime(), nullable=True),
        sa.Column('submission_uuid', sa.String(length=36), nullable=True),
        sa.Column('cnpj_divergente', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_links_ficha_token', 'links_ficha', ['token'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_links_ficha_token', table_name='links_ficha')
    op.drop_table('links_ficha')
