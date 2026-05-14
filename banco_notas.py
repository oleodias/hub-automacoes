# ══════════════════════════════════════════════════════════════
# banco_notas.py — Operações do Banco para Lançamento de Notas
# ══════════════════════════════════════════════════════════════
# Espelho do banco_cadastros.py, mas para o modelo LancamentoNota
# e suas tabelas auxiliares (CentroCusto, OperacaoNota).
#
# Esta é a ÚNICA camada do módulo de Lançamento de Notas que toca
# o PostgreSQL diretamente. Todo o restante (routes, robô, parser)
# chama funções daqui — assim, se um dia migrarmos de banco ou
# precisarmos otimizar uma query, é um lugar só pra mudar.
# ══════════════════════════════════════════════════════════════

import logging
from datetime import datetime
from extensions import db
from models import LancamentoNota, CentroCusto, OperacaoNota

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# HELPER — converte objeto LancamentoNota em dict
# ══════════════════════════════════════════════════════════════

def _lancamento_to_dict(lanc):
    """
    Converte um objeto LancamentoNota do SQLAlchemy em dicionário.
    Centralizando essa conversão aqui, o restante do código sempre
    recebe dict — não precisa lidar com objetos do ORM.
    """
    return {
        'id':                   lanc.id,
        'chave_acesso':         lanc.chave_acesso,
        'numero_nota':          lanc.numero_nota,
        'serie':                lanc.serie,
        'tipo_nota':            lanc.tipo_nota,
        'fornecedor_cnpj':      lanc.fornecedor_cnpj,
        'fornecedor_nome':      lanc.fornecedor_nome,
        # Numeric do Postgres vira Decimal no Python. Converto pra
        # float aqui pra ser JSON-serializable no frontend.
        'valor_total':          float(lanc.valor_total) if lanc.valor_total is not None else 0.0,
        'xml_path':             lanc.xml_path,
        'dados_xml':            lanc.dados_xml or {},
        'dados_complementares': lanc.dados_complementares or {},
        'status':               lanc.status,
        'mensagem_erro':        lanc.mensagem_erro,
        'screenshot_erro':      lanc.screenshot_erro,
        'usuario_id':           lanc.usuario_id,
        'usuario_nome':         lanc.usuario_nome,
        'created_at':           lanc.created_at.strftime('%d/%m/%Y %H:%M') if lanc.created_at else '',
        'updated_at':           lanc.updated_at.strftime('%d/%m/%Y %H:%M') if lanc.updated_at else '',
    }


# ══════════════════════════════════════════════════════════════
# CRUD — LANÇAMENTOS DE NOTAS
# ══════════════════════════════════════════════════════════════

def salvar_lancamento(dados_xml, dados_complementares, xml_path,
                      usuario_id=None, usuario_nome=None, tipo_nota='danfe'):
    """
    Cria um novo lançamento na fila com status 'na_fila'.

    Parâmetros:
        dados_xml            → dict completo retornado por parsear_xml_nfe()
        dados_complementares → dict do formulário (CC por item, parcelas, datas, operação)
        xml_path             → caminho onde o XML foi salvo no disco
        usuario_id           → ID do operador que disparou
        usuario_nome         → nome do operador
        tipo_nota            → 'danfe' (padrão), 'servico' ou 'cupom'

    Retorna o ID do lançamento criado.
    """
    # Extrai dados resumidos do XML para colunas indexadas (busca rápida)
    emitente = dados_xml.get('emitente', {})
    totais   = dados_xml.get('totais', {})

    lanc = LancamentoNota(
        chave_acesso         = dados_xml.get('chave_acesso'),
        numero_nota          = dados_xml.get('numero_nota'),
        serie                = dados_xml.get('serie'),
        tipo_nota            = tipo_nota,
        fornecedor_cnpj      = emitente.get('cnpj'),
        fornecedor_nome      = emitente.get('razao_social'),
        valor_total          = totais.get('valor_total_nota', 0.0),
        xml_path             = xml_path,
        dados_xml            = dados_xml,
        dados_complementares = dados_complementares,
        status               = 'na_fila',
        usuario_id           = usuario_id,
        usuario_nome         = usuario_nome or 'Sistema',
    )

    db.session.add(lanc)
    db.session.commit()

    logger.info(
        f"[NOTAS] Lançamento criado | ID: {lanc.id} | "
        f"NF {lanc.numero_nota} | {lanc.fornecedor_nome}"
    )
    return lanc.id


