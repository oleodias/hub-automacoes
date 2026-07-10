# Handoff Completo — Automação de Relatórios aos Laboratórios

> Registro **exaustivo** da sessão: objetivo, arquitetura, cada arquivo/função,
> dados de referência (labs, e-mails, seletores APEX), regras da agenda, todos os
> bugs e correções, log de decisões, histórico de commits, estado atual,
> pendências e checklist de produção.
>
> **Branch:** `claude/automacao-relatorios-laboratorios`
> **Empresa:** Ciamed Distribuidora de Medicamentos LTDA
> **Sistema-fonte:** NL / NLWeb (apps Oracle APEX 19.2)

---

## 1. Objetivo

Automatizar a rotina (hoje manual) de **gerar relatórios de Vendas e Estoque** no
NL para **14 laboratórios** e **enviá-los por e-mail**, em datas definidas por
regras de calendário. Cada laboratório recebe seus arquivos `.xlsx` por e-mail;
uma colega interna recebe um aviso de cada envio (sucesso/erro).

## 2. Arquitetura (3 camadas)

```
┌─────────────┐   HTTP+token    ┌──────────────────┐   chama    ┌────────────────┐
│   n8n       │ ───────────────▶│  Hub (Flask)     │ ─────────▶ │  Robô RPA      │
│ (agenda +   │                 │  fila + iniciar  │  Selenium  │ (NL / APEX)    │
│  e-mails)   │ ◀─ manifesto ── │  + download      │ ◀ arquivos │  Chrome        │
└─────────────┘                 └──────────────────┘            └────────────────┘
        │                                                              
        └──────────── e-mail por laboratório (Gmail OAuth2) ──────────▶ laboratórios
                      + aviso por lab para a colega
```

- **Robô (RPA)** — `automacoes/relatorios/` — gera os relatórios no NL e devolve
  um **manifesto** `lab_id → arquivos`.
- **Hub (Flask)** — `routes/relatorios.py` — fila (igual ao Cadastro), dispara o
  robô e serve os arquivos por download. Protegido por token.
- **n8n** — `n8n/` — o "cérebro": decide o que enviar hoje, orquestra o Hub e
  manda os e-mails.

> **Por que fila + Wait?** Espelha o fluxo de **Cadastro de Clientes** já em
> produção: o n8n entra na fila do Hub, um nó **Wait** dorme até ser a vez
> (o Hub acorda via `resume_url`), o robô roda sozinho, e a fila é liberada.

---

## 3. Robô RPA — `automacoes/relatorios/`

### 3.1 Arquivos
| Arquivo | Papel |
|---|---|
| `gerar_relatorios.py` | Robô principal (Selenium). Gera Estoque + Demanda, baixa CSV, converte p/ `.xlsx`, devolve manifesto. |
| `labs_config.py` | Mapa dos 14 labs + seletores das telas APEX. |
| `pos_processamento.py` | Hooks de pós-processamento por lab. **Fresenius ligado** (`fresenius_desconto`) — ver §4.1. |
| `testar_endpoint.py` | Testa `POST /relatorios/iniciar` via HTTP. |
| `job_teste.json` / `job_sun_geral.json` / `job_fresenius.json` / `job_multi.json` | Jobs de teste. |

### 3.2 Contrato (entrada/saída do `executar(job)`)
```jsonc
// entrada
{ "tipo": 1, "modo_fantasma": false, "modo_lento": false,
  "envios": [ {"id":"bayer__T1","lab_id":"bayer","periodo_ini":"01/05/2026","periodo_fim":"31/05/2026"} ] }
// saída
{ "status":"Sucesso"|"Sucesso com avisos"|"Erro", "msg":"...", "pasta":"<abs>",
  "exec":"exec_AAAAMMDD_HHMMSS",   // (preenchido pelo Hub; subpasta da execução)
  "itens":[{"id":"bayer__T1","lab_id":"bayer","nome":"Bayer",
            "arquivos":["Estoque - Bayer.xlsx","Mapa de Venda - Bayer - 01-05-2026 a 31-05-2026.xlsx"], // nomes de arquivo (anexos)
            "com_dados":["Estoque","Mapa de Venda"],   // rótulos amigáveis COM dados (p/ o aviso)
            "vazios":[]}],                             // rótulos amigáveis SEM dados (p/ o aviso)
  "avisos":[...] }
```

### 3.3 Otimização (dedup)
Cada combinação única é gerada **uma vez**:
- **Estoque** por (`modelo + setor`): cada lab tem o SEU modelo. **Labs comuns** filtram
  **Privado** → 1 arquivo. **Os dois labs Sun** geram Privado **e** Público (2 arquivos,
  separados). Cada lab tem modelo próprio (Sandoz RS/SC e SP **não** compartilham mais).
- **Venda** por (`modelo + operação + período`) → cada lab tem modelo próprio (Sandoz
  RS/SC e SP agora têm modelos dedicados → 2 arquivos separados).

