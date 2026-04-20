# ══════════════════════════════════════════════════════════════
# routes/fornecedor.py — Cadastro de Fornecedor
# ══════════════════════════════════════════════════════════════

import sys
import subprocess
import time as time_module
from flask import Blueprint, render_template, request, Response
from utils.fila import minha_vez, iniciar_execucao, finalizar_execucao, sair_da_fila, posicao_na_fila

fornecedor_bp = Blueprint('fornecedor', __name__)


@fornecedor_bp.route('/cadastro_fornecedor')
def cadastro_fornecedor():
    return render_template('cadastro_fornecedor.html')


@fornecedor_bp.route('/run_fornecedor')
def run_fornecedor():
    meu_id     = request.args.get('fila_id', '')
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
        except Exception as e:
            yield f"data: ❌ Erro interno: {str(e)}\n\n"
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()

    return Response(generate(), mimetype='text/event-stream')
