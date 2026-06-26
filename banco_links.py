# ══════════════════════════════════════════════════════════════
# banco_links.py — Operações dos Links de Ficha gerados
# ══════════════════════════════════════════════════════════════
# Camada única que toca a tabela links_ficha. O link deixou de ser um
# "selo solto" e passou a ter registro no banco, para dar controle e
# rastreabilidade: quem gerou, para qual cliente, quando, validade e uso.
# ══════════════════════════════════════════════════════════════

import logging
import secrets
from datetime import datetime, timedelta
from extensions import db
from models import LinkFicha

logger = logging.getLogger(__name__)

# Validade do link após gerado.
VALIDADE_DIAS = 7


def _status(link):
    """Status derivado do link: 'usado' | 'expirado' | 'ativo'."""
    if link.usado_em:
        return 'usado'
    if datetime.now() > link.expira_em:
        return 'expirado'
    return 'ativo'


def _to_dict(link):
    return {
        'id':              link.id,
        'token':           link.token,
        'cnpj_cliente':    link.cnpj_cliente,
        'gerado_por_id':   link.gerado_por_id,
        'gerado_por_nome': link.gerado_por_nome,
        'vendedor':        link.vendedor,
        'representante':   link.representante,
        'captacao':        link.captacao,
        'tipo':            link.tipo,
        'codigo_nl':       link.codigo_nl,
        'status':          _status(link),
        'cnpj_divergente': bool(link.cnpj_divergente),
        'submission_uuid': link.submission_uuid,
        'created_at':      link.created_at.strftime('%d/%m/%Y %H:%M') if link.created_at else '',
        'expira_em':       link.expira_em.strftime('%d/%m/%Y %H:%M') if link.expira_em else '',
        'usado_em':        link.usado_em.strftime('%d/%m/%Y %H:%M') if link.usado_em else '',
    }


def criar_link(cnpj_cliente, vendedor, representante, captacao, tipo,
               codigo_nl, gerado_por_id, gerado_por_nome):
    """Cria o registro do link e devolve o token (segredo da URL)."""
    token = secrets.token_urlsafe(24)
    link = LinkFicha(
        token=token,
        cnpj_cliente=cnpj_cliente,
        vendedor=vendedor,
        representante=representante,
        captacao=captacao,
        tipo=tipo,
        codigo_nl=codigo_nl,
        gerado_por_id=gerado_por_id,
        gerado_por_nome=gerado_por_nome,
        expira_em=datetime.now() + timedelta(days=VALIDADE_DIAS),
    )
    db.session.add(link)
    db.session.commit()
    logger.info(
        f"[LINK] Gerado | por {gerado_por_nome} | CNPJ {cnpj_cliente} | "
        f"vendedor {vendedor} | tipo {tipo}"
    )
    return token


def buscar_link(token):
    """Retorna o objeto LinkFicha pelo token, ou None."""
    if not token:
        return None
    return LinkFicha.query.filter_by(token=token).first()


def validar_link(token):
    """
    Valida um token de link.

    Retorna (link, None) se utilizável, ou (None, motivo) onde
    motivo ∈ {'ausente', 'invalido', 'expirado', 'usado'}.
    """
    if not token:
        return None, 'ausente'
    link = buscar_link(token)
    if not link:
        return None, 'invalido'
    if link.usado_em:
        return None, 'usado'
    if datetime.now() > link.expira_em:
        return None, 'expirado'
    return link, None


def marcar_usado(token, submission_uuid, cnpj_divergente):
    """Marca o link como usado, vinculando a submissão criada."""
    link = buscar_link(token)
    if not link:
        return False
    link.usado_em = datetime.now()
    link.submission_uuid = submission_uuid
    link.cnpj_divergente = bool(cnpj_divergente)
    db.session.commit()
    return True


def excluir_link(link_id):
    """Exclui um link gerado pelo seu id. Retorna True se existia."""
    link = db.session.get(LinkFicha, link_id)
    if not link:
        return False
    cnpj = link.cnpj_cliente
    db.session.delete(link)
    db.session.commit()
    logger.info(f"[LINK] Excluido | id {link_id} | CNPJ {cnpj}")
    return True


def listar_links(busca=None, status=None, data_de=None, data_ate=None):
    """Lista os links gerados (mais recentes primeiro) com filtros opcionais."""
    query = LinkFicha.query.order_by(LinkFicha.created_at.desc())

    if busca:
        termo = f'%{busca}%'
        query = query.filter(
            db.or_(
                LinkFicha.cnpj_cliente.ilike(termo),
                LinkFicha.vendedor.ilike(termo),
                LinkFicha.gerado_por_nome.ilike(termo),
                LinkFicha.representante.ilike(termo),
            )
        )

    if data_de:
        try:
            dt = datetime.strptime(data_de, '%d/%m/%Y') if '/' in data_de else datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(LinkFicha.created_at >= dt)
        except ValueError:
            pass

    if data_ate:
        try:
            dt = datetime.strptime(data_ate, '%d/%m/%Y') if '/' in data_ate else datetime.strptime(data_ate, '%Y-%m-%d')
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(LinkFicha.created_at <= dt)
        except ValueError:
            pass

    # Status é derivado (depende da hora atual), então filtramos em Python.
    resultado = [_to_dict(l) for l in query.all()]
    if status:
        resultado = [r for r in resultado if r['status'] == status]
    return resultado


def estatisticas():
    """Contagens para o painel da página de Links Gerados."""
    todos = LinkFicha.query.all()
    stats = {'total': len(todos), 'ativo': 0, 'usado': 0, 'expirado': 0, 'divergentes': 0}
    for l in todos:
        stats[_status(l)] += 1
        if l.cnpj_divergente:
            stats['divergentes'] += 1
    return stats