### 3.4 Funções (todas em `gerar_relatorios.py`)
| Função | O que faz |
|---|---|
| `_sleep(s)` | Pausa × `_FATOR_LENTIDAO` (env `RELATORIOS_SLOWMO` ou `modo_lento`→3x). |
| `_js_click` | Clique via JS (padrão do projeto). |
| `_set_valor` | **Robusto:** `scrollIntoView` + foco/mouse + `apex.item().setValue()` + `input`/`change` + `jQuery.trigger('change')` + fallback `Select`. |
| `_definir_select` | Garante um `<select>` no valor alvo forçando transição REAL; se já estiver no alvo, faz **"wiggle"** (vai na outra e volta) p/ forçar o `change`. Usado na **Operação** (Demanda) e no **Setor** Público/Privado (Estoque). `rotulo` só cosmético no log. |
| `_selecionar_modelo` | Troca o "saved report" por **value** (preferido) ou **label** (nome); aplica via `_set_valor`. |
| `_entrar_na_tela` | Posiciona o Selenium no contexto certo: **nova aba → topo → iframe** (procura o marcador). Se o NL abrir a **página de erro do navegador** (`ERR_TOO_MANY_REDIRECTS` / "Redirecionamento em excesso") no lugar da tela, levanta `ErroRedirecionamentoNL` **na hora** (sem esperar o timeout). |
| `_eh_pagina_erro_chrome` | Detecta se o contexto atual é a página de erro do Chrome de redirecionamento (por id `sub-frame-error`/`main-frame-error` e por texto, como salvaguarda). |
| `_abrir_favorito` | Abre a estrela de favoritos, clica no atalho pelo `invoker_code` e chama `_entrar_na_tela`. |
| `_recuperar_sessao_nl` | Recuperação após erro do NL: **refaz o login** (re-navega e reautentica), limpando o loop de redirecionamento por sessão velha. |
| `_abrir_favorito_resiliente` | Envolve `_abrir_favorito` com **retry** (padrão **3 tentativas**): a cada falha (`ErroRedirecionamentoNL`/`TimeoutException`) refaz o login e tenta de novo; **só desiste** (levanta o erro → aviso ao TI) após esgotar. Trata o erro intermitente do NL na 1ª execução do dia. |
| `_esperar_apex_pronto` | Espera o overlay de processamento do APEX sumir (best-effort). |
| `_clicar_real` | Clique robusto p/ `a-Menu`/diálogos: sequência `mouseover→mousedown→mouseup→click`. |
| `_clicar_item_menu` | Acha item do menu Ações **pelo texto** (id numérico muda) + `_clicar_real`. |
| `_fechar_dialogo` | Clica no **"X"** do diálogo (jQuery UI) após o CSV (best-effort). |
| `_baixar_csv` | Ações → Download (por texto) → CSV → fecha diálogo → espera baixar. **CSV de 0 byte = relatório vazio → devolve `None`** (não vira anexo). |
| `_esperar_download` | Espera o `.csv`/`.xlsx` estável; **ignora artefatos** (`downloads.htm`, `.tmp`, `.crdownload`); **à prova de corrida**. **Aceita 0 byte** (estável + sem `.crdownload`) — é o que o APEX baixa quando não há dados. |
| `_csv_para_xlsx` | Converte CSV (detecta separador/encoding) p/ `.xlsx` (pandas). |
| `gerar_analise_estoque` | Tela A, ordem CRÍTICA: **modelo → Consultar → setor → Consultar → baixar** (selecionar o modelo RESETA o filtro de setor; por isso o setor vem DEPOIS). Vazio → `None` (0 byte). Nome sempre `Estoque - {Lab} - {Privado\|Público}` ("/" do nome vira "-"). |
| `gerar_demanda` | Tela B: **datas → operação → modelo → Consultar** → baixa (vazio → `None`, via 0 byte). Nome amigável = `Mapa de Venda - {Lab} - {período}` (Sun ganha `(Público\|Privado)`). |
| `aplicar_pos_processamento` | Roda hooks do lab **in-place** sobre o .xlsx de venda (preserva o nome), 1x por combo. Ver §4.1. |
| `executar(job)` | Orquestra: login → estoques (dedup) → vendas (dedup) → manifesto. |
| `main()` | Standalone: aceita **arquivo .json**, **JSON inline** ou **stdin**. |

### 3.5 Constantes do robô
- `PASTA_BASE` = env `RELATORIOS_DOWNLOAD_DIR` ou `./downloads_relatorios`.
- `TIMEOUT_PADRAO=30`, `TIMEOUT_DOWNLOAD=180`.
- `_FATOR_LENTIDAO` = env `RELATORIOS_SLOWMO` (modo observação).

---

## 4. Dados de referência — laboratórios (`labs_config.py`)

