# ══════════════════════════════════════════════════════════════
# models.py — Modelos do Banco de Dados (SQLAlchemy)
# ══════════════════════════════════════════════════════════════
# Cada classe aqui representa uma TABELA no PostgreSQL.
# Cada atributo da classe representa uma COLUNA na tabela.
# ══════════════════════════════════════════════════════════════

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ── MÓDULOS DO HUB (lista central de permissões) ─────────────
# Usada para gerar o JSON de permissões padrão e para o painel admin.
# Se um dia criar um módulo novo, basta adicionar aqui.

MODULOS_HUB = {
    'itens':       'Cadastro de Itens',
    'mdf':         'Relatório MDF-e',
    'fornecedor':  'Cadastro de Fornecedor',
    'clientes':    'Cadastro de Clientes',
    'cnpj':        'Consulta CNPJ',
    'monitor':     'Monitor de Cadastros',
}


def permissoes_padrao():
    """Retorna dict com todos os módulos liberados (padrão para novos usuários)."""
    return {modulo: True for modulo in MODULOS_HUB}


# ══════════════════════════════════════════════════════════════
# MODELO: Usuário
# ══════════════════════════════════════════════════════════════

class Usuario(db.Model):
    """
    Representa um usuário do Hub de Automações.

    Cargos:
        'admin'    → acesso total, gerencia usuários e permissões
        'operador' → acesso controlado por módulo (campo permissoes)

    Permissões:
        JSON com cada módulo como chave e true/false como valor.
        Ex: {"itens": true, "mdf": true, "fornecedor": false, ...}
        Quando cargo = 'admin', as permissões são ignoradas (tudo liberado).
    """

    __tablename__ = 'usuarios'

    # Identificador único auto-incrementado
    id = db.Column(db.Integer, primary_key=True)

    # Nome completo do usuário
    nome = db.Column(db.String(150), nullable=False)

    # Email (usado para login) — único, não pode repetir
    email = db.Column(db.String(150), unique=True, nullable=False)

    # Senha hasheada (criptografada de forma irreversível)
    # Nunca armazenamos a senha em texto. O hash é gerado pelo
    # werkzeug.security e não pode ser "desfeito" — só comparado.
    senha_hash = db.Column(db.String(256), nullable=False)

    # Cargo: 'admin' ou 'operador'
    cargo = db.Column(db.String(20), default='operador')

    # Permissões por módulo (JSON)
    # Exemplo: {"itens": true, "mdf": true, "fornecedor": false}
    permissoes = db.Column(db.JSON, default=permissoes_padrao)

    # Conta ativa ou desativada (desativar sem deletar)
    ativo = db.Column(db.Boolean, default=True)

    # Datas
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # ── Métodos de senha ──────────────────────────────────────

    def definir_senha(self, senha_texto):
        """
        Recebe a senha em texto puro e salva o HASH.
        A senha original nunca é armazenada.
        Exemplo: "minhasenha123" → "pbkdf2:sha256:260000$..."
        """
        self.senha_hash = generate_password_hash(senha_texto)

    def verificar_senha(self, senha_texto):
        """
        Compara a senha digitada no login com o hash salvo.
        Retorna True se bater, False se não.
        """
        return check_password_hash(self.senha_hash, senha_texto)

    # ── Métodos de permissão ──────────────────────────────────

    def is_admin(self):
        """Retorna True se o usuário é admin."""
        return self.cargo == 'admin'

    def tem_permissao(self, modulo):
        """
        Verifica se o usuário tem acesso a um módulo específico.
        Admin SEMPRE tem acesso a tudo.
        """
        if self.is_admin():
            return True
        return (self.permissoes or {}).get(modulo, False)

    def __repr__(self):
        return f'<Usuario {self.nome} | {self.cargo}>'


# ══════════════════════════════════════════════════════════════
# MODELO: Submissão (ficha cadastral de cliente)
# ══════════════════════════════════════════════════════════════

class Submissao(db.Model):
    """
    Representa uma submissão de ficha cadastral de cliente.

    Ciclo de vida do status:
        'pendente'   → ficha enviada, aguardando análise
        'aprovado'   → farmacêutica aprovou
        'reprovado'  → farmacêutica reprovou (vendedor pode corrigir)
        'cadastrado' → robô RPA finalizou o cadastro no ERP
    """

    __tablename__ = 'submissoes'

    uuid = db.Column(db.String(36), primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False)
    razao_social = db.Column(db.String(255))
    tentativa = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pendente')
    dados_json = db.Column(db.JSON, default=dict)
    docs_enviados = db.Column(db.JSON, default=list)
    motivos_reprovacao = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<Submissao {self.uuid[:8]}... | {self.razao_social} | {self.status}>'
    

# ══════════════════════════════════════════════════════════════
# ROBÔS DO HUB (lista central para rastreamento)
# ══════════════════════════════════════════════════════════════

ROBOS_HUB = {
    'itens_fase1':  'Cadastro de Itens — Fase 1 (NCM)',
    'itens_fase2':  'Cadastro de Itens — Fase 2 (ERP)',
    'mdf':          'Relatório MDF-e',
    'fornecedor':   'Cadastro de Fornecedor',
    'cliente_novo': 'Cadastro de Cliente (Novo)',
}


# ══════════════════════════════════════════════════════════════
# MODELO: Execução de Robô
# ══════════════════════════════════════════════════════════════

class Execucao(db.Model):
    """
    Registra cada execução de robô no Hub.

    Ciclo de vida:
        1. Usuário dispara o robô → cria registro com status 'executando'
        2. Robô termina → atualiza para 'sucesso', 'erro' ou 'aviso'
        3. Duração é calculada automaticamente (fim - inicio)

    O campo 'detalhes' é um JSON livre para guardar informações extras:
        - Em caso de erro: {"erro": "mensagem do erro"}
        - Em caso de aviso: {"avisos": ["msg1", "msg2"]}
        - Qualquer dado relevante do robô
    """

    __tablename__ = 'execucoes'

    id = db.Column(db.Integer, primary_key=True)

    # Quem disparou
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nome = db.Column(db.String(150), default='Sistema')

    # Qual robô
    robo = db.Column(db.String(50), nullable=False)

    # Status: 'executando', 'sucesso', 'erro', 'aviso'
    status = db.Column(db.String(20), default='executando')

    # Timestamps
    inicio     = db.Column(db.DateTime, default=datetime.now)
    fim        = db.Column(db.DateTime, nullable=True)
    duracao_seg = db.Column(db.Integer, nullable=True)

    # Detalhes extras (JSON livre)
    detalhes = db.Column(db.JSON, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Execucao {self.id} | {self.robo} | {self.status}>'
