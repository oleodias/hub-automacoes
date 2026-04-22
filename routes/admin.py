# ══════════════════════════════════════════════════════════════
# routes/admin.py — Painel Admin + Gestão de Usuários
# ══════════════════════════════════════════════════════════════

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from extensions import db
from models import Usuario, MODULOS_HUB, permissoes_padrao
from utils.auth import admin_required

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

ARQUIVO_CHAMADOS = 'dados/chamados.json'


# ══════════════════════════════════════════════════════════════
# PÁGINAS
# ══════════════════════════════════════════════════════════════

@admin_bp.route('/admin')
@admin_required
def admin():
    return render_template('admin.html', modulos=MODULOS_HUB)


@admin_bp.route('/suporte')
def suporte():
    return render_template('suporte.html')


# ══════════════════════════════════════════════════════════════
# CHAMADOS
# ══════════════════════════════════════════════════════════════

def carregar_chamados():
    if not os.path.exists(ARQUIVO_CHAMADOS):
        return []
    with open(ARQUIVO_CHAMADOS, 'r', encoding='utf-8') as f:
        return json.load(f)


def salvar_chamados(chamados):
    os.makedirs(os.path.dirname(ARQUIVO_CHAMADOS), exist_ok=True)
    with open(ARQUIVO_CHAMADOS, 'w', encoding='utf-8') as f:
        json.dump(chamados, f, indent=4, ensure_ascii=False)


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


# ══════════════════════════════════════════════════════════════
# GESTÃO DE USUÁRIOS
# ══════════════════════════════════════════════════════════════

@admin_bp.route('/api/usuarios', methods=['GET'])
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.created_at.desc()).all()
    lista = []
    for u in usuarios:
        lista.append({
            'id':         u.id,
            'nome':       u.nome,
            'email':      u.email,
            'cargo':      u.cargo,
            'permissoes': u.permissoes or {},
            'ativo':      u.ativo,
            'created_at': u.created_at.strftime('%d/%m/%Y %H:%M') if u.created_at else '',
            'updated_at': u.updated_at.strftime('%d/%m/%Y %H:%M') if u.updated_at else '',
        })
    return jsonify(lista)


