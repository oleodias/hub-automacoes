# ══════════════════════════════════════════════════════════════
# routes/fornecedor.py — Cadastro de Fornecedor
# ══════════════════════════════════════════════════════════════

import sys
import subprocess
import time as time_module
from utils.fila import minha_vez, iniciar_execucao, finalizar_execucao, sair_da_fila, posicao_na_fila
from utils.auth import permissao_required
from utils.rastreio import iniciar_execucao_robo, finalizar_execucao_robo
from flask import Blueprint, render_template, request, Response, session, current_app

fornecedor_bp = Blueprint('fornecedor', __name__)


@fornecedor_bp.route('/cadastro_fornecedor')
@permissao_required('fornecedor')
def cadastro_fornecedor():
    return render_template('cadastro_fornecedor.html')


@fornecedor_bp.route('/run_fornecedor')
@permissao_required('fornecedor')
def run_fornecedor():
    meu_id     = request.args.get('fila_id', '')
    dados_json = request.args.get('dados', '{}')
    uid = session.get('usuario_id')
    unome = session.get('usuario_nome', 'Sistema')
    app = current_app._get_current_object()

    # Extrai info do fornecedor para o rastreio
    import json as json_lib
    try:
        dados_forn = json_lib.loads(dados_json)
        forn_cnpj = dados_forn.get('cnpj', '')
        forn_razao = dados_forn.get('razao_social', '')
    except Exception:
        forn_cnpj = ''
        forn_razao = ''

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
            exec_id = iniciar_execucao_robo('fornecedor', usuario_id=uid, usuario_nome=unome, detalhes={
                'cnpj': forn_cnpj,
                'razao_social': forn_razao,
            })
        try:
            process = subprocess.Popen(
                [sys.executable, 'automacoes/robo_fornecedor.py', dados_json],
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
            finalizar_execucao()

    return Response(generate(), mimetype='text/event-stream')