| lab_id | Nome | modelo_venda (saved report) | Estoque | Operações | E-mails de produção |
|---|---|---|---|---|---|
| `bayer` | Bayer | `103052508672357463` | privado | 11 | operacoescomerciaisbhp@bayer.com; elias.zanatta@bayer.com; paula.yokomizo@bayer.com |
| `csl` | CSL | `103030134957924372` | privado | 11 | csl@wfbconsultoria.com.br; Rafael.Esteves@csl.com.au |
| `fresenius` | Fresenius | `118673391603879778` | privado | 11 | jailton.silva@fresenius-kabi.com |
| `glaxo` | Glaxo | `103036051703963152` | privado | 11 | alexandre.x.mitsuda@gsk.com |
| `organon` | Organon | `103037225680969181` | privado | 11 | rodrigo.blas@organon.com |
| `roche` | Roche | `103031583388937239` | privado | 11 | brasil.operacoescomerciais@roche.com; joao.pessoa@roche.com |
| `sandoz_rs_sc` | Sandoz RS/SC | `136574346184500748` | privado | 11 | marcelo.novelli@sandoz.com; isaque.fedrigo@sandoz.com |
| `sandoz_sp` | Sandoz SP | `136575483055504796` | privado | 11 | roger.damian@sandoz.com |
| `sankyo` | Sankyo | `103034120207945481` | privado | 11 | marcio.honorati@daiichisankyo.com; pedro.mota@daiichisankyo.com; alexandre.jesus@daiichisankyo.com |
| `sun_geral` | Sun Geral | `124266373295785439` | privado + **publico** | **11 + 17** | Gisele.Lemos@sunpharma.com; Ana.ferreira@sunpharma.com |
| `sun_13082` | Sun Item 13082 | `103087407870276850` | **privado + público** | 11 | Cecilia.Castro@sunpharma.com; Edgar.Lopes@sunpharma.com |
| `united` | United (M) | `103039329135977606` | privado | 11 | leonardo.rossi@knighttx.com |
| `apsen` | Apsen | `151161973987373936` | **— (sem estoque)** | **17** | airton.lima@apsen.com.br; Gabriela.Teixeira@apsen.com.br |
| `mappel_quifa` | Mappel / Quifa | `151162540967387633` | **só público** | **11 + 17** | jeferson.squefi@interplayers.com.br |

- **Labs do setor público (adicionados 2026-07):** `apsen` e `mappel_quifa`. **Apsen** manda
  **só venda** (sem estoque), operação **17 (Público)**. **Mappel / Quifa** manda estoque **só
  Público** e venda **Privado + Público** (11 + 17). Modelos: "MAPA PÚBLICO - APSEN", "MAPA
  PÚBLICO - MAPPEL / QUIFA" e "ESTOQUE MAPPEL / QUIFA". Envio **mensal** (dia 1º, mês anterior).
