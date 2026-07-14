"""prefixar todas as tabelas com cm_hub_aut_

O Hub saiu do Postgres local para um Postgres na VM do servidor, onde o padrão
de nomenclatura exige o prefixo 'cm_hub_aut_' em todas as tabelas. Os
__tablename__ do models.py e o SQL cru de utils/fila.py já foram atualizados
para os nomes prefixados; esta migration renomeia as 14 tabelas no banco para
que o schema bata com o código.

IDEMPOTENTE de propósito: só renomeia uma tabela se o nome ANTIGO existir e o
NOVO ainda não. Assim a mesma migration serve aos dois cenários sem quebrar:
  - Banco local (dev), ainda sem prefixo → renomeia de fato.
  - Banco da VM, já com as tabelas 'cm_hub_aut_*' → vira no-op.

Na VM, onde as tabelas já nascem prefixadas, o correto é marcar o histórico com
'alembic stamp head' (sem executar). A idempotência acima é só uma rede de
segurança caso alguém rode 'alembic upgrade head' por engano.

Índices e constraints (ex.: ix_notas_mes_ano) acompanham o rename da tabela e
mantêm o nome — não precisam de tratamento à parte.

Revision ID: c9e0f1a2b3c4
Revises: b7c8d9e0f1a2
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e0f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PREFIXO = 'cm_hub_aut_'

# Nomes originais (sem prefixo) das 14 tabelas do Hub.
TABELAS = [
    'usuarios',
    'submissoes',
    'links_ficha',
    'execucoes',
    'fila_execucao',
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


def _renomear(de_nome: str, para_nome: str) -> None:
    """Renomeia 'de_nome' → 'para_nome' apenas se for seguro (idempotente)."""
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if de_nome in existentes and para_nome not in existentes:
        op.rename_table(de_nome, para_nome)


def upgrade() -> None:
    """Prefixa as tabelas: 'usuarios' → 'cm_hub_aut_usuarios', etc."""
    for tabela in TABELAS:
        _renomear(tabela, PREFIXO + tabela)


def downgrade() -> None:
    """Remove o prefixo: 'cm_hub_aut_usuarios' → 'usuarios', etc."""
    for tabela in TABELAS:
        _renomear(PREFIXO + tabela, tabela)
