# ══════════════════════════════════════════════════════════════
# routes/clientes.py — Cadastro e Reativação de Clientes
# ══════════════════════════════════════════════════════════════
# Maior blueprint do Hub. Contém:
#   - Página de cadastro/reativação
#   - Ficha digital do cliente
#   - Recebimento de fichas (com enriquecimento CNPJ.ws)
#   - Fluxo de aprovação/reprovação (farmacêutica)
#   - Monitor de cadastros + exportação Excel
#   - Fila de cadastro (integração N8N)
#   - Endpoint de integração N8N → Robô RPA
# ══════════════════════════════════════════════════════════════

import os
import re
import json
from io import BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import requests as req_ext
import uuid as uuid_lib

import banco_cadastros
from utils.cnpj_ws import consultar_cnpj_ws
from utils.fila import cadastro_entrar, cadastro_liberar_proximo
from automacoes.clientes import cadastro_novo
from automacoes.clientes import cadastro_reativacao

import logging
logger = logging.getLogger(__name__)

clientes_bp = Blueprint('clientes', __name__)


# ── Páginas ───────────────────────────────────────────────────

@clientes_bp.route('/cadastro_clientes')
def cadastro_clientes():
    return render_template('cadastro_clientes.html')


@clientes_bp.route('/ficha_cliente')
def ficha_cliente():
    return render_template('ficha_cliente.html')


