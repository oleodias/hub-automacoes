# ══════════════════════════════════════════════════════════════
# routes/mdf.py — Relatório MDF-e
# ══════════════════════════════════════════════════════════════

import os
import subprocess
import time as time_module
from flask import Blueprint, render_template, request, Response, send_file
from utils.fila import minha_vez, iniciar_execucao, finalizar_execucao, sair_da_fila, posicao_na_fila

mdf_bp = Blueprint('mdf', __name__)


@mdf_bp.route('/relatorio_mdf')
def relatorio_mdf():
    return render_template('relatorio_mdf.html')


@mdf_bp.route('/run_mdf', methods=['GET'])
def rota_mdf():
    meu_id      = request.args.get('fila_id', '')
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
            processo = subprocess.Popen(
                ['python', '-u', 'automacoes/robo_mdf.py', data_inicio, data_fim],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', bufsize=1
            )
            for linha in iter(processo.stdout.readline, ''):
                if linha:
                    yield f"data: {linha.strip()}\n\n"
            processo.stdout.close()
            processo.wait()
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()

    return Response(gerar_logs(), mimetype='text/event-stream')


@mdf_bp.route('/download_mdf')
def download_mdf():
    caminho_arquivo = os.path.join(os.getcwd(), "Relatorio_MDFs_Gerado.xlsx")
    if not os.path.exists(caminho_arquivo):
        return "❌ O arquivo não foi encontrado.", 404
    try:
        return send_file(caminho_arquivo, as_attachment=True, download_name="Relatorio_MDF_Ciamed.xlsx")
    except Exception as e:
        return f"Erro interno ao tentar baixar o arquivo: {e}", 500
