# ══════════════════════════════════════════════════════════════
# labs_config.py — Mapa dos laboratórios e seletores do NL (APEX)
# ──────────────────────────────────────────────────────────────
# Fonte da verdade dos XPATHs/IDs: prompt "Prompt_de_Xpaths_para_o_Script".
# As telas de relatório são apps Oracle APEX dentro do NL e NÃO estão em
# iframe (confirmado), então os seletores são acessados direto.
#
# Estratégia de seleção do "modelo salvo" (saved report): sempre pelo
# VALUE numérico (estável), nunca pelo número visível "9.", "10."… porque
# o número muda e há nomes repetidos (ex.: duas opções "MAPA VENDA BAYER").
# ══════════════════════════════════════════════════════════════

# ── Tela A: Análise de Estoque (app APEX 104:366, região R117088519510763187)
ESTOQUE = {
    "favorito_invoker": "N&L@3123343633",          # favorito "Analise de Estoque"
    "item_filtro": "P366_FILTRO",                  # select Público(1)/Privado(2)
    "filtro_setor": {"publico": "1", "privado": "2"},
    "saved_reports": "R117088519510763187_saved_reports",
    "modelo_value": "153738614031239522",          # "1. ESTOQUE PARA MAPA" (fixo p/ todos)
    "btn_consultar": "B117091108340763197",
    "actions_button": "R117088519510763187_actions_button",
    "download_menu_item": "R117088519510763187_actions_menu_14i",
    "download_csv": "R117088519510763187_download_CSV",
    "item_marcador": "P366_FILTRO",                # presença = tela carregou
}

# ── Tela B: Demanda Fornecedor (app APEX 104:117, região R40762810755068572)
DEMANDA = {
    "favorito_invoker": "N&L@3123313830",          # favorito "Demanda fornecedor"
    "data_ini": "P117_VALIDADE_INI",
    "data_fim": "P117_VALIDADE_FIM",
    "operacao": "P117_OPERACOES_VENDA",
    "saved_reports": "R40762810755068572_saved_reports",
    "btn_consultar": "B40766510306068601",
    "actions_button": "R40762810755068572_actions_button",
    "download_menu_item": "R40762810755068572_actions_menu_14i",
    "download_csv": "R40762810755068572_download_CSV",
    "item_marcador": "P117_VALIDADE_INI",          # presença = tela carregou
}

# Operações de Venda (select P117_OPERACOES_VENDA)
OPERACAO_PRIVADO = "11"   # 11 - VENDA FATURAMENTO LIQUIDO PRIVADO (padrão)
OPERACAO_PUBLICO = "17"   # 17 - VENDA FATURAMENTO LIQUIDO PÚBLICO (só Sun Geral)

# ── Laboratórios ──────────────────────────────────────────────
# modelo_venda = VALUE do <option> no select de saved_reports da Demanda.
# estoque      = setores do estoque que o lab recebe (padrão só "privado").
# operacoes    = operações de venda a gerar (padrão só "11").
# pos          = hooks de pós-processamento (fase posterior).
LABS = {
    "bayer":        {"nome": "Bayer",            "modelo_venda": "103052508672357463", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "csl":          {"nome": "CSL",              "modelo_venda": "103030134957924372", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    # ⚠️ PENDENTE DE CONFIRMAÇÃO: o usuário citou "10. MAPA DE VENDA FRESENIUS",
    # mas no HTML do select a opção 10 é "MAPA DE VENDA GLAXO". A única opção de
    # Fresenius existente é a "22. MAPA VENDA FRESENIUS" (value abaixo). Ajustar
    # se a confirmação apontar outro value.
    "fresenius":    {"nome": "Fresenius",        "modelo_venda": "94439473807980962", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO], "pos": ["fresenius_desconto"]},
    "glaxo":        {"nome": "Glaxo",            "modelo_venda": "103036051703963152", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "organon":      {"nome": "Organon",          "modelo_venda": "103037225680969181", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "roche":        {"nome": "Roche",            "modelo_venda": "103031583388937239", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    # Sandoz RS/SC e SP usam o MESMO modelo → o dedup gera a venda 1x só.
    "sandoz_rs_sc": {"nome": "Sandoz RS/SC",     "modelo_venda": "103032823287941952", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "sandoz_sp":    {"nome": "Sandoz SP",        "modelo_venda": "103032823287941952", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "sankyo":       {"nome": "Sankyo",           "modelo_venda": "103034120207945481", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "united":       {"nome": "United M",         "modelo_venda": "103039329135977606", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    # Sun Geral: estoque Público+Privado e venda Privado(11)+Público(17) → 4 arquivos.
    "sun_geral":    {"nome": "Sun Geral",        "modelo_venda": "96107110384505749", "estoque": ["privado", "publico"], "operacoes": [OPERACAO_PRIVADO, OPERACAO_PUBLICO]},
    # Sun item 13082: modelo "26. SUN - ITEM 13082" (confirmado pelo usuário).
    "sun_13082":    {"nome": "Sun Item 13082",   "modelo_venda": "103087407870276850", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
}
