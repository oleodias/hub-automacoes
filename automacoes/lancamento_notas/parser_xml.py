# ══════════════════════════════════════════════════════════════
# automacoes/lancamento_notas/parser_xml.py
# ══════════════════════════════════════════════════════════════
# Lê o XML de uma NF-e (modelo 55) e devolve um dict estruturado
# pronto para alimentar as 4 abas do Hub e o robô do NLWeb.
#
# Função principal:
#   parsear_xml_nfe(caminho_xml) → dict
#
# Não faz I/O de banco, não chama o sistema — pura extração.
# Isolar isso aqui significa que se o ERP mudar amanhã, este
# arquivo continua intacto.
# ══════════════════════════════════════════════════════════════

import os
import xml.etree.ElementTree as ET
from typing import Optional

# Namespace padrão da NF-e (Portal Nacional da SEFAZ)
NS = {'n': 'http://www.portalfiscal.inf.br/nfe'}


# ══════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════

def _text(elem: Optional[ET.Element], caminho: str, default: str = '') -> str:
    """
    Extrai texto de um subcaminho dentro do elemento.
    Retorna default se o caminho não existir ou estiver vazio.

    Ex: _text(infNFe, 'n:ide/n:nNF') → '57866'
    """
    if elem is None:
        return default
    achado = elem.find(caminho, NS)
    if achado is None or achado.text is None:
        return default
    return achado.text.strip()


def _to_float(s: str, default: float = 0.0) -> float:
    """Converte string para float. Vazio ou inválido vira default."""
    if not s:
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _formatar_cnpj(cnpj: str) -> str:
    """Formata 14 dígitos como 00.000.000/0000-00. Devolve original se != 14."""
    if not cnpj or len(cnpj) != 14 or not cnpj.isdigit():
        return cnpj
    return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'


# ══════════════════════════════════════════════════════════════
# PARSERS DE CADA SEÇÃO
# ══════════════════════════════════════════════════════════════

def _parsear_emitente(inf_nfe: ET.Element) -> dict:
    """Dados do emitente (quem está VENDENDO — o fornecedor da Ciamed)."""
    emit = inf_nfe.find('n:emit', NS)
    if emit is None:
        return {}

    cnpj = _text(emit, 'n:CNPJ')
    return {
        'cnpj':            cnpj,
        'cnpj_formatado':  _formatar_cnpj(cnpj),
        'razao_social':    _text(emit, 'n:xNome'),
        'fantasia':        _text(emit, 'n:xFant'),
        'ie':              _text(emit, 'n:IE'),
        'crt':             _text(emit, 'n:CRT'),  # Código regime tributário
        'endereco': {
            'logradouro':  _text(emit, 'n:enderEmit/n:xLgr'),
            'numero':      _text(emit, 'n:enderEmit/n:nro'),
            'complemento': _text(emit, 'n:enderEmit/n:xCpl'),
            'bairro':      _text(emit, 'n:enderEmit/n:xBairro'),
            'municipio':   _text(emit, 'n:enderEmit/n:xMun'),
            'uf':          _text(emit, 'n:enderEmit/n:UF'),
            'cep':         _text(emit, 'n:enderEmit/n:CEP'),
        },
        'telefone': _text(emit, 'n:enderEmit/n:fone'),
    }


def _parsear_destinatario(inf_nfe: ET.Element) -> dict:
    """Dados do destinatário (a Ciamed, no nosso caso)."""
    dest = inf_nfe.find('n:dest', NS)
    if dest is None:
        return {}

    cnpj = _text(dest, 'n:CNPJ')
    return {
        'cnpj':           cnpj,
        'cnpj_formatado': _formatar_cnpj(cnpj),
        'razao_social':   _text(dest, 'n:xNome'),
        'ie':             _text(dest, 'n:IE'),
    }


def _parsear_itens(inf_nfe: ET.Element) -> list:
    """
    Lista de itens da nota. Cada item vira uma linha na aba 2
    do hub, onde o usuário escolhe o centro de custo.
    """
    itens = []
    for det in inf_nfe.findall('n:det', NS):
        prod = det.find('n:prod', NS)
        if prod is None:
            continue

        numero_item = det.get('nItem', '')

        itens.append({
            'numero':         int(numero_item) if numero_item.isdigit() else 0,
            'codigo':         _text(prod, 'n:cProd'),
            'codigo_ean':     _text(prod, 'n:cEAN'),
            'descricao':      _text(prod, 'n:xProd'),
            'ncm':            _text(prod, 'n:NCM'),
            'cfop':           _text(prod, 'n:CFOP'),
            'unidade':        _text(prod, 'n:uCom'),
            'quantidade':     _to_float(_text(prod, 'n:qCom')),
            'valor_unitario': _to_float(_text(prod, 'n:vUnCom')),
            'valor_total':    _to_float(_text(prod, 'n:vProd')),
            'valor_desconto': _to_float(_text(prod, 'n:vDesc')),
            'valor_frete':    _to_float(_text(prod, 'n:vFrete')),
        })
    return itens


def _parsear_duplicatas(inf_nfe: ET.Element) -> list:
    """
    Parcelas da fatura. É AQUI que mora a magia da aba 3:
    se vier preenchido, o hub pré-popula tudo.
    """
    duplicatas = []
    cobr = inf_nfe.find('n:cobr', NS)
    if cobr is None:
        return duplicatas

    for dup in cobr.findall('n:dup', NS):
        duplicatas.append({
            'numero':          _text(dup, 'n:nDup'),
            'data_vencimento': _text(dup, 'n:dVenc'),
            'valor':           _to_float(_text(dup, 'n:vDup')),
        })
    return duplicatas


