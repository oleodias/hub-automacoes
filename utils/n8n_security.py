# ══════════════════════════════════════════════════════════════
# utils/n8n_security.py — Proteções da comunicação Hub ↔ N8N
# ══════════════════════════════════════════════════════════════
# Por enquanto contém o "porteiro de URLs" contra SSRF (V-04).
#
# SSRF, em palavras simples: o Hub recebe de fora uma URL (resume_url)
# e "visita" ela pra avisar o N8N que pode continuar. Se um atacante
# mandar uma URL apontando pra DENTRO da rede (roteador, banco interno,
# etc.), o Hub viraria uma "ponte" pra atacar a rede interna.
#
# Defesa: só visitar URLs cujo host seja o do N8N OFICIAL — a lista de
# hosts permitidos é derivada do próprio .env (os webhooks do N8N).
# ══════════════════════════════════════════════════════════════

import os
import hmac
import logging
from functools import wraps
from urllib.parse import urlparse

from flask import request, jsonify

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# AUTENTICAÇÃO DOS WEBHOOKS DO N8N (V-03) — "crachá secreto"
# ══════════════════════════════════════════════════════════════
# Os endpoints que SÓ o N8N chama exigem um header X-Hub-Token com
# um segredo compartilhado (variável N8N_HUB_TOKEN no .env).
#
# Trava contra quebra: se N8N_HUB_TOKEN não estiver configurado, a
# proteção fica DESLIGADA (apenas registra aviso no log). Assim o Hub
# continua funcionando até você criar o segredo nos dois lados.
# ══════════════════════════════════════════════════════════════

HEADER_TOKEN = 'X-Hub-Token'


def exigir_token_n8n(view):
    """Decorator: exige o header X-Hub-Token correto (se o segredo existir)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        token_esperado = os.getenv('N8N_HUB_TOKEN', '').strip()

        if not token_esperado:
            logger.warning(
                "[AUTH N8N] N8N_HUB_TOKEN não configurado — endpoint %s está DESPROTEGIDO. "
                "Crie o segredo no .env (e no N8N) para ligar a proteção.",
                request.path
            )
            return view(*args, **kwargs)

        recebido = request.headers.get(HEADER_TOKEN, '')
        # compare_digest evita 'timing attack' (descobrir o token pelo tempo de resposta).
        if not recebido or not hmac.compare_digest(recebido, token_esperado):
            logger.warning(
                "[AUTH N8N] Token inválido/ausente em %s (IP %s) — recusado.",
                request.path, request.remote_addr
            )
            return jsonify({'erro': 'não autorizado'}), 401

        return view(*args, **kwargs)

    return wrapper


def _netloc(url):
    """Extrai 'host:porta' de uma URL http(s). Retorna None se inválida."""
    try:
        p = urlparse((url or '').strip())
    except Exception:
        return None
    if p.scheme not in ('http', 'https') or not p.netloc:
        return None
    return p.netloc.lower()


def hosts_permitidos():
    """
    Monta o conjunto de 'host:porta' confiáveis a partir do .env.
    Deriva dos webhooks oficiais do N8N (mesmo host da resume_url) e,
    opcionalmente, de N8N_RESUME_HOSTS (lista extra separada por vírgula).
    """
    hosts = set()
    for var in ('N8N_WEBHOOK_CADASTRO', 'N8N_WEBHOOK_REPROCESSAR', 'N8N_BASE_URL'):
        nl = _netloc(os.getenv(var, ''))
        if nl:
            hosts.add(nl)

    extra = os.getenv('N8N_RESUME_HOSTS', '')
    for item in extra.split(','):
        item = item.strip().lower()
        if item:
            hosts.add(item)

    return hosts


def resume_url_confiavel(url):
    """
    True se a URL aponta para o N8N oficial (mesmo host dos webhooks).
    Falha "fechado": se não houver host configurado ou a URL for estranha,
    retorna False (recusa por segurança).
    """
    nl = _netloc(url)
    if not nl:
        logger.warning("[SSRF] resume_url ausente ou em formato inválido — recusada.")
        return False

    permitidos = hosts_permitidos()
    if not permitidos:
        logger.error(
            "[SSRF] Nenhum host do N8N configurado no .env "
            "(N8N_WEBHOOK_CADASTRO / N8N_RESUME_HOSTS). Recusando resume_url por segurança."
        )
        return False

    if nl in permitidos:
        return True

    logger.warning(
        "[SSRF] resume_url recusada: host '%s' não está na lista de hosts do N8N %s.",
        nl, sorted(permitidos)
    )
    return False
