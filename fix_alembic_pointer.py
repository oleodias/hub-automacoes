# ══════════════════════════════════════════════════════════════
# fix_alembic_pointer.py — correção pontual do ponteiro Alembic
# ══════════════════════════════════════════════════════════════
# Atualiza a tabela alembic_version diretamente, pulando a leitura
# da versão atual (que aponta para um arquivo deletado).
# Pode deletar este arquivo depois que rodar com sucesso.
# ══════════════════════════════════════════════════════════════

from app import app
from extensions import db
from sqlalchemy import text

# Head atual conforme `alembic history`
NOVA_VERSAO = '068e3f9e1759'

with app.app_context():
    # ── 1. Mostra o que está hoje ───────────────────────────
    atual = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print(f"Versão atual (quebrada): {atual}")

    # ── 2. Atualiza para a head válida ──────────────────────
    db.session.execute(
        text("UPDATE alembic_version SET version_num = :v"),
        {'v': NOVA_VERSAO}
    )
    db.session.commit()

    # ── 3. Confirma ─────────────────────────────────────────
    nova = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print(f"Versão atualizada para: {nova}")
    print("\nPronto! Agora você pode rodar os comandos do Alembic normalmente.")