# ══════════════════════════════════════════════════════════════
# RECEBER FICHA DO CLIENTE
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/receber_ficha', methods=['POST'])
def receber_ficha():

    # ── 1. Verificar se é correção ─────────────────────────────
    uuid_existente = request.form.get('uuid', '').strip()
    is_correcao    = bool(uuid_existente)

    if is_correcao:
        sub_original = banco_cadastros.buscar_submissao(uuid_existente)
        if not sub_original:
            return jsonify({'status': 'erro', 'mensagem': 'UUID inválido ou expirado.'}), 400
        submission_uuid = uuid_existente
        docs_originais  = sub_original['docs_enviados']
    else:
        submission_uuid = str(uuid_lib.uuid4())
        docs_originais  = []

    # ── 2. Extrair campos de texto ─────────────────────────────
    campos = {
        'vendedor':               request.form.get('vendedor',               ''),
        'representante':          request.form.get('representante',           ''),
        'captacao':               request.form.get('captacao',                ''),
        'tipo_cadastro':          request.form.get('tipo_cadastro',           ''),
        'codigo_nl':              request.form.get('codigo_nl',               ''),
        'contribuinte_icms':      request.form.get('contribuinte_icms',       ''),
        'possui_regime_especial': request.form.get('possui_regime_especial',  ''),
        'regra_faturamento':      request.form.get('regra_faturamento',       ''),
        'cnpj':                   request.form.get('cnpj',                    ''),
        'razao_social':           request.form.get('razao_social',            ''),
        'endereco':               request.form.get('endereco',                ''),
        'telefone_empresa':       request.form.get('telefone_empresa',        ''),
        'whatsapp':               request.form.get('whatsapp',                ''),
        'email_xml_1':            request.form.get('email_xml_1',             ''),
        'email_xml_2':            request.form.get('email_xml_2',             ''),
        'email_xml_3':            request.form.get('email_xml_3',             ''),
        'compras_nome':           request.form.get('compras_nome',            ''),
        'compras_tel':            request.form.get('compras_tel',             ''),
        'compras_email':          request.form.get('compras_email',           ''),
        'rec_nome':               request.form.get('rec_nome',                ''),
        'rec_tel':                request.form.get('rec_tel',                 ''),
        'rec_email':              request.form.get('rec_email',               ''),
        'fin_nome':               request.form.get('fin_nome',                ''),
        'fin_tel':                request.form.get('fin_tel',                 ''),
        'fin_email':              request.form.get('fin_email',               ''),
        'farma_nome':             request.form.get('farma_nome',              ''),
        'farma_tel':              request.form.get('farma_tel',               ''),
        'farma_email':            request.form.get('farma_email',             ''),
    }

    # ── 2.1. Enriquecimento via CNPJ.ws ───────────────────────
    cnpj_limpo = re.sub(r'\D', '', campos['cnpj'])
    dados_cnpj_ws = consultar_cnpj_ws(cnpj_limpo)

    campos['cnpj_limpo']               = cnpj_limpo
    campos['nome_fantasia']            = dados_cnpj_ws['nome_fantasia']
    campos['inscricao_estadual']       = dados_cnpj_ws['inscricao_estadual']
    campos['cnae_principal_descricao'] = dados_cnpj_ws['cnae_principal_descricao']
    campos['cep']                      = dados_cnpj_ws['cep']
    campos['logradouro']               = dados_cnpj_ws['logradouro']
    campos['numero']                   = dados_cnpj_ws['numero']
    campos['complemento']              = dados_cnpj_ws['complemento']
    campos['bairro']                   = dados_cnpj_ws['bairro']
    campos['uf']                       = dados_cnpj_ws['uf']
    campos['_cnpj_ws_status']          = dados_cnpj_ws['_cnpj_ws_status']

    # ── 3. Salvar arquivos ─────────────────────────────────────
    lista_docs = [
        'doc_regime_especial', 'doc_alvara', 'doc_crt', 'doc_afe',
        'doc_balanco', 'doc_balancete', 'doc_contrato'
    ]
    pasta_uuid = os.path.join('uploads_fichas', submission_uuid)
    os.makedirs(pasta_uuid, exist_ok=True)

    docs_novos  = []
    docs_manter = json.loads(request.form.get('docs_manter', '[]'))

    for doc_nome in lista_docs:
        arquivo = request.files.get(doc_nome)
        if arquivo and arquivo.filename:
            nome_seguro = secure_filename(arquivo.filename)
            ext         = os.path.splitext(nome_seguro)[1].lower() or '.pdf'
            caminho     = os.path.join(pasta_uuid, f"{doc_nome}{ext}")
            arquivo.save(caminho)
            docs_novos.append(doc_nome)

    # ── 4. Calcular docs finais ────────────────────────────────
    docs_mantidos_validos = [d for d in docs_manter if d in docs_originais]
    docs_finais           = list(set(docs_novos + docs_mantidos_validos))

    # ── 5. Categorizar documentos ──────────────────────────────
    if is_correcao:
        docs_ja_existentes = [d for d in docs_mantidos_validos]
        docs_substituidos  = [d for d in docs_novos if d in docs_originais]
        docs_adicionados   = [d for d in docs_novos if d not in docs_originais]
        nova_tentativa = banco_cadastros.incrementar_tentativa(
            submission_uuid, campos, docs_finais
        )
    else:
        docs_ja_existentes = []
        docs_substituidos  = []
        docs_adicionados   = []
        nova_tentativa     = 1
        banco_cadastros.salvar_submissao(
            submission_uuid, campos['cnpj'], campos['razao_social'],
            campos, docs_finais
        )

    # ── 6. Nomes legíveis dos docs ─────────────────────────────
    nomes_legiveis = {
        'doc_regime_especial': 'Regime Especial de ICMS',
        'doc_alvara':          'Alvará Sanitário',
        'doc_crt':             'Certidão de Regularidade',
        'doc_afe':             'Publicação AFE / AE',
        'doc_balanco':         'Último Balanço e DRE',
        'doc_balancete':       'Balancete (< 90 dias)',
        'doc_contrato':        'Contrato Social',
    }

    def nomes(lista):
        return ', '.join(nomes_legiveis.get(d, d) for d in lista) if lista else '—'

    # ── 7. Payload para o N8N ──────────────────────────────────
    payload_n8n = {
        **campos,
        'uuid':               submission_uuid,
        'tentativa':          nova_tentativa,
        'is_correcao':        str(is_correcao).lower(),
        'docs_ja_existentes': nomes(docs_ja_existentes),
        'docs_substituidos':  nomes(docs_substituidos),
        'docs_adicionados':   nomes(docs_adicionados),
    }

    # ── 8. Disparar para o N8N ─────────────────────────────────
    N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_CADASTRO')
    payload_str     = {k: str(v) for k, v in payload_n8n.items()}

    arquivos_abertos = {}
    pasta = os.path.join('uploads_fichas', submission_uuid)

    if os.path.exists(pasta):
        for arquivo in os.listdir(pasta):
            nome_sem_ext = os.path.splitext(arquivo)[0]
            caminho      = os.path.join(pasta, arquivo)
            if nome_sem_ext in docs_finais:
                arquivos_abertos[nome_sem_ext] = (
                    arquivo, open(caminho, 'rb'), 'application/octet-stream'
                )

    try:
        resposta_n8n = req_ext.post(
            N8N_WEBHOOK_URL, data=payload_str,
            files=arquivos_abertos if arquivos_abertos else None,
            timeout=60
        )
        logger.info(f"[N8N] Status: {resposta_n8n.status_code} | UUID: {submission_uuid}")
        return jsonify({'status': 'ok', 'uuid': submission_uuid})
    except Exception as e:
        logger.error(f"[N8N] Erro ao disparar webhook: {e}")
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500
    finally:
        for nome, (_, fp, _) in arquivos_abertos.items():
            try:
                fp.close()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
