# ══════════════════════════════════════════════════════════════
# routes/itens.py — Cadastro de Itens (NCM + ERP)
# ══════════════════════════════════════════════════════════════

import sys
import subprocess
import time as time_module
from flask import Blueprint, render_template, request, Response, session, current_app
from utils.fila import minha_vez, iniciar_execucao, finalizar_execucao, sair_da_fila, posicao_na_fila
from utils.auth import permissao_required
from utils.rastreio import iniciar_execucao_robo, finalizar_execucao_robo

itens_bp = Blueprint('itens', __name__)


@itens_bp.route('/cadastro_itens')
@permissao_required('itens')
def cadastro_itens():
    return render_template('cadastro_itens.html')


@itens_bp.route('/run_fase1', methods=['GET'])
@permissao_required('itens')
def rota_fase1():
    meu_id = request.args.get('fila_id', '')
    uid = session.get('usuario_id')
    unome = session.get('usuario_nome', 'Sistema')
    app = current_app._get_current_object()

    # Captura o nome do XML que está na pasta de entrada
    import os
    arquivos_xml = [f for f in os.listdir('XML_Entrada') if f.endswith('.xml')]
    xml_nome = arquivos_xml[0] if arquivos_xml else 'nenhum arquivo'

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
        with app.app_context():
            exec_id = iniciar_execucao_robo('itens_fase1', usuario_id=uid, usuario_nome=unome, detalhes={
                'arquivo_xml': xml_nome,
            })
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
            with app.app_context():
                finalizar_execucao_robo(exec_id, 'sucesso')
        except Exception as e:
            with app.app_context():
                finalizar_execucao_robo(exec_id, 'erro', {'erro': str(e)})
            yield f"data: ❌ Erro: {str(e)}\n\n"
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()

    return Response(gerar_logs(), mimetype='text/event-stream')


@itens_bp.route('/run_fase2', methods=['GET'])
@permissao_required('itens')
def run_fase2():
    meu_id = request.args.get('fila_id', '')
    uid = session.get('usuario_id')
    unome = session.get('usuario_nome', 'Sistema')
    app = current_app._get_current_object()

    import os
    arquivos_xml = [f for f in os.listdir('XML_Entrada') if f.endswith('.xml')]
    xml_nome = arquivos_xml[0] if arquivos_xml else 'nenhum arquivo'

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
        with app.app_context():
            exec_id = iniciar_execucao_robo('itens_fase2', usuario_id=uid, usuario_nome=unome, detalhes={
                'arquivo_xml': xml_nome,
            })
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
            with app.app_context():
                finalizar_execucao_robo(exec_id, 'sucesso')
        except Exception as e:
            with app.app_context():
                finalizar_execucao_robo(exec_id, 'erro', {'erro': str(e)})
            yield f"data: ❌ Erro: {str(e)}\n\n"
            yield "data: [FIM_DO_PROCESSO]\n\n"
        finally:
            finalizar_execucao()

    return Response(gerar_logs(), mimetype='text/event-stream')
