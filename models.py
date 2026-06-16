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
    'cep':         'Cadastro de CEP',
    'monitor':     'Monitor de Cadastros',
    'notas':       'Controle de Notas Fiscais',
    'lancamento_notas': 'Lançamento de Notas',
}


def permissoes_padrao():
    """Retorna dict com todos os módulos liberados (padrão para novos usuários)."""
    return {modulo: True for modulo in MODULOS_HUB}


# ── ROBÔS DO HUB (lista central p/ filtros de histórico) ─────
# Chaves são EXATAMENTE os nomes passados em iniciar_execucao_robo(...).
# Ao criar um robô novo, adicione aqui e o filtro do histórico
# (admin e meu_historico) já passa a listá-lo automaticamente.

ROBOS_HUB = {
    'itens_fase1':        'Itens — Fase 1',
    'itens_fase2':        'Itens — Fase 2',
    'mdf':                'Relatório MDF-e',
    'fornecedor':         'Fornecedor',
    'cliente_novo':       'Cliente Novo',
    'cliente_reativacao': 'Cliente Reativação',
    'cadastro_cep':       'Cadastro de CEP',
}

SETORES_CIAMED = [
    'TI',
    'Controladoria',
    'Comercial Público',
    'Comercial Privado',
    'Jurídico',
    'Estoque',
    'Faturamento',
    'Fiscal',
    'Logística',
    'Compras',
    'Financeiro',
    'RH / Departamento Pessoal',
    'Qualidade / Farmacêutica',
    'Diretoria',
]

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
        'erro_robo'  → robô falhou, aguardando reprocessamento manual
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
    erro_robo = db.Column(db.JSON, nullable=True)

    # Controle do envio ao N8N (C2/A-05). A ficha é salva ANTES de chamar o
    # N8N; se o webhook falha (N8N fora do ar), a ficha ficaria "órfã" — salva
    # mas nunca processada. Estes campos deixam isso visível no Monitor para o
    # operador reenviar com 1 clique. 'enviado' é o estado normal; 'falhou'
    # sinaliza que precisa reenviar. n8n_payload guarda o que enviar de novo.
    envio_n8n   = db.Column(db.String(20), default='enviado', server_default='enviado')
    n8n_erro    = db.Column(db.Text, nullable=True)
    n8n_payload = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<Submissao {self.uuid[:8]}... | {self.razao_social} | {self.status}>'


# ══════════════════════════════════════════════════════════════
# MODELO: Link de Ficha gerado (controle/rastreio de links)
# ══════════════════════════════════════════════════════════════

class LinkFicha(db.Model):
    """
    Registra cada link de ficha gerado no Hub, para controle e auditoria.

    Permite responder: quem gerou o link, para qual cliente (CNPJ), quando,
    qual a validade e se já foi usado. O 'token' é o segredo que vai na URL
    (?t=token) — sem ele não dá para abrir nem enviar uma ficha nova.

    Status (derivado): 'ativo' | 'usado' | 'expirado'.
    """

    __tablename__ = 'links_ficha'

    id    = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Cliente para quem o link foi gerado (CNPJ só com dígitos)
    cnpj_cliente = db.Column(db.String(14), nullable=False)

    # Quem gerou (operador logado) — pode ser diferente do vendedor
    gerado_por_id   = db.Column(db.Integer)
    gerado_por_nome = db.Column(db.String(150))

    # Dados de rastreio que o link carrega
    vendedor      = db.Column(db.String(255))
    representante = db.Column(db.String(255))
    captacao      = db.Column(db.String(50))
    tipo          = db.Column(db.String(20))   # 'NOVO' | 'REATIVACAO'
    codigo_nl     = db.Column(db.String(50))

    # Validade e uso
    created_at = db.Column(db.DateTime, default=datetime.now)
    expira_em  = db.Column(db.DateTime, nullable=False)
    usado_em   = db.Column(db.DateTime, nullable=True)
    submission_uuid = db.Column(db.String(36), nullable=True)

    # Alerta: o CNPJ preenchido na ficha não bateu com o do link
    cnpj_divergente = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<LinkFicha {self.token[:8]}... | {self.cnpj_cliente} | por {self.gerado_por_nome}>'
    

