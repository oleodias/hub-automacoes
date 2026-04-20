# ══════════════════════════════════════════════════════════════
# routes/main.py — Rotas principais do Hub
# ══════════════════════════════════════════════════════════════
# Home, upload de XML e endpoints da fila genérica.
# ══════════════════════════════════════════════════════════════

import os
from flask import Blueprint, render_template, request, jsonify
from utils.fila import entrar_na_fila, posicao_na_fila, sair_da_fila, _em_execucao

main_bp = Blueprint('main', __name__)


# ── HOME ──────────────────────────────────────────────────────

@main_bp.route('/')
def home():
    return render_template('home.html')


# ── UPLOAD DE XML (Cadastro de Itens) ─────────────────────────

UPLOAD_FOLDER = 'XML_Entrada'

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'erro', 'msg': 'Nenhum arquivo enviado'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'erro', 'msg': 'Nome vazio'})

    if file:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        try:
            for arquivo_velho in os.listdir(UPLOAD_FOLDER):
                caminho_velho = os.path.join(UPLOAD_FOLDER, arquivo_velho)
                if os.path.isfile(caminho_velho):
                    os.remove(caminho_velho)
        except Exception as e:
            print(f"⚠️ Erro ao limpar a pasta: {e}")

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        return jsonify({'status': 'ok', 'msg': f'Arquivo salvo e fila limpa: {file.filename}'})


# ── FILA GENÉRICA ─────────────────────────────────────────────

@main_bp.route('/fila/entrar', methods=['POST'])
def fila_entrar():
    meu_id = entrar_na_fila()
    return jsonify({'id': meu_id, 'posicao': posicao_na_fila(meu_id)})


@main_bp.route('/fila/status/<meu_id>')
def fila_status(meu_id):
    pos = posicao_na_fila(meu_id)
    return jsonify({
        'posicao':     pos,
        'minha_vez':   pos == 1 and _em_execucao is None,
        'em_execucao': _em_execucao is not None
    })


@main_bp.route('/fila/sair/<meu_id>', methods=['POST'])
def fila_sair(meu_id):
    sair_da_fila(meu_id)
    return jsonify({'ok': True})
