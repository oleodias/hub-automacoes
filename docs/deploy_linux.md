# Deploy do Hub em um servidor Linux

Guia prático para colocar o **Hub de Automações** no ar em um servidor Linux
(a máquina virtual da empresa). Pensado para ser seguido por quem vai
administrar o servidor — copie e cole os comandos, ajustando os valores em
MAIÚSCULO.

> **Importante:** o Hub é uma aplicação Flask que depende do **projeto
> inteiro** (`app.py`, `models.py`, `routes/`, `utils/`, `automacoes/`,
> `templates/`, `static/`, `migrations/`…). **Não** adianta copiar só o
> `app.py` — mande o repositório completo (de preferência via `git clone`).

---

## Visão geral

| Peça | O que é | Como sobe |
|------|---------|-----------|
| **App (Flask)** | o Hub em si | Gunicorn (Linux) atrás do Nginx |
| **PostgreSQL** | banco do Hub | serviço no servidor (ou container) |
| **n8n** | agenda + e-mails | já existe (cloud ou container) |

Este guia cobre **App + banco**. O n8n normalmente já está configurado à parte.

---

## 1. Pegar o projeto (via Git)

```bash
git clone <URL_DO_REPOSITORIO> hub-automacoes
cd hub-automacoes
git checkout main          # ou a branch combinada
```

> Se não puder usar Git, receba um `.zip` da pasta **inteira** do projeto,
> **exceto**: `.env` (segredos — veja abaixo), `venv/`,
> `downloads_relatorios/` e qualquer `*workflow*.json`.

---

## 2. Ambiente Python e dependências

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn        # servidor de produção (não vem no requirements)
```

---

## 3. Configurar o `.env` (segredos ficam SÓ no servidor)

⚠️ **Nunca receba o `.env` do desenvolvedor por e-mail/chat.** Ele contém
segredos (chave do Flask, senha do banco, token do n8n). Em vez disso, copie o
modelo e preencha os valores reais **no próprio servidor**:

```bash
cp .env.example .env
nano .env          # preencha os campos
```

Campos essenciais para produção:

```ini
AMBIENTE=prod

# Gere no servidor com:
#   python -c "import secrets; print(secrets.token_hex(32))"
FLASK_SECRET_KEY=<COLE_A_CHAVE_GERADA>

# Aponta para o Postgres do servidor:
DATABASE_URL=postgresql://USUARIO:SENHA@HOST:5432/hub_automacoes
```

### ⚠️ Senha com caracteres especiais na `DATABASE_URL`

Se a **senha do banco** tiver `@`, `!`, `#`, `$`, `/`, `:` etc., ela precisa ser
**codificada** na URL — senão o Postgres reclama de "could not translate host
name". Gere a senha codificada assim:

```bash
python -c "from urllib.parse import quote; print(quote('SUA_SENHA_CRUA', safe=''))"
```

Tabela rápida: `@`→`%40`, `!`→`%21`, `#`→`%23`, `$`→`%24`, `%`→`%25`,
`&`→`%26`, `:`→`%3A`, `/`→`%2F`.
Exemplo: senha `Abc@!920G` vira `Abc%40%21920G`.

---

## 4. Preparar o banco (Alembic)

O padrão de nomes das tabelas usa o prefixo **`cm_hub_aut_`**. Como você prepara
o banco depende do estado dele:

- **Postgres do servidor VAZIO** (sem tabelas ainda):
  ```bash
  alembic upgrade head
  ```
  Isso cria todas as tabelas já com o prefixo `cm_hub_aut_`.

- **Postgres do servidor JÁ COM as tabelas `cm_hub_aut_*`** (criadas à mão, ou
  restauradas via `pg_dump`):
  ```bash
  alembic stamp head
  ```
  Isso **marca** o histórico do Alembic como atualizado **sem tentar recriar**
  as tabelas. Rodar `upgrade` nesse caso poderia dar erro.

Confirme a versão em qualquer um dos casos:
```bash
alembic current        # deve mostrar c9e0f1a2b3c4 (head)
```

> Migrar os dados do PC de dev para o servidor? Use `pg_dump` no dev e
> `pg_restore`/`psql` no servidor — e então `alembic stamp head`.

---

## 5. Subir o app com Gunicorn

Teste rápido (fica preso no terminal; `Ctrl+C` para sair):
```bash
gunicorn --bind 127.0.0.1:5000 app:app
```

Se responder, configure como **serviço** para subir sozinho no boot. Crie
`/etc/systemd/system/hub.service`:

```ini
[Unit]
Description=Hub de Automacoes (Flask/Gunicorn)
After=network.target

[Service]
User=SEU_USUARIO
WorkingDirectory=/caminho/para/hub-automacoes
EnvironmentFile=/caminho/para/hub-automacoes/.env
ExecStart=/caminho/para/hub-automacoes/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hub
sudo systemctl status hub        # conferir se está "active (running)"
```

---

## 6. Nginx na frente (HTTPS + proxy)

O Hub em `prod` já espera rodar atrás do Nginx (o `ProxyFix` no `app.py` lê o
`X-Forwarded-For`). Exemplo mínimo de `server`:

```nginx
server {
    listen 80;
    server_name SEU_DOMINIO_OU_IP;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Para HTTPS, use Certbot (Let's Encrypt) ou o certificado da empresa.

---

## 7. Checklist final

- [ ] `alembic current` mostra `c9e0f1a2b3c4 (head)`
- [ ] As 14 tabelas do banco começam com `cm_hub_aut_` (`\dt` no `psql`)
- [ ] `systemctl status hub` = **active (running)**
- [ ] Login funciona (prova `cm_hub_aut_usuarios`)
- [ ] Abrir um chamado no Suporte funciona (prova as FKs)
- [ ] Disparar um robô entra/sai da fila (prova `cm_hub_aut_fila_execucao`)
- [ ] `AMBIENTE=prod` no `.env` (liga cookies `Secure` e o `ProxyFix`)

---

## Erros comuns

- **"could not translate host name ..."** → senha da `DATABASE_URL` com
  caractere especial não codificado (veja o passo 3).
- **"relation cm_hub_aut_xxx does not exist"** → faltou rodar `alembic upgrade
  head` (banco vazio) ou `alembic stamp head` (banco já pronto).
- **App sobe mas dá 500 no login** → `DATABASE_URL` errada ou banco sem as
  tabelas.
- **"FLASK_SECRET_KEY não definida"** → o `.env` não foi preenchido; o app se
  recusa a subir sem a chave (proposital, por segurança).

---

### Arquivos relacionados
- **`.env.example`** — modelo das variáveis de ambiente
- **`COMO_ALTERAR_O_BANCO.md`** — fluxo de mudanças de schema (Alembic)
- **`migração_pc_hub.md`** — setup do Hub do zero em um PC de dev
