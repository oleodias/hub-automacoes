"""controle de envio ao N8N nas submissoes (anti ficha orfa)

Resolve A-05: a ficha e salva antes de chamar o N8N. Se o webhook falha,
a ficha ficava 'orfa' (salva mas nunca processada). Adiciona colunas para
sinalizar o status do envio e guardar o que reenviar:

  - envio_n8n   : 'enviado' (normal) | 'falhou' (precisa reenviar)
  - n8n_erro    : mensagem do erro do ultimo envio
  - n8n_payload : dados a reenviar ao N8N (replay pelo Monitor)

Linhas existentes recebem 'enviado' (server_default), pois ja foram
processadas antes desta mudanca.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'submissoes',
        sa.Column('envio_n8n', sa.String(length=20),
                  server_default='enviado', nullable=True),
    )
    op.add_column('submissoes', sa.Column('n8n_erro', sa.Text(), nullable=True))
    op.add_column('submissoes', sa.Column('n8n_payload', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('submissoes', 'n8n_payload')
    op.drop_column('submissoes', 'n8n_erro')
    op.drop_column('submissoes', 'envio_n8n')
