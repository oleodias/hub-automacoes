# ══════════════════════════════════════════════════════════════
# migrations/env.py — Configuração do Alembic para o Hub
# ══════════════════════════════════════════════════════════════
# Este arquivo diz ao Alembic:
#   1. Onde está o banco de dados (DATABASE_URL do .env)
#   2. Quais modelos existem (importa o models.py)
#   3. Como rodar as migrations
#
# Você NÃO precisa editar este arquivo no dia a dia.
# Ele só é usado internamente pelo comando 'alembic'.
# ══════════════════════════════════════════════════════════════

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Adiciona a raiz do projeto ao path do Python ──────────────
# Sem isso, o Alembic não consegue importar extensions.py e models.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Carrega as variáveis do .env ──────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Importa nossos modelos ────────────────────────────────────
# O Alembic precisa conhecer TODOS os modelos para poder comparar
# o que está no código com o que está no banco e gerar as migrations.
from extensions import db
from models import Submissao, Usuario, Execucao  # noqa: F401 — importa para o Alembic enxergar

# ── Configuração do Alembic ───────────────────────────────────
config = context.config

# Lê o arquivo alembic.ini para configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Diz ao Alembic qual é o "metadata" dos nossos modelos
# (metadata = a descrição de todas as tabelas e colunas)
target_metadata = db.metadata

# ── Pega a URL do banco do .env ───────────────────────────────
# Em vez de deixar a URL fixa no alembic.ini (que vai pro Git),
# pegamos do .env (que NÃO vai pro Git). Mais seguro.
database_url = os.getenv('DATABASE_URL')


def run_migrations_offline():
    """
    Modo offline: gera o SQL sem conectar ao banco.
    Útil para revisar o que vai mudar antes de aplicar.
    Você provavelmente não vai usar isso no dia a dia.
    """
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Modo online: conecta ao banco e aplica as migrations.
    Este é o modo que usamos normalmente.
    """
    # Monta a configuração de conexão usando a URL do .env
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Executa ───────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
