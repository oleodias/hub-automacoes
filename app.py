from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, send_file
import os
import sys
import json
from datetime import datetime
import subprocess
import requests



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
HORA_INICIO = 7  # 07:00
HORA_FIM = 18    # 18:00
DIAS_UTEIS = [0, 1, 2, 3, 4] # 0 = Segunda, 4 = Sexta

@app.before_request
def verificar_horario():
    # 1. Deixa carregar imagens e CSS normalmente
    if request.endpoint and 'static' in request.endpoint:
        return None

    # 2. CHAVE MESTRA: Se você digitar ?bypass=leo_admin na URL, libera o acesso
    if request.args.get('bypass') == 'leo_admin':
        session['acesso_noturno'] = True
        return redirect(url_for('home'))

    # 3. Se você já tem o passe livre salvo na sessão, pode continuar
    if session.get('acesso_noturno'):
        return None

    # 4. Trava do Relógio para o resto da empresa
    agora = datetime.now()
    if agora.weekday() not in DIAS_UTEIS or not (HORA_INICIO <= agora.hour < HORA_FIM):
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

@app.route('/run_fase1', methods=['GET']) # ⚠️ Mudou para GET!
def rota_fase1():
    def gerar_logs():
        # Usamos o nome exato do seu arquivo: fase1_ncm.py
        comando = [sys.executable, "-X", "utf8", "-u", "automacoes/fase1_ncm.py"]       
        processo = subprocess.Popen(
            comando, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8', 
            bufsize=1
        )
        
        for linha in iter(processo.stdout.readline, ''):
            linha_limpa = linha.strip()
            if not linha_limpa:
                linha_limpa = " " 
                
            yield f"data: {linha_limpa}\n\n"
            
        processo.stdout.close()
        processo.wait()
        
        yield "data: [FIM_DO_PROCESSO]\n\n"
        
    return Response(gerar_logs(), mimetype='text/event-stream')

@app.route('/run_fase2', methods=['GET']) # ⚠️ Mudou para GET por causa da transmissão ao vivo!
def run_fase2():
    def gerar_logs():
        # O "-X utf8" força o Windows a entender os Emojis! 
        # O "-u" força a mandar a mensagem na mesma hora.
        comando = [sys.executable, "-X", "utf8", "-u", "automacoes/fase2_item.py"]       
        
        # Popen abre o robô em segundo plano
        processo = subprocess.Popen(
            comando, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            encoding='utf-8', # <--- Avisa o Flask para ler em UTF-8 também
            bufsize=1
        )
        
        # Fica lendo linha por linha do terminal em tempo real
        for linha in iter(processo.stdout.readline, ''):
            linha_limpa = linha.strip()
            if not linha_limpa:
                linha_limpa = " " # Mantém linhas em branco visíveis
                
            yield f"data: {linha_limpa}\n\n"
            
        processo.stdout.close()
        processo.wait()
        
        yield "data: [FIM_DO_PROCESSO]\n\n"
        
    # Retorna o transmissor ao vivo (SSE)
    return Response(gerar_logs(), mimetype='text/event-stream')

@app.route('/run_mdf', methods=['GET'])
def rota_mdf():
    # Pega as datas que o Javascript enviou
    data_inicio = request.args.get('inicio', '01/01/2026')
    data_fim = request.args.get('fim', '31/01/2026')

    def gerar_logs():
        # Passamos as datas como argumentos extras para o robô
        processo = subprocess.Popen(
            ['python', '-u', 'automacoes/robo_mdf.py', data_inicio, data_fim], 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )
        
        for linha in iter(processo.stdout.readline, ''):
            if linha:
                yield f"data: {linha.strip()}\n\n"
        processo.stdout.close()
        processo.wait()
        
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
    # Recebe os dados do JavaScript em formato JSON
    dados_json = request.args.get('dados', '{}')
    
    def generate():
        try:
            # Chama o robô passando os dados como argumento
            process = subprocess.Popen(
                [sys.executable, 'automacoes/robo_fornecedor.py', dados_json],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8'
            )
            
            for line in process.stdout:
                linha = line.strip()
                if linha:
                    yield f"data: {linha}\n\n"
                    
            process.wait()
            
        except Exception as e:
            yield f"data: > ❌ Erro interno no servidor: {str(e)}\n\n"
            yield f"data: [FIM_DO_PROCESSO]\n\n"

    return Response(generate(), mimetype='text/event-stream')

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
        response = requests.get(url, headers=headers, timeout=15)
        
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
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f'https://publica.cnpj.ws/cnpj/{cnpj}'
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            msg = "CNPJ não encontrado."
            if response.status_code == 429:
                msg = "Muitas consultas! Aguarde 1 minuto."
            return jsonify({'erro': True, 'message': msg}), response.status_code
    except Exception as e:
        return jsonify({'erro': True, 'message': str(e)}), 500

@app.route('/consulta_cnpj_completa')
def consulta_cnpj_completa():
    return render_template('consulta_cnpj.html')

if __name__ == '__main__':
    print("🚀 SERVIDOR ONLINE! Acesse pelo IP da sua máquina.")
    app.run(host='0.0.0.0', port=5000, debug=True)

    