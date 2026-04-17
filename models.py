# ══════════════════════════════════════════════════════════════
# models.py — Modelos do Banco de Dados (SQLAlchemy)
# ══════════════════════════════════════════════════════════════
# Cada classe aqui representa uma TABELA no PostgreSQL.
# Cada atributo da classe representa uma COLUNA na tabela.
#
# Exemplo visual:
#
#   class Submissao     →  tabela "submissoes" no banco
#       uuid            →  coluna "uuid" (chave primária)
#       cnpj            →  coluna "cnpj"
#       razao_social    →  coluna "razao_social"
#       ...
#
# O SQLAlchemy cuida de criar a tabela, inserir, buscar, atualizar
# e deletar registros — sem você escrever SQL na mão.
# ══════════════════════════════════════════════════════════════

from datetime import datetime
from extensions import db


class Submissao(db.Model):
    """
    Representa uma submissão de ficha cadastral de cliente.

    Cada vez que um vendedor envia uma ficha pelo formulário digital,
    uma Submissao é criada. Se a farmacêutica reprovar, o vendedor
    corrige e a mesma Submissao é atualizada (incrementa tentativa).

    Ciclo de vida do status:
        'pendente'   → ficha enviada, aguardando análise
        'aprovado'   → farmacêutica aprovou
        'reprovado'  → farmacêutica reprovou (vendedor pode corrigir)
        'cadastrado' → robô RPA finalizou o cadastro no ERP
    """

    # ── Nome da tabela no banco ───────────────────────────────
    # Sem isso, o SQLAlchemy usaria "submissao" (nome da classe).
    # Definimos explicitamente para manter o mesmo nome do SQLite.
    __tablename__ = 'submissoes'

    # ── Colunas ───────────────────────────────────────────────

    # Identificador único da submissão (gerado pelo Python com uuid4)
    # db.String(36) = texto de até 36 caracteres (tamanho padrão de um UUID)
    # primary_key=True = esta é a chave primária da tabela
    uuid = db.Column(db.String(36), primary_key=True)

    # CNPJ do cliente (obrigatório)
    # nullable=False = não pode ser vazio (equivale ao NOT NULL do SQL)
    cnpj = db.Column(db.String(20), nullable=False)

    # Razão social do cliente
    razao_social = db.Column(db.String(255))

    # Número da tentativa atual (1 = primeira vez, 2 = primeira correção, etc)
    # default=1 = se não informar, começa em 1
    tentativa = db.Column(db.Integer, default=1)

    # Status atual da submissão
    # Valores possíveis: 'pendente', 'aprovado', 'reprovado', 'cadastrado'
    status = db.Column(db.String(20), default='pendente')

    # Dados completos da ficha em formato JSON
    # db.JSON = o PostgreSQL tem suporte NATIVO a JSON, muito melhor que
    # guardar como texto e ficar fazendo json.loads/json.dumps manual.
    # Você pode buscar, filtrar e até indexar campos dentro do JSON!
    dados_json = db.Column(db.JSON, default=dict)

    # Lista dos documentos enviados (ex: ['doc_contrato', 'doc_afe'])
    # Também JSON nativo — antes era texto com json.dumps/loads
    docs_enviados = db.Column(db.JSON, default=list)

    # Histórico de reprovações acumulado
    # Lista de dicts: [{'tentativa': 1, 'motivo': '...', 'data': '...'}]
    motivos_reprovacao = db.Column(db.JSON, default=list)

    # Data de criação — agora é DateTime de verdade, não texto!
    # O banco sabe que é uma data e pode ordenar/filtrar corretamente.
    # default=datetime.now = preenche automaticamente ao criar
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Data da última atualização
    # onupdate=datetime.now = atualiza automaticamente toda vez que salvar
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # ── Método de representação ───────────────────────────────
    # Quando você der print() num objeto Submissao, aparece algo legível
    # em vez de <Submissao object at 0x...>
    def __repr__(self):
        return f'<Submissao {self.uuid[:8]}... | {self.razao_social} | {self.status}>'
