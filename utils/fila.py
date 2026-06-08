# ══════════════════════════════════════════════════════════════
# utils/fila.py — Fila de execução dos robôs (PERSISTENTE no Postgres)
# ══════════════════════════════════════════════════════════════
# Garante "um robô por vez". Antes a fila vivia na memória de UM
# processo (quebrava com vários workers/containers — item A-01).
# Agora a fila vive no banco (tabela fila_execucao), então TODOS os
# workers enxergam a mesma fila.
#
# Há duas filas, separadas pela coluna 'recurso':
#   - 'rpa'      → robôs de itens / MDF / fornecedor
#   - 'cadastro' → fluxo de cadastro de clientes (N8N)
#
# "Pegar a vez" é ATÔMICO (item A-02): usamos uma trava de transação
# do Postgres (pg_advisory_xact_lock) por recurso, então dois workers
# nunca assumem ao mesmo tempo.
#
# WATCHDOG (item A-03): se um robô travar (N8N caiu, ERP congelou) e
# nunca finalizar, a execução é considerada "presa" depois de
# FILA_TIMEOUT_MIN minutos e liberada automaticamente.
# ══════════════════════════════════════════════════════════════

import os
import threading
import time as time_module
import uuid as uuid_lib
from datetime import datetime, timedelta

import requests as req_ext
from sqlalchemy import create_engine, text

import logging
logger = logging.getLogger(__name__)

from utils.n8n_security import resume_url_confiavel


RECURSO_RPA      = 'rpa'
RECURSO_CADASTRO = 'cadastro'


def _timeout_min():
    """Minutos até considerar uma execução 'travada' (ajustável no .env)."""
    try:
        return int(os.getenv('FILA_TIMEOUT_MIN', '15'))
    except (TypeError, ValueError):
        return 15


# ── Engine próprio (independente do contexto Flask) ───────────
# A fila roda dentro de geradores SSE e de threads (acordar o N8N),
# fora do contexto de request do Flask. Por isso usamos um engine
# próprio em vez de db.session, que exige contexto de app.

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                url = os.getenv('DATABASE_URL')
                if not url:
                    raise RuntimeError("DATABASE_URL não definida — a fila precisa do banco.")
                _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


def _expirar_travadas(conn, recurso):
    """Watchdog: remove execuções 'executando' paradas além do tempo-limite."""
    limite = datetime.now() - timedelta(minutes=_timeout_min())
    res = conn.execute(text("""
        DELETE FROM fila_execucao
        WHERE recurso = :r AND status = 'executando' AND iniciado_em < :limite
    """), {"r": recurso, "limite": limite})
    if res.rowcount:
        logger.warning(
            "[FILA] Watchdog liberou %s execução(ões) travada(s) no recurso '%s'.",
            res.rowcount, recurso
        )


def _recurso_do_token(token):
    with _get_engine().connect() as conn:
        return conn.execute(
            text("SELECT recurso FROM fila_execucao WHERE token = :t"),
            {"t": token}
        ).scalar()


# ══════════════════════════════════════════════════════════════
# FILA GENÉRICA (itens, MDF, fornecedor) — recurso 'rpa'
# ══════════════════════════════════════════════════════════════

