from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
import os
import sys
import json
from datetime import datetime, time
import subprocess
import requests
import threading
import time as time_module
from werkzeug.utils import secure_filename
from automacoes.clientes.leitor_ficha import processar_ficha_cliente
from automacoes.clientes import cadastro_novo
import re
import requests
from bs4 import BeautifulSoup
from flask import jsonify, render_template
import urllib3
import requests as req_ext
import uuid as uuid_lib          # ← NOVO: para gerar o UUID de cada submissão
import banco_cadastros           # ← NOVO: módulo SQLite de cadastros

# Desliga os avisos chatos de segurança quando usamos verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── SISTEMA DE FILA ──────────────────────
_lock_execucao = threading.Lock()
_fila = []
_em_execucao = None

def _gerar_id():
    return f"{int(time_module.time() * 1000)}"

def entrar_na_fila():
    global _fila
    with _lock_execucao:
        meu_id = _gerar_id()
        _fila.append(meu_id)
        return meu_id

def minha_vez(meu_id):
    global _em_execucao, _fila
    with _lock_execucao:
        if _em_execucao is not None:
            return False
        return bool(_fila and _fila[0] == meu_id)

def iniciar_execucao(meu_id):
    global _em_execucao, _fila
    with _lock_execucao:
        _em_execucao = meu_id
        if meu_id in _fila:
            _fila.remove(meu_id)

def finalizar_execucao():
    global _em_execucao
    with _lock_execucao:
        _em_execucao = None

def sair_da_fila(meu_id):
    global _fila
    with _lock_execucao:
        if meu_id in _fila:
            _fila.remove(meu_id)

def posicao_na_fila(meu_id):
    global _fila, _em_execucao
    with _lock_execucao:
        if _em_execucao == meu_id:
            return 0
        if meu_id in _fila:
            return _fila.index(meu_id) + 1
        return -1
# ─────────────────────────────────────────

app = Flask(__name__, template_folder='templates_reestilizados')
app.secret_key = 'ciamed_super_secreta_2026'

# ← NOVO: Inicializa o banco de cadastros ao subir o servidor
banco_cadastros.init_db()

# Configura pasta de Upload
UPLOAD_FOLDER = 'XML_Entrada'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# PORTEIRO DIGITAL (CONTROLE DE HORÁRIO)
# ==========================================
HORA_INICIO = time(00, 00)
HORA_FIM    = time(23, 59)
DIAS_UTEIS  = [0, 1, 2, 3, 4, 5, 6]

@app.before_request
def verificar_horario():
    if request.endpoint and 'static' in request.endpoint:
        return None

    # ← MODIFICADO: adicionadas as novas rotas liberadas do porteiro
    if request.endpoint in [
        'ficha_cliente', 'api_cnpj_completo', 'consulta_cnpj',
        'confirmar_acao', 'motivo_reprovacao',
        'receber_ficha', 'api_ficha'          # ← NOVAS
    ]:
        return None

    if request.args.get('bypass') == 'leo_admin':
        session['acesso_noturno'] = True
        return redirect(url_for('home'))

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

# ==========================================
# ROTAS PRINCIPAIS (FRONTEND & UPLOAD)
# ==========================================

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'erro', 'msg': 'Nenhum arquivo enviado'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'erro', 'msg': 'Nome vazio'})
    
    if file:
        pasta_upload = app.config['UPLOAD_FOLDER']
        try:
            for arquivo_velho in os.listdir(pasta_upload):
                caminho_velho = os.path.join(pasta_upload, arquivo_velho)
                if os.path.isfile(caminho_velho):
                    os.remove(caminho_velho)
        except Exception as e:
            print(f"⚠️ Erro ao limpar a pasta: {e}")
        
        filepath = os.path.join(pasta_upload, file.filename)
        file.save(filepath)
        return jsonify({'status': 'ok', 'msg': f'Arquivo salvo e fila limpa: {file.filename}'})

# ==========================================
# ROTAS DOS ROBÔS (FASES)
# ==========================================

