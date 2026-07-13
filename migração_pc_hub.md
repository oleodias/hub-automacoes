# Setup do Hub em um PC novo (Windows)

Guia passo a passo para deixar o **Hub de Automações** rodando do zero em uma máquina nova,
com um banco PostgreSQL **novo e vazio**. Marque cada item conforme avança.

> O banco nasce **sem dados de negócio** (sem submissões/notas antigas) — só com a estrutura
> (tabelas) e os dados de configuração dos seeds. Se um dia quiser o histórico antigo, dá para
> importar depois com `pg_dump`/`pg_restore` do PC antigo.

---

## 1. Instalar os programas

- [ ] **Python 3.11+** (marcar *"Add to PATH"* na instalação)
- [ ] **Git**
- [ ] **Google Chrome** (necessário para os robôs Selenium)
- [ ] **PostgreSQL 16** — instalador em https://www.postgresql.org/download/windows/
      → versão **16.x**, **Windows x86-64**. Na instalação:
  - Componentes: PostgreSQL Server + pgAdmin 4 + Command Line Tools
  - **Anote a senha do superusuário `postgres`**
  - Porta: **5432** (padrão)
- [ ] **Node.js LTS** (v20 ou v22) — https://nodejs.org (marcar *"Add to PATH"*); necessário só para o N8N

---

## 2. Criar o banco e o usuário do Hub

No **PowerShell** (use o `&` na frente porque o caminho tem espaços). Quando pedir
`Password for user postgres:`, digite a senha do superusuário definida na instalação:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE USER hub_user WITH PASSWORD 'Cia#25';"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE hub_automacoes OWNER hub_user;"
```

Conferir (deve entrar no prompt `hub_automacoes=>`; saia com `\q`):

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U hub_user -d hub_automacoes -h localhost
```

> Pode trocar a senha `Cia#25` por outra — só use a mesma no `.env` (passo 4).

---

## 3. Pegar o código

- [ ] Clonar/copiar o projeto para o PC novo.

---

## 4. Configurar o `.env`

Copie `.env.example` para `.env` e preencha:

```
AMBIENTE=dev
FLASK_SECRET_KEY=<gere uma chave aleatória>
DATABASE_URL=postgresql://hub_user:Cia#25@localhost:5432/hub_automacoes
N8N_WEBHOOK_CADASTRO=http://localhost:5678/webhook/...
NLWEB_URL=...
NLWEB_USER=...
NLWEB_PASS=...
```

---

## 5. Instalar as dependências Python

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 6. Criar o schema do banco (migrations)

Com o banco vazio criado no passo 2, isto cria as **14 tabelas do Hub**
(+ a `alembic_version` de controle):

```powershell
alembic upgrade head
```

> O schema é criado **exclusivamente** pelas migrations do Alembic. O app não cria mais tabelas
> sozinho na subida (`db.create_all()` foi removido do boot).

---

## 7. Popular os dados-base (seeds)

```powershell
python scripts/seed_tudo.py
```

Popula unidades, categorias e o FAQ da Central de Suporte. É **idempotente** — pode
rodar de novo sem duplicar.

---

## 8. Criar o usuário administrador

```powershell
python criar_admin.py
```

Informe e-mail e senha quando solicitado.

---

## 9. Subir o Hub

```powershell
python app.py
```

Acesse **http://localhost:5000** e faça login.

---

## 10. Instalar e rodar o N8N (local)

- [ ] Conferir o Node (terminal novo): `node --version` e `npm --version`
- [ ] Instalar: `npm install -g n8n`
- [ ] Subir: `n8n start` → editor em **http://localhost:5678**

### Trazer os workflows do PC antigo
O N8N guarda tudo (workflows + credenciais + chave de criptografia) em
`C:\Users\SEU_USUARIO\.n8n`. Para preservar:

- [ ] Com o N8N **parado** nos dois PCs, copie a pasta `.n8n` **inteira** do PC antigo para o
      mesmo caminho no PC novo, **antes** do primeiro `n8n start`. A *encryption key* (no arquivo
      `config`) precisa vir junto, senão as credenciais salvas ficam ilegíveis.

### Se já rodou `n8n start` antes de copiar
Substitua a pasta `.n8n` recém-criada pela do PC antigo:

```powershell
# 1) pare o n8n (Ctrl+C)
ren "%USERPROFILE%\.n8n" ".n8n_nova_vazia"   # guarda a vazia de lado
# 2) copie a pasta .n8n do PC antigo para C:\Users\SEU_USUARIO\.n8n
# 3) suba de novo:
n8n start
```

### Esqueceu o login do N8N (tela do editor)
Reseta a conta de dono **sem perder os workflows**:

```powershell
# pare o n8n (Ctrl+C), depois:
n8n user-management:reset
n8n start
```

No `http://localhost:5678` aparecerá de novo a tela de cadastro do dono — defina e-mail/senha novos.

---

## 11. ERP (NLWEB)

- [ ] Conferir a rede até o ERP (IP fixo `192.168.200.252:8585`, em `automacoes/cadastroncm.py`).
- [ ] Garantir que o Chrome abre normalmente para os robôs Selenium.

---

## Checklist rápido

- [ ] PostgreSQL instalado + banco `hub_automacoes` criado
- [ ] `.env` preenchido (DATABASE_URL, FLASK_SECRET_KEY, N8N, NLWEB)
- [ ] `pip install -r requirements.txt`
- [ ] `alembic upgrade head` (14 tabelas do Hub)
- [ ] `python scripts/seed_tudo.py`
- [ ] `python criar_admin.py`
- [ ] `python app.py` → login OK em http://localhost:5000
- [ ] N8N rodando com os workflows
