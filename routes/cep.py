# ══════════════════════════════════════════════════════════════
# routes/cep.py — Cadastro de CEP
# ══════════════════════════════════════════════════════════════

import sys
import subprocess
import time as time_module
from utils.fila import minha_vez, iniciar_execucao, finalizar_execucao, sair_da_fila, posicao_na_fila
from utils.auth import permissao_required
from utils.rastreio import iniciar_execucao_robo, finalizar_execucao_robo
from utils.cep_api import consultar_cep
from flask import Blueprint, render_template, request, Response, session, current_app, jsonify

cep_bp = Blueprint('cep', __name__)


@cep_bp.route('/cadastro_cep')
@permissao_required('cep')
def cadastro_cep():
    return render_template('cadastro_cep.html')


@cep_bp.route('/api/consulta_cep/<cep>')
@permissao_required('cep')
def api_consulta_cep(cep):
    """Preview do endereço a partir do CEP (BrasilAPI → ViaCEP)."""
    return jsonify(consultar_cep(cep))


@cep_bp.route('/run_cep')
@permissao_required('cep')
def run_cep():
    meu_id     = request.args.get('fila_id', '')
    dados_json = request.args.get('dados', '{}')
    uid = session.get('usuario_id')
    unome = session.get('usuario_nome', 'Sistema')
    app = current_app._get_current_object()

    # Extrai info do CEP para o rastreio
    import json as json_lib
    try:
        dados_cep = json_lib.loads(dados_json)
        cep_info = dados_cep.get('cep', '')
        cidade_info = dados_cep.get('cidade', '')
    except Exception:
        cep_info = ''
        cidade_info = ''

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
        with app.app_context():
            exec_id = iniciar_execucao_robo('cadastro_cep', usuario_id=uid, usuario_nome=unome, detalhes={
                'cep': cep_info,
                'cidade': cidade_info,
            })
        try:
            # O robô importa pacotes do projeto (automacoes.*, utils.*), por isso
            # rodamos com "-m" a partir da raiz, em vez do caminho do arquivo.
            process = subprocess.Popen(
                [sys.executable, '-m', 'automacoes.clientes.cadastro_cep', dados_json],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding='utf-8'
            )
            for line in process.stdout:
                linha = line.strip()
                if linha:
                    yield f"data: {linha}\n\n"
            process.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
            with app.app_context():
                finalizar_execucao_robo(exec_id, 'sucesso')
        except Exception as e:
            with app.app_context():
                finalizar_execucao_robo(exec_id, 'erro', {'erro': str(e)})
            yield f"data: ❌ Erro interno: {str(e)}\n\n"
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao(meu_id)

    return Response(generate(), mimetype='text/event-stream')
