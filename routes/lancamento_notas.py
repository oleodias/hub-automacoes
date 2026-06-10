# ══════════════════════════════════════════════════════════════
# routes/lancamento_notas.py — Blueprint do Lançamento de Notas
# ══════════════════════════════════════════════════════════════
# Contém:
#   1. Página principal /lancar_nota (renderiza o template)
#   2. POST /notas/upload_xml → recebe XML, parseia, devolve dict
#   3. GET  /notas/dropdowns  → CCs agrupados + operações
#   4. POST /notas/lancar     → cria o lançamento na fila
#   5. GET  /notas/a_rever    → lista de notas com falha (placeholder)
#   6. GET  /monitor_notas    → monitor (placeholder)
#
# Os templates HTML virão no Pacote 5.
# ══════════════════════════════════════════════════════════════

import os
import uuid as uuid_lib
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

import banco_notas
from automacoes.lancamento_notas.parser_xml import parsear_xml_nfe
from utils.auth import permissao_required

import logging
logger = logging.getLogger(__name__)

lancamento_notas_bp = Blueprint('lancamento_notas', __name__)


# ══════════════════════════════════════════════════════════════
# CONSTANTES DE PATH
# ══════════════════════════════════════════════════════════════

PASTA_BASE_XMLS = os.path.join('xmls', 'lancamento_notas')
PASTA_RECEBIDOS = os.path.join(PASTA_BASE_XMLS, 'recebidos')
PASTA_TMP       = os.path.join(PASTA_BASE_XMLS, 'tmp')
PASTA_ERROS     = os.path.join(PASTA_BASE_XMLS, 'erros')


