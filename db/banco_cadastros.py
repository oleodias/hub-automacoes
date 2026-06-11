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

import logging
from datetime import datetime
from extensions import db
from models import Submissao

logger = logging.getLogger(__name__)


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
        'erro_robo':          sub.erro_robo,
        'envio_n8n':          sub.envio_n8n or 'enviado',
        'n8n_erro':           sub.n8n_erro,
        'created_at':         sub.created_at.strftime('%d/%m/%Y %H:%M') if sub.created_at else '',
        'updated_at':         sub.updated_at.strftime('%d/%m/%Y %H:%M') if sub.updated_at else '',
    }


# ══════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════

def init_db():
    """
    Cria todas as tabelas definidas em models.py no PostgreSQL.

    ATENÇÃO: esta função NÃO é mais chamada na subida do app. O schema
    agora é criado e versionado pelas migrations do Alembic
    ('alembic upgrade head'), que são a única fonte de verdade da
    estrutura do banco. Ela fica aqui apenas como utilitário pontual
    (ex.: testes locais rápidos); em produção, use sempre o Alembic.
    """
    db.create_all()
    logger.info("Banco PostgreSQL inicializado via db.create_all() (uso manual).")


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
    logger.info(f"Submissão salva | UUID: {uuid} | Empresa: {razao_social}")


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
        logger.warning(f"UUID não encontrado para reprovação: {uuid}")
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

    logger.info(f"Reprovação registrada | UUID: {uuid} | Tentativa: {sub.tentativa}")
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
        logger.warning(f"UUID não encontrado para incrementar: {uuid}")
        return None

    sub.tentativa += 1
    sub.status = 'pendente'
    sub.dados_json = dados_json
    sub.docs_enviados = docs_enviados
    db.session.commit()

    logger.info(f"Nova tentativa | UUID: {uuid} | Tentativa: {sub.tentativa}")
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
        logger.info(f"Status atualizado | UUID: {uuid} | Status: {status}")

def registrar_erro_robo(uuid, erro_data):
    """
    Registra que o robô falhou nesta submissão.
    Muda o status para 'erro_robo' e salva os detalhes do erro.
 
    Parâmetros:
        uuid      → UUID da submissão
        erro_data → dict com detalhes do erro:
            {
                "etapa_falha":     "fase_3_contatos",
                "etapa_concluida": "fase_2_endereco",
                "erro_detalhe":    "Timeout ao clicar...",
                "data_erro":       "19/05/2026 16:54",
                "tentativa_robo":  1
            }
    """
    sub = db.session.get(Submissao, uuid)
    if not sub:
        logger.warning(f"[ERRO_ROBO] UUID não encontrado: {uuid}")
        return False
 
    sub.status = 'erro_robo'
    sub.erro_robo = erro_data
    db.session.commit()
 
    logger.warning(
        f"[ERRO_ROBO] Registrado | UUID: {uuid} "
        f"| Etapa: {erro_data.get('etapa_falha', '?')} "
        f"| Detalhe: {erro_data.get('erro_detalhe', '?')[:80]}"
    )
    return True
 
 
def reprocessar_submissao(uuid):
    """
    Prepara uma submissão com erro para ser reprocessada pelo robô.
    Só funciona se o status atual for 'erro_robo'.
 
    O que faz:
        - Muda o status para 'aprovado' (pra re-entrar na fila sem re-aprovação)
        - Limpa o erro_robo (pra não confundir com erro anterior)
 
    Retorna True se reprocessou, False se não encontrou ou status inválido.
    """
    sub = db.session.get(Submissao, uuid)
    if not sub:
        logger.warning(f"[REPROCESSAR] UUID não encontrado: {uuid}")
        return False
 
    if sub.status != 'erro_robo':
        logger.warning(f"[REPROCESSAR] UUID {uuid} não está em erro_robo (status: {sub.status})")
        return False
 
    sub.status = 'aprovado'
    sub.erro_robo = None
    db.session.commit()
 
    logger.info(f"[REPROCESSAR] Submissão {uuid} preparada para reprocessamento.")
    return True


# ══════════════════════════════════════════════════════════════
# CONTROLE DE ENVIO AO N8N (C2/A-05)
# ══════════════════════════════════════════════════════════════

def salvar_payload_n8n(uuid, payload):
    """Guarda o payload que (re)enviaremos ao N8N para esta submissão."""
    sub = db.session.get(Submissao, uuid)
    if not sub:
        return False
    sub.n8n_payload = payload
    db.session.commit()
    return True


def marcar_envio_n8n(uuid, status, erro=None):
    """
    Marca o resultado do envio ao N8N.
        status='enviado' → deu certo (limpa o erro)
        status='falhou'  → webhook falhou; guarda a mensagem de erro
    """
    sub = db.session.get(Submissao, uuid)
    if not sub:
        return False
    sub.envio_n8n = status
    sub.n8n_erro = None if status == 'enviado' else (erro or 'Falha ao enviar ao N8N')
    db.session.commit()
    if status == 'falhou':
        logger.warning(f"[N8N] Envio FALHOU | UUID: {uuid} | {sub.n8n_erro}")
    return True


def buscar_payload_n8n(uuid):
    """Retorna o payload guardado para reenvio, ou None."""
    sub = db.session.get(Submissao, uuid)
    return sub.n8n_payload if sub else None


def contar_envios_falhos():
    """Quantas submissões estão com o envio ao N8N pendente (falhou)."""
    return Submissao.query.filter(Submissao.envio_n8n == 'falhou').count()


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
        'erro_robo': 0,
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

    # Quantas fichas falharam no envio ao N8N (alerta do Monitor)
    contagem['envio_falhou'] = contar_envios_falhos()

    return contagem
