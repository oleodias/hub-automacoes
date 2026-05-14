# ══════════════════════════════════════════════════════════════
# routes/notas.py — Controle de Notas Fiscais (Hub Ciamed) — v2
# ══════════════════════════════════════════════════════════════
# v2: SPA único (Kanban + Fornecedores + Panorama em abas).
#     Não existe mais a rota /notas/cadastro — virou aba interna.
#
#   PÁGINA
#     GET  /notas                          → SPA (Kanban/Fornecedores/Panorama)
#
#   API — Listas auxiliares
#     GET  /notas/api/categorias
#     GET  /notas/api/unidades
#
#   API — Fornecedores recorrentes (CRUD completo)
#     GET    /notas/api/fornecedores         (?ativo=1|0|todos, ?unidade=, ?categoria=)
#     GET    /notas/api/fornecedores/<id>
#     POST   /notas/api/fornecedores
#     PUT    /notas/api/fornecedores/<id>
#     PATCH  /notas/api/fornecedores/<id>/toggle
#     DELETE /notas/api/fornecedores/<id>
#
#   API — Notas mensais (Kanban)
#     GET    /notas/api/notas?mes=&ano=
#     POST   /notas/api/notas
#     PATCH  /notas/api/notas/<id>/receber
#     PATCH  /notas/api/notas/<id>/desfazer
#
#   API — Panorama (heatmap anual)
#     GET    /notas/api/panorama?ano=
# ══════════════════════════════════════════════════════════════

from datetime import datetime, date
from flask import Blueprint, render_template, request, jsonify

from extensions import db
from models import (
    NotasCategoria, NotasUnidade, NotasFornecedor, Nota
)
from utils.auth import permissao_required

notas_bp = Blueprint('notas', __name__)


# ══════════════════════════════════════════════════════════════
# Helpers de status / cálculo
# ══════════════════════════════════════════════════════════════

def _status_nota_passada(nota):
    """
    Status de uma nota de um mês JÁ ENCERRADO.
    Retorna 'ok' | 'late' | 'miss'.
    """
    if not nota or not nota.recebida_em:
        return "miss"
    if nota.recebida_em.day <= nota.dia_esperado:
        return "ok"
    return "late"


def _pontualidade_fornecedor(fornecedor_id, hoje):
    """
    Razão de notas entregues no prazo, considerando só meses
    estritamente passados. Retorna float 0..1, ou None se ainda
    não há histórico.
    """
    notas = Nota.query.filter_by(fornecedor_recorrente_id=fornecedor_id).all()
    ok = total = 0
    for n in notas:
        if (n.ano, n.mes) >= (hoje.year, hoje.month):
            continue  # mês atual ou futuro não conta
        total += 1
        if _status_nota_passada(n) == "ok":
            ok += 1
    return (ok / total) if total > 0 else None


def _valor_medio_fornecedor(fornecedor_id):
    """Média dos valores líquidos lançados. None se ainda sem dados."""
    notas = Nota.query.filter(
        Nota.fornecedor_recorrente_id == fornecedor_id,
        Nota.valor_liquido.isnot(None)
    ).all()
    valores = [float(n.valor_liquido) for n in notas]
    return (sum(valores) / len(valores)) if valores else None


# ══════════════════════════════════════════════════════════════
# Helpers de serialização
# ══════════════════════════════════════════════════════════════

def serializar_categoria(c):
    return {"id": c.id, "nome": c.nome, "ordem": c.ordem, "ativa": c.ativa}


def serializar_unidade(u):
    return {"id": u.id, "nome": u.nome, "short": u.short,
            "ordem": u.ordem, "ativa": u.ativa}


