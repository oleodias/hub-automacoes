# ══════════════════════════════════════════════════════════════
# utils/fila.py — Sistema de Fila para os Robôs RPA
# ══════════════════════════════════════════════════════════════
# Controla a execução sequencial dos robôs. Quando dois usuários
# disparam o mesmo robô ao mesmo tempo, o segundo espera o
# primeiro terminar. Evita conflito no ERP.
#
# Existem DUAS filas independentes:
#   1. Fila genérica  → usada pelos robôs de itens, MDF, fornecedor
#   2. Fila de cadastro → usada pelo fluxo N8N de cadastro de clientes
# ══════════════════════════════════════════════════════════════

import threading
import time as time_module
import uuid as uuid_lib
import requests as req_ext

import logging
logger = logging.getLogger(__name__)


# ── FILA GENÉRICA (itens, MDF, fornecedor) ────────────────────

_lock_execucao = threading.Lock()
_fila = []
_em_execucao = None


def _gerar_id():
    return f"{int(time_module.time() * 1000)}"


def entrar_na_fila():
    global _fila
    with _lock_execucao:
        meu_id = _gerar_id()
        _fila.append(meu_id)
        return meu_id


def minha_vez(meu_id):
    global _em_execucao, _fila
    with _lock_execucao:
        if _em_execucao is not None:
            return False
        return bool(_fila and _fila[0] == meu_id)


def iniciar_execucao(meu_id):
    global _em_execucao, _fila
    with _lock_execucao:
        _em_execucao = meu_id
        if meu_id in _fila:
            _fila.remove(meu_id)


def finalizar_execucao():
    global _em_execucao
    with _lock_execucao:
        _em_execucao = None


def sair_da_fila(meu_id):
    global _fila
    with _lock_execucao:
        if meu_id in _fila:
            _fila.remove(meu_id)


def posicao_na_fila(meu_id):
    global _fila, _em_execucao
    with _lock_execucao:
        if _em_execucao == meu_id:
            return 0
        if meu_id in _fila:
            return _fila.index(meu_id) + 1
        return -1


# ── FILA DE CADASTRO (controle via N8N) ───────────────────────

_fila_cadastro = []
_fila_cadastro_lock = threading.Lock()
_cadastro_em_execucao = False


def cadastro_entrar(resume_url):
    """Adiciona uma execução na fila de cadastro. Retorna (id, posicao, sua_vez)."""
    global _cadastro_em_execucao

    novo_id = str(uuid_lib.uuid4())[:8]

    with _fila_cadastro_lock:
        _fila_cadastro.append({
            'id':         novo_id,
            'resume_url': resume_url
        })
        posicao = len(_fila_cadastro)
        sua_vez = posicao == 1 and not _cadastro_em_execucao

    logger.info(f"[FILA] Entrada | ID: {novo_id} | Posição: {posicao}")

    if sua_vez:
        _liberar_proximo_cadastro()

    return novo_id, posicao, sua_vez


def cadastro_liberar_proximo():
    """Remove o atual da fila e acorda o próximo Wait node do N8N."""
    global _cadastro_em_execucao

    with _fila_cadastro_lock:
        if _fila_cadastro:
            concluido = _fila_cadastro.pop(0)
            logger.info(f"[FILA] Concluído | ID: {concluido['id']}")
        _cadastro_em_execucao = False

    _liberar_proximo_cadastro()


def _liberar_proximo_cadastro():
    """Função interna: acorda o próximo Wait node do N8N."""
    global _cadastro_em_execucao

    with _fila_cadastro_lock:
        if not _fila_cadastro or _cadastro_em_execucao:
            return
        proximo = _fila_cadastro[0]
        _cadastro_em_execucao = True

    logger.info(f"[FILA] Liberando | ID: {proximo['id']}")

    def chamar_n8n():
        try:
            # Espera 3 segundos para o n8n ter tempo de chegar no Wait node.
            # Sem esse delay, o Flask tenta acordar o Wait ANTES dele começar
            # a escutar (race condition entre o response do HTTP e o início do Wait).
            time_module.sleep(3)
            req_ext.get(proximo['resume_url'], timeout=10)
            logger.info(f"[FILA] N8N acordado | ID: {proximo['id']}")
        except Exception as e:
            logger.error(f"[FILA] Erro ao acordar N8N: {e}")

    threading.Thread(target=chamar_n8n, daemon=True).start()
