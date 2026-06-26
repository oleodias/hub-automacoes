# ══════════════════════════════════════════════════════════════
# utils/validacao.py — Validações reutilizáveis
# ══════════════════════════════════════════════════════════════
# Funções pequenas e sem dependência de Flask, usadas por várias
# rotas para validar entradas do usuário (senha, destino de redirect,
# identificadores etc.).
# ══════════════════════════════════════════════════════════════

import re
from urllib.parse import urlparse

# Política de senha: mínimo de 8 caracteres, com pelo menos 1 letra e 1 número.
SENHA_TAMANHO_MINIMO = 8


def validar_senha(senha):
    """
    Valida a força de uma senha.

    Regra: pelo menos 8 caracteres, contendo ao menos 1 letra e 1 número.

    Retorna (True, None) se válida, ou (False, mensagem) explicando o erro.
    """
    senha = senha or ''
    if len(senha) < SENHA_TAMANHO_MINIMO:
        return False, f"A senha deve ter pelo menos {SENHA_TAMANHO_MINIMO} caracteres."
    if not re.search(r'[A-Za-z]', senha):
        return False, "A senha deve conter pelo menos uma letra."
    if not re.search(r'\d', senha):
        return False, "A senha deve conter pelo menos um número."
    return True, None


# UUID v4 (formato gerado por uuid.uuid4()), usado nas pastas de uploads.
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE,
)


def eh_uuid_valido(valor):
    """Retorna True se o valor for um UUID v4 bem-formado."""
    return bool(valor) and bool(_UUID_RE.match(valor))


def eh_destino_seguro(destino):
    """
    Retorna True se 'destino' for um caminho INTERNO seguro para redirect.

    Aceita apenas caminhos relativos ao próprio site (ex.: '/clientes').
    Rejeita URLs absolutas, com host/esquema (http://..., //evil.com) e
    qualquer coisa que possa levar o usuário para fora do Hub (open redirect).
    """
    if not destino:
        return False
    # Precisa começar com uma única barra (caminho interno)...
    if not destino.startswith('/') or destino.startswith('//'):
        return False
    # ...e não pode embutir esquema (http:) nem netloc (host).
    partes = urlparse(destino)
    if partes.scheme or partes.netloc:
        return False
    return True
