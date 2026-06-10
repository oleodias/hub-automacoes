# ══════════════════════════════════════════════════════════════
# app.py — Hub de Automações Ciamed (Ponto de Entrada)
# ══════════════════════════════════════════════════════════════
# Este arquivo faz 4 coisas:
#   1. Cria o Flask e configura o banco
#   2. Registra todos os blueprints
#   3. Exige login em TODAS as rotas (exceto as públicas)
#   4. Inicia o servidor
# ══════════════════════════════════════════════════════════════

import os
from datetime import timedelta
from flask import Flask, request, session, redirect, url_for

from dotenv import load_dotenv
load_dotenv()

from extensions import db, limiter
from utils.logging_config import configurar_logging



# ══════════════════════════════════════════════════════════════
# CRIAR E CONFIGURAR O FLASK
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)

# Ambiente: "dev" (seu PC) ou "prod" (servidor). Controla o modo debug.
AMBIENTE = os.getenv('AMBIENTE', 'prod').strip().lower()

# Chave secreta: assina os cookies de login. É OBRIGATÓRIA e NÃO tem
# valor de reserva no código (uma reserva pública deixaria forjar logins).
# Se faltar no .env, o app não sobe — é melhor falhar agora do que rodar inseguro.
app.secret_key = os.getenv('FLASK_SECRET_KEY')
if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY não definida. Crie a variável no arquivo .env "
        "(ex.: gere uma com `python -c \"import secrets; print(secrets.token_hex(32))\"`). "
        "O app não sobe sem ela por segurança."
    )

# Sessão expira após 1 hora de inatividade
app.permanent_session_lifetime = timedelta(hours=1)

# ── Segurança dos cookies de sessão ───────────────────────────
# HttpOnly: o cookie não fica acessível via JavaScript (mitiga roubo por XSS).
# SameSite=Lax: o navegador não envia o cookie em requisições cross-site
#   (mitiga a maior parte dos ataques CSRF).
# Secure: o cookie só trafega por HTTPS. Ligado apenas em produção, pois o
#   ambiente local roda em HTTP — em dev, Secure quebraria o login.
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = (AMBIENTE == 'prod')