def _garantir_pastas():
    """Cria a árvore de pastas se ainda não existir."""
    for pasta in [PASTA_RECEBIDOS, PASTA_TMP, PASTA_ERROS]:
        os.makedirs(pasta, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# PÁGINAS (renderizam HTML)
# ══════════════════════════════════════════════════════════════

@lancamento_notas_bp.route('/lancar_nota')
@permissao_required('lancamento_notas')
def pagina_lancar_nota():
    """Tela principal com as 4 abas."""
    return render_template('lancar_nota.html')


@lancamento_notas_bp.route('/notas_a_rever')
@permissao_required('lancamento_notas')
def pagina_notas_a_rever():
    """Tela de notas que falharam e aguardam decisão manual."""
    return render_template('notas_a_rever.html')


@lancamento_notas_bp.route('/monitor_notas')
@permissao_required('lancamento_notas')
def pagina_monitor_notas():
    """Tela de monitor (histórico completo)."""
    return render_template('monitor_notas.html')


# ══════════════════════════════════════════════════════════════
# UPLOAD DO XML
# ══════════════════════════════════════════════════════════════

@lancamento_notas_bp.route('/notas/upload_xml', methods=['POST'])
@permissao_required('lancamento_notas')
def upload_xml():
    """
    Recebe um XML de NF-e (multipart/form-data, campo 'xml'),
    salva no disco, parseia e devolve os dados extraídos.

    Fluxo:
        1. Valida que recebeu o arquivo e é .xml
        2. Salva em PASTA_TMP com nome aleatório (evita colisão)
        3. Parseia
        4. Se OK: move para PASTA_RECEBIDOS/AAAA/MM/{chave}.xml
        5. Se erro: deleta o tmp e retorna a mensagem
    """
    _garantir_pastas()

    if 'xml' not in request.files:
        return jsonify({'status': 'erro', 'msg': 'Nenhum arquivo enviado.'}), 400

    arquivo = request.files['xml']
    if not arquivo.filename:
        return jsonify({'status': 'erro', 'msg': 'Nome de arquivo vazio.'}), 400

    if not arquivo.filename.lower().endswith('.xml'):
        return jsonify({'status': 'erro', 'msg': 'O arquivo precisa ser .xml.'}), 400

    # 1) Salva temporariamente com nome aleatório
    tmp_nome = f'upload_{uuid_lib.uuid4().hex}.xml'
    tmp_path = os.path.join(PASTA_TMP, tmp_nome)
    arquivo.save(tmp_path)

    # 2) Tenta parsear. Qualquer falha → deleta o tmp e retorna erro
    try:
        dados = parsear_xml_nfe(tmp_path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        logger.warning(f"[NOTAS] Upload rejeitado: {e}")
        return jsonify({
            'status': 'erro',
            'msg': f'Não consegui ler o XML: {e}',
        }), 400

    # 3) Move pro destino final, organizado por ano/mês
    chave        = dados.get('chave_acesso') or uuid_lib.uuid4().hex
    data_emissao = dados.get('data_emissao') or datetime.now().strftime('%Y-%m-%d')
    ano = data_emissao[:4]
    mes = data_emissao[5:7]

    pasta_final = os.path.join(PASTA_RECEBIDOS, ano, mes)
    os.makedirs(pasta_final, exist_ok=True)

    nome_final = secure_filename(f'{chave}.xml')
    destino    = os.path.join(pasta_final, nome_final)

    # Se já existe (mesmo XML enviado antes), adiciona timestamp
    if os.path.exists(destino):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_final = secure_filename(f'{chave}_{timestamp}.xml')
        destino    = os.path.join(pasta_final, nome_final)

    os.rename(tmp_path, destino)

    logger.info(
        f"[NOTAS] XML recebido | NF {dados.get('numero_nota')} | "
        f"{dados.get('emitente', {}).get('razao_social', '')} | path={destino}"
    )

    return jsonify({
        'status':   'ok',
        'xml_path': destino,
        'dados':    dados,
    })


# ══════════════════════════════════════════════════════════════
# DROPDOWNS (consumidos pelo JS da tela)
# ══════════════════════════════════════════════════════════════

@lancamento_notas_bp.route('/notas/dropdowns', methods=['GET'])
@permissao_required('lancamento_notas')
def dropdowns():
    """
    Retorna num único payload tudo que o frontend precisa pra popular
    os dropdowns (CCs agrupados por empresa + operações).
    Evita 2 requests separados na hora de abrir a tela.
    """
    return jsonify({
        'centros_custo': banco_notas.listar_centros_custo_agrupados(),
        'operacoes':     banco_notas.listar_operacoes(),
    })


# ══════════════════════════════════════════════════════════════
# LANÇAR (criação do registro na fila)
# ══════════════════════════════════════════════════════════════

@lancamento_notas_bp.route('/notas/lancar', methods=['POST'])
@permissao_required('lancamento_notas')
def lancar():
    """
    Recebe os dados completos do formulário e cria o lançamento
    com status 'na_fila'. O robô vai consumir daqui.

    Payload esperado (JSON):
    {
        "xml_path":  "...",
        "dados_xml": { ...retorno do parser... },
        "dados_complementares": {
            "centros_custo": [
                {"item_numero": 1, "codigo_cc": "01100002"},
                {"item_numero": 2, "codigo_cc": "01100002"}
            ],
            "parcelas": [
                {"numero": "001", "data_vencimento": "2026-05-06", "valor": 2637.28},
                ...
            ],
            "data_recebimento":  "2026-05-08",
            "data_base":         "2026-05-08",
            "operacao_codigo":   "100"
        }
    }
    """
    payload = request.get_json(silent=True) or {}

    dados_xml            = payload.get('dados_xml')             or {}
    dados_complementares = payload.get('dados_complementares')  or {}
    xml_path             = payload.get('xml_path')              or ''

    # ── Validações ─────────────────────────────────────────────

    erros = _validar_lancamento(dados_xml, dados_complementares)
    if erros:
        return jsonify({'status': 'erro', 'erros': erros}), 400

    # ── Persiste ──────────────────────────────────────────────

    try:
        lanc_id = banco_notas.salvar_lancamento(
            dados_xml            = dados_xml,
            dados_complementares = dados_complementares,
            xml_path             = xml_path,
            usuario_id           = session.get('usuario_id'),
            usuario_nome         = session.get('usuario_nome', 'Sistema'),
            tipo_nota            = 'danfe',
        )
    except banco_notas.LancamentoDuplicado as dup:
        existente = dup.existente
        status_legivel = {
            'na_fila':    'já está na fila',
            'executando': 'está sendo lançada agora pelo robô',
            'concluida':  'já foi lançada com sucesso',
            'a_rever':    'está na aba "A Rever"',
        }.get(existente.get('status'), 'já existe no sistema')
        return jsonify({
            'status': 'duplicado',
            'msg': f'Esta nota {status_legivel}. Para reenviar, cancele o '
                   f'lançamento anterior (nº {existente.get("numero_nota")}).',
            'existente': existente,
        }), 409
    except Exception as e:
        logger.exception(f"[NOTAS] Falha ao salvar lançamento: {e}")
        return jsonify({'status': 'erro', 'msg': f'Erro ao salvar: {e}'}), 500

    return jsonify({
        'status':  'ok',
        'id':      lanc_id,
        'msg':     'Lançamento enviado para a fila com sucesso!',
    })


def _validar_lancamento(dados_xml, dados_complementares):
    """
    Roda todas as validações de negócio antes de aceitar o lançamento.
    Retorna lista de strings de erro. Lista vazia = tudo ok.
    """
    erros = []

    # 1) Campos obrigatórios dos dados_complementares
    obrigatorios = ['data_recebimento', 'data_base', 'operacao_codigo']
    for campo in obrigatorios:
        if not dados_complementares.get(campo):
            erros.append(f"Campo obrigatório ausente: '{campo}'.")

    # 2) Cada item da nota precisa ter um centro de custo selecionado
    itens          = dados_xml.get('itens', []) or []
    ccs_por_item   = dados_complementares.get('centros_custo', []) or []
    ccs_preenchidos = {c.get('item_numero') for c in ccs_por_item if c.get('codigo_cc')}

    for item in itens:
        if item.get('numero') not in ccs_preenchidos:
            erros.append(
                f"Item #{item.get('numero')} ({item.get('codigo')}) "
                f"está sem centro de custo selecionado."
            )

    # 3) Parcelas: pelo menos uma + soma == total da nota (margem zero)
    parcelas = dados_complementares.get('parcelas', []) or []
    if not parcelas:
        erros.append("É preciso informar pelo menos uma parcela.")
    else:
        for i, p in enumerate(parcelas, 1):
            if not p.get('data_vencimento'):
                erros.append(f"Parcela {i} está sem data de vencimento.")
            if p.get('valor') is None or float(p.get('valor', 0)) <= 0:
                erros.append(f"Parcela {i} está com valor inválido.")

        soma_parcelas = round(sum(float(p.get('valor', 0)) for p in parcelas), 2)
        valor_total   = round(float(dados_xml.get('totais', {}).get('valor_total_nota', 0)), 2)
        # Margem zero: combinado com você porque o NLWeb dá erro com qualquer diferença
        if abs(soma_parcelas - valor_total) >= 0.01:
            erros.append(
                f"A soma das parcelas (R$ {soma_parcelas:.2f}) "
                f"é diferente do total da nota (R$ {valor_total:.2f})."
            )

    return erros


# ══════════════════════════════════════════════════════════════
# APIs DE DADOS (consumidas pelo monitor e pela aba "a rever")
# ══════════════════════════════════════════════════════════════

@lancamento_notas_bp.route('/api/notas/listar', methods=['GET'])
@permissao_required('lancamento_notas')
def api_listar_notas():
    """Lista de lançamentos com filtros. Usada pelo Monitor."""
    notas = banco_notas.listar_lancamentos(
        status          = request.args.get('status'),
        data_de         = request.args.get('data_de'),
        data_ate        = request.args.get('data_ate'),
        busca           = request.args.get('busca'),
        fornecedor_cnpj = request.args.get('fornecedor_cnpj'),
    )
    return jsonify({
        'lancamentos': notas,
        'stats':       banco_notas.estatisticas(),
    })


@lancamento_notas_bp.route('/api/notas/<int:lanc_id>', methods=['GET'])
@permissao_required('lancamento_notas')
def api_buscar_nota(lanc_id):
    """Detalhe de um lançamento (usado pelo modal do monitor)."""
    nota = banco_notas.buscar_lancamento(lanc_id)
    if not nota:
        return jsonify({'status': 'erro', 'msg': 'Lançamento não encontrado.'}), 404
    return jsonify({'status': 'ok', 'nota': nota})


@lancamento_notas_bp.route('/api/notas/<int:lanc_id>/cancelar', methods=['POST'])
@permissao_required('lancamento_notas')
def api_cancelar_nota(lanc_id):
    """Cancela uma nota da aba 'a_rever'."""
    ok = banco_notas.cancelar_lancamento(lanc_id)
    if not ok:
        return jsonify({'status': 'erro', 'msg': 'Lançamento não encontrado.'}), 404
    return jsonify({'status': 'ok'})


@lancamento_notas_bp.route('/api/notas/<int:lanc_id>/relancar', methods=['POST'])
@permissao_required('lancamento_notas')
def api_relancar_nota(lanc_id):
    """
    Relança uma nota da aba 'a_rever' (depois que o operador editou).
    Recebe os novos dados_complementares e devolve a nota para a fila.
    """
    payload = request.get_json(silent=True) or {}
    dados_complementares = payload.get('dados_complementares') or {}

    nota = banco_notas.buscar_lancamento(lanc_id)
    if not nota:
        return jsonify({'status': 'erro', 'msg': 'Lançamento não encontrado.'}), 404

    # Revalida com os dados novos antes de relançar
    erros = _validar_lancamento(nota['dados_xml'], dados_complementares)
    if erros:
        return jsonify({'status': 'erro', 'erros': erros}), 400

    banco_notas.atualizar_dados_complementares(lanc_id, dados_complementares)
    banco_notas.atualizar_status(lanc_id, 'na_fila')

    return jsonify({'status': 'ok', 'msg': 'Lançamento devolvido para a fila.'})
