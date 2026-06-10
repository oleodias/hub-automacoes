"""indice unico parcial em lancamentos_notas.chave_acesso (notas ativas)

Resolve A-04: impede que a MESMA nota (mesma chave de acesso) tenha dois
lancamentos ativos ao mesmo tempo — o que faria o robo lancar a nota em
duplicidade no NLWeb. Notas 'cancelada' ficam de fora do indice, entao e
possivel reenviar uma nota depois de cancelar a anterior.

Antes de criar o indice, a migration verifica se ja existem duplicatas
ativas no banco. Se existirem, ela PARA com uma mensagem clara em vez de
falhar com um erro criptico do Postgres — assim da pra tratar os dados
com cuidado antes de aplicar a trava.

Revision ID: b2c3d4e5f6a7
Revises: a0773d001063
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a0773d001063'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDICE = 'uq_lancamentos_notas_chave_ativa'
CONDICAO = "status <> 'cancelada' AND chave_acesso IS NOT NULL"


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 1) Pre-checagem: existem chaves duplicadas entre as notas ativas?
    duplicadas = bind.execute(sa.text(f"""
        SELECT chave_acesso, COUNT(*) AS qtd
        FROM lancamentos_notas
        WHERE {CONDICAO}
        GROUP BY chave_acesso
        HAVING COUNT(*) > 1
        ORDER BY qtd DESC
    """)).fetchall()

    if duplicadas:
        linhas = "\n".join(f"  - chave {c} aparece {q}x" for c, q in duplicadas)
        raise RuntimeError(
            "Nao foi possivel aplicar a trava de unicidade: ja existem notas "
            "ativas com a mesma chave de acesso no banco.\n"
            f"{linhas}\n"
            "Decida (cancelando os lancamentos duplicados pela tela do Hub, ou "
            "ajustando os dados) quais devem permanecer ativos e rode a migration "
            "novamente. Nenhum dado foi alterado."
        )

    # 2) Sem duplicatas: cria o indice unico parcial.
    op.create_index(
        INDICE,
        'lancamentos_notas',
        ['chave_acesso'],
        unique=True,
        postgresql_where=sa.text(CONDICAO),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(INDICE, table_name='lancamentos_notas')
