# ══════════════════════════════════════════════════════════════
# utils/auth.py — Decoradores de Autenticação e Permissão
# ══════════════════════════════════════════════════════════════
# Decoradores são "protetores" que você coloca antes de uma rota.
# Se a pessoa não atende o requisito, ela é redirecionada para o login.
#
# Uso:
#   @login_required          → precisa estar logado
#   @admin_required          → precisa ser admin
#   @permissao_required('mdf')  → precisa ter permissão no módulo 'mdf'
# ══════════════════════════════════════════════════════════════

import logging
from functools import wraps
from flask import session, redirect, url_for, flash, request
from models import Usuario

logger = logging.getLogger(__name__)


def get_usuario_logado():
    """
    Retorna o objeto Usuario do banco a partir da sessão.
    Retorna None se não houver ninguém logado.
    """
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return None
    return Usuario.query.get(usuario_id)


def login_required(f):
    """
    Decorador: a rota só funciona se houver um usuário logado.
    Se não houver, redireciona para a tela de login.

    Uso:
        @app.route('/minha_rota')
        @login_required
        def minha_rota():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login', next=request.path))
        # Verifica se o usuário ainda existe e está ativo
        usuario = get_usuario_logado()
        if not usuario or not usuario.ativo:
            session.clear()
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorador: a rota só funciona se o usuário logado for admin.
    Se não for, redireciona para a home.

    Uso:
        @app.route('/admin/usuarios')
        @login_required
        @admin_required
        def gerenciar_usuarios():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = get_usuario_logado()
        if not usuario or not usuario.is_admin():
            logger.warning(f"Acesso admin negado para usuario_id={session.get('usuario_id')}")
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def permissao_required(modulo):
    """
    Decorador: a rota só funciona se o usuário tiver permissão
    no módulo especificado. Admin sempre passa.

    Uso:
        @app.route('/relatorio_mdf')
        @login_required
        @permissao_required('mdf')
        def relatorio_mdf():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario = get_usuario_logado()
            if not usuario or not usuario.tem_permissao(modulo):
                logger.warning(
                    f"Permissão '{modulo}' negada para {usuario.nome if usuario else 'desconhecido'}"
                )
                return redirect(url_for('main.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