def entrar_na_fila(recurso=RECURSO_RPA):
    """Entra na fila e retorna um token (id) para acompanhar a vez."""
    token = uuid_lib.uuid4().hex
    with _get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO fila_execucao (token, recurso, status, criado_em)
            VALUES (:t, :r, 'aguardando', :agora)
        """), {"t": token, "r": recurso, "agora": datetime.now()})
    return token


def _tentar_assumir(token):
    """
    ATÔMICO: se for a vez deste token (mais antigo aguardando e nenhum
    executando no recurso), marca como 'executando' e retorna True.
    """
    recurso = _recurso_do_token(token)
    if recurso is None:
        return False

    with _get_engine().begin() as conn:
        # Serializa a disputa por este recurso entre todos os workers.
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:r))"), {"r": recurso})
        _expirar_travadas(conn, recurso)

        atual = conn.execute(
            text("SELECT status FROM fila_execucao WHERE token = :t"), {"t": token}
        ).scalar()
        if atual is None:
            return False
        if atual == 'executando':
            return True

        ja_executando = conn.execute(text("""
            SELECT 1 FROM fila_execucao
            WHERE recurso = :r AND status = 'executando' LIMIT 1
        """), {"r": recurso}).first()
        if ja_executando:
            return False

        mais_antigo = conn.execute(text("""
            SELECT token FROM fila_execucao
            WHERE recurso = :r AND status = 'aguardando'
            ORDER BY id LIMIT 1
        """), {"r": recurso}).scalar()

        if mais_antigo == token:
            conn.execute(text("""
                UPDATE fila_execucao
                SET status = 'executando', iniciado_em = :agora
                WHERE token = :t
            """), {"t": token, "agora": datetime.now()})
            return True

    return False


def minha_vez(token):
    """True quando chega a vez deste token (e já assume a execução)."""
    return _tentar_assumir(token)


def iniciar_execucao(token):
    """
    Confirma que este token está executando (idempotente). Mantido por
    compatibilidade com os consumidores; a 'tomada de vez' já acontece
    em minha_vez(). Atualiza o iniciado_em como 'heartbeat'.
    """
    return _tentar_assumir(token)


def finalizar_execucao(token=None, recurso=RECURSO_RPA):
    """Encerra a execução atual, liberando a vez para o próximo da fila."""
    with _get_engine().begin() as conn:
        if token:
            conn.execute(text("DELETE FROM fila_execucao WHERE token = :t"), {"t": token})
        else:
            conn.execute(text("""
                DELETE FROM fila_execucao
                WHERE recurso = :r AND status = 'executando'
            """), {"r": recurso})


def sair_da_fila(token):
    """Remove o token da fila (desistência / timeout no front)."""
    with _get_engine().begin() as conn:
        conn.execute(text("DELETE FROM fila_execucao WHERE token = :t"), {"t": token})


def posicao_na_fila(token):
    """0 = executando, 1.. = posição na espera, -1 = não está na fila."""
    recurso = _recurso_do_token(token)
    if recurso is None:
        return -1
    with _get_engine().connect() as conn:
        info = conn.execute(
            text("SELECT id, status FROM fila_execucao WHERE token = :t"), {"t": token}
        ).first()
        if info is None:
            return -1
        if info.status == 'executando':
            return 0
        # Posição = quantos itens há na frente (inclui quem está executando)
        # + ele mesmo. Itens já finalizados são removidos da tabela.
        return conn.execute(text("""
            SELECT COUNT(*) FROM fila_execucao
            WHERE recurso = :r AND id <= :id
        """), {"r": recurso, "id": info.id}).scalar()


def recurso_em_execucao(recurso=RECURSO_RPA):
    """True se há algum robô executando neste recurso (após o watchdog)."""
    with _get_engine().begin() as conn:
        _expirar_travadas(conn, recurso)
        return conn.execute(text("""
            SELECT 1 FROM fila_execucao
            WHERE recurso = :r AND status = 'executando' LIMIT 1
        """), {"r": recurso}).first() is not None


# ══════════════════════════════════════════════════════════════
# FILA DE CADASTRO (controle via N8N) — recurso 'cadastro'
# ══════════════════════════════════════════════════════════════

def cadastro_entrar(resume_url):
    """Adiciona uma execução na fila de cadastro. Retorna (token, posicao, sua_vez)."""
    token = uuid_lib.uuid4().hex
    with _get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO fila_execucao (token, recurso, status, resume_url, criado_em)
            VALUES (:t, :r, 'aguardando', :url, :agora)
        """), {"t": token, "r": RECURSO_CADASTRO, "url": resume_url, "agora": datetime.now()})

    posicao = posicao_na_fila(token)
    logger.info(f"[FILA] Entrada cadastro | token: {token[:8]} | Posição: {posicao}")

    assumido = _liberar_proximo_cadastro()
    sua_vez = bool(assumido and assumido['token'] == token)
    return token, posicao, sua_vez


