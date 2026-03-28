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
# Chave secreta para gravar a sua "Chave Mestra" no navegador
app.secret_key = 'ciamed_super_secreta_2026'

# Configura pasta de Upload
UPLOAD_FOLDER = 'XML_Entrada'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ==========================================
# PORTEIRO DIGITAL (CONTROLE DE HORÁRIO)
# ==========================================
HORA_INICIO = time(6, 50)   # 06:50
HORA_FIM = time(18, 40)    # 18:40
DIAS_UTEIS = [0, 1, 2, 3, 4] # 0 = Segunda, 4 = Sexta

@app.before_request
def verificar_horario():
    # 1. Deixa carregar imagens e CSS normalmente
    if request.endpoint and 'static' in request.endpoint:
        return None
    
    # 👇 ADICIONE ESTA LINHA: Libera o cliente de acessar a ficha e consultar CNPJ a qualquer hora!
    if request.endpoint in ['ficha_cliente', 'api_cnpj_completo', 'consulta_cnpj']:
        return None 
    # 👆 ---------------------------------------------------------------------------------

    # 2. CHAVE MESTRA: Se você digitar ?bypass=leo_admin na URL, libera o acesso
    if request.args.get('bypass') == 'leo_admin':
        session['acesso_noturno'] = True
        return redirect(url_for('home'))

    # 3. Se você já tem o passe livre salvo na sessão, pode continuar
    if session.get('acesso_noturno'):
        return None

    # 4. Trava do Relógio para o resto da empresa
    agora = datetime.now()
    if agora.weekday() not in DIAS_UTEIS or not (HORA_INICIO <= agora.time() < HORA_FIM):
        return """
        <body style="background-color: #263238; color: white; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <img src="/static/img/ciamedia.png" style="height: 60px; margin-bottom: 20px;" style="height: 60px; margin-bottom: 20px;">
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
        
        # --- 🧹 FAXINEIRA: Limpa a pasta antes de salvar o novo arquivo ---
        try:
            for arquivo_velho in os.listdir(pasta_upload):
                caminho_velho = os.path.join(pasta_upload, arquivo_velho)
                # Verifica se é um arquivo mesmo (e não uma pasta perdida) e apaga
                if os.path.isfile(caminho_velho):
                    os.remove(caminho_velho)
        except Exception as e:
            print(f"⚠️ Erro ao limpar a pasta: {e}")
        # ------------------------------------------------------------------
        
        # Salva o arquivo novo na pasta agora vazia
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
    meu_id = request.args.get('fila_id', '')
    data_inicio = request.args.get('inicio', '01/01/2026')
    data_fim = request.args.get('fim', '31/01/2026')
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
    caminho_arquivo = "Relatorio_MDFs_Março.xlsx" # Tem que ser o mesmo nome que está no seu robo_mdf.py
    try:
        return send_file(caminho_arquivo, as_attachment=True)
    except Exception as e:
        return f"Erro ao baixar arquivo: {e}"
    
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
    meu_id = request.args.get('fila_id', '')
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
        # Cria uma pasta segura para salvar se não existir
        pasta_uploads = os.path.join(app.root_path, 'uploads')
        os.makedirs(pasta_uploads, exist_ok=True)
        
        filename = secure_filename(file.filename)
        caminho_salvo = os.path.join(pasta_uploads, filename)
        file.save(caminho_salvo)
        
        # Chama o nosso robô para ler a ficha e bater na API!
        resultado = processar_ficha_cliente(caminho_salvo)
        
        # Opcional: Apagar a ficha do servidor após extrair para economizar espaço
        if os.path.exists(caminho_salvo):
            os.remove(caminho_salvo)
            
        return jsonify(resultado)
    else:
        return jsonify({"erro": True, "mensagem": "Formato inválido. Envie um arquivo Excel (.xlsx ou .xls)"}), 400
    
@app.route('/iniciar_cadastro_novo', methods=['POST'])
def iniciar_cadastro_novo():
    dados_do_cliente = request.json  # Pega os dados que o JavaScript mandou
    
    # Aciona o motor do robô que acabamos de criar!
    resultado = cadastro_novo.executar(dados_do_cliente)
    
    return jsonify(resultado) # Devolve pra tela se deu Sucesso ou Erro

@app.route('/consulta_cte')
def consulta_cte():
    return render_template('consulta_cte.html')

@app.route('/ficha_cliente')
def ficha_cliente():
    return render_template('ficha_cliente.html')

# ==========================================
# SISTEMA DE BANCO DE DADOS (JSON)
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
            "id": int(datetime.now().timestamp()),
            "nome": dados.get('nome'),
            "setor": dados.get('setor'),
            "assunto": dados.get('assunto'),
            "mensagem": dados.get('mensagem'),
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "status": "pendente"
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
    chamados = carregar_chamados()
    
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
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f'https://publica.cnpj.ws/cnpj/{cnpj}'
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            estabs = data.get('estabelecimento', {})
            
            # --- LÓGICA DA INSCRIÇÃO ESTADUAL (IE) ---
            uf_fornecedor = estabs.get('estado', {}).get('sigla')
            lista_ie = estabs.get('inscricoes_estaduais', [])
            ie_ativa = ""

            for item in lista_ie:
                # REGRA: Mesma UF e Status ATIVO
                if item.get('estado', {}).get('sigla') == uf_fornecedor and item.get('ativo') is True:
                    ie_ativa = item.get('inscricao_estadual')
                    break 

                # Pega o bloco do Simples Nacional (se for nulo, cria um dicionário vazio)
            simples = data.get('simples') or {}
            
            # A API retorna 'Sim' ou 'Não'. Vamos deixar bonitão em maiúsculo:
            status_mei = "SIM" if simples.get('mei') == 'Sim' else "NÃO"

            # Mapeia para o formato que seu JS e Robô já esperam
            resultado = {
                'razao_social': data.get('razao_social'),
                'nome_fantasia': estabs.get('nome_fantasia'),
                'cnpj': cnpj,
                'inscricao_estadual': ie_ativa,
                'mei': status_mei,
                'logradouro': f"{estabs.get('tipo_logradouro', '')} {estabs.get('logradouro', '')}".strip(),                
                'numero': estabs.get('numero'),
                'complemento': estabs.get('complemento'),
                'bairro': estabs.get('bairro'),
                'cep': estabs.get('cep'),
                'uf': uf_fornecedor,
                'municipio': estabs.get('cidade', {}).get('nome'),
                'cnae_fiscal': estabs.get('atividade_principal', {}).get('id'),
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
        # 1. FAXINA NO CNPJ: Tira ponto, barra e traço e deixa só os números puros
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 2. Manda a URL com o CNPJ limpo para a API
        url = f'https://publica.cnpj.ws/cnpj/{cnpj_limpo}'
        
        # 3. Paciência de monge: 45 segundos de timeout
        response = requests.get(url, headers=headers, timeout=45)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            msg = "CNPJ não encontrado."
            if response.status_code == 429:
                msg = "Muitas consultas! Aguarde 1 minuto e tente novamente."
            return jsonify({'erro': True, 'message': msg}), response.status_code
            
    # 4. Tratamento elegante para quando a API demora demais
    except requests.exceptions.Timeout:
        return jsonify({'erro': True, 'message': "A API da Receita Federal demorou muito para responder. Por favor, aguarde uns segundos e tente novamente!"}), 504
        
    # 5. Tratamento para qualquer outro erro (ex: internet caiu)
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
        'posicao': pos,
        'minha_vez': pos == 1 and _em_execucao is None,
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
    # 1. Captura o pacote enviado pelo n8n
    dados_n8n = request.json
    
    # 2. Extrai os dados que você definiu (CNPJ, Razão e Vendedor)
    cnpj = dados_n8n.get('cnpj')
    razao = dados_n8n.get('razao_social')
    vendedor = dados_n8n.get('vendedor')

    # Log para você ver no terminal do VS Code quando o n8n chamar
    print(f"\n🔔 [N8N] Solicitação recebida!")
    print(f"🏢 Cliente: {razao} | 👤 Vendedor: {vendedor}")

    try:
        # 3. Chama o motor do seu robô (ajustando para o formato que ele espera)
        # O cadastro_novo.executar já está importado no seu app.py!
        resultado = cadastro_novo.executar({
            "cnpj": cnpj,
            "razao_social": razao,
            "vendedor": vendedor
        })
        
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Robô finalizou o cadastro de {razao}",
            "resultado": resultado
        }), 200

    except Exception as e:
        print(f"❌ Erro ao processar chamado do n8n: {e}")
        return jsonify({"status": "erro", "detalhes": str(e)}), 500

if __name__ == '__main__':
    print("🚀 SERVIDOR ONLINE! Acesse pelo IP da sua máquina.")
    app.run(host='0.0.0.0', port=5000, debug=True)

    