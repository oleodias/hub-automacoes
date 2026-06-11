# Arquitetura

Visão geral de como as peças do Hub se conectam.

## Visão de alto nível

```
   Navegador (usuário)
        │  HTTPS
        ▼
   ┌─────────┐      ┌──────────────────────── Container do Hub ───────────────────────┐
   │  Nginx  │ ───▶ │  Gunicorn ─▶ Flask (app.py)                                       │
   │ (proxy) │      │     ├─ routes/      (telas e APIs, por blueprint)                 │
   └─────────┘      │     ├─ db/          (camada de dados: banco_cadastros/links/notas)│
                    │     ├─ models.py    (tabelas via SQLAlchemy)                       │
                    │     ├─ utils/fila.py(fila "um robô por vez", no banco)             │
                    │     └─ automacoes/  (robôs Selenium + Chromium)                    │
                    └───────────┬───────────────────────────────┬──────────────────────┘
                                │ SQLAlchemy                     │ Selenium
                                ▼                                ▼
                      ┌──────────────────┐              ┌─────────────────┐
                      │  Banco (externo) │              │   ERP NLWEB      │
                      │ Postgres / Oracle│              │ (NLWEB_URL)      │
                      └──────────────────┘              └─────────────────┘

                      ┌──────────────────┐
                      │       N8N        │  ◀── webhooks (cadastro de clientes)
                      └──────────────────┘
```

- O **banco é externo** ao container — o Hub fala com ele pelo `DATABASE_URL`.
- O **Nginx** termina o HTTPS e repassa para o **Gunicorn** (porta interna 8000).
- Os **robôs** abrem o **Chromium** (headless no servidor) e operam o **ERP**.

## Fluxo web (uma tela)

```
Navegador → Nginx → Gunicorn → Flask
   → routes/<modulo>.py  (recebe a requisição)
       → db/banco_*.py ou models.py  (lê/grava no banco via ORM)
   → devolve HTML (templates/) ou JSON
```

Os blueprints são registrados em `app.py` (auth, main, itens, mdf, fornecedor,
clientes, cnpj, admin, notas, lancamento_notas, suporte). Um `before_request`
global exige login em tudo, exceto numa lista de rotas públicas.

## Fluxo dos robôs (RPA) com a fila

Os robôs não podem rodar dois ao mesmo tempo no mesmo "recurso". A `utils/fila.py`
garante isso usando uma **fila guardada no banco** (tabela
`cm_hub_aut_fila_execucao`), válida entre todos os workers/containers:

```
Usuário aciona um robô
   → entra na fila (INSERT na tabela da fila)
   → espera a vez (a "vez" é decidida com uma trava no banco)
   → quando é a vez: o robô em automacoes/ abre o Chromium e opera o ERP
   → ao terminar: sai da fila e libera o próximo
   → um "watchdog" libera execuções travadas após FILA_TIMEOUT_MIN minutos
```

Há duas filas, separadas pela coluna `recurso`:
- `rpa` → robôs de itens / MDF / fornecedor;
- `cadastro` → fluxo de cadastro de clientes (acionado pelo N8N).

> A trava da fila usa hoje recursos do PostgreSQL. A adaptação para o Oracle é
> uma tarefa combinada — veja [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md), seção 2.3.

## Integração com o N8N

O N8N orquestra o fluxo de **cadastro de clientes**: o Hub chama webhooks do N8N
(`N8N_WEBHOOK_*`) e o N8N chama de volta endpoints públicos do Hub
(`clientes.*`, `cnpj.*`). A autenticidade dessas chamadas é protegida por um
token compartilhado (`N8N_HUB_TOKEN`) e por uma checagem anti-SSRF
(`utils/n8n_security.py`).

## Pastas principais

| Pasta/arquivo | Papel |
|---------------|-------|
| `app.py` | Cria o Flask, registra blueprints, exige login, sobe o servidor. |
| `routes/` | Uma "tela"/conjunto de APIs por arquivo (blueprints). |
| `db/` | Camada de dados (consultas de cadastros, links e notas). |
| `models.py` | Definição das 17 tabelas (SQLAlchemy). |
| `utils/` | Apoio: fila, autenticação, logging, CNPJ, CEBAS, segurança N8N. |
| `automacoes/` | Os robôs Selenium (itens, NCM, MDF, fornecedor, clientes, notas). |
| `migrations/` | Migrations do Alembic (estrutura do banco no Postgres). |
| `scripts/` | Seeds e utilitários de linha de comando. |
| `templates/`, `static/` | Frontend (HTML, CSS, JS, imagens, áudio). |
| `data/` | Dados auxiliares versionados (ex.: planilha CEBAS). |