- **Operações:** `11` = VENDA FATURAMENTO LÍQUIDO **PRIVADO** · `17` = **PÚBLICO** (Sun Geral, Apsen, Mappel/Quifa).
- **Estoque:** **modelo POR LABORATÓRIO** (`modelo_estoque`, tabela abaixo). **Ordem dos
  cliques CRÍTICA:** modelo → Consultar → setor → Consultar → baixar. Selecionar o modelo
  (saved report) **RESETA** o filtro `P366_FILTRO`; por isso o setor é definido DEPOIS do
  modelo (senão o relatório vinha com os dois setores misturados). **Labs comuns filtram
  Privado** (1 arquivo); **só a Sun** gera os dois (`sun_geral` e `sun_13082` → Privado +
  Público, em arquivos SEPARADOS). O modelo fixo antigo `153738614031239522` ("ESTOQUE
  PARA MAPA") está aposentado. **Mappel / Quifa** é um caso novo: estoque **só Público**
  (`estoque=["publico"]`, sem privado).
- **Arquivos por lab:** Sun Geral = **4** (estoque priv+pub + venda 11+17); Sun Ilumya = **3**
  (estoque priv+pub + venda 11); Mappel/Quifa = **3** (estoque público + venda 11+17);
  Apsen = **1** (só venda 17); demais = **2** (estoque + venda).
- **Relatório vazio (estoque OU venda)** — ex.: Ilumya sem Público num mês, ou um lab
  sem vendas numa semana: nesse caso a tela mostra "Item não encontrado" e o APEX baixa
  um **CSV de 0 byte**. O `_baixar_csv` reconhece o 0 byte como "sem dados", **devolve
  `None`** e o robô **pula** aquele arquivo com um aviso — sem travar no download nem
  derrubar o lote (status "Sucesso com avisos"; só não anexa). Vale para **qualquer lab**,
  nas duas telas. Rede de segurança: cada combo (estoque e venda) roda em `try/except`,
  então mesmo uma falha inesperada vira aviso e o lote continua.
- **Manifesto por lab:** `arquivos` (nomes de arquivo p/ anexar) + `com_dados` e `vazios`
  (**rótulos amigáveis** — ex.: "Estoque", "Mapa de Venda", "Estoque (Público)"). O e-mail
  de aviso lista `com_dados` (✅) e `vazios` (⚠️) — texto limpo, sem nome de arquivo cru
  (ver `n8n/README.md` → "Aviso com status de dados"). Os campos fluem pelos Code nodes.
- **Fresenius**: venda **e** estoque por **value** (ambos vieram no HTML). Mantém o hook
  de pós-processamento `fresenius_desconto`.
- **Sandoz RS/SC e SP**: modelos PRÓPRIOS de venda e estoque (não compartilham mais). No
  nome de arquivo a "/" vira "-" → "Sandoz RS-SC".

**Modelos de estoque por lab** (`modelo_estoque` — saved report da Tela A):

| lab_id | Modelo de estoque | value |
|---|---|---|
| `bayer` | ESTOQUE BAYER | `127943964783667034` |
| `csl` | ESTOQUE CSL | `127945131004674976` |
| `fresenius` | ESTOQUE FRESENIUS | `127946236241699626` |
| `glaxo` | ESTOQUE GLAXO | `127947392953704118` |
| `organon` | ESTOQUE ORGANON | `127948686117719839` |
| `roche` | ESTOQUE ROCHE | `127949750666724717` |
| `sandoz_rs_sc` | ESTOQUE SANDOZ - RS/SC | `141893254261950275` |
| `sandoz_sp` | ESTOQUE SANDOZ - SP | `141893746925953898` |
| `sankyo` | ESTOQUE SANKYO | `127953567883773259` |
| `united` | ESTOQUE UNITED | `127959262106822214` |
| `sun_geral` | ESTOQUE SUN PHARMA (MENOS ITEM 13082) | `127955843879806991` |
| `sun_13082` | ESTOQUE SUN PHARMA (ILUMYA) | `127957403756813800` |
| `mappel_quifa` | ESTOQUE MAPPEL / QUIFA (só Público) | `151170092479457151` |

> **Apsen** não tem estoque (só venda), por isso não aparece nesta tabela.
>
> ⚠️ **Pré-requisito operacional:** esses saved reports precisam existir no NL/APEX
> (select `R117088519510763187_saved_reports`) com esses values; senão o robô não
> acha o modelo.

### 4.1 Ajustes por laboratório — pós-processamento (`pos_processamento.py`)

Alguns labs precisam de uma **edição na planilha após a extração**. Isso é
declarado no `labs_config.py` pela chave `"pos": [...]` (lista de hooks) e
aplicado pelo robô **in-place** sobre o `.xlsx` de venda — o anexo mantém o nome
do relatório. Roda **1x por combo** (guarda `pos_feito` em `executar`), e é
seguro porque um lab com hook usa modelo de venda **exclusivo** (o dedup nunca
compartilha esse arquivo com outro lab).

| Lab | Hook | Regra |
|---|---|---|
| `fresenius` | `fresenius_desconto` | **(1)** Soma a coluna **`Vlr Desconto`** de volta na coluna **`Pr Cx`**, linha a linha (o relatório traz o `Pr Cx` *líquido* do desconto; a Fresenius quer o preço *cheio*). Linhas com desconto `0` ficam intactas. **(2)** Depois, **REMOVE a coluna `Vlr Desconto`** do arquivo final — o desconto é acordo interno Ciamed↔cliente e **não pode chegar ao laboratório**. |

**Cuidados técnicos** (já tratados no hook):
- Números são **texto pt-BR** no xlsx (`2.898,5729`). O hook converte pt-BR →
  float p/ somar e devolve em pt-BR (4 casas), só nas linhas alteradas.
- Colunas achadas por nome (ignora caixa/espaços). Se **não achar `Vlr Desconto`**,
  não há o que somar/esconder: copia sem alterar e loga `⚠️`.
- **Confidencialidade:** a coluna `Vlr Desconto` **sempre** sai do arquivo final quando
  existe — inclusive no caso de borda em que o `Pr Cx` não é encontrado (aí não soma, mas
  remove mesmo assim e loga `⚠️` alto: preços podem ficar líquidos → conferir).
- Logs na execução: `✏️ ...desconto somado em 'Pr Cx' em N de M linha(s)` e
  `🗑️ ...coluna 'Vlr Desconto' removida do arquivo final`.
- **Validado** contra arquivo real (somas conferidas) e por teste unitário dos 3 casos
  (normal · sem `Vlr Desconto` · sem `Pr Cx`).

> Para adicionar um ajuste a outro lab: crie a função em `pos_processamento.py`,
> registre em `HOOKS`, e some o nome em `"pos": [...]` do lab no `labs_config.py`.

## 5. Seletores das telas APEX (`labs_config.py`)

**Tela A — Análise de Estoque** (app `104:366`, região `R117088519510763187`)
- favorito: `N&L@3123343633` · filtro: `P366_FILTRO` (Público=`1`/Privado=`2`)
- saved_reports: `R117088519510763187_saved_reports` · Consultar: `B117091108340763197`
- Ações: `..._actions_button` · menu: `..._actions_menu` · Download(fallback): `..._actions_menu_14i` · CSV: `..._download_CSV`
- marcador (tela carregou): `P366_FILTRO`

**Tela B — Demanda Fornecedor** (app `104:117`, região `R40762810755068572`)
- favorito: `N&L@3123313830` · datas: `P117_VALIDADE_INI` / `P117_VALIDADE_FIM` · operação: `P117_OPERACOES_VENDA`
- saved_reports: `R40762810755068572_saved_reports` · Consultar: `B40766510306068601`
- Ações/menu/CSV análogos · marcador: `P117_VALIDADE_INI`

---

## 6. Hub (Flask) — `routes/relatorios.py`

Todos exigem header **`X-Hub-Token`** = `N8N_HUB_TOKEN` (`.env`). Registrados em
`app.py` e nas `ROTAS_PUBLICAS` (login dispensado, token exigido).

| Método | Rota | O que faz |
|---|---|---|
| POST | `/relatorios/fila/entrar` | Entra na fila. Body `{resume_url}`. **Anti-SSRF** no `resume_url`. |
| POST | `/relatorios/fila/liberar_proximo` | Libera o próximo da fila. |
| POST | `/relatorios/iniciar` | **Roda o robô** (síncrono). Body `{tipo, envios}`. Sempre HTTP **200**; corpo `{status:"sucesso"\|"erro_robo", resultado:{itens, exec, pasta, ...}}`. |
| GET | `/relatorios/download?exec=&arquivo=` | Serve um arquivo. Bloqueia traversal (`/`,`\`,`..`) e confina na pasta-base. |

> A fila usa o **mesmo mecanismo do cadastro**, generalizado por recurso
> (`RECURSO_RELATORIOS`) — sem alterar o cadastro.

---

## 7. n8n — `n8n/`

### 7.1 Arquivos
| Arquivo | Papel |
|---|---|
| `fluxo_relatorios.json` | **Workflow importável** (39 nós + 6 sticky notes). |
| `agenda_relatorios.js` | Code "Agenda": regras de data, e-mails, flags. |
| `preparar_envios.js` | Casa manifesto × e-mails por `id` (1 item/lab). |
| `explodir_arquivos.js` | 1 item por arquivo (alimenta o Download). |
| `juntar_binarios.js` | Reagrupa anexos por lab + monta o **HTML** do e-mail. |
| `assets/logo_ciamed_branca.png` | Logo branca (transparente), extraída do manual. |
| `README.md` | Guia de montagem (importável + versão nativa). |

> O nome `fluxo_*` (em vez de `workflow_*`) é proposital: o `.gitignore` ignora
> `*workflow*.json` p/ não vazar exports do n8n com credenciais.

### 7.2 Cadeia de nós (5 blocos)
```
1·Decisão        Schedule 06:30 → Agenda → Tem disparo?
2·Robô           Payload → Fila Entrar → Vez na fila (Wait) → Iniciar Robo → Fila Liberar → Robô OK?
3·Monta e-mails  Preparar Envios → Arquivos do lab → Download → Juntar Binários
4·Envio          Rotear por lab (Switch) ─┬→ Gmail: Bayer ──→ Aviso: Bayer
                                          ├→ Gmail: CSL ────→ Aviso: CSL
                                          └→ ... (14 labs) ...
5·Erro do robô   Robô OK? (false) → Avisos (erro) → TI
```
- **Switch "Rotear por lab"**: 1 saída por `lab_id` (14).
- **Gmail: \<lab\>**: envia HTML + anexos. **On Error: Continue (using error output)** → 2 saídas.
- **Aviso: \<lab\>**: recebe as **duas** saídas e avisa a colega `[OK]`/`[FALHA]` (detecta `$json.error`).
- **Avisos (erro)**: falha do robô (não gerou nada) → e-mail p/ TI (`email_avisos`).

### 7.3 Configuração ao importar (placeholders)
1. **URL do Hub** — trocar `http://localhost:5000` nos 4 nós HTTP.
2. **Token** — `X-Hub-Token` = `TROQUE_PELO_N8N_HUB_TOKEN` → valor real do `.env`.
3. **Credencial Gmail OAuth2** — religar nos 12 `Gmail:` + 12 `Aviso:` + `Avisos (erro)`.
   - 💡 Dica: criar credencial **Header Auth** (`X-Hub-Token`) e usar nos 4 HTTP centraliza o token.

### 7.4 Detalhes do node Gmail (send)
- `sendTo={{$json.to}}` · `subject={{$json.subject}}` · `emailType=html` · `message={{$json.html}}`
- `options.bccList={{$json.bcc}}` · `options.attachmentsUi.attachmentsBinary[0].property={{ Object.keys($binary).join(',') }}`
- Remetente = **conta Gmail autenticada** (sem `fromEmail`).

---

## 8. Agenda — regras de disparo (`agenda_relatorios.js`)

### 8.1 Flags no topo (centralizam tudo)
| Constante | Valor atual | Significado |
|---|---|---|
| `MODO_TESTE` | `true` | Redireciona **todos** os e-mails dos labs p/ `EMAIL_TESTE` (sem BCC). |
| `EMAIL_TESTE` | `leonardodiascaumo@gmail.com` | Destino dos relatórios em teste. |
| `EMAIL_AVISOS` | `ti6@ciamedrs.com.br` | Avisos de erro do robô. |
| `EMAIL_COLEGA` | `leonardodiascaumo@gmail.com` | Colega que recebe o aviso por lab. |
| `FORCAR_TESTE` | `false` | `true` = emite 1 envio fixo (Bayer) ignorando o calendário (teste manual). |
| `RESPONSAVEIS_BCC` | `[]` | BCC dos responsáveis internos (⚠️ preencher p/ produção). |
| `REGRA_TIPO1` | `"dia_1"` | Tipo 1 dispara todo dia 1º (mesmo fim de semana). |
| `SEMANA_ANTERIOR` | `"seg_sex"` | "Semana anterior" = segunda a sexta. |

### 8.2 Tipos de disparo
- **Tipo 1 — dia 1º** (qualquer dia da semana): **os 14 labs** (inclui Apsen e Mappel/Quifa), venda = **mês anterior** inteiro.
- **Tipo 2 — segundas**:
  - `bayer`, `roche` → `semana_anterior` (segunda a sexta da semana passada).
  - `csl`, `fresenius`, `glaxo`, `sun_geral` → `mes_ate_ultima_sexta` (dia 1º do mês vigente até a última sexta).
- **Tipo 3 — quintas**: `sun_13082` → `mes_ate_ultima_quarta`.

### 8.3 Borda tratada (importante)
Na **1ª segunda/quinta do mês** (quando a última sexta/quarta ainda não ocorreu
no mês vigente), o período inverteria. **Decisão:** usa a **semana que antecede**
hoje = última semana do mês passado (seg→sexta/quarta). Implementado em `periodo()`.
> Ex.: 1ª segunda 02/06 → CSL etc. saem com `26/05 → 30/05`.

### 8.4 Saída da Agenda (JSON)
`data_ref`, `modo_teste`, `forcar_teste`, `email_avisos`, `email_colega`,
`tem_disparo`, `tipos`, `qtd_envios`, `envios[]` (cada um com `id`, `lab_id`,
`lab_nome`, `tipo`, `regra_periodo`, `periodo_ini`, `periodo_fim`, `valido`,
`emails`, `bcc`, `emails_producao`), `ignorados[]`.

---

## 9. E-mail — identidade visual (Manual de Identidade CIAMED)

| Item | Valor oficial |
|---|---|
| Teal principal | `#00B3B2` (RGB 0-179-178 · CMYK 87-0-38-0 · **Pantone 326 C**) |
| Cinza secundário | `#6E6E6E` (RGB 110-110-110 · **Cool Gray 11 C**) |
| Fonte | **Helvetica Neue** (fallback Helvetica/Arial) |
| Logo | versão **branca** (extraída do cartão de visita do manual) sobre cabeçalho teal |

- Template **email-safe** (table-based, estilos inline) gerado em
  `juntar_binarios.js` → campo `html`. Cabeçalho teal + logo, corpo "Prezados…"
  + lista de anexos, rodapé "mensagem automática".
- ⚠️ **Logo no e-mail = placeholder `LOGO_URL`** (ainda não resolvida — ver §11).

---

## 10. Log de decisões (cronológico)

1. **Regras da agenda** fechadas: Tipo 1 = dia 1º sempre; semana anterior = seg–sex;
   1ª segunda usa última semana do mês passado; Sandoz = mesmo arquivo.
2. **Anexos**: o usuário escolheu **vários `.xlsx` soltos** (não zip).
3. **MODO_TESTE**: tudo p/ o Gmail do Leonardo; avisos p/ ti6.
4. **Workflow granular/visível**: nós separados; README com versão nativa
   (Split Out + Merge) e importável com Code nodes testados.
5. **Demanda — ordem de cliques** (definida pelo usuário): **datas → operação →
   modelo → Consultar** (modelo por último, antes do Consultar).
6. **Sun Geral**: novo `modelo_venda` = `124266373295785439`.
7. **Operação Público/Privado**: lógica "se está em um, vai pro outro" (wiggle).
8. **Nome dos arquivos** = **nome do relatório salvo** selecionado.
9. **E-mail**: trocado SMTP → **nodes Gmail** (OAuth2, mais fácil de autenticar).
10. **1 Gmail por laboratório** (Switch) — isolamento + personalização.
11. **E-mail HTML** com identidade visual oficial.
12. **Logo**: escolha **inline** (depois pausado — limitação do node Gmail).
13. **Aviso por lab** p/ a colega (sucesso/erro), centralizado em `EMAIL_COLEGA`.
14. **Layout**: organizado + sticky notes.

## 11. Log de bugs e correções (debug em sessão)

| # | Sintoma | Causa | Correção (commit) |
|---|---|---|---|
| 1 | `Job inválido: Expecting property name` | PowerShell remove aspas duplas do JSON inline | `main()` aceita arquivo/stdin (`e7ca4bc`) |
| 2 | Não clicava no filtro Público/Privado | `<select>` APEX só reage após widget ativado | `_set_valor` com `apex.item().setValue()` + foco/mouse (`90d1442`, `9660e90`) |
| 3 | `TimeoutException` no `P366_FILTRO` | Tela APEX está em **`<iframe>`** | `_entrar_na_tela` (topo→iframe→aba) (`9b8f813`) |
| 4 | Não clicava no **Download** do menu Ações | `a-Menu` precisa de mouse-sequence + id numérico muda | clicar **por texto** + `_clicar_real` (`887f6cd`) |
| 5 | Modal de download travava o próximo | diálogo não fechava | `_fechar_dialogo` (X) após CSV (`d0c636f`) |
| 6 | Demanda gerava sempre Bayer (3x) | `_selecionar_modelo` usava `dispatchEvent` cru → IR não recarregava | usa `_set_valor`; ordem datas→op→modelo→Consultar (`6f42b66`, `5e348b7`) |
| 7 | `FileNotFoundError: downloads.htm` | corrida: pegava artefato transitório | filtra `.csv`/`.xlsx`, try/except (`7e4145a`) |
| 8 | Difícil observar o robô | — | `modo_lento`/`RELATORIOS_SLOWMO` + log `🔖` do modelo ativo (`4a55d9d`) |
| 9 | 45 planilhas foram pro GitHub | pasta não ignorada | `.gitignore downloads_relatorios/` + `git rm --cached` (`c991c52`) |
| 10 | n8n `401 não autorizado` | header com placeholder `TROQUE_PELO_...` | trocar o token nos 4 HTTP (config do usuário) |
| 11 | Logo "inline" não viável direto | node Gmail não marca imagem como inline (CID) | pausado; alternativa = API Gmail (MIME) — ver §12 |
| 12 | NL abre página de erro do Chrome (`ERR_TOO_MANY_REDIRECTS` / "Redirecionamento em excesso") ao abrir a tela — intermitente, comum na **1ª execução do dia** | loop de redirecionamento por sessão/cookie velha no `nlwebprod.ciamed.com.br` | `_entrar_na_tela` detecta a página de erro na hora e levanta `ErroRedirecionamentoNL`; `_abrir_favorito_resiliente` **refaz o login e tenta de novo (3x)**; só vira aviso ao TI se persistir. Tradução dedicada em `_explicar_erro`. |

## 12. Pendências / próximos passos

### 12.1 Logo no e-mail (decisão em aberto)
O node **Gmail do n8n não faz inline (CID)** — anexa como arquivo comum. Opções:
- **A) URL pública** (recomendado, simples): hospedar `logo_ciamed_branca.png`
  (site da Ciamed / Cloudinary / ImgBB / GitHub Pages público) e pôr no `LOGO_URL`.
- **B) Inline (CID via API do Gmail)**: trocar os 12 nodes Gmail por **HTTP
  Request** chamando `messages.send` com **MIME** montado no `juntar_binarios.js`
  (logo como parte `inline`). MIME **já validado localmente**; refactor não aplicado.

