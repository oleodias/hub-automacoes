# ══════════════════════════════════════════════════════════════
# routes/suporte.py — Central de Suporte (Hub Ciamed)
# ══════════════════════════════════════════════════════════════
#
#   PÁGINA
#     GET  /suporte                          → Página principal
#
#   API — Chamados (Usuário)
#     POST /api/suporte/chamados             → Criar chamado (multipart)
#     GET  /api/suporte/chamados             → Listar meus chamados
#     GET  /api/suporte/chamados/<id>        → Detalhe + histórico
#     POST /api/suporte/chamados/<id>/cancelar → Cancelar (só se pendente)
#
#   API — Chamados (Admin)
#     GET  /api/suporte/admin/chamados       → Todos os chamados
#     POST /api/suporte/admin/chamados/<id>/responder → Resposta + status
#     POST /api/suporte/admin/chamados/<id>/status    → Mudar status
#     DELETE /api/suporte/admin/chamados/<id>          → Excluir
#
#   API — FAQ
#     GET    /api/suporte/faq                → Listar (agrupado por módulo)
#     GET    /api/suporte/faq/busca?q=       → Buscar
#     POST   /api/suporte/faq               → Criar (admin)
#     PUT    /api/suporte/faq/<id>           → Editar (admin)
#     DELETE /api/suporte/faq/<id>           → Excluir (admin)
#
#   API — Notificações
#     GET  /api/notificacoes                 → Minhas notificações
#     GET  /api/notificacoes/count           → Contagem de não-lidas
#     POST /api/notificacoes/<id>/lida       → Marcar como lida
#     POST /api/notificacoes/ler-todas       → Marcar todas como lidas
#
# ══════════════════════════════════════════════════════════════

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from extensions import db
from models import (
    Chamado, ChamadoAnexo, ChamadoHistorico,
    Notificacao, FaqPergunta, Usuario,
    MODULOS_HUB, SETORES_CIAMED,
)
from utils.auth import admin_required

logger = logging.getLogger(__name__)

suporte_bp = Blueprint('suporte', __name__)

# ── Configuração de uploads ──────────────────────────────────
UPLOAD_DIR = os.path.join('uploads', 'chamados')
EXTENSOES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'xml', 'pdf', 'xlsx', 'csv', 'txt'}
MAX_TAMANHO_BYTES = 10 * 1024 * 1024  # 10MB
MAX_ANEXOS = 5


