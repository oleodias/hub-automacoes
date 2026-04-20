# ══════════════════════════════════════════════════════════════
# routes/auth.py — Login e Logout
# ══════════════════════════════════════════════════════════════

import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import Usuario

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Tela de login do Hub.
    GET  → mostra o formulário
    POST → valida email/senha e cria a sessão
    """
    # Se já está logado, vai direto para a home
    if 'usuario_id' in session:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        # Busca o usuário pelo email
        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            logger.warning(f"Tentativa de login com email inexistente: {email}")
            return render_template('login.html', erro="Email ou senha incorretos.")

        if not usuario.ativo:
            logger.warning(f"Tentativa de login com conta desativada: {email}")
            return render_template('login.html', erro="Conta desativada. Fale com o administrador.")

        if not usuario.verificar_senha(senha):
            logger.warning(f"Senha incorreta para: {email}")
            return render_template('login.html', erro="Email ou senha incorretos.")

        # ── Login bem-sucedido ────────────────────────────────
        session.clear()
        session['usuario_id']   = usuario.id
        session['usuario_nome'] = usuario.nome
        session['usuario_cargo'] = usuario.cargo
        session.permanent = True  # Sessão dura até o timeout configurado

        logger.info(f"Login realizado: {usuario.nome} ({usuario.cargo})")

        # Redireciona para a página que tentou acessar antes (se houver)
        proximo = request.args.get('next', url_for('main.home'))
        return redirect(proximo)

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Encerra a sessão e redireciona para o login."""
    nome = session.get('usuario_nome', 'desconhecido')
    session.clear()
    logger.info(f"Logout realizado: {nome}")
    return redirect(url_for('auth.login'))
