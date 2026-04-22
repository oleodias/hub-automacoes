# ══════════════════════════════════════════════════════════════
# routes/main.py — Rotas principais do Hub
# ══════════════════════════════════════════════════════════════
# Home, upload de XML e endpoints da fila genérica.
# ══════════════════════════════════════════════════════════════

import os
from flask import Blueprint, render_template, request, jsonify, session
from utils.auth import get_usuario_logado
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


# ══════════════════════════════════════════════════════════════
# MEU HISTÓRICO — operador vê suas próprias execuções
# ══════════════════════════════════════════════════════════════

@main_bp.route('/meu_historico')
def meu_historico():
    return render_template('meu_historico.html')


@main_bp.route('/api/meu_historico')
def api_meu_historico():
    """Retorna execuções do usuário logado."""
    from models import Execucao, ROBOS_HUB
    from datetime import datetime

    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'execucoes': [], 'stats': {}})

    query = Execucao.query.filter_by(usuario_id=usuario_id).order_by(Execucao.inicio.desc())

    # Filtros
    robo = request.args.get('robo')
    if robo:
        query = query.filter(Execucao.robo == robo)

    status = request.args.get('status')
    if status:
        query = query.filter(Execucao.status == status)

    limite = request.args.get('limite', 100, type=int)
    execucoes = query.limit(limite).all()

    lista = []
    for e in execucoes:
        if e.duracao_seg is not None:
            mins = e.duracao_seg // 60
            segs = e.duracao_seg % 60
            duracao_fmt = f"{mins}min {segs}s" if mins > 0 else f"{segs}s"
        else:
            duracao_fmt = "—"

        lista.append({
            'id':           e.id,
            'robo':         e.robo,
            'robo_nome':    ROBOS_HUB.get(e.robo, e.robo),
            'status':       e.status,
            'inicio':       e.inicio.strftime('%d/%m/%Y %H:%M:%S') if e.inicio else '',
            'duracao_fmt':  duracao_fmt,
            'detalhes':     e.detalhes or {},
        })

    # Stats do usuário
    from extensions import db
    total = Execucao.query.filter_by(usuario_id=usuario_id).count()
    sucessos = Execucao.query.filter_by(usuario_id=usuario_id, status='sucesso').count()
    erros = Execucao.query.filter_by(usuario_id=usuario_id, status='erro').count()

    return jsonify({
        'execucoes': lista,
        'stats': {
            'total': total,
            'sucesso': sucessos,
            'erro': erros,
            'taxa_sucesso': round((sucessos / total * 100), 1) if total > 0 else 0,
        }
    })
