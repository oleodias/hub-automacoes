# Handoff — Automação de Relatórios aos Laboratórios

> Documento de resumo da sessão: o que foi construído, decisões tomadas,
> estado atual e como continuar. Branch: `claude/automacao-relatorios-laboratorios`.

## 1. Visão geral
Automação que, em datas definidas, **gera relatórios de Vendas/Estoque no NL
(Oracle APEX)** para cada laboratório e **envia por e-mail**. Três camadas:

```
n8n (cérebro/agenda)  →  Hub Flask (fila + dispara o robô + serve arquivos)  →  robô RPA (Selenium/NL)
        └──────────────────────  e-mail por laboratório (Gmail)  ◄───────────────────┘
```

## 2. Robô RPA — `automacoes/relatorios/`
- **`gerar_relatorios.py`** — abre o NL, gera **Análise de Estoque** (por setor
  privado/público) e **Demanda Fornecedor** (por modelo/operação/período), baixa
  em CSV, converte p/ `.xlsx` e devolve um **manifesto** `lab_id → arquivos`.
  - Reaproveita login/navegador do robô de cadastro.
  - **Dedup**: cada combinação única é gerada 1x (estoque privado sai 1x p/ todos).
- **`labs_config.py`** — mapa dos 12 labs (modelo de venda, setores, operações)
  e seletores das telas APEX.
- **`pos_processamento.py`** — hooks por lab (ex.: Fresenius — stub).
- **`testar_endpoint.py`** — testa o `POST /relatorios/iniciar` via HTTP.
- **`job_*.json`** — jobs de teste (teste/bayer, sun_geral, fresenius, multi).

### Aprendizados/correções importantes do robô (debug em sessão)
1. **Tela APEX abre em `<iframe>`** → `_entrar_na_tela()` posiciona o Selenium
   no contexto certo (topo → iframe → aba).
2. **Inputs/selects APEX** → `_set_valor()` usa `apex.item().setValue()` +
   jQuery `change` + ativação por mouse (o `dispatchEvent` cru não “pegava”).
3. **Menu Ações → Download** → clicar pelo **texto** (id numérico muda) +
   sequência de eventos de mouse; fecha o diálogo (X) após o CSV.
4. **Troca de modelo (saved report)** — ordem na Demanda: **datas → operação
   (com “wiggle” p/ não se perder) → modelo → Consultar**.
5. **Nome do arquivo = nome do relatório salvo** selecionado (`_slug_nome`).
6. **`_esperar_download`** à prova de corrida (ignora `downloads.htm`/temporários).
7. **`modo_lento`** / `RELATORIOS_SLOWMO` p/ observar o robô.

## 3. Hub Flask — `routes/relatorios.py`
Endpoints (todos com header **`X-Hub-Token`** = `N8N_HUB_TOKEN` do `.env`):
- `POST /relatorios/fila/entrar` — entra na fila (anti-SSRF no `resume_url`).
- `POST /relatorios/fila/liberar_proximo` — libera o próximo.
- `POST /relatorios/iniciar` — **roda o robô** (síncrono) e devolve o manifesto
  (`status`, `resultado.itens`, `resultado.exec`). Sempre HTTP 200.
- `GET  /relatorios/download?exec=&arquivo=` — serve um arquivo (path confinado).

Registrado em `app.py` e nas `ROTAS_PUBLICAS` (login dispensado, token exigido).
**Validado ponta a ponta via HTTP** (iniciar + download OK).

## 4. n8n — `n8n/`
Workflow importável: **`fluxo_relatorios.json`** (39 nós + 6 sticky notes).
Blocos: **1 Decisão → 2 Robô (fila+Wait) → 3 Monta e-mails → 4 Envio por lab → 5 Erro do robô**.

Code nodes (colar no respectivo node):
- **`agenda_relatorios.js`** — “livro de regras”: decide labs/períodos do dia e
  e-mails. Ajustes no topo: `MODO_TESTE`, `FORCAR_TESTE`, `EMAIL_COLEGA`,
  `EMAIL_AVISOS`, `RESPONSAVEIS_BCC`.
- **`preparar_envios.js`** — casa manifesto × e-mails por `id`.
- **`explodir_arquivos.js`** — 1 item por arquivo.
- **`juntar_binarios.js`** — reagrupa anexos por lab + monta o **HTML** (cores
  oficiais `#00B3B2`/`#6E6E6E`, logo branca).
- **`assets/logo_ciamed_branca.png`** — logo extraída do manual de identidade.

Envio: **Switch** roteia por `lab_id` → **1 Gmail por lab** (HTML + anexos, com
saída de erro) → **1 Aviso por lab** à colega (`[OK]`/`[FALHA]`).

### Regras da agenda (decididas)
- **Tipo 1** — todo dia **1º** (mesmo fim de semana), venda = mês anterior, 12 labs.
- **Tipo 2** — **segundas**: Bayer/Roche (semana anterior seg–sex); CSL/Fresenius/
  Glaxo/Sun Geral (mês vigente até última sexta; na 1ª segunda usa a última
  semana do mês passado).
- **Tipo 3** — **quintas**: Sun 13082 (até última quarta).

## 5. Estado atual (✅ feito)
- Robô validado ponta a ponta (Bayer, Sun Geral 4 arquivos, Multi/dedup, nomes).
- Hub validado via HTTP (token + iniciar + download).
- n8n: workflow montado, **e-mail HTML com identidade visual**, **1 Gmail + 1
  aviso por lab**, layout organizado com sticky notes.
- Primeiro **e-mail de teste recebido com sucesso**.

## 6. Pendências / próximos passos
- **MODO TESTE ligado**: e-mails dos labs vão p/ `leonardodiascaumo@gmail.com`;
  avisos p/ `ti6@ciamedrs.com.br`. Logo no e-mail é **placeholder** (`LOGO_URL`).
- **Logo inline (CID via API do Gmail)** — pausado; MIME já validado localmente.
- **Reenvio em erro** — opções levantadas (retry nativo / loop+wait / dead-letter
  / manual+botão); **a decidir/implementar**.
- Ideias de upgrade: resumo consolidado do dia, log em Google Sheets, feriados.

### Checklist de produção (na Agenda)
1. `FORCAR_TESTE = false` (volta a respeitar o calendário).
2. `MODO_TESTE = false` (envia aos labs reais).
3. Preencher `RESPONSAVEIS_BCC` e revisar `EMAIL_COLEGA`/`EMAIL_AVISOS`.
4. Nos 4 HTTP: **URL do Hub** + **X-Hub-Token**. Religar **credencial Gmail**.
5. Resolver a **logo** (URL pública ou inline) e ativar o workflow no n8n.

## 7. Como testar rápido
```powershell
# Robô standalone (na máquina com Selenium/Chrome):
python -m automacoes.relatorios.gerar_relatorios automacoes/relatorios/job_teste.json

# Endpoint do Hub (com o Hub rodando):
$env:N8N_HUB_TOKEN="<token>"
python -m automacoes.relatorios.testar_endpoint automacoes/relatorios/job_teste.json
```
n8n: importar `n8n/fluxo_relatorios.json`, ajustar URL/token/Gmail, `FORCAR_TESTE=true`, *Execute Workflow*.