# Em produção o app roda atrás do Nginx. Sem isso, o Flask enxerga o IP do
# proxy (sempre o mesmo) em vez do IP real do cliente — o que faria o
# limite de tentativas valer para TODO mundo junto. ProxyFix lê o
# X-Forwarded-For que o Nginx envia. Em dev não há proxy, então não aplica.
if AMBIENTE == 'prod':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Banco de Dados (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Controle de taxa (anti-força-bruta no login)
limiter.init_app(app)

# Configura o sistema de logging (terminal + arquivo)
configurar_logging()


# ══════════════════════════════════════════════════════════════
# CABEÇALHOS DE SEGURANÇA (aplicados a TODA resposta)
# ══════════════════════════════════════════════════════════════

@app.after_request
def aplicar_cabecalhos_seguranca(resposta):
    # Impede o navegador de "adivinhar" o tipo do arquivo (anti-MIME-sniffing).
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    # Impede que o Hub seja embutido em <iframe> de outro site (anti-clickjacking).
    resposta.headers['X-Frame-Options'] = 'DENY'
    # Não vaza a URL interna ao navegar para fora do site.
    resposta.headers['Referrer-Policy'] = 'same-origin'
    # HSTS: força HTTPS. Só em produção, onde de fato há HTTPS.
    if AMBIENTE == 'prod':
        resposta.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return resposta


# ══════════════════════════════════════════════════════════════
# REGISTRAR BLUEPRINTS
# ══════════════════════════════════════════════════════════════

from routes.auth import auth_bp
from routes.main import main_bp
from routes.itens import itens_bp
from routes.mdf import mdf_bp
from routes.fornecedor import fornecedor_bp
from routes.clientes import clientes_bp
from routes.cnpj import cnpj_bp
from routes.admin import admin_bp
from routes.notas import notas_bp
from routes.lancamento_notas import lancamento_notas_bp
from routes.suporte import suporte_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(itens_bp)
app.register_blueprint(mdf_bp)
app.register_blueprint(fornecedor_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(cnpj_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(notas_bp)
app.register_blueprint(lancamento_notas_bp)
app.register_blueprint(suporte_bp)


# ══════════════════════════════════════════════════════════════
# PROTEÇÃO GLOBAL: LOGIN OBRIGATÓRIO
# ══════════════════════════════════════════════════════════════
# Em vez de colocar @login_required em cada rota individualmente,
# usamos um before_request GLOBAL que intercepta TUDO.
# Rotas públicas ficam numa lista de exceções.
# ══════════════════════════════════════════════════════════════

# Rotas que NÃO precisam de login (públicas)
ROTAS_PUBLICAS = {
    'auth.login',                    # tela de login (óbvio)
    'static',                        # arquivos CSS, JS, imagens
    'clientes.ficha_cliente',        # vendedores externos preenchem a ficha
    'clientes.receber_ficha',        # endpoint que recebe a ficha
    'clientes.api_ficha',            # pré-preenchimento na correção
    'clientes.confirmar_acao',       # farmacêutica aprova/reprova via email
    'clientes.motivo_reprovacao',    # farmacêutica preenche motivo
    'clientes.decidir_bloqueio',
    'cnpj.consulta_cnpj',           # usado pela ficha do cliente
    'cnpj.api_cnpj_completo',       # usado pela ficha do cliente
    'clientes.fila_cadastro_entrar',     # N8N chama direto
    'clientes.fila_cadastro_liberar',    # N8N chama direto
    'clientes.n8n_iniciar_cadastro',     # N8N chama direto
    'clientes.n8n_iniciar_reativacao',     # N8N chama direto
}

@app.before_request
def exigir_login():
    """
    Intercepta TODAS as requisições. Se o usuário não está logado
    e a rota não é pública, redireciona para o login.
    """
    # Ignora rotas públicas
    if request.endpoint in ROTAS_PUBLICAS:
        return None

    # Ignora arquivos estáticos
    if request.endpoint and 'static' in request.endpoint:
        return None

    # Se não está logado, redireciona para login
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login', next=request.path))

    return None


# ══════════════════════════════════════════════════════════════
# CONTEXT PROCESSOR: dados do usuário disponíveis em TODOS os templates
# ══════════════════════════════════════════════════════════════

@app.context_processor
def injetar_usuario():
    from utils.auth import get_usuario_logado
    usuario = get_usuario_logado()
    if usuario:
        return {
            'usuario_nome':  usuario.nome,
            'usuario_cargo': usuario.cargo,
            'is_admin':      usuario.is_admin(),
            'tem_permissao': usuario.tem_permissao,
        }
    return {
        'usuario_nome':  '',
        'usuario_cargo': '',
        'is_admin':      False,
        'tem_permissao': lambda m: False,
    }


# ══════════════════════════════════════════════════════════════
# SUBIR SERVIDOR
# ══════════════════════════════════════════════════════════════
# O schema do banco é criado/atualizado pelas migrations do Alembic
# (`alembic upgrade head`), NÃO mais por db.create_all() na subida.
# Assim o Alembic passa a ser a única fonte de verdade da estrutura
# do banco — sem corrida de criação de schema entre múltiplos workers.

if __name__ == '__main__':
    # ATENÇÃO (deploy): este servidor embutido do Flask é só para
    # desenvolvimento. Em produção, NÃO use `python app.py` — sirva o app
    # com Waitress (Windows) ou Gunicorn (Linux) atrás do Nginx com HTTPS.
    # Ex.: waitress-serve --listen=127.0.0.1:5000 app:app
    #
    # O modo debug SÓ liga em desenvolvimento (AMBIENTE=dev no .env).
    # Com debug ligado e exposto, um erro vira um console remoto no servidor.
    debug = (AMBIENTE == 'dev')
    if debug:
        print("🚀 SERVIDOR ONLINE (modo DEV/debug). Acesse pelo IP da sua máquina.")
    else:
        print("🚀 SERVIDOR ONLINE (modo PROD, debug desligado).")
    app.run(host='0.0.0.0', port=5000, debug=debug)
