# Handoff — Correções pós-migração para o servidor Linux (jul/2026)

Resumo da frente de trabalho de estabilização do **Hub de Automações** depois da
migração para o servidor Linux (Docker) da Ciamed. Serve para retomar o trabalho
numa nova sessão sem perder contexto.

> Modo de trabalho combinado com o Leonardo: **validar/provar antes de aplicar em
> produção**, ser explícito sobre o nível de confiança, e **confirmar quando
> envolver regra de negócio**. (Ver memórias do projeto.)

---

## Ambiente e regras de deploy (LER PRIMEIRO)

- O Hub roda em **Docker** na VM `automacoes` (usuário `linuxuser`, projeto em
  `~/hub-automacoes`). Serviços: `hub-web` (Flask/gunicorn), `postgres:16-alpine`,
  `n8n`, `nginx`, `certbot`, `portainer`.
- **Deploy NÃO é por `git pull`.** O código vai por **`curl` do GitHub público**
  (`github.com/oleodias/hub-automacoes`):
  ```bash
  cd ~/hub-automacoes
  curl -fsSL https://raw.githubusercontent.com/oleodias/hub-automacoes/<SHA>/<caminho> -o <caminho>
  docker compose up -d --build hub-web
  ```
- **Divergência servidor↔repo:** o `Dockerfile` e o `docker-compose.yml` **reais só
  existem no servidor** (não versionados). O `docker-compose.yml` do repo é uma
  versão antiga de dev. Alguns `.py` estavam em **Latin-1** (corrigidos repondo do
  GitHub em UTF-8).
- **n8n:** compartilha o **Postgres** do Hub; a comunicação Hub↔n8n é pela **rede
  interna do Docker** (`http://n8n:5678`), não pelo domínio público.
- No **host** o Python é `python3`; **dentro do container** é `python`. Robôs via
  `docker exec ... python ...` bufferizam a saída — usar `python -u` para ver ao vivo.

---

## O que foi RESOLVIDO nesta sessão

1. **Driver Selenium (causa raiz de todos os robôs)** — `SessionNotCreatedException`:
   o `webdriver-manager` baixava o ChromeDriver **151** enquanto o container tem o
   **Chromium 150** do Debian. Criado o helper **`automacoes/navegador.py` →
   `criar_driver(options)`** (usa `CHROME_BIN`/`CHROMEDRIVER_PATH` no servidor;
   webdriver-manager no dev Windows) e migrados os **9 pontos** de criação de driver.
   Commit **`af0367d`**. Validado (MDF rodou de ponta a ponta).
2. **Bug de URL no `robo_mdf`** — `driver.get('NLWEB_URL')` (string literal) →
   `driver.get(url)`. Commit **`8dd6b1a`**.
3. **WORKER TIMEOUT do gunicorn** — robôs longos (MDF de 1 mês = **435s**) eram
   mortos pelo `--timeout 400`. Aumentado para **`--timeout 1800`** no Dockerfile
   **do servidor** (não versionado) + rebuild. Validado (MDF completou pela interface).
4. **Bug de contatos na reativação** (`cadastro_reativacao.py`) — apagava todos os
   contatos e não recriava os obrigatórios **SIMFRETE** (e-mail fixo) e **ENVIO NFE
   ELETRONICA** (com `email_nfe`). Corrigido. Commit **`a4b1544`**.
   ⚠️ **Falta testar** numa reativação real.
5. **Webhook n8n `Connection refused`** — o Hub chamava o n8n pelo domínio público
   de dentro do container. Corrigido no `.env` do servidor:
   `N8N_WEBHOOK_CADASTRO=http://n8n:5678/webhook/cadastro-cliente`. Validado (Status 200).
6. **Feature "ficha sem documentos"** — o nó `Email - Triagem` do n8n quebrava
   quando a ficha vinha sem anexos (`attachmentsBinary` virava `''`).
   - **Hub (feito, commit `4f60ea8`):** `qtd_documentos = len(docs_finais)` no
     payload do `receber_ficha`; status **`aguardando_documentos`** quando sem docs;
     fix do typo **`uploads_fiches` → `uploads_fichas`** no `reprocessar_cadastro`
     (o reprocessamento reenviava SEM os documentos).
   - **n8n (EM ANDAMENTO):** nó `IF` "tem documentos?" + e-mail de reenvio ao vendedor
     reusando o modo correção (`/ficha_cliente?correcao=<uuid>`).

Obs.: também foi feito, à parte, `feat(ui)` aumentando a logo `.brand-logo` de 28px
para 56px (commit **`84487ba`**).

---

## PRÓXIMO PASSO IMEDIATO (onde paramos)

Terminar a feature "ficha sem documentos" no **n8n**. O nó **`IF` "Tem documentos
anexados?"** está com erro de tipo. A configuração correta é:

| Campo | Valor |
|---|---|
| Valor 1 (fx) | `{{ Number($json.body.qtd_documentos) }}` |
| Operador | **Number → is larger than** |
| Valor 2 | `0` |

O `Number(...)` é essencial: o `qtd_documentos` chega como **texto** (`"3"`), e sem
converter dá `'3' is a string but was expecting a number`. Alternativa: ligar o
toggle **"Convert types where required"**.

Depois: conferir que o ramo **`false`** aponta para o e-mail de **reenvio**
("Documentos Pendentes", com link `?correcao=`) — na print apareceu um nó nomeado
"Email - Vendedor Reprovado" no ramo sem documentos, **confirmar se é o e-mail certo**.
Por fim, testar os dois caminhos (ficha com e sem anexos).

---

## Tarefas PENDENTES

- **[n8n] Fechar a feature "ficha sem documentos"** — corrigir o `IF` (acima),
  validar o e-mail de reenvio e testar os dois ramos.
- **[.env servidor] `N8N_WEBHOOK_REPROCESSAR`** ainda aponta para o domínio público
  (`https://automacoes.ciamed.com.br/n8n/webhook/reprocessar`) → trocar para interno
  (`http://n8n:5678/webhook/reprocessar`, confirmando o path com um GET) e recriar o
  `hub-web`. Mesmo padrão do webhook de cadastro.
- **Testar `cadastro_reativacao`** (contatos obrigatórios) numa reativação real.
- **Validar os demais robôs no servidor** (fornecedor, clientes, itens/fase1-fase2,
  relatórios) — o driver já beneficia todos; caçar bugs específicos por robô.
- **Sincronizar `Dockerfile` + `docker-compose.yml` do servidor com o Git** e
  padronizar UTF-8 (elimina a edição "na mão" de timeout/encoding). Manter
  `--timeout 1800` e o `CHROME_BIN`/`CHROMEDRIVER_PATH` do Dockerfile.
- **Atualizar o n8n** (o Leonardo tem a doc oficial) — fazer com backup (pg_dump +
  tar do `n8n_data` + `n8n export:workflow`), fixar a versão (sair do `:latest`).
  Recomendado fazer **depois** de fechar a feature acima.
- **Fluxo de teste/demo do cadastro** — já existe um prompt pronto (workflow n8n de
  teste, e-mails só para o Leonardo, robô simulado, dados fake). Salvar em
  `docs/prompt_fluxo_teste.md` quando quiser.

---

## Referências

- Memórias do projeto (carregadas automaticamente): `deploy-hub-servidor`,
  `divergencia-servidor-repo`, `driver-selenium-navegador`,
  `leonardo-validar-antes-de-aplicar`.
- Arquivos-chave: `automacoes/navegador.py`, `routes/clientes.py`,
  `n8n/fluxo_cadastro_clientes.json`, `CLAUDE.md`.
