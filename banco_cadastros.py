# ══════════════════════════════════════════════════════════════
# banco_cadastros.py — Operações do Banco de Dados (SQLAlchemy)
# ══════════════════════════════════════════════════════════════
# Este arquivo substitui a versão antiga que usava SQLite puro.
#
# IMPORTANTE: a interface (nomes das funções, parâmetros e retornos)
# é IDÊNTICA à versão anterior. O app.py e o restante do código
# continuam chamando as mesmas funções sem saber que o banco mudou.
#
# Mudanças internas:
#   - sqlite3.connect()       →  db.session (SQLAlchemy)
#   - SQL escrito na mão      →  métodos do ORM
#   - json.dumps/json.loads   →  PostgreSQL JSON nativo (automático)
#   - Datas como texto        →  DateTime de verdade
# ══════════════════════════════════════════════════════════════

from datetime import datetime
from extensions import db
from models import Submissao


# ── Helper: converter objeto Submissao → dict ─────────────────
# O app.py acessa os dados como dicionário (ex: sub['cnpj']).
# Este helper converte o objeto SQLAlchemy para dict, mantendo
# a compatibilidade total com o código existente.
# ──────────────────────────────────────────────────────────────

def _submissao_to_dict(sub):
    """
    Converte um objeto Submissao do SQLAlchemy em dicionário,
    no mesmo formato que a versão antiga retornava.
    """
    return {
        'uuid':               sub.uuid,
        'cnpj':               sub.cnpj,
        'razao_social':       sub.razao_social,
        'tentativa':          sub.tentativa,
        'status':             sub.status,
        'dados_json':         sub.dados_json or {},
        'docs_enviados':      sub.docs_enviados or [],
        'motivos_reprovacao': sub.motivos_reprovacao or [],
        'created_at':         sub.created_at.strftime('%d/%m/%Y %H:%M') if sub.created_at else '',
        'updated_at':         sub.updated_at.strftime('%d/%m/%Y %H:%M') if sub.updated_at else '',
    }


# ══════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════

def init_db():
    """
    Cria todas as tabelas definidas em models.py no PostgreSQL.
    Chame isso uma vez ao subir o Flask.

    NOTA: quando adotarmos Alembic (migrations), esta função será
    substituída pelo comando 'alembic upgrade head'. Por enquanto,
    ela garante que as tabelas existam no banco.
    """
    db.create_all()
    print("✅ [BD] Banco PostgreSQL inicializado (tabelas verificadas).")


# ══════════════════════════════════════════════════════════════
# OPERAÇÕES — mesma interface da versão SQLite
# ══════════════════════════════════════════════════════════════

def salvar_submissao(uuid, cnpj, razao_social, dados_json, docs_enviados):
    """
    Salva uma nova submissão (1ª tentativa).

    Parâmetros:
        uuid          → identificador único da submissão
        cnpj          → CNPJ do cliente
        razao_social  → nome da empresa
        dados_json    → dict com todos os campos da ficha
        docs_enviados → lista com nomes dos campos de documento enviados
                        ex: ['doc_alvara', 'doc_crt', 'doc_contrato']
    """
    submissao = Submissao(
        uuid=uuid,
        cnpj=cnpj,
        razao_social=razao_social,
        tentativa=1,
        status='pendente',
        dados_json=dados_json,
        docs_enviados=docs_enviados,
        motivos_reprovacao=[],
    )
    db.session.add(submissao)
    db.session.commit()
    print(f"✅ [BD] Submissão salva | UUID: {uuid} | Empresa: {razao_social}")


def buscar_submissao(uuid):
    """
    Retorna dados de uma submissão pelo UUID.
    Retorna None se não encontrar.

    O retorno é um DICIONÁRIO (igual à versão antiga) com:
        dados_json         → dict
        docs_enviados      → list
        motivos_reprovacao → list de dicts
    """
    sub = db.session.get(Submissao, uuid)
    if not sub:
        return None
    return _submissao_to_dict(sub)


def registrar_reprovacao(uuid, motivo):
    """
    Adiciona um motivo de reprovação ao histórico e muda o status
    para 'reprovado'. O histórico é acumulativo — cada tentativa
    reprovada fica registrada.

    Retorna True se encontrou o UUID, False caso contrário.
    """
    sub = db.session.get(Submissao, uuid)
    if not sub:
        print(f"⚠️ [BD] UUID não encontrado para reprovação: {uuid}")
        return False

    # Copia a lista atual e adiciona o novo motivo
    # (precisamos fazer uma cópia para o SQLAlchemy detectar a mudança)
    motivos = list(sub.motivos_reprovacao or [])
    motivos.append({
        'tentativa': sub.tentativa,
        'motivo':    motivo,
        'data':      datetime.now().strftime('%d/%m/%Y %H:%M'),
    })

    sub.motivos_reprovacao = motivos
    sub.status = 'reprovado'
    db.session.commit()

    print(f"❌ [BD] Reprovação registrada | UUID: {uuid} | Tentativa: {sub.tentativa}")
    return True