# API: dados de uma submissão (pré-preenchimento na correção)
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/api/ficha/<submission_uuid>')
def api_ficha(submission_uuid):
    sub = banco_cadastros.buscar_submissao(submission_uuid)
    if not sub:
        return jsonify({'erro': 'Submissão não encontrada'}), 404
    return jsonify({
        'dados':              sub['dados_json'],
        'docs_enviados':      sub['docs_enviados'],
        'motivos_reprovacao': sub['motivos_reprovacao'],
        'tentativa':          sub['tentativa'],
        'razao_social':       sub['razao_social'],
        'cnpj':               sub['cnpj'],
    })


# ══════════════════════════════════════════════════════════════
# Aprovação / Reprovação (farmacêutica via email)
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/confirmar')
def confirmar_acao():
    acao       = request.args.get('acao',      '')
    empresa    = request.args.get('empresa',   '')
    resume_url = request.args.get('resumeUrl', '')
    motivo     = request.args.get('motivo',    '')
    uuid_ficha = request.args.get('uuid',      '')

    if not resume_url:
        return "Parâmetro resumeUrl ausente.", 400

    try:
        if acao == 'aprovar':
            req_ext.get(resume_url, params={'decisao': 'aprovar'}, timeout=10)
            if uuid_ficha:
                banco_cadastros.atualizar_status(uuid_ficha, 'aprovado')
        elif acao == 'reprovar':
            req_ext.get(resume_url, params={'decisao': 'reprovar', 'motivo': motivo}, timeout=10)
            if uuid_ficha and motivo:
                banco_cadastros.registrar_reprovacao(uuid_ficha, motivo)
        elif acao == 'mascaras':
            req_ext.get(resume_url, params={'mascaras': 'confirmadas'}, timeout=10)
    except Exception as e:
        logger.warning(f"Aviso ao chamar N8N: {e}")

    return render_template('confirmar_acao.html', acao=acao, empresa=empresa, motivo=motivo)


@clientes_bp.route('/motivo_reprovacao')
def motivo_reprovacao():
    resume_url = request.args.get('resumeUrl', '')
    empresa    = request.args.get('empresa',   '')
    cnpj       = request.args.get('cnpj',      '')
    uuid_ficha = request.args.get('uuid',      '')
    return render_template(
        'motivo_reprovacao.html',
        resume_url=resume_url, empresa=empresa,
        cnpj=cnpj, uuid=uuid_ficha
    )


# ══════════════════════════════════════════════════════════════
# Monitor de Cadastros
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/monitor_cadastros')
def monitor_cadastros():
    return render_template('monitor_cadastros.html')


@clientes_bp.route('/api/monitor_cadastros')
def api_monitor_cadastros():
    cadastros = banco_cadastros.listar_submissoes(
        status   = request.args.get('status'),
        tipo     = request.args.get('tipo'),
        busca    = request.args.get('busca'),
        data_de  = request.args.get('data_de'),
        data_ate = request.args.get('data_ate'),
    )
    stats = banco_cadastros.stats_submissoes()
    return jsonify({'cadastros': cadastros, 'stats': stats})


@clientes_bp.route('/download_doc/<uuid>/<doc_nome>')
def download_doc(uuid, doc_nome):
    pasta_cliente = os.path.join(os.getcwd(), 'uploads_fichas', uuid)
    if os.path.exists(pasta_cliente):
        for arquivo in os.listdir(pasta_cliente):
            nome_sem_extensao = os.path.splitext(arquivo)[0]
            if nome_sem_extensao == doc_nome:
                caminho_completo = os.path.join(pasta_cliente, arquivo)
                return send_file(caminho_completo, as_attachment=False)
    return "❌ Documento não encontrado.", 404


