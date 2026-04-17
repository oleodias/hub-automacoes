# ══════════════════════════════════════════════════════════════
# extensions.py — Instâncias centrais do Hub de Automações
# ══════════════════════════════════════════════════════════════
# Por que este arquivo existe?
#
# O SQLAlchemy precisa de um objeto "db" que é usado em TODO o projeto:
# nos modelos (models.py), nas rotas (app.py), nos blueprints futuros.
#
# Se criarmos o "db" dentro do app.py, qualquer arquivo que precisar
# dele teria que importar do app.py — e isso causa importação circular
# (app importa models, models importa app → erro).
#
# Solução: criamos o "db" aqui, num arquivo neutro que não importa
# ninguém. Todo mundo importa daqui sem conflito.
# ══════════════════════════════════════════════════════════════

from flask_sqlalchemy import SQLAlchemy

# Esta é a instância principal do banco de dados.
# Ela será inicializada com o Flask no app.py usando db.init_app(app)
db = SQLAlchemy()