def serializar_fornecedor(f, hoje=None):
    """
    FornecedorRecorrente → dict no formato que o React (fornecedores.jsx
    e panorama.jsx) espera: chaves camelCase, com pontualidade e
    valorMedio computados.
    """
    if hoje is None:
        hoje = date.today()

    valor_medio = (float(f.valor_medio) if f.valor_medio is not None
                   else _valor_medio_fornecedor(f.id))

    return {
        "id": f.id,
        "fornecedor": f.fornecedor,
        "cnpj": f.cnpj or "",
        "categoria": f.categoria_id,        # React usa 'categoria'
        "unidade": f.unidade_id,            # React usa 'unidade'
        "diaEsperado": f.dia_esperado,
        "retencaoPadrao": f.retencao_padrao,
        "valorMedio": valor_medio,
        "observacoes": f.observacoes or "",
        "iniciadoEm": f.iniciado_em or "",
        "ativo": f.ativo,
        "pontualidade": _pontualidade_fornecedor(f.id, hoje),
    }


def serializar_nota(n):
    """Nota → dict no formato camelCase que o app.jsx espera."""
    return {
        "id": n.id,
        "fornecedor": n.fornecedor,
        "unidade": n.unidade_id,
        "categoria": n.categoria_id,
        "cnpj": n.cnpj or "",
        "diaEsperado": n.dia_esperado,
        "recebidaEm": n.recebida_em.isoformat() if n.recebida_em else None,
        "nfNumero": n.nf_numero or "",
        "valor": float(n.valor_liquido) if n.valor_liquido is not None else None,
        "retencao": n.retencao,
        "avulsa": n.avulsa,
        "observacoes": n.observacoes or "",
        "historico": [],
    }


def _parse_date(val):
    """Aceita ISO date ('2026-05-07') ou None. Devolve date ou None."""
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)[:10]).date()
    except (ValueError, TypeError):
        return None


def _validar_fornecedor_payload(data):
    """
    Valida o corpo de criação/edição de fornecedor.
    Retorna (erro_str | None, dados_limpos | None).
    """
    nome = (data.get('fornecedor') or '').strip()
    cat = data.get('categoria_id')
    uni = data.get('unidade_id')
    dia = data.get('dia_esperado')

    if not nome:
        return "Nome do fornecedor é obrigatório", None
    if not cat or not db.session.get(NotasCategoria, cat):
        return "Categoria inválida", None
    if not uni or not db.session.get(NotasUnidade, uni):
        return "Unidade inválida", None
    try:
        dia = int(dia)
        if not (1 <= dia <= 31):
            raise ValueError
    except (TypeError, ValueError):
        return "Dia esperado deve ser entre 1 e 31", None

    # valor_medio é opcional
    valor_medio = data.get('valor_medio')
    if valor_medio in ('', None):
        valor_medio = None
    else:
        try:
            valor_medio = float(valor_medio)
        except (TypeError, ValueError):
            return "Valor médio inválido", None

    limpo = {
        "fornecedor": nome,
        "cnpj": (data.get('cnpj') or '').strip() or None,
        "categoria_id": cat,
        "unidade_id": uni,
        "dia_esperado": dia,
        "valor_medio": valor_medio,
        "retencao_padrao": bool(data.get('retencao_padrao', False)),
        "observacoes": (data.get('observacoes') or '').strip() or None,
    }
    return None, limpo


# ══════════════════════════════════════════════════════════════
# PÁGINA
# ══════════════════════════════════════════════════════════════

@notas_bp.route('/notas')
@permissao_required('notas')
def kanban_notas():
    """SPA único — Kanban + Fornecedores + Panorama (abas internas)."""
    return render_template('notas_kanban.html')


# ══════════════════════════════════════════════════════════════
# API — Listas auxiliares
# ══════════════════════════════════════════════════════════════

@notas_bp.route('/notas/api/categorias', methods=['GET'])
@permissao_required('notas')
def api_listar_categorias():
    incluir_inativas = request.args.get('incluir_inativas') == '1'
    q = NotasCategoria.query
    if not incluir_inativas:
        q = q.filter_by(ativa=True)
    cats = q.order_by(NotasCategoria.ordem, NotasCategoria.nome).all()
    return jsonify([serializar_categoria(c) for c in cats])