def cadastro_liberar_proximo():
    """Remove o atual da fila de cadastro e acorda o próximo Wait node do N8N."""
    with _get_engine().begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:r))"), {"r": RECURSO_CADASTRO})
        res = conn.execute(text("""
            DELETE FROM fila_execucao
            WHERE recurso = :r AND status = 'executando'
        """), {"r": RECURSO_CADASTRO})
        if res.rowcount:
            logger.info("[FILA] Cadastro concluído | liberando próximo.")
    _liberar_proximo_cadastro()


def _liberar_proximo_cadastro():
    """
    ATÔMICO: se ninguém está executando, assume o próximo da fila de
    cadastro e dispara (em thread) a chamada que acorda o N8N.
    Retorna o item assumido (dict) ou None.
    """
    with _get_engine().begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:r))"), {"r": RECURSO_CADASTRO})
        _expirar_travadas(conn, RECURSO_CADASTRO)

        if conn.execute(text("""
            SELECT 1 FROM fila_execucao
            WHERE recurso = :r AND status = 'executando' LIMIT 1
        """), {"r": RECURSO_CADASTRO}).first():
            return None

        proximo = conn.execute(text("""
            SELECT id, token, resume_url FROM fila_execucao
            WHERE recurso = :r AND status = 'aguardando'
            ORDER BY id LIMIT 1
        """), {"r": RECURSO_CADASTRO}).first()
        if proximo is None:
            return None

        conn.execute(text("""
            UPDATE fila_execucao
            SET status = 'executando', iniciado_em = :agora
            WHERE id = :id
        """), {"id": proximo.id, "agora": datetime.now()})

        assumido = {"token": proximo.token, "resume_url": proximo.resume_url}

    logger.info(f"[FILA] Liberando cadastro | token: {assumido['token'][:8]}")
    threading.Thread(
        target=_acordar_n8n,
        args=(assumido['token'], assumido['resume_url']),
        daemon=True
    ).start()
    return assumido


def _acordar_n8n(token, resume_url):
    """Acorda o Wait node do N8N (com defesa anti-SSRF, item V-04)."""
    try:
        if not resume_url_confiavel(resume_url):
            logger.error(f"[FILA] resume_url recusada (anti-SSRF) | token: {token[:8]}")
            return
        # Espera 3s para o N8N chegar no Wait node antes de acordá-lo
        # (evita corrida entre a resposta HTTP e o início do Wait).
        time_module.sleep(3)
        req_ext.get(resume_url, timeout=10)
        logger.info(f"[FILA] N8N acordado | token: {token[:8]}")
    except Exception as e:
        logger.error(f"[FILA] Erro ao acordar N8N: {e}")


def fila_cadastro_status_dict():
    """Estado atual da fila de cadastro — usado no endpoint de status/debug."""
    with _get_engine().begin() as conn:
        _expirar_travadas(conn, RECURSO_CADASTRO)
        em_exec = conn.execute(text("""
            SELECT 1 FROM fila_execucao
            WHERE recurso = :r AND status = 'executando' LIMIT 1
        """), {"r": RECURSO_CADASTRO}).first() is not None
        pendentes = conn.execute(text("""
            SELECT token, resume_url FROM fila_execucao
            WHERE recurso = :r AND status = 'aguardando'
            ORDER BY id
        """), {"r": RECURSO_CADASTRO}).fetchall()

    return {
        "em_execucao": em_exec,
        "tamanho_fila": len(pendentes),
        "itens": [
            {"id": row.token, "resume_url": (row.resume_url or "")[:80] + "..."}
            for row in pendentes
        ],
    }


def fila_cadastro_reset():
    """Destrava a fila de cadastro à força. Retorna a quantidade removida."""
    with _get_engine().begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:r))"), {"r": RECURSO_CADASTRO})
        qtd = conn.execute(text("""
            SELECT COUNT(*) FROM fila_execucao WHERE recurso = :r
        """), {"r": RECURSO_CADASTRO}).scalar()
        conn.execute(text("DELETE FROM fila_execucao WHERE recurso = :r"), {"r": RECURSO_CADASTRO})
    logger.warning(f"[FILA] ⚠️ RESET forçado da fila de cadastro! {qtd} item(ns) removido(s).")
    return qtd