def _extensao_ok(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSOES_PERMITIDAS


def _gerar_protocolo():
    """Gera o próximo protocolo no formato SUP-XXXX."""
    ultimo = db.session.query(db.func.max(Chamado.id)).scalar() or 0
    return f"SUP-{str(ultimo + 1).zfill(4)}"


def _criar_notificacao(usuario_id, chamado_id, tipo, titulo):
    """Helper para criar uma notificação."""
    notif = Notificacao(
        usuario_id=usuario_id,
        chamado_id=chamado_id,
        tipo=tipo,
        titulo=titulo,
    )
    db.session.add(notif)


def _serializar_chamado(c, incluir_historico=False):
    """Converte um Chamado em dict para JSON."""
    mod_nome = MODULOS_HUB.get(c.modulo, 'Geral')
    dados = {
        'id':         c.id,
        'protocolo':  c.protocolo,
        'usuario_id': c.usuario_id,
        'usuario':    c.usuario.nome if c.usuario else 'Desconhecido',
        'modulo':     c.modulo,
        'modulo_nome': mod_nome,
        'prioridade': c.prioridade,
        'assunto':    c.assunto,
        'mensagem':   c.mensagem,
        'status':     c.status,
        'created_at': c.created_at.strftime('%d/%m/%Y %H:%M') if c.created_at else '',
        'updated_at': c.updated_at.strftime('%d/%m/%Y %H:%M') if c.updated_at else '',
        'anexos': [{
            'id':            a.id,
            'nome_arquivo':  a.nome_arquivo,
            'tipo_mime':     a.tipo_mime,
            'tamanho_bytes': a.tamanho_bytes,
            'tamanho_fmt':   f"{a.tamanho_bytes / 1024:.0f} KB" if a.tamanho_bytes else '',
        } for a in c.anexos],
    }
    if incluir_historico:
        dados['historico'] = [{
            'id':              h.id,
            'tipo':            h.tipo,
            'status_anterior': h.status_anterior,
            'status_novo':     h.status_novo,
            'mensagem':        h.mensagem,
            'usuario':         h.usuario.nome if h.usuario else 'Sistema',
            'created_at':      h.created_at.strftime('%d/%m/%Y %H:%M') if h.created_at else '',
        } for h in c.historico]
    return dados


# ══════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════

@suporte_bp.route('/suporte')
def suporte():
    return render_template('suporte.html', modulos=MODULOS_HUB, setores=SETORES_CIAMED)


# ══════════════════════════════════════════════════════════════
# API — CHAMADOS (Usuário)
# ══════════════════════════════════════════════════════════════

@suporte_bp.route('/api/suporte/chamados', methods=['POST'])
def criar_chamado():
    """Cria um novo chamado com possíveis anexos (multipart/form-data)."""
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'status': 'erro', 'msg': 'Usuário não autenticado.'}), 401

        # Dados do formulário (multipart)
        modulo     = request.form.get('modulo', 'geral')
        prioridade = request.form.get('prioridade', 'media')
        assunto    = request.form.get('assunto', '').strip()
        mensagem   = request.form.get('mensagem', '').strip()

        if not assunto or not mensagem:
            return jsonify({'status': 'erro', 'msg': 'Assunto e descrição são obrigatórios.'}), 400

        # Valida prioridade
        if prioridade not in ('baixa', 'media', 'alta', 'critica'):
            prioridade = 'media'

        # Valida módulo
        if modulo not in MODULOS_HUB and modulo != 'geral':
            modulo = 'geral'

        # Gera protocolo
        protocolo = _gerar_protocolo()

        # Cria o chamado
        chamado = Chamado(
            protocolo=protocolo,
            usuario_id=usuario_id,
            modulo=modulo,
            prioridade=prioridade,
            assunto=assunto,
            mensagem=mensagem,
            status='pendente',
        )
        db.session.add(chamado)
        db.session.flush()  # pega o ID antes do commit

        # Histórico: criação
        hist = ChamadoHistorico(
            chamado_id=chamado.id,
            usuario_id=usuario_id,
            tipo='criacao',
            status_novo='pendente',
            mensagem='Chamado criado',
        )
        db.session.add(hist)

        # Processa anexos (se houver)
        arquivos = request.files.getlist('anexos')
        if len(arquivos) > MAX_ANEXOS:
            arquivos = arquivos[:MAX_ANEXOS]

        pasta_chamado = os.path.join(UPLOAD_DIR, protocolo)
        os.makedirs(pasta_chamado, exist_ok=True)

        for arq in arquivos:
            if arq and arq.filename and _extensao_ok(arq.filename):
                nome_seguro = secure_filename(arq.filename)
                caminho = os.path.join(pasta_chamado, nome_seguro)
                arq.save(caminho)

                tamanho = os.path.getsize(caminho)
                if tamanho > MAX_TAMANHO_BYTES:
                    os.remove(caminho)
                    continue

                anexo = ChamadoAnexo(
                    chamado_id=chamado.id,
                    nome_arquivo=nome_seguro,
                    caminho=caminho,
                    tipo_mime=arq.content_type,
                    tamanho_bytes=tamanho,
                )
                db.session.add(anexo)

        db.session.commit()

        logger.info(f"[SUPORTE] Chamado #{protocolo} criado por {session.get('usuario_nome')}")
        return jsonify({
            'status': 'ok',
            'protocolo': protocolo,
            'chamado_id': chamado.id,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"[SUPORTE] Erro ao criar chamado: {str(e)}")
        return jsonify({'status': 'erro', 'msg': 'Erro interno ao salvar chamado.'}), 500


@suporte_bp.route('/api/suporte/chamados', methods=['GET'])
def listar_meus_chamados():
    """Lista os chamados do usuário logado."""
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'status': 'erro', 'msg': 'Não autenticado.'}), 401

    chamados = (Chamado.query
                .filter_by(usuario_id=usuario_id)
                .order_by(Chamado.created_at.desc())
                .all())

    return jsonify({
        'chamados': [_serializar_chamado(c) for c in chamados],
        'stats': {
            'total':      len(chamados),
            'pendente':   sum(1 for c in chamados if c.status == 'pendente'),
            'em_analise': sum(1 for c in chamados if c.status == 'em_analise'),
            'resolvido':  sum(1 for c in chamados if c.status == 'resolvido'),
        },
    })


@suporte_bp.route('/api/suporte/chamados/<int:chamado_id>', methods=['GET'])
def detalhe_chamado(chamado_id):
    """Detalhe de um chamado com histórico completo."""
    usuario_id = session.get('usuario_id')
    chamado = Chamado.query.get(chamado_id)

    if not chamado:
        return jsonify({'status': 'erro', 'msg': 'Chamado não encontrado.'}), 404

    # Só o dono ou admin pode ver
    usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
    if chamado.usuario_id != usuario_id and (not usuario or not usuario.is_admin()):
        return jsonify({'status': 'erro', 'msg': 'Sem permissão.'}), 403

    return jsonify({
        'status': 'ok',
        'chamado': _serializar_chamado(chamado, incluir_historico=True),
    })