def incrementar_tentativa(uuid, dados_json, docs_enviados):
    """
    Atualiza a submissão com os dados da correção:
        - Incrementa o contador de tentativas
        - Volta o status para 'pendente'
        - Substitui dados_json e docs_enviados pelos novos valores

    Retorna o número da nova tentativa, ou None se UUID não existir.
    """
    sub = db.session.get(Submissao, uuid)
    if not sub:
        print(f"⚠️ [BD] UUID não encontrado para incrementar: {uuid}")
        return None

    sub.tentativa += 1
    sub.status = 'pendente'
    sub.dados_json = dados_json
    sub.docs_enviados = docs_enviados
    db.session.commit()

    print(f"🔄 [BD] Nova tentativa | UUID: {uuid} | Tentativa: {sub.tentativa}")
    return sub.tentativa


def atualizar_status(uuid, status):
    """
    Atualiza apenas o status de uma submissão.
    Status válidos: 'pendente', 'aprovado', 'reprovado', 'cadastrado'
    """
    sub = db.session.get(Submissao, uuid)
    if sub:
        sub.status = status
        db.session.commit()
        print(f"📋 [BD] Status atualizado | UUID: {uuid} | Status: {status}")


def listar_submissoes(status=None, tipo=None, busca=None, data_de=None, data_ate=None):
    """
    Retorna lista de todas as submissões com filtros opcionais.
    Usada pela tela de Monitor de Cadastros.

    Filtros:
        status   → 'pendente' | 'aprovado' | 'reprovado' | 'cadastrado'
        tipo     → 'NOVO' | 'REATIVACAO' (busca dentro do dados_json)
        busca    → texto livre para empresa ou CNPJ
        data_de  → string 'dd/mm/yyyy' — filtra a partir desta data
        data_ate → string 'dd/mm/yyyy' — filtra até esta data
    """
    # Começa com uma query base ordenada por data (mais recente primeiro)
    query = Submissao.query.order_by(Submissao.created_at.desc())

    # ── Filtro por status ─────────────────────────────────────
    if status:
        query = query.filter(Submissao.status == status)

    # ── Filtro por busca (empresa ou CNPJ) ────────────────────
    # ilike = case-insensitive LIKE (busca sem diferenciar maiúscula/minúscula)
    if busca:
        termo = f'%{busca}%'
        query = query.filter(
            db.or_(
                Submissao.razao_social.ilike(termo),
                Submissao.cnpj.ilike(termo),
            )
        )

    # ── Filtro por data ───────────────────────────────────────
    # Agora com DateTime de verdade! Muito mais confiável que comparar strings.
    if data_de:
        try:
            # Aceita formato 'dd/mm/yyyy' ou 'yyyy-mm-dd'
            if '/' in data_de:
                dt_de = datetime.strptime(data_de, '%d/%m/%Y')
            else:
                dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(Submissao.created_at >= dt_de)
        except ValueError:
            pass

    if data_ate:
        try:
            if '/' in data_ate:
                dt_ate = datetime.strptime(data_ate, '%d/%m/%Y')
            else:
                dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
            # Adiciona 1 dia para incluir o dia inteiro
            dt_ate = dt_ate.replace(hour=23, minute=59, second=59)
            query = query.filter(Submissao.created_at <= dt_ate)
        except ValueError:
            pass

    # ── Executa a query ───────────────────────────────────────
    submissoes = query.all()

    # ── Filtro por tipo (dentro do JSON) ──────────────────────
    # Este filtro é feito em Python porque o campo 'tipo_cadastro'
    # está dentro do dados_json. No futuro, se precisar de performance,
    # podemos usar o operador JSON do PostgreSQL.
    resultado = []
    for sub in submissoes:
        if tipo:
            tipo_cadastro = (sub.dados_json or {}).get('tipo_cadastro', '')
            if tipo_cadastro != tipo:
                continue
        resultado.append(_submissao_to_dict(sub))

    return resultado


def stats_submissoes():
    """
    Retorna contagem por status para o painel de estatísticas.
    Retorno: dict com chaves 'total', 'pendente', 'aprovado',
             'reprovado', 'cadastrado'.
    """
    contagem = {
        'total': 0,
        'pendente': 0,
        'aprovado': 0,
        'reprovado': 0,
        'cadastrado': 0,
    }

    # Uma única query agrupada por status — eficiente e limpa
    resultados = (
        db.session.query(Submissao.status, db.func.count())
        .group_by(Submissao.status)
        .all()
    )

    for status, qtd in resultados:
        chave = status or 'pendente'
        if chave in contagem:
            contagem[chave] = qtd
        contagem['total'] += qtd

    return contagem