### 12.2 Reenvio em caso de erro (opções levantadas)
| Opção | Pega transitório | Pega permanente | Auto | Esforço |
|---|:--:|:--:|:--:|---|
| 1 Retry On Fail (nativo) | ✅ | ❌ | ✅ | 5 min |
| 2 Loop + Wait | ✅✅ | ❌ | ✅ | médio |
| 3 Dead-letter (Sheet/endpoint + fluxo agendado) | ✅ | ✅ | ✅✅ | alto |
| 4 Reenvio manual / botão no e-mail de erro | ✅ | ✅ | ❌ | médio |

> Recomendação dada: **1 + 4(b)**; subir p/ **3** se quiser zero intervenção.
> **A decidir/implementar.**

### 12.3 Ideias de upgrade
- **Resumo consolidado do dia** (1 e-mail p/ TI com o placar geral).
- **Log de execuções** em Google Sheets (auditoria).
- **Tratamento de feriados** (regras Tipo 1/2/3 ignoram feriado hoje).

## 13. Checklist de produção
1. `FORCAR_TESTE = false` (volta a respeitar o calendário).
2. `MODO_TESTE = false` (envia aos **labs reais** — botão de produção).
3. Preencher `RESPONSAVEIS_BCC`; revisar `EMAIL_COLEGA`/`EMAIL_AVISOS`.
4. 4 HTTP: **URL do Hub** + **X-Hub-Token**. Religar **credencial Gmail**.
5. Resolver a **logo** (§12.1) e **ativar** o workflow no n8n (toggle *Active*).
6. Conferir o **fuso** do servidor n8n (a agenda assume **America/Sao_Paulo**).
7. (Opcional) `N8N_RESUME_HOSTS` no `.env` do Hub (mesmo do Cadastro).