@suporte_bp.route('/api/suporte/chamados/<int:chamado_id>/cancelar', methods=['POST'])
def cancelar_chamado(chamado_id):
    """Usuário cancela um chamado (só se pendente)."""
    usuario_id = session.get('usuario_id')
    chamado = Chamado.query.get(chamado_id)

    if not chamado:
        return jsonify({'status': 'erro', 'msg': 'Chamado não encontrado.'}), 404
    if chamado.usuario_id != usuario_id:
        return jsonify({'status': 'erro', 'msg': 'Sem permissão.'}), 403
    if chamado.status != 'pendente':
        return jsonify({'status': 'erro', 'msg': 'Só é possível cancelar chamados pendentes.'}), 400

    status_anterior = chamado.status
    chamado.status = 'cancelado'

    hist = ChamadoHistorico(
        chamado_id=chamado.id,
        usuario_id=usuario_id,
        tipo='mudanca_status',
        status_anterior=status_anterior,
        status_novo='cancelado',
        mensagem='Chamado cancelado pelo solicitante',
    )
    db.session.add(hist)
    db.session.commit()

    logger.info(f"[SUPORTE] Chamado #{chamado.protocolo} cancelado por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# API — CHAMADOS (Admin)
# ══════════════════════════════════════════════════════════════

@suporte_bp.route('/api/suporte/admin/chamados', methods=['GET'])
@admin_required
def admin_listar_chamados():
    """Lista TODOS os chamados (admin)."""
    status_filtro = request.args.get('status')
    query = Chamado.query.order_by(Chamado.created_at.desc())

    if status_filtro and status_filtro != 'todos':
        query = query.filter_by(status=status_filtro)

    chamados = query.all()
    return jsonify({
        'chamados': [_serializar_chamado(c) for c in chamados],
        'stats': {
            'total':      Chamado.query.count(),
            'pendente':   Chamado.query.filter_by(status='pendente').count(),
            'em_analise': Chamado.query.filter_by(status='em_analise').count(),
            'resolvido':  Chamado.query.filter_by(status='resolvido').count(),
        },
    })


@suporte_bp.route('/api/suporte/admin/chamados/<int:chamado_id>/responder', methods=['POST'])
@admin_required
def admin_responder_chamado(chamado_id):
    """Admin responde a um chamado (texto + opcionalmente muda status)."""
    chamado = Chamado.query.get(chamado_id)
    if not chamado:
        return jsonify({'status': 'erro', 'msg': 'Chamado não encontrado.'}), 404

    dados = request.get_json()
    resposta    = (dados.get('resposta') or '').strip()
    novo_status = dados.get('status')

    if not resposta:
        return jsonify({'status': 'erro', 'msg': 'A resposta não pode ser vazia.'}), 400

    admin_id = session.get('usuario_id')

    # Registra a resposta no histórico
    hist = ChamadoHistorico(
        chamado_id=chamado.id,
        usuario_id=admin_id,
        tipo='resposta_admin',
        mensagem=resposta,
    )
    db.session.add(hist)

    # Muda status se solicitado
    if novo_status and novo_status != chamado.status:
        status_anterior = chamado.status
        chamado.status = novo_status

        hist_status = ChamadoHistorico(
            chamado_id=chamado.id,
            usuario_id=admin_id,
            tipo='mudanca_status',
            status_anterior=status_anterior,
            status_novo=novo_status,
        )
        db.session.add(hist_status)

    # Notifica o dono do chamado
    _criar_notificacao(
        usuario_id=chamado.usuario_id,
        chamado_id=chamado.id,
        tipo='resposta_admin',
        titulo=f'Nova resposta no chamado #{chamado.protocolo}',
    )

    db.session.commit()

    admin_nome = session.get('usuario_nome', 'Admin')
    logger.info(f"[SUPORTE] Admin {admin_nome} respondeu chamado #{chamado.protocolo}")
    return jsonify({'status': 'ok'})


@suporte_bp.route('/api/suporte/admin/chamados/<int:chamado_id>/status', methods=['POST'])
@admin_required
def admin_mudar_status(chamado_id):
    """Admin muda o status de um chamado."""
    chamado = Chamado.query.get(chamado_id)
    if not chamado:
        return jsonify({'status': 'erro', 'msg': 'Chamado não encontrado.'}), 404

    dados = request.get_json()
    novo_status = dados.get('status')

    if novo_status not in ('pendente', 'em_analise', 'resolvido', 'cancelado'):
        return jsonify({'status': 'erro', 'msg': 'Status inválido.'}), 400

    status_anterior = chamado.status
    if novo_status == status_anterior:
        return jsonify({'status': 'ok', 'msg': 'Status já é esse.'})

    chamado.status = novo_status

    admin_id = session.get('usuario_id')
    hist = ChamadoHistorico(
        chamado_id=chamado.id,
        usuario_id=admin_id,
        tipo='mudanca_status',
        status_anterior=status_anterior,
        status_novo=novo_status,
    )
    db.session.add(hist)

    # Monta texto da notificação
    status_labels = {
        'pendente': 'Pendente',
        'em_analise': 'Em Análise',
        'resolvido': 'Resolvido',
        'cancelado': 'Cancelado',
    }
    tipo_notif = 'chamado_resolvido' if novo_status == 'resolvido' else 'status_alterado'
    titulo_notif = f'Chamado #{chamado.protocolo} atualizado para {status_labels.get(novo_status, novo_status)}'

    _criar_notificacao(
        usuario_id=chamado.usuario_id,
        chamado_id=chamado.id,
        tipo=tipo_notif,
        titulo=titulo_notif,
    )

    db.session.commit()
    logger.info(f"[SUPORTE] Status #{chamado.protocolo}: {status_anterior} → {novo_status}")
    return jsonify({'status': 'ok'})


@suporte_bp.route('/api/suporte/admin/chamados/<int:chamado_id>', methods=['DELETE'])
@admin_required
def admin_excluir_chamado(chamado_id):
    """Admin exclui um chamado (e seus anexos/histórico via cascade)."""
    chamado = Chamado.query.get(chamado_id)
    if not chamado:
        return jsonify({'status': 'erro', 'msg': 'Chamado não encontrado.'}), 404

    protocolo = chamado.protocolo

    # Remove arquivos físicos
    pasta = os.path.join(UPLOAD_DIR, protocolo)
    if os.path.isdir(pasta):
        import shutil
        shutil.rmtree(pasta, ignore_errors=True)

    db.session.delete(chamado)
    db.session.commit()

    logger.info(f"[SUPORTE] Chamado #{protocolo} excluído por {session.get('usuario_nome')}")
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# API — FAQ
# ══════════════════════════════════════════════════════════════

@suporte_bp.route('/api/suporte/faq', methods=['GET'])
def listar_faq():
    """Lista todas as FAQs ativas, agrupadas por módulo."""
    perguntas = (FaqPergunta.query
                 .filter_by(ativo=True)
                 .order_by(FaqPergunta.modulo, FaqPergunta.ordem, FaqPergunta.id)
                 .all())

    # Agrupa por módulo
    grupos = {}
    for p in perguntas:
        if p.modulo not in grupos:
            mod_nome = MODULOS_HUB.get(p.modulo, 'Geral')
            grupos[p.modulo] = {
                'modulo':    p.modulo,
                'nome':      mod_nome,
                'perguntas': [],
            }
        grupos[p.modulo]['perguntas'].append({
            'id':       p.id,
            'pergunta': p.pergunta,
            'resposta': p.resposta,
            'ordem':    p.ordem,
        })

    return jsonify({'faq': list(grupos.values())})


@suporte_bp.route('/api/suporte/faq/busca', methods=['GET'])
def buscar_faq():
    """Busca no FAQ por termo."""
    termo = request.args.get('q', '').strip()
    if not termo or len(termo) < 2:
        return jsonify({'resultados': []})

    filtro = f"%{termo}%"
    perguntas = (FaqPergunta.query
                 .filter_by(ativo=True)
                 .filter(
                     db.or_(
                         FaqPergunta.pergunta.ilike(filtro),
                         FaqPergunta.resposta.ilike(filtro),
                     )
                 )
                 .order_by(FaqPergunta.modulo, FaqPergunta.ordem)
                 .all())

    return jsonify({
        'resultados': [{
            'id':       p.id,
            'modulo':   p.modulo,
            'modulo_nome': MODULOS_HUB.get(p.modulo, 'Geral'),
            'pergunta': p.pergunta,
            'resposta': p.resposta,
        } for p in perguntas],
    })


@suporte_bp.route('/api/suporte/faq', methods=['POST'])
@admin_required
def criar_faq():
    """Admin cria uma nova pergunta FAQ."""
    dados = request.get_json()
    pergunta = FaqPergunta(
        modulo=dados.get('modulo', 'geral'),
        pergunta=dados.get('pergunta', '').strip(),
        resposta=dados.get('resposta', '').strip(),
        ordem=dados.get('ordem', 0),
    )
    if not pergunta.pergunta or not pergunta.resposta:
        return jsonify({'status': 'erro', 'msg': 'Pergunta e resposta são obrigatórios.'}), 400

    db.session.add(pergunta)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': pergunta.id})


@suporte_bp.route('/api/suporte/faq/<int:faq_id>', methods=['PUT'])
@admin_required
def editar_faq(faq_id):
    """Admin edita uma pergunta FAQ."""
    pergunta = FaqPergunta.query.get(faq_id)
    if not pergunta:
        return jsonify({'status': 'erro', 'msg': 'FAQ não encontrada.'}), 404

    dados = request.get_json()
    if 'modulo'   in dados: pergunta.modulo   = dados['modulo']
    if 'pergunta' in dados: pergunta.pergunta = dados['pergunta'].strip()
    if 'resposta' in dados: pergunta.resposta = dados['resposta'].strip()
    if 'ordem'    in dados: pergunta.ordem    = dados['ordem']
    if 'ativo'    in dados: pergunta.ativo    = dados['ativo']

    db.session.commit()
    return jsonify({'status': 'ok'})


@suporte_bp.route('/api/suporte/faq/<int:faq_id>', methods=['DELETE'])
@admin_required
def excluir_faq(faq_id):
    """Admin exclui uma pergunta FAQ."""
    pergunta = FaqPergunta.query.get(faq_id)
    if not pergunta:
        return jsonify({'status': 'erro', 'msg': 'FAQ não encontrada.'}), 404

    db.session.delete(pergunta)
    db.session.commit()
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# API — NOTIFICAÇÕES
# ══════════════════════════════════════════════════════════════

@suporte_bp.route('/api/notificacoes', methods=['GET'])
def listar_notificacoes():
    """Lista notificações do usuário logado."""
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'notificacoes': []})

    notifs = (Notificacao.query
              .filter_by(usuario_id=usuario_id)
              .order_by(Notificacao.created_at.desc())
              .limit(20)
              .all())

    return jsonify({
        'notificacoes': [{
            'id':          n.id,
            'tipo':        n.tipo,
            'titulo':      n.titulo,
            'lida':        n.lida,
            'chamado_id':  n.chamado_id,
            'protocolo':   n.chamado.protocolo if n.chamado else None,
            'created_at':  n.created_at.strftime('%d/%m/%Y %H:%M') if n.created_at else '',
        } for n in notifs],
    })