@notas_bp.route('/notas/api/unidades', methods=['GET'])
@permissao_required('notas')
def api_listar_unidades():
    incluir_inativas = request.args.get('incluir_inativas') == '1'
    q = NotasUnidade.query
    if not incluir_inativas:
        q = q.filter_by(ativa=True)
    unidades = q.order_by(NotasUnidade.ordem, NotasUnidade.nome).all()
    return jsonify([serializar_unidade(u) for u in unidades])


# ══════════════════════════════════════════════════════════════
# API — Fornecedores recorrentes (CRUD)
# ══════════════════════════════════════════════════════════════

@notas_bp.route('/notas/api/fornecedores', methods=['GET'])
@permissao_required('notas')
def api_listar_fornecedores():
    """
    Lista fornecedores. Filtros opcionais:
        ?ativo=1|0|todos   (default: todos)
        ?unidade=ID
        ?categoria=ID
    """
    q = NotasFornecedor.query

    ativo = request.args.get('ativo', 'todos')
    if ativo == '1':
        q = q.filter_by(ativo=True)
    elif ativo == '0':
        q = q.filter_by(ativo=False)

    unidade = request.args.get('unidade')
    if unidade:
        q = q.filter_by(unidade_id=unidade)

    categoria = request.args.get('categoria')
    if categoria:
        q = q.filter_by(categoria_id=categoria)

    forns = q.order_by(NotasFornecedor.fornecedor, NotasFornecedor.unidade_id).all()
    hoje = date.today()
    return jsonify([serializar_fornecedor(f, hoje) for f in forns])


@notas_bp.route('/notas/api/fornecedores/<int:fid>', methods=['GET'])
@permissao_required('notas')
def api_obter_fornecedor(fid):
    f = db.session.get(NotasFornecedor, fid)
    if not f:
        return jsonify({"erro": "Fornecedor não encontrado"}), 404
    return jsonify(serializar_fornecedor(f))


@notas_bp.route('/notas/api/fornecedores', methods=['POST'])
@permissao_required('notas')
def api_criar_fornecedor():
    """Cria um novo fornecedor recorrente."""
    data = request.get_json() or {}
    erro, limpo = _validar_fornecedor_payload(data)
    if erro:
        return jsonify({"erro": erro}), 400

    hoje = date.today()
    f = NotasFornecedor(
        fornecedor=limpo['fornecedor'],
        cnpj=limpo['cnpj'],
        categoria_id=limpo['categoria_id'],
        unidade_id=limpo['unidade_id'],
        dia_esperado=limpo['dia_esperado'],
        valor_medio=limpo['valor_medio'],
        retencao_padrao=limpo['retencao_padrao'],
        observacoes=limpo['observacoes'],
        iniciado_em=f"{hoje.year}-{hoje.month:02d}",
        ativo=True,
    )
    db.session.add(f)
    db.session.commit()
    return jsonify(serializar_fornecedor(f, hoje)), 201


@notas_bp.route('/notas/api/fornecedores/<int:fid>', methods=['PUT'])
@permissao_required('notas')
def api_atualizar_fornecedor(fid):
    """Atualiza um fornecedor inteiro."""
    f = db.session.get(NotasFornecedor, fid)
    if not f:
        return jsonify({"erro": "Fornecedor não encontrado"}), 404

    data = request.get_json() or {}
    erro, limpo = _validar_fornecedor_payload(data)
    if erro:
        return jsonify({"erro": erro}), 400

    f.fornecedor = limpo['fornecedor']
    f.cnpj = limpo['cnpj']
    f.categoria_id = limpo['categoria_id']
    f.unidade_id = limpo['unidade_id']
    f.dia_esperado = limpo['dia_esperado']
    f.valor_medio = limpo['valor_medio']
    f.retencao_padrao = limpo['retencao_padrao']
    f.observacoes = limpo['observacoes']
    if 'ativo' in data:
        f.ativo = bool(data['ativo'])

    db.session.commit()
    return jsonify(serializar_fornecedor(f))


