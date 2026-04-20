# ══════════════════════════════════════════════════════════════
# routes/admin.py — Painel Admin e Sistema de Chamados
# ══════════════════════════════════════════════════════════════

import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify

import logging
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

ARQUIVO_CHAMADOS = 'dados/chamados.json'


# ── Helpers de persistência (JSON) ────────────────────────────

def carregar_chamados():
    if not os.path.exists(ARQUIVO_CHAMADOS):
        return []
    with open(ARQUIVO_CHAMADOS, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_chamados(chamados):
    os.makedirs(os.path.dirname(ARQUIVO_CHAMADOS), exist_ok=True)
    with open(ARQUIVO_CHAMADOS, 'w', encoding='utf-8') as f:
        json.dump(chamados, f, indent=4, ensure_ascii=False)


# ── Rotas ─────────────────────────────────────────────────────

@admin_bp.route('/suporte')
def suporte():
    return render_template('suporte.html')


@admin_bp.route('/admin')
def admin():
    return render_template('admin.html')


@admin_bp.route('/enviar_chamado', methods=['POST'])
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
        logger.error(f"Erro ao salvar chamado: {str(e)}")
        return jsonify({'status': 'erro', 'msg': 'Erro interno ao salvar no banco.'})


@admin_bp.route('/api/chamados', methods=['GET'])
def get_chamados():
    return jsonify(carregar_chamados())


@admin_bp.route('/api/chamados/<int:id>/status', methods=['POST'])
def update_status(id):
    novo_status = request.get_json().get('status')
    chamados    = carregar_chamados()
    for c in chamados:
        if c['id'] == id:
            c['status'] = novo_status
            break
    salvar_chamados(chamados)
    return jsonify({'status': 'ok'})


@admin_bp.route('/api/chamados/<int:id>', methods=['DELETE'])
def delete_chamado(id):
    chamados = carregar_chamados()
    chamados = [c for c in chamados if c['id'] != id]
    salvar_chamados(chamados)
    return jsonify({'status': 'ok'})