@suporte_bp.route('/api/notificacoes/count', methods=['GET'])
def contar_notificacoes():
    """Contagem de notificações não-lidas (para o badge do sininho)."""
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'count': 0})

    count = Notificacao.query.filter_by(usuario_id=usuario_id, lida=False).count()
    return jsonify({'count': count})


@suporte_bp.route('/api/notificacoes/<int:notif_id>/lida', methods=['POST'])
def marcar_lida(notif_id):
    """Marca uma notificação como lida."""
    usuario_id = session.get('usuario_id')
    notif = Notificacao.query.get(notif_id)
    if notif and notif.usuario_id == usuario_id:
        notif.lida = True
        db.session.commit()
    return jsonify({'status': 'ok'})


@suporte_bp.route('/api/notificacoes/ler-todas', methods=['POST'])
def marcar_todas_lidas():
    """Marca todas as notificações do usuário como lidas."""
    usuario_id = session.get('usuario_id')
    if usuario_id:
        Notificacao.query.filter_by(usuario_id=usuario_id, lida=False).update({'lida': True})
        db.session.commit()
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# DOWNLOAD DE ANEXOS
# ══════════════════════════════════════════════════════════════

@suporte_bp.route('/api/suporte/anexos/<int:anexo_id>/download', methods=['GET'])
def download_anexo(anexo_id):
    """Baixa um anexo de chamado."""
    usuario_id = session.get('usuario_id')
    anexo = ChamadoAnexo.query.get(anexo_id)
    if not anexo:
        return jsonify({'status': 'erro', 'msg': 'Anexo não encontrado.'}), 404

    # Verifica permissão (dono ou admin)
    chamado = Chamado.query.get(anexo.chamado_id)
    usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
    if chamado.usuario_id != usuario_id and (not usuario or not usuario.is_admin()):
        return jsonify({'status': 'erro', 'msg': 'Sem permissão.'}), 403

    pasta = os.path.dirname(anexo.caminho)
    nome = os.path.basename(anexo.caminho)
    return send_from_directory(pasta, nome, as_attachment=True, download_name=anexo.nome_arquivo)