@notas_bp.route('/notas/api/fornecedores/<int:fid>/toggle', methods=['PATCH'])
@permissao_required('notas')
def api_toggle_fornecedor(fid):
    """Inverte o flag ativo (pausar / reativar)."""
    f = db.session.get(NotasFornecedor, fid)
    if not f:
        return jsonify({"erro": "Fornecedor não encontrado"}), 404

    f.ativo = not f.ativo
    db.session.commit()
    return jsonify(serializar_fornecedor(f))


@notas_bp.route('/notas/api/fornecedores/<int:fid>', methods=['DELETE'])
@permissao_required('notas')
def api_remover_fornecedor(fid):
    """
    Remove um fornecedor recorrente DEFINITIVAMENTE.

    Importante: as notas mensais já geradas a partir dele NÃO são
    apagadas — elas guardam os dados denormalizados (nome, cnpj,
    categoria, etc.), então o histórico do Kanban continua íntegro.
    Apenas o vínculo (fornecedor_recorrente_id) fica órfão, o que é
    inofensivo. Se preferir não perder o cadastro, use o toggle
    (pausar) em vez de deletar.
    """
    f = db.session.get(NotasFornecedor, fid)
    if not f:
        return jsonify({"erro": "Fornecedor não encontrado"}), 404

    # Desvincula as notas já geradas (preserva histórico)
    Nota.query.filter_by(fornecedor_recorrente_id=fid).update(
        {Nota.fornecedor_recorrente_id: None}
    )

    db.session.delete(f)
    db.session.commit()
    return jsonify({"ok": True, "removido": fid})


# ══════════════════════════════════════════════════════════════
# API — Notas mensais (Kanban)
# ══════════════════════════════════════════════════════════════

def _gerar_notas_do_mes(mes, ano):
    """
    Garante que existam notas para todos os fornecedores ativos
    neste mês/ano. Idempotente.
    """
    criadas = 0
    fornecedores = NotasFornecedor.query.filter_by(ativo=True).all()

    for f in fornecedores:
        existe = Nota.query.filter_by(
            mes=mes, ano=ano, fornecedor_recorrente_id=f.id
        ).first()
        if existe:
            continue

        nova = Nota(
            mes=mes,
            ano=ano,
            fornecedor_recorrente_id=f.id,
            fornecedor=f.fornecedor,
            cnpj=f.cnpj,
            categoria_id=f.categoria_id,
            unidade_id=f.unidade_id,
            dia_esperado=f.dia_esperado,
            retencao=f.retencao_padrao,   # herda o padrão do fornecedor
            avulsa=False,
        )
        db.session.add(nova)
        criadas += 1

    if criadas:
        db.session.commit()
    return criadas


@notas_bp.route('/notas/api/notas', methods=['GET'])
@permissao_required('notas')
def api_listar_notas():
    """Lista notas do mês/ano. Auto-gera a partir dos fornecedores ativos."""
    try:
        mes = int(request.args.get('mes'))
        ano = int(request.args.get('ano'))
    except (TypeError, ValueError):
        return jsonify({"erro": "Parâmetros 'mes' e 'ano' são obrigatórios"}), 400

    if not (1 <= mes <= 12):
        return jsonify({"erro": "Mês deve ser entre 1 e 12"}), 400

    _gerar_notas_do_mes(mes, ano)

    notas = (Nota.query
             .filter_by(mes=mes, ano=ano)
             .order_by(Nota.dia_esperado, Nota.fornecedor)
             .all())
    return jsonify([serializar_nota(n) for n in notas])


