"""baseline inicial

Revision ID: a879dd2a923b
Revises: e5d58f95823c
Create Date: 2026-04-20 08:31:38.555203

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a879dd2a923b'
down_revision: Union[str, Sequence[str], None] = 'e5d58f95823c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
