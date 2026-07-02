# ══════════════════════════════════════════════════════════════
# labs_config.py — Mapa dos laboratórios e seletores do NL (APEX)
# ──────────────────────────────────────────────────────────────
# Fonte da verdade dos XPATHs/IDs: prompt "Prompt_de_Xpaths_para_o_Script".
# As telas de relatório são apps Oracle APEX dentro do NL. O portal pode
# renderizá-las em <iframe>; o robô entra no contexto certo sozinho via
# _entrar_na_tela() (procura o marcador no topo e nos iframes).
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
    # ⚠️ NÃO há mais modelo fixo aqui: o modelo do estoque agora é POR LABORATÓRIO
    #    (LABS[...]["modelo_estoque"]), igual ao modelo_venda da Demanda.
    "btn_consultar": "B117091108340763197",
    "actions_button": "R117088519510763187_actions_button",
    "actions_menu": "R117088519510763187_actions_menu",   # container do dropdown
    "download_menu_item": "R117088519510763187_actions_menu_14i",  # fallback (id muda)
    "download_csv": "R117088519510763187_download_CSV",
    "item_marcador": "P366_FILTRO",                # presença = tela carregou
}

# Rótulo do setor (com acento) p/ nome de arquivo e título da planilha.
SETOR_LABEL = {"publico": "Público", "privado": "Privado"}

# ── Tela B: Demanda Fornecedor (app APEX 104:117, região R40762810755068572)
DEMANDA = {
    "favorito_invoker": "N&L@3123313830",          # favorito "Demanda fornecedor"
    "data_ini": "P117_VALIDADE_INI",
    "data_fim": "P117_VALIDADE_FIM",
    "operacao": "P117_OPERACOES_VENDA",
    "saved_reports": "R40762810755068572_saved_reports",
    "btn_consultar": "B40766510306068601",
    "actions_button": "R40762810755068572_actions_button",
    "actions_menu": "R40762810755068572_actions_menu",   # container do dropdown
    "download_menu_item": "R40762810755068572_actions_menu_14i",  # fallback (id muda)
    "download_csv": "R40762810755068572_download_CSV",
    "item_marcador": "P117_VALIDADE_INI",          # presença = tela carregou
}

# Operações de Venda (select P117_OPERACOES_VENDA)
OPERACAO_PRIVADO = "11"   # 11 - VENDA FATURAMENTO LIQUIDO PRIVADO (padrão)
OPERACAO_PUBLICO = "17"   # 17 - VENDA FATURAMENTO LIQUIDO PÚBLICO (só Sun Geral)

# Rótulo da operação — entra no nome do arquivo de venda só quando o lab tem as
# duas operações (Sun Geral), p/ distinguir os arquivos de 11 e 17.
OP_LABEL = {OPERACAO_PRIVADO: "Privado", OPERACAO_PUBLICO: "Público"}

# ── Laboratórios ──────────────────────────────────────────────
# modelo_venda   = VALUE do <option> no select de saved_reports da Demanda.
# modelo_estoque = VALUE do <option> no select de saved_reports do Estoque.
#                  Seleção SEMPRE por VALUE (estável); o número visível "1.","2."… muda.
# estoque        = setores a gerar. Comuns = ["privado"] (1 arquivo). Só a Sun usa
#                  ["privado","publico"] (gera os 2, em arquivos SEPARADOS).
# operacoes      = operações de venda a gerar (padrão só "11" = privado).
# pos            = hooks de pós-processamento (fase posterior).
LABS = {
    "bayer":        {"nome": "Bayer",            "modelo_venda": "103052508672357463", "modelo_estoque": "127943964783667034", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "csl":          {"nome": "CSL",              "modelo_venda": "103030134957924372", "modelo_estoque": "127945131004674976", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    # Fresenius: venda E estoque por VALUE (ambos já vieram no HTML).
    # PÓS-PROCESSAMENTO: o relatório traz "Pr Cx" líquido + coluna "Vlr Desconto";
    # o hook fresenius_desconto soma o desconto de volta no Pr Cx (preço cheio).
    "fresenius":    {"nome": "Fresenius",        "modelo_venda": "118673391603879778", "modelo_estoque": "127946236241699626", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO], "pos": ["fresenius_desconto"]},
    "glaxo":        {"nome": "Glaxo",            "modelo_venda": "103036051703963152", "modelo_estoque": "127947392953704118", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "organon":      {"nome": "Organon",          "modelo_venda": "103037225680969181", "modelo_estoque": "127948686117719839", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "roche":        {"nome": "Roche",            "modelo_venda": "103031583388937239", "modelo_estoque": "127949750666724717", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    # Sandoz RS/SC e SP agora têm modelos PRÓPRIOS (venda E estoque) — nada compartilhado.
    # No NOME DE ARQUIVO a "/" vira "-" (proibida em nome de arquivo): "Sandoz RS-SC".
    "sandoz_rs_sc": {"nome": "Sandoz RS/SC",     "modelo_venda": "136574346184500748", "modelo_estoque": "141893254261950275", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "sandoz_sp":    {"nome": "Sandoz SP",        "modelo_venda": "136575483055504796", "modelo_estoque": "141893746925953898", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "sankyo":       {"nome": "Sankyo",           "modelo_venda": "103034120207945481", "modelo_estoque": "127953567883773259", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    "united":       {"nome": "United M",         "modelo_venda": "103039329135977606", "modelo_estoque": "127959262106822214", "estoque": ["privado"], "operacoes": [OPERACAO_PRIVADO]},
    # Sun Geral: estoque Público+Privado e venda Privado(11)+Público(17) → 4 arquivos.
    # Estoque "MENOS ITEM 13082" (o item 13082/Ilumya tem o seu próprio modelo abaixo).
    "sun_geral":    {"nome": "Sun Pharma",        "modelo_venda": "124266373295785439", "modelo_estoque": "127955843879806991", "estoque": ["privado", "publico"], "operacoes": [OPERACAO_PRIVADO, OPERACAO_PUBLICO]},
    # Sun item 13082 (Ilumya): modelo de estoque próprio "10. ESTOQUE SUN PHARMA (ILUMYA)".
    # Estoque da Ilumya também sai Público+Privado (filtro acionado); a VENDA dela
    # continua só privado (operacoes=[11]) — estoque e venda são independentes.
    "sun_13082":    {"nome": "Sun Pharma (Ilumya)",   "modelo_venda": "103087407870276850", "modelo_estoque": "127957403756813800", "estoque": ["privado", "publico"], "operacoes": [OPERACAO_PRIVADO]},
}