@notas_bp.route('/notas/api/notas', methods=['POST'])
@permissao_required('notas')
def api_criar_nota():
    """Cria uma nota AVULSA."""
    data = request.get_json() or {}

    try:
        mes = int(data.get('mes'))
        ano = int(data.get('ano'))
    except (TypeError, ValueError):
        return jsonify({"erro": "mes/ano obrigatórios"}), 400

    nome = (data.get('fornecedor') or '').strip()
    cat = data.get('categoria')
    uni = data.get('unidade')
    if not (nome and cat and uni):
        return jsonify({"erro": "fornecedor, categoria e unidade obrigatórios"}), 400

    try:
        dia = int(data.get('diaEsperado') or 1)
    except (TypeError, ValueError):
        dia = 1

    n = Nota(
        mes=mes,
        ano=ano,
        fornecedor_recorrente_id=None,
        fornecedor=nome,
        cnpj=(data.get('cnpj') or '').strip() or None,
        categoria_id=cat,
        unidade_id=uni,
        dia_esperado=dia,
        recebida_em=_parse_date(data.get('recebidaEm')),
        nf_numero=(data.get('nfNumero') or '').strip() or None,
        valor_liquido=data.get('valor'),
        retencao=bool(data.get('retencao', False)),
        avulsa=True,
        observacoes=(data.get('observacoes') or '').strip() or None,
    )
    db.session.add(n)
    db.session.commit()
    return jsonify(serializar_nota(n)), 201


@notas_bp.route('/notas/api/notas/<int:nid>/receber', methods=['PATCH'])
@permissao_required('notas')
def api_receber_nota(nid):
    """Marca uma nota como recebida."""
    n = db.session.get(Nota, nid)
    if not n:
        return jsonify({"erro": "Nota não encontrada"}), 404

    data = request.get_json() or {}
    n.recebida_em = _parse_date(data.get('recebidaEm')) or date.today()
    n.nf_numero = (data.get('nfNumero') or '').strip() or None
    n.valor_liquido = data.get('valor')
    if 'retencao' in data:
        n.retencao = bool(data['retencao'])
    if 'observacoes' in data:
        n.observacoes = (data['observacoes'] or '').strip() or None

    db.session.commit()
    return jsonify(serializar_nota(n))


@notas_bp.route('/notas/api/notas/<int:nid>/desfazer', methods=['PATCH'])
@permissao_required('notas')
def api_desfazer_nota(nid):
    """Desfaz o recebimento (limpa data, NF, valor)."""
    n = db.session.get(Nota, nid)
    if not n:
        return jsonify({"erro": "Nota não encontrada"}), 404

    n.recebida_em = None
    n.nf_numero = None
    n.valor_liquido = None
    db.session.commit()
    return jsonify(serializar_nota(n))


# ══════════════════════════════════════════════════════════════
# API — Panorama (heatmap anual)
# ══════════════════════════════════════════════════════════════

@notas_bp.route('/notas/api/panorama', methods=['GET'])
@permissao_required('notas')
def api_panorama():
    """
    Retorna o status histórico de cada fornecedor, mês a mês, do ano
    pedido. SÓ os meses já encerrados — o mês atual e os futuros o
    próprio frontend resolve (com dados ao vivo do Kanban).

    Resposta:
        [
          { "fornecedor_id": 5, "mensal": { "1": "ok", "2": "miss", ... } },
          ...
        ]
    onde cada status ∈ {'ok', 'late', 'miss'}.
    """
    try:
        ano = int(request.args.get('ano'))
    except (TypeError, ValueError):
        return jsonify({"erro": "Parâmetro 'ano' é obrigatório"}), 400

    hoje = date.today()
    fornecedores = NotasFornecedor.query.all()

    resultado = []
    for f in fornecedores:
        notas_ano = Nota.query.filter_by(
            fornecedor_recorrente_id=f.id, ano=ano
        ).all()
        notas_por_mes = {n.mes: n for n in notas_ano}

        mensal = {}
        for mes in range(1, 13):
            # só meses estritamente passados
            if (ano, mes) >= (hoje.year, hoje.month):
                continue
            mensal[mes] = _status_nota_passada(notas_por_mes.get(mes))

        resultado.append({"fornecedor_id": f.id, "mensal": mensal})

    return jsonify(resultado)
