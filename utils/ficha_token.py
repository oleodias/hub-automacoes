# ══════════════════════════════════════════════════════════════
# utils/ficha_token.py — Token assinado do link da ficha (V-05)
# ══════════════════════════════════════════════════════════════
# O link da ficha de cadastro é público (vendedores externos preenchem).
# Para evitar que qualquer um abra/envie uma ficha à toa, o link passa a
# carregar um "selo" assinado pelo Hub, com prazo de validade.
#
# Usamos itsdangerous (já vem com o Flask) para assinar os dados com a
# FLASK_SECRET_KEY. Ninguém consegue forjar um token sem a chave, e o
# próprio token guarda o instante de criação — então a validade é
# verificada na hora de abrir (max_age).
# ══════════════════════════════════════════════════════════════

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# Identifica este uso específico da chave (boa prática do itsdangerous).
_SALT = 'ficha-link-v1'

# Validade do link: 7 dias.
VALIDADE_SEGUNDOS = 7 * 24 * 60 * 60


def _serializer():
    # Criado sob demanda para usar a secret_key já carregada no app.
    return URLSafeTimedSerializer(current_app.secret_key, salt=_SALT)


def gerar_token_ficha(dados):
    """Assina um dict de dados (vendedor, rep, cap, tipo, codigo_nl) e
    devolve o token em texto, pronto para entrar na URL (?t=...)."""
    return _serializer().dumps(dados)


def validar_token_ficha(token):
    """
    Valida o token do link da ficha.

    Retorna (dados, None) se válido, ou (None, motivo) caso contrário,
    onde motivo ∈ {'ausente', 'expirado', 'invalido'}.
    """
    if not token:
        return None, 'ausente'
    try:
        dados = _serializer().loads(token, max_age=VALIDADE_SEGUNDOS)
        return dados, None
    except SignatureExpired:
        return None, 'expirado'
    except BadSignature:
        return None, 'invalido'
