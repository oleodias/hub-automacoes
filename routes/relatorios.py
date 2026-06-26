# ══════════════════════════════════════════════════════════════
# routes/relatorios.py — Endpoints do robô de relatórios (N8N)
# ══════════════════════════════════════════════════════════════
# Espelha o padrão do cadastro de clientes:
#   • fila com resume_url (serializa via N8N Wait/resume) — recurso 'relatorios'
#   • /iniciar dispara o robô SÍNCRONO (gerar_relatorios.executar) e
#     devolve o MANIFESTO (lab_id → arquivos), registrando no Monitor
#   • /download entrega cada .xlsx para o N8N anexar no e-mail (SMTP)
#
# Todos os endpoints chamados pelo N8N exigem o header X-Hub-Token
# (@exigir_token_n8n) e entram em ROTAS_PUBLICAS no app.py.
# ══════════════════════════════════════════════════════════════

import os
import logging

from flask import Blueprint, request, jsonify, send_file

from utils.n8n_security import exigir_token_n8n, resume_url_confiavel
from utils.fila import (
    cadastro_entrar,
    cadastro_liberar_proximo,
    fila_cadastro_status_dict,
    RECURSO_RELATORIOS,
)
from utils.rastreio import iniciar_execucao_robo, finalizar_execucao_robo
from automacoes.relatorios import gerar_relatorios
from automacoes.relatorios.gerar_relatorios import PASTA_BASE

logger = logging.getLogger(__name__)

relatorios_bp = Blueprint('relatorios', __name__)


# ══════════════════════════════════════════════════════════════
# Fila de relatórios (mesmo mecanismo do cadastro, recurso 'relatorios')
# ══════════════════════════════════════════════════════════════

@relatorios_bp.route('/relatorios/fila/entrar', methods=['POST'])
@exigir_token_n8n
def relatorios_fila_entrar():
    dados = request.get_json(silent=True) or {}
    resume_url = dados.get('resume_url', '')
    if not resume_url:
        return jsonify({'erro': 'resume_url obrigatório'}), 400

    # Anti-SSRF (V-04): a URL é guardada e depois "visitada" pelo Hub.
    if not resume_url_confiavel(resume_url):
        return jsonify({'erro': 'resume_url inválida'}), 400

    novo_id, posicao, sua_vez = cadastro_entrar(resume_url, RECURSO_RELATORIOS)
    return jsonify({'id': novo_id, 'posicao': posicao, 'sua_vez': sua_vez})


@relatorios_bp.route('/relatorios/fila/liberar_proximo', methods=['POST'])
@exigir_token_n8n
def relatorios_fila_liberar():
    cadastro_liberar_proximo(RECURSO_RELATORIOS)
    return jsonify({'status': 'ok'})


@relatorios_bp.route('/relatorios/fila/status', methods=['GET'])
def relatorios_fila_status():
    """Estado da fila de relatórios — debug (exige login, como no cadastro)."""
    return jsonify(fila_cadastro_status_dict(RECURSO_RELATORIOS))


# ══════════════════════════════════════════════════════════════
# Disparo do robô (síncrono) — devolve o manifesto lab_id → arquivos
# ══════════════════════════════════════════════════════════════

@relatorios_bp.route('/relatorios/iniciar', methods=['POST'])
@exigir_token_n8n
def relatorios_iniciar():
    job = request.get_json(silent=True) or {}
    envios = job.get('envios') or []
    if not isinstance(envios, list) or not envios:
        return jsonify({"status": "erro", "detalhes": "Campo 'envios' ausente ou vazio."}), 400

    logger.info(f"[N8N] Relatórios: iniciando robô para {len(envios)} envio(s).")

    exec_id = iniciar_execucao_robo('relatorios', detalhes={'qtd_envios': len(envios), 'tipo': job.get('tipo')})
    try:
        resultado = gerar_relatorios.executar(job)
        status_robo = resultado.get('status', 'Erro')

        # 'exec' = nome da subpasta da execução, usado pelo /relatorios/download
        pasta = resultado.get('pasta') or ''
        resultado['exec'] = os.path.basename(pasta) if pasta else ''

        if status_robo in ('Sucesso', 'Sucesso com avisos'):
            finalizar_execucao_robo(exec_id, 'sucesso', {'itens': resultado.get('itens'), 'avisos': resultado.get('avisos')})
            return jsonify({"status": "sucesso", "resultado": resultado}), 200

        # Erro controlado do robô (não exceção) — 200 p/ o N8N ler o corpo e decidir.
        finalizar_execucao_robo(exec_id, 'erro', {'msg': resultado.get('msg')})
        return jsonify({"status": "erro_robo", "resultado": resultado}), 200

    except Exception as e:  # noqa: BLE001
        finalizar_execucao_robo(exec_id, 'erro', {'erro': str(e)})
        logger.error(f"[N8N] Exceção no robô de relatórios: {e}")
        return jsonify({"status": "erro_robo", "mensagem": str(e)}), 200


# ══════════════════════════════════════════════════════════════
# Download de um arquivo gerado (o N8N anexa no e-mail)
# ══════════════════════════════════════════════════════════════

@relatorios_bp.route('/relatorios/download', methods=['GET'])
@exigir_token_n8n
def relatorios_download():
    exec_dir = request.args.get('exec', '')
    arquivo = request.args.get('arquivo', '')
    if not exec_dir or not arquivo:
        return jsonify({'erro': "parâmetros 'exec' e 'arquivo' obrigatórios"}), 400

    # Só nomes simples (sem separador/traversal).
    proibidos = ('/', '\\', '..')
    if any(p in exec_dir for p in proibidos) or any(p in arquivo for p in proibidos):
        return jsonify({'erro': 'parâmetro inválido'}), 400

    base = os.path.realpath(PASTA_BASE)
    caminho = os.path.realpath(os.path.join(base, exec_dir, arquivo))
    # Confina o caminho dentro da pasta-base (defesa em profundidade).
    if not (caminho == base or caminho.startswith(base + os.sep)):
        return jsonify({'erro': 'caminho não permitido'}), 403
    if not os.path.isfile(caminho):
        return jsonify({'erro': 'arquivo não encontrado'}), 404

    return send_file(caminho, as_attachment=True, download_name=arquivo)
