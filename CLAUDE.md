# Hub de Automações — Ciamed

Aplicação web (Flask) que centraliza e orquestra os **robôs RPA** dos setores
administrativo e fiscal da Ciamed. Em vez de scripts soltos rodando no terminal,
colaboradores autorizados acionam rotinas complexas (cadastros, fiscal,
relatórios) por uma interface web, com execução monitorável.

- **Empresa:** Ciamed Distribuidora de Medicamentos LTDA
- **ERP-fonte automatizado:** NL / NLWeb (Oracle APEX 19.2) — é o sistema que os robôs operam via Selenium.
- **Banco do próprio Hub:** PostgreSQL (SQLAlchemy + Alembic). *Não confundir com o Oracle do ERP.*

> Idioma do projeto: **português**. Código, comentários, commits e nomes de
> arquivo seguem o estilo já existente (comentários explicativos, didáticos).

---

## Stack

- **Backend:** Python + Flask (`app.py` é o ponto de entrada; blueprints em `routes/`)
- **RPA:** Selenium WebDriver (Chrome) — robôs em `automacoes/`
- **Dados:** Pandas (CSV→xlsx etc.); PostgreSQL via SQLAlchemy; migrations com Alembic
- **Frontend:** HTML/CSS/JS (Vanilla) + Bootstrap (`templates/`, `static/`)
- **Orquestração externa:** n8n (agenda + e-mails), túnel via `cloudflared`
- **Infra:** `docker-compose.yml`

---

## Mapa do repositório

| Caminho | Papel |
|---|---|
| `app.py` | Cria o Flask, configura segurança/banco, registra blueprints, exige login. |
| `routes/` | Blueprints (um por área): `auth`, `main`, `itens`, `mdf`, `fornecedor`, `clientes`, `cnpj`, `admin`, `notas`, `suporte`, `relatorios`. |
| `automacoes/` | Robôs Selenium: `clientes/`, `relatorios/`, `cadastro_item.py`, `cadastro_ncm.py`, `robo_fornecedor.py`, `robo_mdf.py`, `login_navegacao.py`, `motor_xml.py`… |
| `models.py` | Modelos SQLAlchemy. |
| `extensions.py` | `db` (SQLAlchemy), `limiter` (rate-limit). |
| `utils/` | `auth`, `fila` (fila de execução), `n8n_security` (anti-SSRF), `cnpj_ws`, `cebas`, `rastreio`, `validacao`, `logging_config`. |
| `migrations/`, `alembic.ini` | Migrations do banco do Hub. |
| `n8n/` | Workflows/Code nodes (agenda, e-mails). Ver handoff de relatórios. |
| `docs/` | Handoffs detalhados por feature. |
| `templates/`, `static/` | Frontend. |
| `banco_*.py` | Acesso a dados (cadastros, links, notas). |

---

## Convenções e padrões importantes

- **Login obrigatório em todas as rotas**, exceto as listadas em `ROTAS_PUBLICAS` (`app.py`). Rotas chamadas pelo n8n dispensam login mas **exigem header `X-Hub-Token`** (= `N8N_HUB_TOKEN` no `.env`).
- **Segredos vêm do `.env`** (`python-dotenv`). `FLASK_SECRET_KEY` é obrigatória — sem ela o app não sobe (proposital, por segurança). Nunca commitar segredos.
- **`AMBIENTE`** (`dev`/`prod`) controla debug, cookies `Secure` e `ProxyFix` (Nginx em prod).
- **Padrão de integração com n8n:** o robô roda síncrono pelo Hub e devolve um **manifesto** estruturado; rotas longas usam **fila + Wait** (n8n entra na fila, o Hub acorda via `resume_url`). Reaproveitar esse padrão ao criar novas automações orquestradas.
- **Clique no APEX é via JS** (`_js_click`) e telas ficam em `<iframe>` — padrão herdado nos robôs Selenium.
- `.gitignore` ignora `downloads_relatorios/` e `*workflow*.json` (evita vazar exports do n8n com credenciais — por isso os workflows versionados usam o prefixo `fluxo_*`).

---

## Como rodar

```powershell
# Hub (servidor web)
python app.py            # usa .env; AMBIENTE=dev liga debug

# Migrations (banco do Hub — PostgreSQL)
alembic upgrade head

# Robô de relatórios standalone (máquina com Selenium/Chrome/NL)
python -m automacoes.relatorios.gerar_relatorios automacoes/relatorios/job_teste.json
```

---

## Documentação detalhada

- **[docs/handoff_migracao_robos.md](docs/handoff_migracao_robos.md)** — handoff da estabilização pós-migração ao servidor Linux (Docker): correções dos robôs (driver Selenium, timeout do gunicorn, webhook do n8n), a feature "ficha sem documentos", as regras de deploy (curl do GitHub, divergência servidor↔repo) e as tarefas pendentes.
- **[docs/handoff_relatorios.md](docs/handoff_relatorios.md)** — handoff EXAUSTIVO da automação de relatórios aos laboratórios (robô RPA + Hub + n8n): arquitetura, todos os arquivos/funções, dados dos 14 labs, seletores APEX, regras da agenda, bugs/correções, pendências e checklist de produção.
- **[docs/migracao_oracle.md](docs/migracao_oracle.md)** — plano da migração do Hub para o servidor da empresa (PostgreSQL → Oracle 19c): fases, synonyms, carga de dados, adaptações da aplicação (`utils/fila.py`), validação e checklist.
- **[ESTRUTURA_BANCO_ORACLE.md](ESTRUTURA_BANCO_ORACLE.md)** — schema do banco DO HUB traduzido para Oracle 19c (DDL pronto p/ a TI, prefixo `cm_hub_aut_`). *Não confundir com o Oracle do ERP.*
- **[COMO_ALTERAR_O_BANCO.md](COMO_ALTERAR_O_BANCO.md)** — fluxo para mudanças de schema (Alembic no dev + SQL traduzido para a TI aplicar no Oracle).
- **[migração_pc_hub.md](migração_pc_hub.md)** — setup do Hub do zero em um PC novo (Postgres de dev).
- **[docs/deploy_linux.md](docs/deploy_linux.md)** — deploy do Hub em um servidor Linux (Gunicorn + Nginx + Postgres): obter o projeto, `.env` sem vazar segredos, `alembic upgrade`/`stamp head`, serviço systemd e checklist.
- **[n8n/README.md](n8n/README.md)** — guia de montagem dos workflows n8n.

> Ao concluir uma frente grande de trabalho, registrar um handoff em `docs/` e
> adicionar o link aqui. Manter este `CLAUDE.md` enxuto — ele é o índice carregado
> em toda sessão; o detalhe mora nos handoffs.
