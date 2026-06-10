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
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Esta é a instância principal do banco de dados.
# Ela será inicializada com o Flask no app.py usando db.init_app(app)
db = SQLAlchemy()

# Controle de taxa (anti-força-bruta). Sem limites globais: só as rotas
# decoradas com @limiter.limit(...) são limitadas — assim o resto do Hub
# não é afetado. A contagem fica em memória (suficiente para 1 servidor).
# A chave é o IP de origem (get_remote_address).
# storage_uri='memory://' é explícito de propósito: deixa claro que a
# contagem é em memória (escolha consciente para 1 servidor) e silencia
# o aviso do flask-limiter sobre storage não configurado.
limiter = Limiter(key_func=get_remote_address, storage_uri='memory://')