@admin_bp.route('/api/usuarios', methods=['POST'])
@admin_required
def criar_usuario():
    dados = request.get_json()
    nome  = (dados.get('nome') or '').strip()
    email = (dados.get('email') or '').strip().lower()
    senha = (dados.get('senha') or '').strip()
    cargo = dados.get('cargo', 'operador')

    if not nome or not email or not senha:
        return jsonify({'erro': 'Nome, email e senha são obrigatórios.'}), 400
    if len(senha) < 4:
        return jsonify({'erro': 'A senha deve ter pelo menos 4 caracteres.'}), 400
    if Usuario.query.filter_by(email=email).first():
        return jsonify({'erro': 'Já existe um usuário com este email.'}), 400

    usuario = Usuario(
        nome=nome, email=email, cargo=cargo,
        permissoes=permissoes_padrao(), ativo=True,
    )
    usuario.definir_senha(senha)
    db.session.add(usuario)
    db.session.commit()

    logger.info(f"Usuário criado: {nome} ({email}) por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok', 'id': usuario.id})


@admin_bp.route('/api/usuarios/<int:id>', methods=['PUT'])
@admin_required
def editar_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404

    dados = request.get_json()
    if 'nome' in dados:
        usuario.nome = dados['nome'].strip()
    if 'email' in dados:
        novo_email = dados['email'].strip().lower()
        existente = Usuario.query.filter_by(email=novo_email).first()
        if existente and existente.id != id:
            return jsonify({'erro': 'Já existe outro usuário com este email.'}), 400
        usuario.email = novo_email
    if 'cargo' in dados:
        usuario.cargo = dados['cargo']
    if 'permissoes' in dados:
        usuario.permissoes = dados['permissoes']

    db.session.commit()
    logger.info(f"Usuário editado: {usuario.nome} (ID: {id}) por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok'})


@admin_bp.route('/api/usuarios/<int:id>/toggle', methods=['POST'])
@admin_required
def toggle_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
    if usuario.id == session.get('usuario_id'):
        return jsonify({'erro': 'Você não pode desativar sua própria conta.'}), 400

    usuario.ativo = not usuario.ativo
    db.session.commit()
    acao = "ativado" if usuario.ativo else "desativado"
    logger.info(f"Usuário {acao}: {usuario.nome} (ID: {id}) por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok', 'ativo': usuario.ativo})


@admin_bp.route('/api/usuarios/<int:id>/reset_senha', methods=['POST'])
@admin_required
def reset_senha(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404

    nova_senha = (request.get_json().get('senha') or '').strip()
    if len(nova_senha) < 4:
        return jsonify({'erro': 'A senha deve ter pelo menos 4 caracteres.'}), 400

    usuario.definir_senha(nova_senha)
    db.session.commit()
    logger.info(f"Senha resetada: {usuario.nome} (ID: {id}) por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok'})


@admin_bp.route('/api/usuarios/<int:id>', methods=['DELETE'])
@admin_required
def deletar_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado.'}), 404
    if usuario.id == session.get('usuario_id'):
        return jsonify({'erro': 'Você não pode deletar sua própria conta.'}), 400

    nome = usuario.nome
    db.session.delete(usuario)
    db.session.commit()
    logger.info(f"Usuário deletado: {nome} (ID: {id}) por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# HISTÓRICO DE EXECUÇÕES
# ══════════════════════════════════════════════════════════════

@admin_bp.route('/api/execucoes', methods=['GET'])
@admin_required
def listar_execucoes():
    """
    Retorna lista de execuções com filtros opcionais.
    Query params: robo, status, usuario, data_de, data_ate, limite
    """
    from models import Execucao, ROBOS_HUB
    from datetime import datetime

    query = Execucao.query.order_by(Execucao.inicio.desc())

    # Filtro por robô
    robo = request.args.get('robo')
    if robo:
        query = query.filter(Execucao.robo == robo)

    # Filtro por status
    status = request.args.get('status')
    if status:
        query = query.filter(Execucao.status == status)

    # Filtro por usuário
    usuario = request.args.get('usuario')
    if usuario:
        query = query.filter(Execucao.usuario_nome.ilike(f'%{usuario}%'))

    # Filtro por data
    data_de = request.args.get('data_de')
    if data_de:
        try:
            if '/' in data_de:
                dt = datetime.strptime(data_de, '%d/%m/%Y')
            else:
                dt = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(Execucao.inicio >= dt)
        except ValueError:
            pass

    data_ate = request.args.get('data_ate')
    if data_ate:
        try:
            if '/' in data_ate:
                dt = datetime.strptime(data_ate, '%d/%m/%Y')
            else:
                dt = datetime.strptime(data_ate, '%Y-%m-%d')
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Execucao.inicio <= dt)
        except ValueError:
            pass

    # Limite
    limite = request.args.get('limite', 100, type=int)
    execucoes = query.limit(limite).all()

    lista = []
    for e in execucoes:
        # Formata duração
        if e.duracao_seg is not None:
            mins = e.duracao_seg // 60
            segs = e.duracao_seg % 60
            duracao_fmt = f"{mins}min {segs}s" if mins > 0 else f"{segs}s"
        else:
            duracao_fmt = "—"

        lista.append({
            'id':            e.id,
            'robo':          e.robo,
            'robo_nome':     ROBOS_HUB.get(e.robo, e.robo),
            'status':        e.status,
            'usuario_nome':  e.usuario_nome,
            'inicio':        e.inicio.strftime('%d/%m/%Y %H:%M:%S') if e.inicio else '',
            'fim':           e.fim.strftime('%d/%m/%Y %H:%M:%S') if e.fim else '',
            'duracao_fmt':   duracao_fmt,
            'duracao_seg':   e.duracao_seg,
            'detalhes':      e.detalhes or {},
        })

    # Stats rápidas
    from sqlalchemy import func
    total = Execucao.query.count()
    sucessos = Execucao.query.filter_by(status='sucesso').count()
    erros = Execucao.query.filter_by(status='erro').count()
    executando = Execucao.query.filter_by(status='executando').count()

    return jsonify({
        'execucoes': lista,
        'stats': {
            'total': total,
            'sucesso': sucessos,
            'erro': erros,
            'executando': executando,
            'taxa_sucesso': round((sucessos / total * 100), 1) if total > 0 else 0,
        }
    })