def buscar_lancamento(lanc_id):
    """
    Retorna um lançamento pelo ID, em formato dict.
    Retorna None se não encontrar.
    """
    lanc = db.session.get(LancamentoNota, lanc_id)
    if not lanc:
        return None
    return _lancamento_to_dict(lanc)


def listar_lancamentos(status=None, data_de=None, data_ate=None,
                       busca=None, fornecedor_cnpj=None):
    """
    Lista lançamentos com filtros opcionais.
    Ordena do mais recente para o mais antigo.

    Filtros:
        status          → 'na_fila' | 'executando' | 'concluida' | 'a_rever' | 'cancelada'
        data_de/ate     → 'dd/mm/yyyy' ou 'yyyy-mm-dd'
        busca           → texto livre (procura em fornecedor_nome e numero_nota)
        fornecedor_cnpj → CNPJ exato (com ou sem máscara)
    """
    query = LancamentoNota.query.order_by(LancamentoNota.created_at.desc())

    if status:
        query = query.filter(LancamentoNota.status == status)

    if busca:
        termo = f'%{busca}%'
        query = query.filter(
            db.or_(
                LancamentoNota.fornecedor_nome.ilike(termo),
                LancamentoNota.numero_nota.ilike(termo),
                LancamentoNota.chave_acesso.ilike(termo),
            )
        )

    if fornecedor_cnpj:
        # Aceita CNPJ formatado ou só dígitos
        cnpj_limpo = ''.join(c for c in fornecedor_cnpj if c.isdigit())
        if cnpj_limpo:
            query = query.filter(LancamentoNota.fornecedor_cnpj == cnpj_limpo)

    if data_de:
        try:
            if '/' in data_de:
                dt_de = datetime.strptime(data_de, '%d/%m/%Y')
            else:
                dt_de = datetime.strptime(data_de, '%Y-%m-%d')
            query = query.filter(LancamentoNota.created_at >= dt_de)
        except ValueError:
            pass

    if data_ate:
        try:
            if '/' in data_ate:
                dt_ate = datetime.strptime(data_ate, '%d/%m/%Y')
            else:
                dt_ate = datetime.strptime(data_ate, '%Y-%m-%d')
            dt_ate = dt_ate.replace(hour=23, minute=59, second=59)
            query = query.filter(LancamentoNota.created_at <= dt_ate)
        except ValueError:
            pass

    return [_lancamento_to_dict(l) for l in query.all()]


def atualizar_status(lanc_id, status):
    """
    Atualiza apenas o status de um lançamento.
    Status válidos: 'na_fila' | 'executando' | 'concluida' | 'a_rever' | 'cancelada'
    """
    lanc = db.session.get(LancamentoNota, lanc_id)
    if not lanc:
        logger.warning(f"[NOTAS] ID {lanc_id} não encontrado para atualizar status")
        return False
    lanc.status = status
    db.session.commit()
    logger.info(f"[NOTAS] Status atualizado | ID: {lanc_id} | Status: {status}")
    return True


def atualizar_dados_complementares(lanc_id, dados_complementares):
    """
    Sobrescreve os dados_complementares. Usado quando o usuário
    edita um lançamento 'a_rever' e quer relançar.
    """
    lanc = db.session.get(LancamentoNota, lanc_id)
    if not lanc:
        return False
    lanc.dados_complementares = dados_complementares
    db.session.commit()
    return True


# ══════════════════════════════════════════════════════════════
# CICLO DE VIDA DO LANÇAMENTO
# ══════════════════════════════════════════════════════════════
# Wrappers semânticos do atualizar_status, mais legíveis no código
# que chama. Ex: "marcar_concluida(id)" lê melhor que
# "atualizar_status(id, 'concluida')".
# ══════════════════════════════════════════════════════════════

def marcar_em_execucao(lanc_id):
    """Robô começou a processar este lançamento."""
    return atualizar_status(lanc_id, 'executando')


def marcar_concluida(lanc_id):
    """Robô terminou com sucesso, nota lançada no NLWeb."""
    return atualizar_status(lanc_id, 'concluida')


