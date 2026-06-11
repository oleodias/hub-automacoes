# Banco de Dados

O Hub usa **SQLAlchemy** (ORM) + **Alembic** (migrations). O mesmo código fala
com **PostgreSQL** ou **Oracle** — muda só o `DATABASE_URL`.

- **Dev (seu PC):** PostgreSQL local.
- **Homologação/Produção (servidor):** Oracle da empresa.

Todas as tabelas usam o prefixo padrão da empresa **`cm_hub_aut_`**, em **todos
os ambientes**, para o código ser único. São **17 tabelas** (veja a lista em
[BANCO_DE_DADOS_ORACLE.md](BANCO_DE_DADOS_ORACLE.md)).

---

## 1. PostgreSQL (dev)

String de conexão (no `.env`):

```
DATABASE_URL=postgresql://hub_user:SENHA@localhost:5432/hub_automacoes
```

Criar a estrutura e os dados-base:

```bash
alembic upgrade head            # cria/atualiza as tabelas
python scripts/seed_tudo.py     # popula unidades, categorias, CC, operações, FAQ
python criar_admin.py           # cria o primeiro usuário admin
```

As migrations ficam em `migrations/versions/`. O schema é criado **só** pelo
Alembic (o app não cria tabelas sozinho na subida).

---

## 2. Oracle (homologação e produção)

### 2.1. String de conexão

O driver é o **`python-oracledb`** em modo **thin** — **não** precisa instalar o
Oracle Client na máquina.

```
DATABASE_URL=oracle+oracledb://USUARIO:SENHA@HOST:PORTA/?service_name=NOME_DO_SERVICO
```

Exemplo (produção):

```
DATABASE_URL=oracle+oracledb://HUB_PROD:SENHA@oracle-empresa:1521/?service_name=ORCLPDB1
```

### 2.2. Separação por schemas (homologação × produção)

A empresa usa **um servidor Oracle** com **dois usuários/schemas**:

```
        Servidor Oracle (um só)
        ┌─────────────────────────────────────────┐
        │  HUB_HOMOLOG  → 17 tabelas (TESTE)        │
        │  HUB_PROD     → 17 tabelas (REAIS)        │
        └─────────────────────────────────────────┘
```

Cada schema tem a **sua própria cópia** das 17 tabelas. Os dados ficam
fisicamente separados — um teste em homologação nunca toca a produção. O Hub é
idêntico nos dois; só o `DATABASE_URL` (qual usuário conecta) muda.

**Como montar (com a TI):**

1. A TI cria os usuários `HUB_HOMOLOG` e `HUB_PROD` — há um modelo pronto em
   [`deploy/oracle/criar_schemas.sql`](../deploy/oracle/criar_schemas.sql).
2. Conectado **como cada usuário**, a TI roda o **DDL** das tabelas (de
   [BANCO_DE_DADOS_ORACLE.md](BANCO_DE_DADOS_ORACLE.md)) — uma vez por schema.
3. No Hub, cada ambiente recebe o seu `.env` apontando para o schema certo.

> No Oracle, **o Alembic não roda** — a estrutura vem do DDL. As migrations do
> Alembic continuam valendo para o PostgreSQL (dev).

### 2.3. ⚠️ Pontos a validar no Oracle (com a TI, em homologação)

A troca para o Oracle **não é só mudar o `DATABASE_URL`**. Há trechos que hoje
usam recursos exclusivos do PostgreSQL e precisam de ajuste — a fazer e testar
em **homologação**, junto com a TI, antes da produção:

1. **Fila dos robôs (`utils/fila.py`):** usa `pg_advisory_xact_lock(...)` e
   `hashtext(...)` (a "trava" que garante um robô por vez). Esses comandos
   **não existem no Oracle** — o equivalente é `DBMS_LOCK` ou
   `SELECT ... FOR UPDATE`. Esse ajuste é uma tarefa **futura e combinada**,
   feita com o Hub já no servidor e o Oracle no ar.

2. **Tabela `cm_hub_aut_fila_execucao`:** o DDL de
   [BANCO_DE_DADOS_ORACLE.md](BANCO_DE_DADOS_ORACLE.md) hoje descreve **16**
   tabelas e **não inclui** a `fila_execucao` (a 17ª). Ela precisa ser criada no
   Oracle quando a fila for adaptada (item 1).

3. **Índice único parcial** `uq_lancamentos_notas_chave_ativa` (com cláusula
   `WHERE`): sintaxe do PostgreSQL; no Oracle vira um índice baseado em função.

4. **Ressalvas gerais de tipo:** boolean, sequences/identity, tamanho de
   identificadores e tipos de texto (`TEXT` → `CLOB`/`VARCHAR2`). O mapeamento
   está em [BANCO_DE_DADOS_ORACLE.md](BANCO_DE_DADOS_ORACLE.md).

> **Resumo honesto:** o **PostgreSQL é o caminho testado hoje**. O **Oracle está
> preparado** (driver incluído, prefixo aplicado, DDL e schemas documentados),
> mas os pontos acima devem ser **validados em homologação com a TI** antes de ir
> para produção.

---

## 3. Migrations (Alembic)

```bash
alembic upgrade head          # aplica todas as migrations pendentes
alembic downgrade -1          # desfaz a última (reversível)
alembic history               # lista o histórico
alembic current               # mostra em que versão o banco está
```

Para criar uma migration nova, veja [CONTRIBUINDO.md](CONTRIBUINDO.md).

> A migration `e5f6a7b8c9d0` é a que aplica o prefixo `cm_hub_aut_` (renomeia as
> 17 tabelas). Num PostgreSQL novo, o Alembic roda a baseline (nomes simples) e
> depois essa migration (prefixo) — o resultado final já fica prefixado.
