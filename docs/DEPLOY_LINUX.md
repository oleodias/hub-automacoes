# Deploy no servidor Linux (Docker)

Guia para subir e atualizar o Hub no **servidor Linux** da empresa, rodando em
**Docker**. Vale para **homologação** e **produção** — a diferença é só qual
arquivo `.env` e qual `docker-compose` cada um usa.

> Quer só o resumo prático (uma página)? Veja [`deploy/README.md`](../deploy/README.md).

> O **banco não roda no container**. O Hub se conecta ao Oracle da empresa pela
> rede, pelo `DATABASE_URL`. O container leva só a aplicação (Flask), os robôs e
> o Chromium.

---

## 1. Pré-requisitos no servidor

- [ ] **Docker** e **Docker Compose** instalados (`docker --version`, `docker compose version`).
- [ ] **Git** instalado.
- [ ] Acesso de rede do servidor até:
  - o **Oracle** da empresa (host/porta do banco);
  - o **ERP NLWEB** (endereço configurado em `NLWEB_URL`; internamente costuma
    ser algo como `192.168.200.252:8585` — confirme com a TI);
  - o **N8N**.
- [ ] **Nginx** na frente, com **HTTPS** (ver `deploy/nginx.conf.example`).

---

## 2. Pegar o código

```bash
# Exemplo de caminho; ajuste conforme o padrão do servidor
git clone <URL_DO_REPOSITORIO> /opt/hub-automacoes
cd /opt/hub-automacoes
```

Para **homologação**, use a branch `homologacao`; para **produção**, a `main`:

```bash
git checkout homologacao    # ou: git checkout main
```

> Copie também a pasta interna **`scripts/dados/`** (com `lista_cc.txt` e
> `lista_operacoes.txt`) do ambiente antigo — ela é ignorada pelo Git e é usada
> pelos seeds de centros de custo/operações.

---

## 3. Configurar o `.env` do ambiente

Cada ambiente tem o seu arquivo (que **não** vai pro Git):

```bash
# Homologação
cp .env.homolog.example .env.homologacao
nano .env.homologacao        # preencha FLASK_SECRET_KEY, DATABASE_URL (HUB_HOMOLOG), etc.

# Produção
cp .env.prod.example .env.producao
nano .env.producao           # preencha com os valores REAIS (schema HUB_PROD)
```

O que cada variável significa está em [VARIAVEIS_AMBIENTE.md](VARIAVEIS_AMBIENTE.md).

---

## 4. Subir o Hub

A imagem é a mesma; muda o arquivo de compose:

```bash
# Homologação
docker compose -f docker-compose.homolog.yml up -d --build

# Produção
docker compose -f docker-compose.prod.yml up -d --build
```

Confira:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

O Hub fica escutando só no `localhost` do servidor (`127.0.0.1:8000` produção,
`127.0.0.1:8010` homologação). Quem expõe para a rede, com HTTPS, é o **Nginx**.

---

## 5. Banco: criar a estrutura e os dados-base

> **Atenção:** o container **não** mexe no banco sozinho (de propósito). Os
> passos abaixo são feitos **uma vez**, à mão, na primeira instalação.

### 5a. PostgreSQL (dev e homologação inicial)

```bash
# rode os comandos de dentro do container do Hub:
docker compose -f docker-compose.homolog.yml exec hub alembic upgrade head
docker compose -f docker-compose.homolog.yml exec hub python scripts/seed_tudo.py
docker compose -f docker-compose.homolog.yml exec hub python criar_admin.py
```

### 5b. Oracle (homologação/produção)

No Oracle, a estrutura **não** vem do Alembic — vem do **DDL** que a TI roda
dentro de cada schema (`HUB_HOMOLOG` e `HUB_PROD`). Veja
[BANCO_DE_DADOS.md](BANCO_DE_DADOS.md) e o DDL em
[BANCO_DE_DADOS_ORACLE.md](BANCO_DE_DADOS_ORACLE.md). Depois de as tabelas
existirem, rode só os seeds e o admin:

```bash
docker compose -f docker-compose.prod.yml exec hub python scripts/seed_tudo.py
docker compose -f docker-compose.prod.yml exec hub python criar_admin.py
```

---

## 6. Atualizar o Hub (no dia a dia)

Use o "botão" de atualização — ele faz `git pull` + rebuild do container:

```bash
./deploy/atualizar.sh homolog     # atualiza homologação
./deploy/atualizar.sh prod        # atualiza produção
```

> **Sempre** atualize e teste em **homologação** antes de tocar a **produção**.

Se a atualização incluir uma **migration nova** (mudança na estrutura do banco)
e o banco for **PostgreSQL**, rode o upgrade manualmente após o deploy:

```bash
docker compose -f docker-compose.prod.yml exec hub alembic upgrade head
```

No **Oracle**, mudanças de estrutura são combinadas e aplicadas junto com a TI.

---

## 7. Robôs (Selenium) no servidor

Os robôs rodam em **modo headless** (sem janela) no servidor — o código já usa
as flags certas para Linux (`--headless=new`, `--no-sandbox`,
`--disable-dev-shm-usage`). A imagem já traz o **Chromium** e o
**chromium-driver** instalados.

> Observação: o código localiza o driver via `webdriver-manager`. Valide o
> primeiro acionamento de cada robô em **homologação** — é o lugar certo para
> ajustar qualquer detalhe de driver/navegador antes da produção.

---

## 8. Problemas comuns

| Sintoma | Provável causa |
|---------|----------------|
| Container reinicia sozinho | Erro no `.env` (ex.: falta `FLASK_SECRET_KEY`) — veja os `logs`. |
| "could not connect" ao banco | `DATABASE_URL` errado ou sem rota de rede até o Oracle. |
| Login não funciona (cookie) | Acesso por HTTP em vez de HTTPS — em servidor, use o Nginx com HTTPS. |
| Upload de XML/planilha falha | `client_max_body_size` baixo no Nginx (use ~50M). |
| Robô não acha o ERP | Rede do servidor sem rota até o `NLWEB_URL`. |