# ══════════════════════════════════════════════════════════════
# Exportar fichas como Excel
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/api/exportar_fichas')
def exportar_fichas():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    registros = banco_cadastros.listar_submissoes(
        status   = request.args.get('status'),
        tipo     = request.args.get('tipo'),
        busca    = request.args.get('busca'),
        data_de  = request.args.get('data_de'),
        data_ate = request.args.get('data_ate'),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Fichas Cadastrais"

    COR_TITULO_BG = "1A2744"
    COR_HEADER_BG = "0EE6B8"
    COR_HEADER_FT = "090D14"
    COR_LINHA_PAR = "EEF4FF"
    COR_LINHA_IMP = "FFFFFF"
    COR_STATUS = {
        "pendente":   ("FEF3C7", "92400E"),
        "aprovado":   ("D1FAE5", "065F46"),
        "reprovado":  ("FEE2E2", "991B1B"),
        "cadastrado": ("EDE9FE", "5B21B6"),
    }

    def fill(cor):
        return PatternFill("solid", start_color=cor, end_color=cor)

    def borda():
        s = Side(style="thin", color="CCCCCC")
        return Border(left=s, right=s, top=s, bottom=s)

    def cel_fmt(cell, bold=False, cor_ft="000000", cor_bg=None, size=9, wrap=False, h_align="left"):
        cell.font      = Font(name="Arial", bold=bold, color=cor_ft, size=size)
        cell.alignment = Alignment(horizontal=h_align, vertical="center", wrap_text=wrap)
        cell.border    = borda()
        if cor_bg:
            cell.fill = fill(cor_bg)

    # Título
    ws.merge_cells("A1:R1")
    ws["A1"] = "CIAMED  —  Relatório de Fichas Cadastrais"
    ws["A1"].font      = Font(name="Arial", bold=True, size=15, color=COR_TITULO_BG)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws["A1"].fill      = fill("F0F4FF")
    ws.row_dimensions[1].height = 30

    # Subtítulo
    params = request.args
    partes = []
    if params.get("status"):   partes.append(f"Status: {params['status']}")
    if params.get("tipo"):     partes.append(f"Tipo: {params['tipo']}")
    if params.get("busca"):    partes.append(f"Busca: {params['busca']}")
    if params.get("data_de"):  partes.append(f"De: {params['data_de']}")
    if params.get("data_ate"): partes.append(f"Até: {params['data_ate']}")
    filtros_str = "  |  ".join(partes) if partes else "Sem filtros"

    ws.merge_cells("A2:R2")
    ws["A2"] = f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}     •     Filtros: {filtros_str}     •     Total: {len(registros)} ficha(s)"
    ws["A2"].font      = Font(name="Arial", size=9, color="555555", italic=True)
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
    ws["A2"].fill      = fill("F0F4FF")
    ws.row_dimensions[2].height = 16
    ws.row_dimensions[3].height = 6

    # Cabeçalhos
    COLUNAS = [
        ("Data/Hora", 18), ("Razão Social", 32), ("CNPJ", 17),
        ("Tipo", 14), ("Status", 14), ("Tentativa", 9),
        ("Cód. ERP", 12), ("Vendedor", 15), ("Representante", 16),
        ("Captação", 15), ("ICMS Contribuinte", 15), ("Regime Especial", 15),
        ("Regra Faturamento", 15), ("Telefone", 14), ("WhatsApp", 14),
        ("E-mail XML", 28), ("Documentos", 38), ("Motivo Reprovação", 42),
    ]

    NOMES_DOCS = {
        "doc_regime_especial": "Regime Especial ICMS",
        "doc_alvara": "Alvará Sanitário",
        "doc_crt": "Certidão de Regularidade",
        "doc_afe": "AFE / AE",
        "doc_balanco": "Balanço e DRE",
        "doc_balancete": "Balancete",
        "doc_contrato": "Contrato Social",
    }

    LIN_HEADER = 4
    for col_idx, (titulo, largura) in enumerate(COLUNAS, start=1):
        cell = ws.cell(row=LIN_HEADER, column=col_idx, value=titulo)
        cel_fmt(cell, bold=True, cor_ft=COR_HEADER_FT, cor_bg=COR_HEADER_BG, size=9, h_align="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = largura
    ws.row_dimensions[LIN_HEADER].height = 22

    # Dados
    LABEL_STATUS = {
        "pendente": "⏳ Em Análise", "aprovado": "✅ Aprovado",
        "reprovado": "❌ Reprovado", "cadastrado": "🤖 Cadastrado ERP",
    }

    for i, c in enumerate(registros):
        lin    = LIN_HEADER + 1 + i
        d      = c.get("dados_json") or {}
        status = c.get("status", "pendente")
        bg_lin = COR_LINHA_PAR if i % 2 == 0 else COR_LINHA_IMP

        docs_lista = [NOMES_DOCS.get(x, x) for x in (c.get("docs_enviados") or [])]
        docs_str   = ", ".join(docs_lista) if docs_lista else "—"
        motivos    = c.get("motivos_reprovacao") or []
        motivo_str = motivos[-1]["motivo"] if motivos else "—"

        valores = [
            c.get("created_at", "—"), c.get("razao_social", "—"), c.get("cnpj", "—"),
            d.get("tipo_cadastro", "—"), LABEL_STATUS.get(status, status),
            f"{c.get('tentativa', 1)}ª", d.get("cod_erp", "—"),
            d.get("vendedor", "—"), d.get("representante", "—"),
            d.get("captacao", "—"), d.get("contribuinte_icms", "—"),
            d.get("possui_regime_especial", "—"), d.get("regra_faturamento", "—"),
            d.get("telefone_empresa", "—"), d.get("whatsapp", "—"),
            d.get("email_xml_1", "—"), docs_str, motivo_str,
        ]

        for col_idx, valor in enumerate(valores, start=1):
            cell = ws.cell(row=lin, column=col_idx, value=valor)
            h_al = "center" if col_idx in [4, 5, 6, 7] else "left"
            if col_idx == 5:
                bg_s, ft_s = COR_STATUS.get(status, (bg_lin, "000000"))
                cel_fmt(cell, cor_ft=ft_s, cor_bg=bg_s, size=9, h_align="center", bold=True)
            else:
                cel_fmt(cell, cor_ft="222222", cor_bg=bg_lin, size=9, h_align=h_al, wrap=(col_idx in [16, 17, 18]))
        ws.row_dimensions[lin].height = 18

    ws.freeze_panes = "A5"
    ultima_col = get_column_letter(len(COLUNAS))
    ws.auto_filter.ref = f"A{LIN_HEADER}:{ultima_col}{LIN_HEADER + len(registros)}"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    nome_arquivo = f"Fichas_Cadastrais_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ══════════════════════════════════════════════════════════════
# Fila de Cadastro (integração N8N)
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/fila_cadastro/entrar', methods=['POST'])
def fila_cadastro_entrar():
    dados      = request.get_json()
    resume_url = dados.get('resume_url', '')
    if not resume_url:
        return jsonify({'erro': 'resume_url obrigatório'}), 400

    novo_id, posicao, sua_vez = cadastro_entrar(resume_url)
    return jsonify({'id': novo_id, 'posicao': posicao, 'sua_vez': sua_vez})


@clientes_bp.route('/fila_cadastro/liberar_proximo', methods=['POST'])
def fila_cadastro_liberar():
    cadastro_liberar_proximo()
    return jsonify({'status': 'ok'})


# ══════════════════════════════════════════════════════════════
# Integração N8N → Robô RPA
# ══════════════════════════════════════════════════════════════

@clientes_bp.route('/n8n_iniciar_cadastro', methods=['POST'])
def n8n_iniciar_cadastro():
    dados_n8n = request.json
    cnpj      = dados_n8n.get('cnpj')
    razao     = dados_n8n.get('razao_social')
    vendedor  = dados_n8n.get('vendedor')
    logger.info(f"[N8N] Solicitação recebida!")
    logger.info(f"Cliente: {razao} | 👤 Vendedor: {vendedor}")
    try:
        resultado = cadastro_novo.executar({
            "cnpj": cnpj, "razao_social": razao, "vendedor": vendedor
        })
        return jsonify({
            "status": "sucesso",
            "mensagem": f"Robô finalizou o cadastro de {razao}",
            "resultado": resultado
        }), 200
    except Exception as e:
        logger.error(f"Erro ao processar chamado do n8n: {e}")
        return jsonify({"status": "erro", "detalhes": str(e)}), 500