def mover_para_a_rever(lanc_id, mensagem_erro=None, screenshot_erro=None):
    """
    Robô falhou. Move o lançamento para a aba "A Rever",
    onde o operador decide o que fazer.
    """
    lanc = db.session.get(LancamentoNota, lanc_id)
    if not lanc:
        return False
    lanc.status          = 'a_rever'
    lanc.mensagem_erro   = mensagem_erro
    lanc.screenshot_erro = screenshot_erro
    db.session.commit()
    logger.info(
        f"[NOTAS] Movido para A Rever | ID: {lanc_id} | Erro: {mensagem_erro}"
    )
    return True


def cancelar_lancamento(lanc_id):
    """Usuário decidiu cancelar definitivamente um lançamento da fila 'a_rever'."""
    return atualizar_status(lanc_id, 'cancelada')


# ══════════════════════════════════════════════════════════════
# CONSULTAS PARA TELAS
# ══════════════════════════════════════════════════════════════

def listar_a_rever():
    """Atalho para a página 'Notas a Rever'."""
    return listar_lancamentos(status='a_rever')


def proximo_da_fila():
    """
    Retorna o próximo lançamento aguardando execução, em formato dict.
    Usado pelo robô quando a fila libera. None se não houver.
    """
    lanc = (LancamentoNota.query
            .filter_by(status='na_fila')
            .order_by(LancamentoNota.created_at.asc())  # FIFO
            .first())
    return _lancamento_to_dict(lanc) if lanc else None


def estatisticas():
    """
    Estatísticas para o painel do Monitor.
    Retorna dict com contagens por status + total geral.
    """
    contagens = dict(
        db.session.query(
            LancamentoNota.status,
            db.func.count(LancamentoNota.id)
        ).group_by(LancamentoNota.status).all()
    )

    return {
        'total':       sum(contagens.values()),
        'na_fila':     contagens.get('na_fila', 0),
        'executando':  contagens.get('executando', 0),
        'concluidas':  contagens.get('concluida', 0),
        'a_rever':     contagens.get('a_rever', 0),
        'canceladas':  contagens.get('cancelada', 0),
    }


# ══════════════════════════════════════════════════════════════
# DADOS AUXILIARES — CENTROS DE CUSTO E OPERAÇÕES
# ══════════════════════════════════════════════════════════════

def listar_centros_custo_agrupados():
    """
    Retorna os centros de custo ATIVOS agrupados por empresa, no
    formato perfeito pro <optgroup> do dropdown:

        {
            'Ciamed RS': [
                {'codigo': '01100001', 'descricao': 'Portaria e Recepção'},
                {'codigo': '01100002', 'descricao': 'TI Informatica'},
                ...
            ],
            'Ciamed SP': [...],
            ...
        }
    """
    ccs = (CentroCusto.query
           .filter_by(ativo=True)
           .order_by(CentroCusto.empresa, CentroCusto.codigo)
           .all())

    agrupado = {}
    for cc in ccs:
        empresa = cc.empresa or 'Sem empresa'
        agrupado.setdefault(empresa, []).append({
            'codigo':    cc.codigo,
            'descricao': cc.descricao,
        })
    return agrupado


def listar_operacoes():
    """
    Retorna todas as operações ATIVAS, ordenadas por código.
    Usada pelo autocomplete do campo "Operação" na aba 4.
    """
    ops = (OperacaoNota.query
           .filter_by(ativo=True)
           .order_by(OperacaoNota.codigo)
           .all())
    return [{'codigo': o.codigo, 'descricao': o.descricao} for o in ops]


def buscar_operacao(codigo):
    """Retorna uma operação pelo código exato, ou None."""
    op = OperacaoNota.query.filter_by(codigo=codigo).first()
    if not op:
        return None
    return {'codigo': op.codigo, 'descricao': op.descricao, 'ativo': op.ativo}


def buscar_centro_custo(codigo):
    """Retorna um CC pelo código exato, ou None."""
    cc = CentroCusto.query.filter_by(codigo=codigo).first()
    if not cc:
        return None
    return {
        'codigo':    cc.codigo,
        'descricao': cc.descricao,
        'empresa':   cc.empresa,
        'ativo':     cc.ativo,
    }