@app.route('/run_fase1', methods=['GET'])
def rota_fase1():
    meu_id = request.args.get('fila_id', '')
    def gerar_logs():
        tentativas = 0
        while not minha_vez(meu_id):
            tentativas += 1
            if tentativas > 120:
                yield "data: ❌ Timeout na fila. Tente novamente.\n\n"
                sair_da_fila(meu_id)
                return
            yield f"data: [FILA] posição {posicao_na_fila(meu_id)}\n\n"
            time_module.sleep(1)
        iniciar_execucao(meu_id)
        yield "data: [FILA_LIBERADA]\n\n"
        try:
            comando = [sys.executable, "-X", "utf8", "-u", "automacoes/fase1_ncm.py"]
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
            for linha in iter(processo.stdout.readline, ''):
                linha_limpa = linha.strip()
                if not linha_limpa: linha_limpa = " "
                yield f"data: {linha_limpa}\n\n"
            processo.stdout.close()
            processo.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()
    return Response(gerar_logs(), mimetype='text/event-stream')

@app.route('/run_fase2', methods=['GET'])
def run_fase2():
    meu_id = request.args.get('fila_id', '')
    def gerar_logs():
        tentativas = 0
        while not minha_vez(meu_id):
            tentativas += 1
            if tentativas > 120:
                yield "data: ❌ Timeout na fila. Tente novamente.\n\n"
                sair_da_fila(meu_id)
                return
            yield f"data: [FILA] posição {posicao_na_fila(meu_id)}\n\n"
            time_module.sleep(1)
        iniciar_execucao(meu_id)
        yield "data: [FILA_LIBERADA]\n\n"
        try:
            comando = [sys.executable, "-X", "utf8", "-u", "automacoes/fase2_item.py"]
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
            for linha in iter(processo.stdout.readline, ''):
                linha_limpa = linha.strip()
                if not linha_limpa: linha_limpa = " "
                yield f"data: {linha_limpa}\n\n"
            processo.stdout.close()
            processo.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()
    return Response(gerar_logs(), mimetype='text/event-stream')

