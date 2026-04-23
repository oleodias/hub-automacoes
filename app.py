# ══════════════════════════════════════════════════════════════
# app.py — Hub de Automações Ciamed (Ponto de Entrada)
# ══════════════════════════════════════════════════════════════
# Este arquivo faz 5 coisas:
#   1. Cria o Flask e configura o banco
#   2. Registra todos os blueprints
#   3. Exige login em TODAS as rotas (exceto as públicas)
#   4. Define o porteiro digital (controle de horário)
#   5. Inicia o servidor
# ══════════════════════════════════════════════════════════════

import os
from datetime import datetime, time, timedelta
from flask import Flask, request, session, redirect, url_for
import urllib3

from dotenv import load_dotenv
load_dotenv()

from extensions import db
import banco_cadastros
from utils.logging_config import configurar_logging


# ══════════════════════════════════════════════════════════════
# CRIAR E CONFIGURAR O FLASK
# ══════════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'chave_reserva_caso_falhe')

# Sessão expira após 8 horas de inatividade
app.permanent_session_lifetime = timedelta(hours=1)

# Banco de Dados (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Desliga avisos de SSL do Selenium
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configura o sistema de logging (terminal + arquivo)
configurar_logging()


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

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(itens_bp)
app.register_blueprint(mdf_bp)
app.register_blueprint(fornecedor_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(cnpj_bp)
app.register_blueprint(admin_bp)


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
# PORTEIRO DIGITAL (CONTROLE DE HORÁRIO)
# ══════════════════════════════════════════════════════════════

HORA_INICIO = time(00, 00)
HORA_FIM    = time(23, 59)
DIAS_UTEIS  = [0, 1, 2, 3, 4, 5, 6]

@app.before_request
def verificar_horario():
    # Não aplica para rotas públicas ou login
    if request.endpoint in ROTAS_PUBLICAS:
        return None
    if request.endpoint and 'static' in request.endpoint:
        return None

    if request.args.get('bypass') == 'leo_admin':
        session['acesso_noturno'] = True
        return redirect(url_for('main.home'))

    if session.get('acesso_noturno'):
        return None

    agora = datetime.now()
    if agora.weekday() not in DIAS_UTEIS or not (HORA_INICIO <= agora.time() < HORA_FIM):
        return """
        <body style="background-color: #263238; color: white; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <img src="/static/img/ciamedia.png" style="height: 60px; margin-bottom: 20px;">
            <h1 style="color: #05776c; margin-bottom: 10px;">🌙 Sistema em Repouso</h1>
            <p style="font-size: 1.2rem; color: #b0bec5; margin-bottom: 30px; text-align: center; max-width: 500px;">
                A Central de Automação Fiscal da Ciamed opera exclusivamente em horário comercial.
            </p>
            <div style="padding: 20px 40px; border: 1px solid #05776c; border-radius: 8px; background-color: rgba(5, 119, 108, 0.1); text-align: center;">
                <strong style="color: white;">Horário de Funcionamento:</strong><br>
                <span style="color: #b0bec5;">Segunda a Sexta: 08:00 às 18:00</span>
            </div>
        </body>
        """, 403


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
# INICIALIZAR BANCO E SUBIR SERVIDOR
# ══════════════════════════════════════════════════════════════

with app.app_context():
    banco_cadastros.init_db()

if __name__ == '__main__':
    print("🚀 SERVIDOR ONLINE! Acesse pelo IP da sua máquina.")
    app.run(host='0.0.0.0', port=5000, debug=True)