# ══════════════════════════════════════════════════════════════
# ROBÔS DO HUB (lista central para rastreamento)
# ══════════════════════════════════════════════════════════════

ROBOS_HUB = {
    'itens_fase1':  'Cadastro de Itens — Fase 1 (NCM)',
    'itens_fase2':  'Cadastro de Itens — Fase 2 (ERP)',
    'mdf':          'Relatório MDF-e',
    'fornecedor':   'Cadastro de Fornecedor',
    'cliente_novo': 'Cadastro de Cliente (Novo)',
    'lancamento_notas_danfe':   'Lançamento de Notas — DANFE',
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


# ══════════════════════════════════════════════════════════════
# MODELO: Fila de Execução (controle "um robô por vez")
# ══════════════════════════════════════════════════════════════

class FilaExecucao(db.Model):
    """
    Fila persistente no banco para garantir "um robô por vez", mesmo com
    vários workers/containers (resolve A-01).

    Há duas filas, separadas pela coluna 'recurso':
      - 'rpa'      → robôs de itens / MDF / fornecedor
      - 'cadastro' → fluxo de cadastro de clientes (N8N)

    Como a "vez" é definida no banco (e não na memória de um processo),
    qualquer worker enxerga a mesma fila. A coluna 'iniciado_em' alimenta
    o watchdog: uma execução parada além do tempo-limite é considerada
    travada e liberada automaticamente.
    """

    __tablename__ = 'fila_execucao'

    # id autoincrement define a ORDEM (FIFO) de chegada.
    id = db.Column(db.BigInteger, primary_key=True)

    # token: identificador público entregue a quem entra na fila.
    token = db.Column(db.String(36), nullable=False, unique=True)

    # recurso disputado: 'rpa' ou 'cadastro'
    recurso = db.Column(db.String(30), nullable=False)

    # status: 'aguardando' ou 'executando'
    status = db.Column(db.String(20), nullable=False, default='aguardando')

    # usado só pela fila de cadastro (URL que acorda o Wait node do N8N)
    resume_url = db.Column(db.Text, nullable=True)

    criado_em   = db.Column(db.DateTime, default=datetime.now, nullable=False)
    iniciado_em = db.Column(db.DateTime, nullable=True)

    # Índice para achar rápido "quem está aguardando/executando neste recurso".
    __table_args__ = (
        db.Index('ix_fila_execucao_recurso_status', 'recurso', 'status'),
    )

    def __repr__(self):
        return f'<FilaExecucao {self.token} | {self.recurso} | {self.status}>'


# ══════════════════════════════════════════════════════════════
# MODELO: Lançamento de Nota
# ══════════════════════════════════════════════════════════════

class LancamentoNota(db.Model):
    """
    Representa um lançamento de nota fiscal no Hub.

    Ciclo de vida do status:
        'na_fila'    → usuário enviou XML e preencheu, esperando robô
        'executando' → robô RPA está rodando agora
        'concluida'  → robô finalizou com sucesso no NLWeb
        'a_rever'    → robô falhou, usuário precisa decidir o que fazer
        'cancelada'  → usuário desistiu na aba "A Rever"

    Tipos de nota (preparando para os futuros):
        'danfe'   → nota fiscal eletrônica (modelo 55) — começamos por este
        'servico' → nota de serviço
        'cupom'   → cupom fiscal
    """

    __tablename__ = 'lancamentos_notas'

    # Índice único PARCIAL: impede duas notas ATIVAS com a mesma chave de
    # acesso (na_fila/executando/concluida/a_rever). Notas 'cancelada' ficam
    # de fora, então é possível reenviar uma nota depois de cancelar a antiga.
    # O filtro é específico do PostgreSQL (postgresql_where).
    __table_args__ = (
        db.Index(
            'uq_lancamentos_notas_chave_ativa',
            'chave_acesso',
            unique=True,
            postgresql_where=db.text("status <> 'cancelada' AND chave_acesso IS NOT NULL"),
        ),
    )

    id              = db.Column(db.Integer, primary_key=True)
    chave_acesso    = db.Column(db.String(44), index=True)   # índice de busca; unicidade via índice parcial acima
    numero_nota     = db.Column(db.String(20))
    serie           = db.Column(db.String(5))
    tipo_nota       = db.Column(db.String(20), default='danfe')
    fornecedor_cnpj = db.Column(db.String(20))
    fornecedor_nome = db.Column(db.String(255))

    # Numeric(15,2) garante precisão de centavos. Nunca use Float pra dinheiro
    # — Float é binário e perde precisão (0.1 + 0.2 != 0.3 em float).
    valor_total = db.Column(db.Numeric(15, 2))

    # Caminho do XML salvo em xmls/lancamento_notas/recebidos/AAAA/MM/
    xml_path = db.Column(db.String(500))

    # JSON com o resultado do parser (itens, duplicatas, totais, etc).
    # PostgreSQL armazena isso como JSONB nativo — pode até queryar dentro do JSON depois.
    dados_xml = db.Column(db.JSON, default=dict)

    # JSON com o que o USUÁRIO preencheu nas 4 abas:
    # { centros_custo: [{item_idx, codigo}], parcelas: [...],
    #   data_recebimento, data_base, operacao_codigo }
    dados_complementares = db.Column(db.JSON, default=dict)

    status          = db.Column(db.String(20), default='na_fila')
    mensagem_erro   = db.Column(db.Text)
    screenshot_erro = db.Column(db.String(500))

    # Quem disparou o lançamento (operador no Hub)
    usuario_id   = db.Column(db.Integer)
    usuario_nome = db.Column(db.String(150))

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<LancamentoNota {self.numero_nota} | {self.fornecedor_nome} | {self.status}>'


# ══════════════════════════════════════════════════════════════
# MODELO: Centro de Custo
# ══════════════════════════════════════════════════════════════

class CentroCusto(db.Model):
    """
    Centros de custo selecionáveis pelo usuário ao lançar uma nota
    (um por item). Tabela populada via scripts/seed_dados_notas.py.

    Campo 'empresa' é usado para agrupar no <optgroup> do dropdown.
    """

    __tablename__ = 'centros_custo'

    id        = db.Column(db.Integer, primary_key=True)
    # String, não Integer: o código tem zero à esquerda (ex: '01100001')
    codigo    = db.Column(db.String(20), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(255), nullable=False)
    empresa   = db.Column(db.String(50))   # 'Ciamed RS', 'Ciamed SP', etc.
    ativo     = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CentroCusto {self.codigo} | {self.descricao}>'


# ══════════════════════════════════════════════════════════════
# MODELO: Operação de Nota
# ══════════════════════════════════════════════════════════════

class OperacaoNota(db.Model):
    """
    Operações disponíveis no NLWeb para lançar uma nota.
    Tabela populada via scripts/seed_dados_notas.py.

    Usada no autocomplete do campo "Operação" da aba 4.
    """

    __tablename__ = 'operacoes_nota'

    id        = db.Column(db.Integer, primary_key=True)
    # String para preservar formatos como "1.000", "9.999"
    codigo    = db.Column(db.String(20), unique=True, nullable=False, index=True)
    descricao = db.Column(db.String(500), nullable=False)
    ativo     = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<OperacaoNota {self.codigo} | {self.descricao[:40]}>'
    

# ══════════════════════════════════════════════════════════════
# MÓDULO: Controle de Notas Fiscais
# ══════════════════════════════════════════════════════════════
# Três tabelas:
#   notas_categorias    → tipos de despesa (energia, água, etc.)
#   notas_unidades      → Matriz e filiais
#   notas_fornecedores  → fornecedores recorrentes (cadastro)
#
# A tabela 'notas' (lançamentos mensais) vem na Fase 1C, quando
# conectarmos o Kanban ao banco.
# ══════════════════════════════════════════════════════════════


class NotasCategoria(db.Model):
    """
    Categoria de despesa (energia, água, internet, etc.).

    Usa string como PK (slug) pra manter compatibilidade direta
    com o React app, que já trabalha com IDs string ("energia",
    "agua", etc.) desde o mock.js.

    Soft-delete via 'ativa': inativas não aparecem nos dropdowns
    de cadastro novo, mas continuam visíveis em registros antigos.
    """

    __tablename__ = 'notas_categorias'

    id    = db.Column(db.String(50),  primary_key=True)   # slug: "energia"
    nome  = db.Column(db.String(100), nullable=False)      # "Energia elétrica"
    ordem = db.Column(db.Integer,     default=0)           # ordenação na UI
    ativa = db.Column(db.Boolean,     default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<NotasCategoria {self.id} | {self.nome}>'


class NotasUnidade(db.Model):
    """
    Unidade da empresa (Matriz, Filial 2, Filial 3 SC, Filial 4).

    Igual à NotasCategoria, usa string como PK pra bater com o
    React app. O campo 'short' é o rótulo compacto que aparece
    nos cards do Kanban (MTZ, F2, F3 SC, F4).
    """

    __tablename__ = 'notas_unidades'

    id    = db.Column(db.String(20),  primary_key=True)   # slug: "matriz", "f2"
    nome  = db.Column(db.String(100), nullable=False)      # "Matriz (1)"
    short = db.Column(db.String(10),  nullable=False)      # "MTZ", "F2"
    ordem = db.Column(db.Integer,     default=0)
    ativa = db.Column(db.Boolean,     default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<NotasUnidade {self.id} | {self.nome}>'


class NotasFornecedor(db.Model):
    """
    Fornecedor recorrente que envia notas mensais.

    REGRA IMPORTANTE: cada combinação fornecedor+unidade é uma
    LINHA SEPARADA. Se a Microsoft fatura pra Matriz e pra F3, são
    duas linhas — não um único registro com várias unidades.
    Isso permite que cada combinação tenha seu próprio dia esperado
    e gere uma Nota distinta no Kanban mensal.
    """

    __tablename__ = 'notas_fornecedores'

    id           = db.Column(db.Integer, primary_key=True)
    fornecedor   = db.Column(db.String(200), nullable=False)
    cnpj         = db.Column(db.String(20),  nullable=True)

    categoria_id = db.Column(db.String(50), db.ForeignKey('notas_categorias.id'), nullable=False)
    unidade_id   = db.Column(db.String(20), db.ForeignKey('notas_unidades.id'),   nullable=False)

    dia_esperado = db.Column(db.Integer, nullable=False)   # 1 a 31

    # ── Campos v2 ──────────────────────────────────────────────
    retencao_padrao = db.Column(db.Boolean, default=False)
    # Lista de TIPOS de retenção marcados como padrão (ex: ["inss", "iss"]).
    # O código em routes/notas.py lê/grava isto como lista JSON.
    retencoes_padrao = db.Column(db.JSON, default=list)
    valor_medio     = db.Column(db.Numeric(12, 2), nullable=True)
    iniciado_em     = db.Column(db.String(7), nullable=True)   # "2026-05"
    observacoes     = db.Column(db.Text, nullable=True)
    
    ativo        = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relacionamentos (acesso fácil ao categoria.nome e unidade.nome no Python)
    categoria = db.relationship('NotasCategoria', backref='fornecedores')
    unidade   = db.relationship('NotasUnidade',   backref='fornecedores')

    def __repr__(self):
        return f'<NotasFornecedor {self.id} | {self.fornecedor} | {self.unidade_id}>'
    
class Nota(db.Model):
    """Lançamento mensal de uma nota fiscal — usado pelo Kanban."""
    __tablename__ = 'notas'

    id = db.Column(db.Integer, primary_key=True)

    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)

    fornecedor_recorrente_id = db.Column(
        db.Integer, db.ForeignKey('notas_fornecedores.id'), nullable=True
    )

    # Dados denormalizados (preservam histórico mesmo se fornecedor é editado)
    fornecedor   = db.Column(db.String(200), nullable=False)
    cnpj         = db.Column(db.String(20),  nullable=True)
    categoria_id = db.Column(db.String(50), db.ForeignKey('notas_categorias.id'), nullable=False)
    unidade_id   = db.Column(db.String(20), db.ForeignKey('notas_unidades.id'),   nullable=False)
    dia_esperado = db.Column(db.Integer, nullable=False)

    # Recebimento
    recebida_em   = db.Column(db.Date,           nullable=True)
    nf_numero     = db.Column(db.String(50),     nullable=True)
    valor_liquido = db.Column(db.Numeric(12, 2), nullable=True)
    retencao      = db.Column(db.Boolean,        default=False)
    observacoes   = db.Column(db.Text,           nullable=True)

    # Flag de avulsa (não vem de fornecedor recorrente)
    avulsa = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    fornecedor_recorrente = db.relationship('NotasFornecedor', backref='notas_geradas')
    categoria = db.relationship('NotasCategoria')
    unidade   = db.relationship('NotasUnidade')

    __table_args__ = (
        db.Index('ix_notas_mes_ano', 'mes', 'ano'),
        db.Index('ix_notas_unidade_mes_ano', 'unidade_id', 'mes', 'ano'),
    )

    def __repr__(self):
        return f'<Nota {self.id} | {self.fornecedor} | {self.mes}/{self.ano}>'
    

# ══════════════════════════════════════════════════════════════
# MÓDULO: Central de Suporte
# ══════════════════════════════════════════════════════════════
# Cinco tabelas:
#   chamados              → tickets abertos pelos usuários
#   chamados_anexos       → arquivos anexados a um chamado
#   chamados_historico    → timeline de eventos do chamado
#   notificacoes          → avisos para o usuário (sininho)
#   faq_perguntas         → perguntas frequentes por módulo
# ══════════════════════════════════════════════════════════════
 
 
class Chamado(db.Model):
    """
    Chamado de suporte aberto por um usuário do Hub.
 
    Ciclo de vida do status:
        'pendente'     → recém-criado, ninguém olhou ainda
        'em_analise'   → admin reconheceu e está trabalhando
        'resolvido'    → problema resolvido
        'cancelado'    → usuário desistiu (só pode cancelar se pendente)
 
    Prioridade:
        'baixa'   → resolução em até 24h
        'media'   → resolução em até 8h
        'alta'    → resolução em até 2h
        'critica' → resolução em até 30min
 
    Protocolo:
        Formato SUP-XXXX, gerado automaticamente na criação.
        Visível para o usuário e usado para referência rápida.
    """
 
    __tablename__ = 'chamados'
 
    id         = db.Column(db.Integer, primary_key=True)
    protocolo  = db.Column(db.String(20), unique=True, nullable=False, index=True)
 
    # Quem abriu (puxado da sessão, não digitado)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
 
    # Módulo relacionado (chave de MODULOS_HUB ou 'geral')
    modulo     = db.Column(db.String(50), default='geral')
 
    # Classificação
    prioridade = db.Column(db.String(20), default='media')
 
    # Conteúdo
    assunto    = db.Column(db.String(255), nullable=False)
    mensagem   = db.Column(db.Text, nullable=False)
 
    # Status do chamado
    status     = db.Column(db.String(20), default='pendente')
 
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
 
    # Relacionamentos
    usuario   = db.relationship('Usuario', backref='chamados')
    anexos    = db.relationship('ChamadoAnexo', backref='chamado', cascade='all, delete-orphan')
    historico = db.relationship('ChamadoHistorico', backref='chamado', cascade='all, delete-orphan',
                                order_by='ChamadoHistorico.created_at')
 
    def __repr__(self):
        return f'<Chamado #{self.protocolo} | {self.assunto[:30]} | {self.status}>'
 
 
class ChamadoAnexo(db.Model):
    """
    Arquivo anexado a um chamado (print, XML, PDF, etc.).
 
    Os arquivos ficam em: uploads/chamados/SUP-XXXX/nome_arquivo.ext
    Tamanho máximo: 10MB por arquivo, 5 arquivos por chamado.
    """
 
    __tablename__ = 'chamados_anexos'
 
    id             = db.Column(db.Integer, primary_key=True)
    chamado_id     = db.Column(db.Integer, db.ForeignKey('chamados.id'), nullable=False)
    nome_arquivo   = db.Column(db.String(255), nullable=False)
    caminho        = db.Column(db.String(500), nullable=False)
    tipo_mime      = db.Column(db.String(100))
    tamanho_bytes  = db.Column(db.Integer)
    created_at     = db.Column(db.DateTime, default=datetime.now)
 
    def __repr__(self):
        return f'<ChamadoAnexo {self.nome_arquivo} | chamado={self.chamado_id}>'
 
 
class ChamadoHistorico(db.Model):
    """
    Evento na timeline de um chamado.
 
    Tipos de evento:
        'criacao'          → chamado foi criado
        'mudanca_status'   → status mudou (registra anterior e novo)
        'resposta_admin'   → admin escreveu uma resposta
        'anexo'            → arquivo foi anexado
 
    A timeline é montada ordenando por created_at.
    """
 
    __tablename__ = 'chamados_historico'
 
    id              = db.Column(db.Integer, primary_key=True)
    chamado_id      = db.Column(db.Integer, db.ForeignKey('chamados.id'), nullable=False)
    usuario_id      = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    tipo            = db.Column(db.String(30), nullable=False)
    status_anterior = db.Column(db.String(20), nullable=True)
    status_novo     = db.Column(db.String(20), nullable=True)
    mensagem        = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.now)
 
    # Relacionamento para pegar o nome de quem fez a ação
    usuario = db.relationship('Usuario')
 
    def __repr__(self):
        return f'<ChamadoHistorico {self.tipo} | chamado={self.chamado_id}>'
 
 
class Notificacao(db.Model):
    """
    Notificação visual para o usuário (sininho na navbar).
 
    Criada automaticamente quando:
        - Admin muda o status de um chamado do usuário
        - Admin responde a um chamado do usuário
 
    O frontend faz polling a cada 60s em /api/notificacoes/count
    para atualizar o badge do sininho.
    """
 
    __tablename__ = 'notificacoes'
 
    id          = db.Column(db.Integer, primary_key=True)
    usuario_id  = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    chamado_id  = db.Column(db.Integer, db.ForeignKey('chamados.id'), nullable=True)
    tipo        = db.Column(db.String(30), nullable=False)
    titulo      = db.Column(db.String(255), nullable=False)
    lida        = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.now)
 
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='notificacoes')
    chamado = db.relationship('Chamado')
 
    def __repr__(self):
        return f'<Notificacao {self.tipo} | user={self.usuario_id} | lida={self.lida}>'
 
 
class FaqPergunta(db.Model):
    """
    Pergunta frequente exibida na Central de Suporte.
 
    Organizada por módulo (chave de MODULOS_HUB ou 'geral').
    Admin pode criar/editar/excluir pelo painel.
    Suporta markdown básico na resposta.
    Soft-delete via 'ativo'.
    """
 
    __tablename__ = 'faq_perguntas'
 
    id         = db.Column(db.Integer, primary_key=True)
    modulo     = db.Column(db.String(50), nullable=False, index=True)
    pergunta   = db.Column(db.String(500), nullable=False)
    resposta   = db.Column(db.Text, nullable=False)
    ordem      = db.Column(db.Integer, default=0)
    ativo      = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
 
    def __repr__(self):
        return f'<FaqPergunta {self.id} | {self.modulo} | {self.pergunta[:40]}>'