def _parsear_fatura(inf_nfe: ET.Element) -> dict:
    """Dados da fatura (existe quando há cobrança parcelada)."""
    fat = inf_nfe.find('n:cobr/n:fat', NS)
    if fat is None:
        return {}
    return {
        'numero':          _text(fat, 'n:nFat'),
        'valor_original':  _to_float(_text(fat, 'n:vOrig')),
        'valor_desconto':  _to_float(_text(fat, 'n:vDesc')),
        'valor_liquido':   _to_float(_text(fat, 'n:vLiq')),
    }


def _parsear_totais(inf_nfe: ET.Element) -> dict:
    """Totais consolidados da nota (somatórios de ICMS, IPI, etc.)."""
    icms_tot = inf_nfe.find('n:total/n:ICMSTot', NS)
    if icms_tot is None:
        return {}
    return {
        'valor_produtos':       _to_float(_text(icms_tot, 'n:vProd')),
        'valor_frete':          _to_float(_text(icms_tot, 'n:vFrete')),
        'valor_seguro':         _to_float(_text(icms_tot, 'n:vSeg')),
        'valor_desconto':       _to_float(_text(icms_tot, 'n:vDesc')),
        'valor_outras':         _to_float(_text(icms_tot, 'n:vOutro')),
        'valor_total_ipi':      _to_float(_text(icms_tot, 'n:vIPI')),
        'valor_base_icms':      _to_float(_text(icms_tot, 'n:vBC')),
        'valor_total_icms':     _to_float(_text(icms_tot, 'n:vICMS')),
        'valor_total_icms_st':  _to_float(_text(icms_tot, 'n:vST')),
        'valor_total_pis':      _to_float(_text(icms_tot, 'n:vPIS')),
        'valor_total_cofins':   _to_float(_text(icms_tot, 'n:vCOFINS')),
        'valor_total_nota':     _to_float(_text(icms_tot, 'n:vNF')),
    }


def _parsear_pagamentos(inf_nfe: ET.Element) -> list:
    """
    Formas de pagamento (campo <pag>). Existe a partir do layout 4.0.
    Tipos comuns: 01=Dinheiro, 03=Cartão de crédito, 15=Boleto, 99=Outros.
    """
    pags = []
    for det_pag in inf_nfe.findall('n:pag/n:detPag', NS):
        pags.append({
            'tipo':  _text(det_pag, 'n:tPag'),
            'valor': _to_float(_text(det_pag, 'n:vPag')),
        })
    return pags


# ══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════

def parsear_xml_nfe(caminho_xml: str) -> dict:
    """
    Lê o XML de uma NF-e (modelo 55) e devolve um dict completo.

    Levanta:
        FileNotFoundError → se o arquivo não existe
        ValueError        → se não for um XML de NF-e válido
        ET.ParseError     → se o XML estiver corrompido

    Retorno: dict com chaves
        chave_acesso, numero_nota, serie, modelo, data_emissao,
        natureza_operacao, emitente, destinatario, itens, duplicatas,
        fatura, totais, pagamentos, informacoes_adicionais
    """
    if not os.path.exists(caminho_xml):
        raise FileNotFoundError(f'Arquivo XML não encontrado: {caminho_xml}')

    tree = ET.parse(caminho_xml)
    root = tree.getroot()

    # Localiza o <infNFe>, que é a raiz dos dados (independente de assinatura/eventos)
    inf_nfe = root.find('.//n:infNFe', NS)
    if inf_nfe is None:
        raise ValueError(
            'XML inválido: não encontrei o nó <infNFe>. '
            'Verifique se este é mesmo um XML de NF-e modelo 55.'
        )

    ide = inf_nfe.find('n:ide', NS)

    # A chave de acesso fica no atributo Id do <infNFe>, com prefixo "NFe"
    id_attr = inf_nfe.get('Id', '')
    chave_acesso = id_attr.replace('NFe', '') if id_attr.startswith('NFe') else id_attr

    return {
        # ── Cabeçalho ──────────────────────────────────────
        'chave_acesso':      chave_acesso,
        'numero_nota':       _text(ide, 'n:nNF'),
        'serie':             _text(ide, 'n:serie'),
        'modelo':            _text(ide, 'n:mod'),
        'data_emissao':      _text(ide, 'n:dhEmi')[:10],   # só a data (YYYY-MM-DD)
        'data_saida':        _text(ide, 'n:dhSaiEnt')[:10],
        'natureza_operacao': _text(ide, 'n:natOp'),
        'tipo_operacao':     _text(ide, 'n:tpNF'),    # 0=Entrada, 1=Saída
        'finalidade':        _text(ide, 'n:finNFe'),  # 1=Normal, 2=Compl, 3=Ajuste, 4=Dev

        # ── Partes envolvidas ──────────────────────────────
        'emitente':      _parsear_emitente(inf_nfe),
        'destinatario':  _parsear_destinatario(inf_nfe),

        # ── Itens, valores e cobrança ─────────────────────
        'itens':       _parsear_itens(inf_nfe),
        'totais':      _parsear_totais(inf_nfe),
        'duplicatas':  _parsear_duplicatas(inf_nfe),
        'fatura':      _parsear_fatura(inf_nfe),
        'pagamentos':  _parsear_pagamentos(inf_nfe),

        # ── Observações ────────────────────────────────────
        'informacoes_adicionais': _text(inf_nfe, 'n:infAdic/n:infCpl'),
    }