## 14. Como testar
```powershell
# 1) Robô standalone (máquina com Selenium/Chrome/NL):
python -m automacoes.relatorios.gerar_relatorios automacoes/relatorios/job_teste.json
#    (variações: job_sun_geral.json — 4 arquivos; job_multi.json — dedup; modo_lento já ligado no multi)

# 2) Endpoint do Hub (com o Hub rodando — python app.py):
$env:N8N_HUB_TOKEN="<token>"
python -m automacoes.relatorios.testar_endpoint automacoes/relatorios/job_teste.json

# 3) Download direto:
$h=@{ "X-Hub-Token"="<token>" }
Invoke-WebRequest "http://localhost:5000/relatorios/download?exec=<exec>&arquivo=<arquivo>.xlsx" -Headers $h -OutFile teste.xlsx
```
**n8n:** importar `n8n/fluxo_relatorios.json` → ajustar URL/token/Gmail →
`FORCAR_TESTE=true` na Agenda → *Execute Workflow* → conferir e-mail + aviso `[OK]`.

## 15. Estado atual (✅ validado nesta sessão)
- Robô ponta a ponta: **Bayer** ✅, **Sun Geral** (4 arquivos) ✅, **Multi/dedup** ✅, **nomes pelo relatório salvo** ✅.
- Hub via HTTP: **token + iniciar + download** ✅.
- n8n: **fluxo completo**, e-mail **HTML com identidade visual**, **1 Gmail + 1 aviso por lab**, layout organizado com sticky notes ✅.
- **Primeiro e-mail de teste recebido com sucesso** ✅.

