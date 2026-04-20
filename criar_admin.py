# ══════════════════════════════════════════════════════════════
# criar_admin.py — Cria o primeiro usuário admin do Hub
# ══════════════════════════════════════════════════════════════
# Rode uma vez: python criar_admin.py
# Depois pode deletar este arquivo se quiser.
# ══════════════════════════════════════════════════════════════

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Importa o app para ter o contexto do Flask/SQLAlchemy
from app import app
from extensions import db
from models import Usuario, permissoes_padrao


def criar_admin():
    print("\n══════════════════════════════════════════")
    print("  Criar Usuário Administrador do Hub")
    print("══════════════════════════════════════════\n")

    nome  = input("Nome completo: ").strip()
    email = input("Email (usado para login): ").strip().lower()
    senha = input("Senha: ").strip()

    if not nome or not email or not senha:
        print("❌ Todos os campos são obrigatórios.")
        return

    with app.app_context():
        # Verifica se já existe
        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            print(f"⚠️ Já existe um usuário com o email {email}.")
            return

        # Cria o admin
        admin = Usuario(
            nome=nome,
            email=email,
            cargo='admin',
            permissoes=permissoes_padrao(),
            ativo=True,
        )
        admin.definir_senha(senha)

        db.session.add(admin)
        db.session.commit()

        print(f"\n✅ Admin criado com sucesso!")
        print(f"   Nome:  {admin.nome}")
        print(f"   Email: {admin.email}")
        print(f"   Cargo: {admin.cargo}")
        print(f"\nAgora rode 'python app.py' e faça login no Hub.")


if __name__ == '__main__':
    criar_admin()