@app.route('/run_mdf', methods=['GET'])
def rota_mdf():
    meu_id     = request.args.get('fila_id', '')
    data_inicio = request.args.get('inicio', '01/01/2026')
    data_fim    = request.args.get('fim', '31/01/2026')
    def gerar_logs():
        tentativas = 0
        while not minha_vez(meu_id):
            tentativas += 1
            if tentativas > 120:
                yield "data: ❌ Timeout na fila. Tente novamente.\n\n"
                sair_da_fila(meu_id)
                return
            yield f"data: [FILA] posição {posicao_na_fila(meu_id)}\n\n"
            time_module.sleep(1)
        iniciar_execucao(meu_id)
        yield "data: [FILA_LIBERADA]\n\n"
        try:
            processo = subprocess.Popen(['python', '-u', 'automacoes/robo_mdf.py', data_inicio, data_fim], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
            for linha in iter(processo.stdout.readline, ''):
                if linha: yield f"data: {linha.strip()}\n\n"
            processo.stdout.close()
            processo.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()
    return Response(gerar_logs(), mimetype='text/event-stream')

@app.route('/download_mdf')
def download_mdf():
    caminho_arquivo = os.path.join(os.getcwd(), "Relatorio_MDFs_Gerado.xlsx")
    if not os.path.exists(caminho_arquivo):
        return "❌ O arquivo não foi encontrado. O robô pode não ter encontrado dados neste período ou ocorreu um erro na geração.", 404
    try:
        return send_file(caminho_arquivo, as_attachment=True, download_name="Relatorio_MDF_Ciamed.xlsx")
    except Exception as e:
        return f"Erro interno ao tentar baixar o arquivo: {e}", 500

@app.route('/cadastro_fornecedor')
def cadastro_fornecedor():
    return render_template('cadastro_fornecedor.html')

@app.route('/cadastro_itens')
def cadastro_itens():
    return render_template('cadastro_itens.html')

@app.route('/relatorio_mdf')
def relatorio_mdf():
    return render_template('relatorio_mdf.html')

@app.route('/run_fornecedor')
def run_fornecedor():
    meu_id    = request.args.get('fila_id', '')
    dados_json = request.args.get('dados', '{}')
    def generate():
        tentativas = 0
        while not minha_vez(meu_id):
            tentativas += 1
            if tentativas > 120:
                yield "data: ❌ Timeout na fila. Tente novamente.\n\n"
                sair_da_fila(meu_id)
                return
            yield f"data: [FILA] posição {posicao_na_fila(meu_id)}\n\n"
            time_module.sleep(1)
        iniciar_execucao(meu_id)
        yield "data: [FILA_LIBERADA]\n\n"
        try:
            process = subprocess.Popen([sys.executable, 'automacoes/robo_fornecedor.py', dados_json], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8')
            for line in process.stdout:
                linha = line.strip()
                if linha: yield f"data: {linha}\n\n"
            process.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        except Exception as e:
            yield f"data: ❌ Erro interno: {str(e)}\n\n"
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()
    return Response(generate(), mimetype='text/event-stream')

@app.route('/cadastro_clientes')
def cadastro_clientes():
    return render_template('cadastro_clientes.html')

@app.route('/api/upload_ficha_cliente', methods=['POST'])
def upload_ficha_cliente():
    if 'file' not in request.files:
        return jsonify({"erro": True, "mensagem": "Nenhum arquivo enviado."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"erro": True, "mensagem": "Arquivo vazio."}), 400
    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        pasta_uploads = os.path.join(app.root_path, 'uploads')
        os.makedirs(pasta_uploads, exist_ok=True)
        filename     = secure_filename(file.filename)
        caminho_salvo = os.path.join(pasta_uploads, filename)
        file.save(caminho_salvo)
        resultado = processar_ficha_cliente(caminho_salvo)
        if os.path.exists(caminho_salvo):
            os.remove(caminho_salvo)
        return jsonify(resultado)
    else:
        return jsonify({"erro": True, "mensagem": "Formato inválido. Envie um arquivo Excel (.xlsx ou .xls)"}), 400

@app.route('/iniciar_cadastro_novo', methods=['POST'])
def iniciar_cadastro_novo():
    dados_do_cliente = request.json
    resultado = cadastro_novo.executar(dados_do_cliente)
    return jsonify(resultado)

@app.route('/consulta_cte')
def consulta_cte():
    return render_template('consulta_cte.html')

@app.route('/ficha_cliente')
def ficha_cliente():
    return render_template('ficha_cliente.html')


# ══════════════════════════════════════════════════════════════════════════════
# ROTA NOVA: Receber ficha do cliente
# ──────────────────────────────────────────────────────────────────────────────
# O JS agora envia para cá em vez de direto pro N8N.
# O Flask:
#   1. Salva os arquivos em uploads_fichas/{uuid}/
#   2. Salva os dados no SQLite
#   3. Compara documentos (quando for correção)
#   4. Repassa para o N8N via JSON com todos os metadados
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/receber_ficha', methods=['POST'])
def receber_ficha():

    # ── 1. Verificar se é correção (tem uuid no form) ──────────────────────
    uuid_existente = request.form.get('uuid', '').strip()
    is_correcao    = bool(uuid_existente)

    if is_correcao:
        sub_original = banco_cadastros.buscar_submissao(uuid_existente)
        if not sub_original:
            return jsonify({'status': 'erro', 'mensagem': 'UUID inválido ou expirado.'}), 400
        submission_uuid = uuid_existente
        docs_originais  = sub_original['docs_enviados']
    else:
        submission_uuid = str(uuid_lib.uuid4())
        docs_originais  = []

    # ── 2. Extrair campos de texto ─────────────────────────────────────────
    campos = {
        'vendedor':               request.form.get('vendedor',               ''),
        'representante':          request.form.get('representante',           ''),
        'captacao':               request.form.get('captacao',                ''),
        'tipo_cadastro':          request.form.get('tipo_cadastro',           ''),
        'contribuinte_icms':      request.form.get('contribuinte_icms',       ''),
        'possui_regime_especial': request.form.get('possui_regime_especial',  ''),
        'regra_faturamento':      request.form.get('regra_faturamento',       ''),
        'cnpj':                   request.form.get('cnpj',                    ''),
        'razao_social':           request.form.get('razao_social',            ''),
        'endereco':               request.form.get('endereco',                ''),
        'telefone_empresa':       request.form.get('telefone_empresa',        ''),
        'whatsapp':               request.form.get('whatsapp',                ''),
        'email_xml_1':            request.form.get('email_xml_1',             ''),
        'email_xml_2':            request.form.get('email_xml_2',             ''),
        'email_xml_3':            request.form.get('email_xml_3',             ''),
        'compras_nome':           request.form.get('compras_nome',            ''),
        'compras_tel':            request.form.get('compras_tel',             ''),
        'compras_email':          request.form.get('compras_email',           ''),
        'rec_nome':               request.form.get('rec_nome',                ''),
        'rec_tel':                request.form.get('rec_tel',                 ''),
        'rec_email':              request.form.get('rec_email',               ''),
        'fin_nome':               request.form.get('fin_nome',                ''),
        'fin_tel':                request.form.get('fin_tel',                 ''),
        'fin_email':              request.form.get('fin_email',               ''),
        'farma_nome':             request.form.get('farma_nome',              ''),
        'farma_tel':              request.form.get('farma_tel',               ''),
        'farma_email':            request.form.get('farma_email',             ''),
    }

    # ── 3. Salvar arquivos em uploads_fichas/{uuid}/ ───────────────────────
    lista_docs  = [
        'doc_regime_especial', 'doc_alvara', 'doc_crt', 'doc_afe',
        'doc_balanco', 'doc_balancete', 'doc_contrato'
    ]
    pasta_uuid  = os.path.join('uploads_fichas', submission_uuid)
    os.makedirs(pasta_uuid, exist_ok=True)

    docs_novos   = []  # docs com NOVO arquivo nesta submissão
    docs_manter  = json.loads(request.form.get('docs_manter', '[]'))

    for doc_nome in lista_docs:
        arquivo = request.files.get(doc_nome)
        if arquivo and arquivo.filename:
            nome_seguro = secure_filename(arquivo.filename)
            ext         = os.path.splitext(nome_seguro)[1].lower() or '.pdf'
            caminho     = os.path.join(pasta_uuid, f"{doc_nome}{ext}")
            arquivo.save(caminho)
            docs_novos.append(doc_nome)

    # ── 4. Calcular docs finais disponíveis ───────────────────────────────
    # docs_manter são os que o vendedor NÃO resubmetiu mas existiam antes
    docs_mantidos_validos = [d for d in docs_manter if d in docs_originais]
    docs_finais           = list(set(docs_novos + docs_mantidos_validos))

    # ── 5. Categorizar documentos (só relevante na correção) ───────────────
    if is_correcao:
        # 📎 Já existentes: estavam no original E não foram resubmetidos
        docs_ja_existentes = [d for d in docs_mantidos_validos]
        # 🔄 Substituídos: estavam no original E foram resubmetidos com arquivo novo
        docs_substituidos  = [d for d in docs_novos if d in docs_originais]
        # 🆕 Adicionados: NÃO estavam no original E foram enviados agora
        docs_adicionados   = [d for d in docs_novos if d not in docs_originais]

        nova_tentativa = banco_cadastros.incrementar_tentativa(
            submission_uuid, campos, docs_finais
        )
    else:
        docs_ja_existentes = []
        docs_substituidos  = []
        docs_adicionados   = []
        nova_tentativa     = 1

        banco_cadastros.salvar_submissao(
            submission_uuid,
            campos['cnpj'],
            campos['razao_social'],
            campos,
            docs_finais
        )

    # ── 6. Montar nomes legíveis dos docs para exibir nos emails ──────────
    # O N8N vai usar estas strings diretamente nos emails da farmacêutica
    nomes_legíveis = {
        'doc_regime_especial': 'Regime Especial de ICMS',
        'doc_alvara':          'Alvará Sanitário',
        'doc_crt':             'Certidão de Regularidade',
        'doc_afe':             'Publicação AFE / AE',
        'doc_balanco':         'Último Balanço e DRE',
        'doc_balancete':       'Balancete (< 90 dias)',
        'doc_contrato':        'Contrato Social',
    }

    def nomes(lista):
        return ', '.join(nomes_legíveis.get(d, d) for d in lista) if lista else '—'

    # ── 7. Montar payload para o N8N ──────────────────────────────────────
    payload_n8n = {
        **campos,
        'uuid':               submission_uuid,
        'tentativa':          nova_tentativa,
        'is_correcao':        str(is_correcao).lower(),
        'docs_ja_existentes': nomes(docs_ja_existentes),
        'docs_substituidos':  nomes(docs_substituidos),
        'docs_adicionados':   nomes(docs_adicionados),
    }

    # ── 8. Disparar para o Webhook do N8N (multipart com arquivos) ────────
    N8N_WEBHOOK_URL = "https://ciamedrs.app.n8n.cloud/webhook-test/receber-cadastro-teste-em-casa"

    payload_str = {k: str(v) for k, v in payload_n8n.items()}

    arquivos_abertos = {}
    pasta = os.path.join('uploads_fichas', submission_uuid)

    if os.path.exists(pasta):
        for arquivo in os.listdir(pasta):
            nome_sem_ext = os.path.splitext(arquivo)[0]
            extensao     = os.path.splitext(arquivo)[1]
            caminho      = os.path.join(pasta, arquivo)
            if nome_sem_ext in docs_finais:
                arquivos_abertos[nome_sem_ext] = (
                    arquivo,
                    open(caminho, 'rb'),
                    'application/octet-stream'
                )

    try:
        resposta_n8n = requests.post(
            N8N_WEBHOOK_URL,
            data=payload_str,
            files=arquivos_abertos if arquivos_abertos else None,
            timeout=60
        )
        print(f"✅ [N8N] Status: {resposta_n8n.status_code} | UUID: {submission_uuid} | Tentativa: {nova_tentativa} | Docs: {list(arquivos_abertos.keys())}")
        return jsonify({'status': 'ok', 'uuid': submission_uuid})

    except Exception as e:
        print(f"❌ [N8N] Erro ao disparar webhook: {e}")
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

    finally:
        for nome, (_, fp, _) in arquivos_abertos.items():
            try:
                fp.close()
            except Exception:
                pass

# ══════════════════════════════════════════════════════════════════════════════
# ROTA NOVA: Retornar dados de uma submissão para pré-preenchimento
# ──────────────────────────────────────────────────────────────────────────────
# O JS chama esta rota quando detecta ?correcao=UUID na URL da ficha
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/ficha/<submission_uuid>')
def api_ficha(submission_uuid):
    sub = banco_cadastros.buscar_submissao(submission_uuid)
    if not sub:
        return jsonify({'erro': 'Submissão não encontrada'}), 404

    return jsonify({
        'dados':              sub['dados_json'],
        'docs_enviados':      sub['docs_enviados'],
        'motivos_reprovacao': sub['motivos_reprovacao'],
        'tentativa':          sub['tentativa'],
        'razao_social':       sub['razao_social'],
        'cnpj':               sub['cnpj'],
    })


# ──────────────────────────────────────────────────────────────────────────────
# ROTA: Farmacêutica clica no botão do email → Flask chama N8N e mostra tela bonita
#
# Uso nos emails do N8N:
#   APROVAR:  /confirmar?acao=aprovar&empresa=NOME&resumeUrl=URL_N8N
#   MÁSCARAS: /confirmar?acao=mascaras&empresa=NOME&resumeUrl=URL_N8N
#   REPROVAR: → vai para /motivo_reprovacao (não passa por aqui diretamente)
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/confirmar')
def confirmar_acao():
    acao       = request.args.get('acao',      '')
    empresa    = request.args.get('empresa',   '')
    resume_url = request.args.get('resumeUrl', '')
    motivo     = request.args.get('motivo',    '')
    uuid_ficha = request.args.get('uuid',      '')

    if not resume_url:
        return "Parâmetro resumeUrl ausente.", 400

    try:
        if acao == 'aprovar':
            req_ext.get(resume_url, params={'decisao': 'aprovar'}, timeout=10)
            if uuid_ficha:
                banco_cadastros.atualizar_status(uuid_ficha, 'aprovado')

        elif acao == 'reprovar':
            req_ext.get(resume_url, params={'decisao': 'reprovar', 'motivo': motivo}, timeout=10)
            if uuid_ficha and motivo:
                banco_cadastros.registrar_reprovacao(uuid_ficha, motivo)

        elif acao == 'mascaras':
            req_ext.get(resume_url, params={'mascaras': 'confirmadas'}, timeout=10)

    except Exception as e:
        print(f"⚠️ Aviso ao chamar N8N: {e}")

    return render_template('confirmar_acao.html', acao=acao, empresa=empresa, motivo=motivo)


# ──────────────────────────────────────────────────────────────────────────────
# ROTA: Formulário de motivo de reprovação
# Farmacêutica clica "Reprovar" → preenche motivo → vai para /confirmar
# ──────────────────────────────────────────────────────────────────────────────

@app.route('/motivo_reprovacao')
def motivo_reprovacao():
    resume_url = request.args.get('resumeUrl', '')
    empresa    = request.args.get('empresa',   '')
    cnpj       = request.args.get('cnpj',      '')
    uuid_ficha = request.args.get('uuid',      '')   # ← NOVO
    return render_template(
        'motivo_reprovacao.html',
        resume_url=resume_url,
        empresa=empresa,
        cnpj=cnpj,
        uuid=uuid_ficha                               # ← NOVO
    )


# ==========================================
# SISTEMA DE BANCO DE DADOS (JSON) — Chamados
# ==========================================
ARQUIVO_CHAMADOS = 'dados/chamados.json'

def carregar_chamados():
    if not os.path.exists(ARQUIVO_CHAMADOS):
        return []
    with open(ARQUIVO_CHAMADOS, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_chamados(chamados):
    with open(ARQUIVO_CHAMADOS, 'w', encoding='utf-8') as f:
        json.dump(chamados, f, indent=4, ensure_ascii=False)

# ==========================================
# ROTAS DO ADMIN E DO SUPORTE
# ==========================================

@app.route('/suporte')
def suporte():
    return render_template('suporte.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/enviar_chamado', methods=['POST'])
def enviar_chamado():
    try:
        dados = request.get_json()
        novo_chamado = {
            "id":       int(datetime.now().timestamp()),
            "nome":     dados.get('nome'),
            "setor":    dados.get('setor'),
            "assunto":  dados.get('assunto'),
            "mensagem": dados.get('mensagem'),
            "data":     datetime.now().strftime("%d/%m/%Y %H:%M"),
            "status":   "pendente"
        }
        chamados = carregar_chamados()
        chamados.append(novo_chamado)
        salvar_chamados(chamados)
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"ERRO AO SALVAR CHAMADO: {str(e)}")
        return jsonify({'status': 'erro', 'msg': 'Erro interno ao salvar no banco.'})

@app.route('/api/chamados', methods=['GET'])
def get_chamados():
    return jsonify(carregar_chamados())

@app.route('/api/chamados/<int:id>/status', methods=['POST'])
def update_status(id):
    novo_status = request.get_json().get('status')
    chamados    = carregar_chamados()
    for c in chamados:
        if c['id'] == id:
            c['status'] = novo_status
            break
    salvar_chamados(chamados)
    return jsonify({'status': 'ok'})

@app.route('/api/chamados/<int:id>', methods=['DELETE'])
def delete_chamado(id):
    chamados = carregar_chamados()
    chamados = [c for c in chamados if c['id'] != id]
    salvar_chamados(chamados)
    return jsonify({'status': 'ok'})

@app.route('/consulta_cnpj/<cnpj>')
def consulta_cnpj(cnpj):
    try:
        headers  = {'User-Agent': 'Mozilla/5.0'}
        url      = f'https://publica.cnpj.ws/cnpj/{cnpj}'
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data   = response.json()
            estabs = data.get('estabelecimento', {})
            uf_fornecedor = estabs.get('estado', {}).get('sigla')
            lista_ie      = estabs.get('inscricoes_estaduais', [])
            ie_ativa      = ""
            for item in lista_ie:
                if item.get('estado', {}).get('sigla') == uf_fornecedor and item.get('ativo') is True:
                    ie_ativa = item.get('inscricao_estadual')
                    break
            simples    = data.get('simples') or {}
            status_mei = "SIM" if simples.get('mei') == 'Sim' else "NÃO"
            resultado  = {
                'razao_social':    data.get('razao_social'),
                'nome_fantasia':   estabs.get('nome_fantasia'),
                'cnpj':            cnpj,
                'inscricao_estadual': ie_ativa,
                'mei':             status_mei,
                'logradouro':      f"{estabs.get('tipo_logradouro', '')} {estabs.get('logradouro', '')}".strip(),
                'numero':          estabs.get('numero'),
                'complemento':     estabs.get('complemento'),
                'bairro':          estabs.get('bairro'),
                'cep':             estabs.get('cep'),
                'uf':              uf_fornecedor,
                'municipio':       estabs.get('cidade', {}).get('nome'),
                'cnae_fiscal':     estabs.get('atividade_principal', {}).get('id'),
                'cnae_fiscal_descricao': estabs.get('atividade_principal', {}).get('descricao'),
                'data_inicio_atividade': estabs.get('data_inicio_atividade'),
                'descricao_identificador_matriz_filial': "MATRIZ" if estabs.get('tipo') == "Matriz" else "FILIAL",
                'codigo_natureza_juridica': data.get('natureza_juridica', {}).get('id'),
                'natureza_juridica': data.get('natureza_juridica', {}).get('descricao')
            }
            return jsonify(resultado)
        else:
            msg = "CNPJ não encontrado ou erro na API."
            if response.status_code == 429: msg = "Muitas consultas! Aguarde 1 minuto."
            return jsonify({'erro': True, 'message': msg}), response.status_code
    except Exception as e:
        return jsonify({'erro': True, 'message': str(e)}), 500

@app.route('/api/cnpj_completo/<cnpj>')
def api_cnpj_completo(cnpj):
    try:
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        headers    = {'User-Agent': 'Mozilla/5.0'}
        url        = f'https://publica.cnpj.ws/cnpj/{cnpj_limpo}'
        response   = requests.get(url, headers=headers, timeout=45)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            msg = "CNPJ não encontrado."
            if response.status_code == 429:
                msg = "Muitas consultas! Aguarde 1 minuto e tente novamente."
            return jsonify({'erro': True, 'message': msg}), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({'erro': True, 'message': "A API da Receita Federal demorou muito. Tente novamente!"}), 504
    except Exception as e:
        return jsonify({'erro': True, 'message': f"Erro de comunicação: {str(e)}"}), 500

@app.route('/consulta_cnpj_completa')
def consulta_cnpj_completa():
    return render_template('consulta_cnpj.html')

@app.route('/fila/entrar', methods=['POST'])
def fila_entrar():
    meu_id = entrar_na_fila()
    return jsonify({'id': meu_id, 'posicao': posicao_na_fila(meu_id)})

@app.route('/fila/status/<meu_id>')
def fila_status(meu_id):
    pos = posicao_na_fila(meu_id)
    return jsonify({
        'posicao':     pos,
        'minha_vez':   pos == 1 and _em_execucao is None,
        'em_execucao': _em_execucao is not None
    })

@app.route('/fila/sair/<meu_id>', methods=['POST'])
def fila_sair(meu_id):
    sair_da_fila(meu_id)
    return jsonify({'ok': True})

# ==========================================
# ROTA DE INTEGRAÇÃO: n8n -> ROBÔ RPA
# ==========================================
@app.route('/n8n_iniciar_cadastro', methods=['POST'])
def n8n_iniciar_cadastro():
    dados_n8n = request.json
    cnpj      = dados_n8n.get('cnpj')
    razao     = dados_n8n.get('razao_social')
    vendedor  = dados_n8n.get('vendedor')
    print(f"\n🔔 [N8N] Solicitação recebida!")
    print(f"🏢 Cliente: {razao} | 👤 Vendedor: {vendedor}")
    try:
        resultado = cadastro_novo.executar({
            "cnpj": cnpj,
            "razao_social": razao,
            "vendedor": vendedor
        })
        return jsonify({
            "status":    "sucesso",
            "mensagem":  f"Robô finalizou o cadastro de {razao}",
            "resultado": resultado
        }), 200
    except Exception as e:
        print(f"❌ Erro ao processar chamado do n8n: {e}")
        return jsonify({"status": "erro", "detalhes": str(e)}), 500


if __name__ == '__main__':
    print("🚀 SERVIDOR ONLINE! Acesse pelo IP da sua máquina.")
    app.run(host='0.0.0.0', port=5000, debug=True)