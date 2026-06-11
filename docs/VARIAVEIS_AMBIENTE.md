# Variáveis de ambiente (`.env`)

O Hub é configurado por um arquivo `.env` (que **nunca** vai pro Git). Cada
ambiente tem o seu — copie do modelo correspondente:

- Dev: `.env.dev.example` → `.env`
- Homologação: `.env.homolog.example` → `.env.homologacao`
- Produção: `.env.prod.example` → `.env.producao`

## Tabela de variáveis

| Variável | Obrigatória? | O que faz |
|----------|:---:|-----------|
| `AMBIENTE` | Sim | `dev`, `homolog` ou `prod`. Controla debug e as travas de segurança (em servidor: cookies seguros, HSTS, ProxyFix). |
| `FLASK_SECRET_KEY` | **Sim** | Chave que assina o login. Sem ela, o Hub **não sobe**. Gere uma por ambiente. |
| `DATABASE_URL` | **Sim** | Endereço do banco. É o que mais muda entre ambientes (Postgres no dev; Oracle `HUB_HOMOLOG`/`HUB_PROD` no servidor). |
| `PUBLIC_BASE_URL` | Recomendada (servidor) | Domínio **público** usado para montar os links de ficha enviados a clientes externos (ex.: `https://fichas.SEU-DOMINIO.com.br`, sem barra no fim). Vazia = o link usa o endereço do navegador do operador (só serve em dev/rede interna). |
| `FILA_TIMEOUT_MIN` | Não (padrão 15) | Minutos até o "watchdog" considerar um robô travado e liberar a fila. |
| `N8N_WEBHOOK_CADASTRO` | Para cadastro | URL do webhook do N8N que dispara o fluxo de cadastro de clientes. |
| `N8N_WEBHOOK_REPROCESSAR` | Para reprocessar | URL do webhook usado pelo botão "reprocessar cadastro". |
| `N8N_HUB_TOKEN` | Recomendada (prod) | "Crachá secreto" entre N8N e Hub. Vazia = webhooks do N8N **sem** proteção (o Hub avisa no log). |
| `N8N_RESUME_HOSTS` | Não | Hosts extras liberados na `resume_url` (anti-SSRF). Normalmente não precisa. |
| `NLWEB_URL` | Para os robôs | Endereço do ERP NLWEB que os robôs operam. |
| `NLWEB_USER` | Para os robôs | Usuário do ERP. |
| `NLWEB_PASS` | Para os robôs | Senha do ERP. |
| `WEB_CONCURRENCY` | Não (padrão 3) | Nº de workers do Gunicorn (só no container). Poucos, porque os robôs são pesados. |
| `GUNICORN_TIMEOUT` | Não (padrão 120) | Tempo (s) até o Gunicorn matar um worker travado. |
| `GUNICORN_LOGLEVEL` | Não (padrão info) | Nível de log do Gunicorn. |

## Formatos do `DATABASE_URL`

```bash
# PostgreSQL (dev)
postgresql://hub_user:SENHA@localhost:5432/hub_automacoes

# Oracle (homologação) — driver thin, sem Oracle Client
oracle+oracledb://HUB_HOMOLOG:SENHA@oracle-empresa:1521/?service_name=ORCLPDB1

# Oracle (produção)
oracle+oracledb://HUB_PROD:SENHA@oracle-empresa:1521/?service_name=ORCLPDB1
```

## Gerar uma `FLASK_SECRET_KEY`

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Use uma **diferente** para cada ambiente (a de homologação não deve ser igual à
de produção).
