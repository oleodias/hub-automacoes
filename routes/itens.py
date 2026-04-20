# ══════════════════════════════════════════════════════════════
# routes/itens.py — Cadastro de Itens (NCM + ERP)
# ══════════════════════════════════════════════════════════════

import sys
import subprocess
import time as time_module
from flask import Blueprint, render_template, request, Response
from utils.fila import minha_vez, iniciar_execucao, finalizar_execucao, sair_da_fila, posicao_na_fila

itens_bp = Blueprint('itens', __name__)


@itens_bp.route('/cadastro_itens')
def cadastro_itens():
    return render_template('cadastro_itens.html')


@itens_bp.route('/run_fase1', methods=['GET'])
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
            processo = subprocess.Popen(
                comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', bufsize=1
            )
            for linha in iter(processo.stdout.readline, ''):
                linha_limpa = linha.strip()
                if not linha_limpa:
                    linha_limpa = " "
                yield f"data: {linha_limpa}\n\n"
            processo.stdout.close()
            processo.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()

    return Response(gerar_logs(), mimetype='text/event-stream')


@itens_bp.route('/run_fase2', methods=['GET'])
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
            processo = subprocess.Popen(
                comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', bufsize=1
            )
            for linha in iter(processo.stdout.readline, ''):
                linha_limpa = linha.strip()
                if not linha_limpa:
                    linha_limpa = " "
                yield f"data: {linha_limpa}\n\n"
            processo.stdout.close()
            processo.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()

    return Response(gerar_logs(), mimetype='text/event-stream')