## 16. Histórico de commits da sessão (cronológico)
```
e4c13ba feat: robô RPA de Estoque/Demanda no NL com dedup e CSV→xlsx
f27f993 fix: Fresenius usa relatório próprio selecionado por nome
3c6f894 feat: endpoints do Hub (fila + iniciar + download) p/ o N8N
ebb8aa2 feat: agenda do n8n (Code node) com e-mails e períodos
71446b6 feat: aplica regras de agenda decididas
8c671c9 feat: Code node que junta manifesto do robô com e-mails
99f1c53 feat: loop de anexos no n8n + guia de montagem do workflow
4db6067 feat: MODO_TESTE redireciona e-mails para teste
0a7c376 refactor: workflow granular com nodes nativos visíveis
e7ca4bc fix: aceitar job via arquivo .json ou stdin no teste standalone
90d1442 fix: seta filtro de estoque via apex.item().setValue()
9660e90 fix: ativa widget do filtro (foco/mouse) e erro legível
9b8f813 fix: entra no iframe/aba da tela APEX automaticamente
887f6cd fix: clique robusto no Download do menu Ações (APEX a-Menu)
48cb6cd test: jobs de teste para Sun Geral, Fresenius e multi-lab
739c302 feat(n8n): workflow importável (fluxo_relatorios.json)
789fc14 test: script para testar o endpoint POST /relatorios/iniciar
d0c636f fix: fecha o diálogo de download (X) após clicar no CSV
6f42b66 fix: troca real do modelo (saved report) na Demanda
7e4145a fix: espera de download à prova de corrida e artefatos
4a55d9d feat: modo lento (observação) + diagnóstico do modelo ativo
5e348b7 fix: troca do modelo por último, antes do Consultar
e4cd7f3 feat: novo modelo Sun Geral + operação à prova de 'se perder'
a75ea89 feat: nomeia arquivos pelo nome do relatório salvo selecionado
c991c52 chore: ignora downloads_relatorios/ e remove planilhas versionadas
ea53c41 feat(n8n): FORCAR_TESTE na agenda p/ testar em qualquer dia
0e4e5bd feat(n8n): nodes de e-mail trocados por Gmail (OAuth2)
48bf500 feat(n8n): um node Gmail por laboratório (Switch por lab_id)
fbbea88 style(n8n): paleta oficial Ciamed no e-mail + logo branca
1bdde6f feat(n8n): aviso por laboratório (sucesso/erro) para a colega
b06a6ff refactor(n8n): centraliza e-mail da colega (email_colega na Agenda)
99f0ec6 style(n8n): layout organizado, espaçado e com sticky notes
131c87b docs: handoff/resumo da automação de relatórios
```

## 17. Pontos a confirmar / observações
- **Fresenius**: venda e estoque por `value` (já preenchidos). Pós-processamento **ligado**
  (`fresenius_desconto` — soma `Vlr Desconto` em `Pr Cx`; ver §4.1).
- **Sandoz RS/SC vs SP**: agora têm modelos **próprios** (venda E estoque) → cada uma gera
  seus arquivos (não compartilham mais). No nome de arquivo a "/" vira "-" ("Sandoz RS-SC").
- **Pasta `exec`** no Hub persiste até limpeza — necessária p/ reenvio só-e-mail.
- **Histórico**: as 45 planilhas saíram do tip, mas **continuam no histórico** do
  Git (scrub completo = reescrita de histórico + force-push, se desejarem).
- **Logo**: `n8n/assets/logo_ciamed_branca.png` versionada, mas repo é **privado**
  (raw do GitHub não abre em e-mail → precisa host público OU inline).
