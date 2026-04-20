# ══════════════════════════════════════════════════════════════
# app.py — Hub de Automações Ciamed (Ponto de Entrada)
# ══════════════════════════════════════════════════════════════
# Este arquivo agora é ENXUTO. Ele só faz 4 coisas:
#   1. Cria o Flask e configura o banco
#   2. Registra todos os blueprints (rotas organizadas por módulo)
#   3. Define o porteiro digital (controle de horário)
#   4. Inicia o servidor
#
# As rotas estão em:
#   routes/main.py       → home, upload, fila genérica
#   routes/itens.py      → cadastro de itens, fase1, fase2
#   routes/mdf.py        → relatório MDF-e
#   routes/fornecedor.py → cadastro de fornecedor
#   routes/clientes.py   → clientes, ficha, monitor, N8N
#   routes/cnpj.py       → consultas CNPJ
#   routes/admin.py      → painel admin, chamados, suporte
# ══════════════════════════════════════════════════════════════

import os
from datetime import datetime, time
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

app = Flask(__name__, template_folder='templates_reestilizados')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'chave_reserva_caso_falhe')

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

from routes.main import main_bp
from routes.itens import itens_bp
from routes.mdf import mdf_bp
from routes.fornecedor import fornecedor_bp
from routes.clientes import clientes_bp
from routes.cnpj import cnpj_bp
from routes.admin import admin_bp

app.register_blueprint(main_bp)
app.register_blueprint(itens_bp)
app.register_blueprint(mdf_bp)
app.register_blueprint(fornecedor_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(cnpj_bp)
app.register_blueprint(admin_bp)


# ══════════════════════════════════════════════════════════════
# PORTEIRO DIGITAL (CONTROLE DE HORÁRIO)
# ══════════════════════════════════════════════════════════════

HORA_INICIO = time(00, 00)
HORA_FIM    = time(23, 59)
DIAS_UTEIS  = [0, 1, 2, 3, 4, 5, 6]

@app.before_request
def verificar_horario():
    if request.endpoint and 'static' in request.endpoint:
        return None

    if request.endpoint in [
        'clientes.ficha_cliente', 'cnpj.api_cnpj_completo', 'cnpj.consulta_cnpj',
        'clientes.confirmar_acao', 'clientes.motivo_reprovacao',
        'clientes.receber_ficha', 'clientes.api_ficha'
    ]:
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
            <p style="margin-top: 40px; font-size: 0.85rem; color: #6c757d;">
                Controladoria • Acesso Restrito
            </p>
        </body>
        """, 403


# ══════════════════════════════════════════════════════════════
# INICIALIZAR BANCO E SUBIR SERVIDOR
# ══════════════════════════════════════════════════════════════

with app.app_context():
    banco_cadastros.init_db()

if __name__ == '__main__':
    print("🚀 SERVIDOR ONLINE! Acesse pelo IP da sua máquina.")
    app.run(host='0.0.0.0', port=5000, debug=True)
