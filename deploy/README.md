# Comece por aqui (TI) — Subir o Hub no servidor

Página de entrada para quem vai **instalar o Hub de Automações no servidor**.
O guia completo, com explicações, está em
[`../docs/DEPLOY_LINUX.md`](../docs/DEPLOY_LINUX.md) — aqui fica o resumo prático.

## Visão geral em 30 segundos

- O Hub roda em **Docker** (container com Flask + robôs + Chromium + Gunicorn).
- O **banco é externo** (Oracle da empresa) — o Hub conecta via `DATABASE_URL`.
- Dois ambientes no servidor: **homologação** (teste) e **produção** (real),
  isolados por **schemas Oracle** diferentes (`HUB_HOMOLOG` e `HUB_PROD`).
- O **Nginx** fica na frente, com HTTPS, e repassa para o Hub (localhost).

## Arquivos desta pasta

| Arquivo | Para quê |
|---------|----------|
| `atualizar.sh` | "Botão" de deploy: `git pull` + rebuild do container. |
| `nginx.conf.example` | Modelo do proxy reverso com HTTPS (homolog + prod). |
| `oracle/criar_schemas.sql` | Modelo para criar os usuários `HUB_HOMOLOG` e `HUB_PROD`. |

## Passo a passo (primeira instalação)

```bash
# 1) Pré-requisitos no servidor: Docker, Docker Compose e Git instalados.
#    Liberar rede do servidor até: Oracle, ERP NLWEB e N8N.

# 2) Pegar o código (escolha a branch do ambiente)
git clone <URL_DO_REPOSITORIO> /opt/hub-automacoes
cd /opt/hub-automacoes
git checkout main            # produção   (homologação: git checkout homologacao)

# 3) Configurar o .env do ambiente (NUNCA vai pro Git)
cp .env.prod.example .env.producao
nano .env.producao          # preencher FLASK_SECRET_KEY, DATABASE_URL (HUB_PROD), etc.

# 4) Banco: criar os schemas e as tabelas no Oracle (com o DBA)
#    - Usar deploy/oracle/criar_schemas.sql para criar HUB_HOMOLOG e HUB_PROD
#    - Rodar o DDL de docs/BANCO_DE_DADOS_ORACLE.md DENTRO de cada schema
#    (ver docs/BANCO_DE_DADOS.md, seções 2.2 e 2.3 — há pontos a validar)

# 5) Subir o Hub
docker compose -f docker-compose.prod.yml up -d --build

# 6) Dados-base e usuário admin (uma vez)
docker compose -f docker-compose.prod.yml exec hub python scripts/seed_tudo.py
docker compose -f docker-compose.prod.yml exec hub python criar_admin.py

# 7) Nginx: usar deploy/nginx.conf.example como base (ajustar domínios e certificados)
```

## Atualizações no dia a dia

```bash
./deploy/atualizar.sh homolog     # testar primeiro em homologação
./deploy/atualizar.sh prod        # depois publicar em produção
```

## ⚠️ Pontos que precisam de decisão/validação da TI

1. **Topologia Oracle:** confirmado **1 servidor, 2 schemas** (`HUB_HOMOLOG` /
   `HUB_PROD`). Revisar tablespaces, quotas e senhas em `oracle/criar_schemas.sql`.
2. **Fila dos robôs no Oracle:** `utils/fila.py` usa hoje recursos exclusivos do
   PostgreSQL (`pg_advisory_xact_lock`/`hashtext`) e a tabela
   `cm_hub_aut_fila_execucao` ainda não está no DDL Oracle. Precisa de adaptação
   antes de usar a fila em produção no Oracle — ver `docs/BANCO_DE_DADOS.md` (2.3).
3. **N8N de homologação:** decidir se usa o N8N Cloud da produção ou um separado
   para teste — ver `docs/N8N.md` (seção 6).

> Dúvidas de configuração? Tudo está detalhado em [`../docs/`](../docs/).
