# Migração do Hub para o servidor da empresa (PostgreSQL → Oracle 19c)

Plano completo para tirar o Hub de Automações da máquina de desenvolvimento
e colocá-lo no servidor da Ciamed, com o banco no **Oracle Database 19c
Standard Edition 2 (19.0.0.0.0)**.

- **Público:** equipe de TI (banco/infra) + Leonardo (aplicação)
- **Última atualização:** 13/07/2026
- **Schema de referência:** [ESTRUTURA_BANCO_ORACLE.md](../ESTRUTURA_BANCO_ORACLE.md)
  (14 tabelas, prefixo `cm_hub_aut_`, alembic head `b7c8d9e0f1a2`)

---

## 1. Visão geral — o que migra e o que muda

```
HOJE (dev)                              DEPOIS (servidor da empresa)
─────────────────────────               ────────────────────────────
Flask (app.py) ── localhost:5000        Flask ── servidor (atrás do Nginx, AMBIENTE=prod)
PostgreSQL 16 ── localhost:5432         Oracle 19c ── banco corporativo (schema/usuário do Hub)
N8N ── localhost:5678                   N8N ── no servidor (pasta ~/.n8n migrada junto)
Robôs Selenium ── Chrome local          Robôs Selenium ── Chrome do servidor (acesso ao NLWeb)
```

A migração tem **5 fases**, nesta ordem:

| Fase | O quê                                     | Quem     | Referência           |
| ---- | ----------------------------------------- | -------- | -------------------- |
| 1    | Criar usuário/schema + estrutura (DDL)    | TI       | Seção 2              |
| 2    | Criar os SYNONYMs (nomes sem prefixo)     | TI       | Seção 3              |
| 3    | Carregar os dados atuais (INSERTs)        | TI       | Seção 4              |
| 4    | Adaptar e configurar a aplicação          | Leonardo | Seção 5              |
| 5    | Validar (contagens + smoke test)          | Ambos    | Seção 6              |

---

## 2. Fase 1 — Estrutura (TI)

1. Criar o usuário/schema do Hub no Oracle (sugestão: `HUB_AUT`), com quota
   no tablespace e privilégios básicos:

   ```sql
   -- Como DBA (ajustar senha e tablespace ao padrão da casa):
   CREATE USER hub_aut IDENTIFIED BY "TROCAR_ESTA_SENHA"
       DEFAULT TABLESPACE users
       QUOTA UNLIMITED ON users;

   GRANT CREATE SESSION, CREATE TABLE, CREATE SYNONYM TO hub_aut;
   ```

   > **Charset:** o Hub grava texto acentuado (português) em quase todas as
   > tabelas. O banco/PDB deve estar em **AL32UTF8** (padrão nas instalações
   > 19c recentes — só confirmar).

2. Conectado **como `hub_aut`**, executar o DDL completo da
   **Seção 3 do [ESTRUTURA_BANCO_ORACLE.md](../ESTRUTURA_BANCO_ORACLE.md)**
   (cria as 14 tabelas + índices, já na ordem certa das FKs).

3. A tabela `alembic_version` **não** precisa ser criada — o controle de
   versão do schema no Oracle é manual (processo descrito em
   [COMO_ALTERAR_O_BANCO.md](../COMO_ALTERAR_O_BANCO.md)).

---

## 3. Fase 2 — SYNONYMs (TI)

A aplicação (SQLAlchemy) referencia as tabelas **sem** o prefixo
(`usuarios`, `notas`, ...), mas o padrão da TI usa `cm_hub_aut_`. A ponte
mais simples — **zero mudança de código** — são sinônimos privados no
schema em que o app conecta:

```sql
-- Conectado como HUB_AUT (o mesmo usuário que o app usará):
CREATE SYNONYM usuarios           FOR cm_hub_aut_usuarios;
CREATE SYNONYM submissoes         FOR cm_hub_aut_submissoes;
CREATE SYNONYM links_ficha        FOR cm_hub_aut_links_ficha;
CREATE SYNONYM execucoes          FOR cm_hub_aut_execucoes;
CREATE SYNONYM fila_execucao      FOR cm_hub_aut_fila_execucao;
CREATE SYNONYM notas_categorias   FOR cm_hub_aut_notas_categorias;
CREATE SYNONYM notas_unidades     FOR cm_hub_aut_notas_unidades;
CREATE SYNONYM notas_fornecedores FOR cm_hub_aut_notas_fornecedores;
CREATE SYNONYM notas              FOR cm_hub_aut_notas;
CREATE SYNONYM chamados           FOR cm_hub_aut_chamados;
CREATE SYNONYM chamados_anexos    FOR cm_hub_aut_chamados_anexos;
CREATE SYNONYM chamados_historico FOR cm_hub_aut_chamados_historico;
CREATE SYNONYM notificacoes       FOR cm_hub_aut_notificacoes;
CREATE SYNONYM faq_perguntas      FOR cm_hub_aut_faq_perguntas;
```

> **Alternativa** (se a TI não quiser sinônimos): alterar os `__tablename__`
> no `models.py` para os nomes prefixados. Funciona igual, mas espalha o
> prefixo pelo código e obriga a manter dois nomes por tabela entre dev
> (Postgres) e prod (Oracle). Os sinônimos evitam isso.

---

## 4. Fase 3 — Dados (TI executa, Leonardo gera)

### 4.1. Gerar o arquivo de INSERTs (na máquina de dev)

```powershell
venv\Scripts\activate
python scripts/exportar_dados_oracle.py
```

O script lê o PostgreSQL local e gera
**`scripts/export_oracle/dados_hub_oracle.sql`** com:

- `INSERT`s de **todas as 14 tabelas**, na ordem correta das FKs;
- ids originais preservados (mesmos números do Postgres);
- datas via `TO_TIMESTAMP`/`TO_DATE`, booleanos como 0/1, campos JSON como
  literais `CLOB` (com quebra automática para textos longos);
- ao final, os `ALTER TABLE ... START WITH LIMIT VALUE` que
  **ressincronizam os contadores IDENTITY** (sem isso, o primeiro INSERT
  do app colidiria com um id já carregado);
- `COMMIT` no final.

> 🔐 **Sensível:** o arquivo contém os **hashes de senha** dos usuários e
> dados de clientes (fichas). Transferir por canal seguro e apagar as
> cópias depois da carga. A pasta `scripts/export_oracle/` está no
> `.gitignore` — **não** vai para o Git.

### 4.2. Executar no Oracle

Conectado como `HUB_AUT` (SQL*Plus, SQLcl ou SQL Developer):

```sql
@dados_hub_oracle.sql
```

### 4.3. O que está sendo carregado (retrato de 13/07/2026)

| Tabela                          | Linhas | Conteúdo                                   |
| ------------------------------- | -----: | ------------------------------------------ |
| `cm_hub_aut_usuarios`           |      5 | contas de acesso (com hash de senha)       |
| `cm_hub_aut_submissoes`         |      6 | fichas cadastrais já processadas           |
| `cm_hub_aut_links_ficha`        |      1 | link de ficha gerado                       |
| `cm_hub_aut_execucoes`          |     66 | histórico de execuções dos robôs           |
| `cm_hub_aut_fila_execucao`      |      0 | (fila é transitória — nasce vazia)         |
| `cm_hub_aut_notas_categorias`   |     11 | categorias do Kanban de notas              |
| `cm_hub_aut_notas_unidades`     |      4 | Matriz e filiais                           |
| `cm_hub_aut_notas_fornecedores` |      1 | fornecedor recorrente                      |
| `cm_hub_aut_notas`              |      1 | nota do Kanban                             |
| `cm_hub_aut_chamados`           |      0 | —                                          |
| `cm_hub_aut_chamados_anexos`    |      0 | —                                          |
| `cm_hub_aut_chamados_historico` |      0 | —                                          |
| `cm_hub_aut_notificacoes`       |      0 | —                                          |
| `cm_hub_aut_faq_perguntas`      |     10 | FAQ da Central de Suporte                  |

> Os números acima são o retrato de quando este documento foi escrito.
> **Gere o arquivo de novo no dia da migração** — ele sempre exporta o
> estado atual, e a tabela de conferência da Seção 6 usa o arquivo gerado.

> **Nota sobre strings vazias:** no Oracle, `''` equivale a `NULL`. Se
> alguma coluna de texto tiver string vazia no Postgres, ela vira `NULL` na
> carga — para o Hub isso é indiferente (o app trata os dois igual).

---

## 5. Fase 4 — Adaptações da aplicação (Leonardo)

### 5.1. Driver e conexão

O driver muda de `psycopg2` para **`python-oracledb`** (modo *thin*, não
precisa de Oracle Client instalado):

```powershell
pip install oracledb
# e adicionar ao requirements.txt:  oracledb==<versão instalada>
```

`.env` do servidor:

```
AMBIENTE=prod
DATABASE_URL=oracle+oracledb://hub_aut:SENHA@servidor-oracle:1521/?service_name=NOME_DO_SERVICO
```

> Pedir à TI o **host**, a **porta** (padrão 1521) e o **service name** do
> banco. O restante do `.env` (FLASK_SECRET_KEY, N8N, NLWEB) segue igual ao
> de dev — ver [migração_pc_hub.md](../migração_pc_hub.md).

O SQLAlchemy 2.0 tem dialeto nativo para `oracledb` — os modelos, os tipos
`JSON`/`Boolean` e as queries do ORM (incluindo `.ilike()`) funcionam sem
mudança.

### 5.2. `utils/fila.py` — ÚNICO módulo com SQL específico de Postgres

A fila usa SQL cru com dois recursos que **não existem no Oracle**. É a
única adaptação de código obrigatória do projeto:

**(a) `pg_advisory_xact_lock(hashtext(:r))`** — 4 ocorrências (linhas
~119, 244, 261 e 337). É o "cadeado" que serializa a disputa pela vez na
fila. Equivalente no Oracle: uma **tabela-mutex** com uma linha por recurso,
travada com `SELECT ... FOR UPDATE` (o lock também é liberado no
commit/rollback, igual ao advisory lock transacional):

```sql
-- DDL extra (TI cria junto com a Fase 1):
CREATE TABLE cm_hub_aut_fila_mutex (
    recurso VARCHAR2(30 CHAR) NOT NULL,
    CONSTRAINT pk_cm_hub_aut_fila_mutex PRIMARY KEY (recurso)
);
INSERT INTO cm_hub_aut_fila_mutex (recurso) VALUES ('rpa');
INSERT INTO cm_hub_aut_fila_mutex (recurso) VALUES ('cadastro');
COMMIT;
CREATE SYNONYM fila_mutex FOR cm_hub_aut_fila_mutex;
```

```python
# Em utils/fila.py, trocar as 4 ocorrências de:
conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:r))"), {"r": recurso})
# por:
conn.execute(text("SELECT recurso FROM fila_mutex WHERE recurso = :r FOR UPDATE"), {"r": recurso})
```

**(b) `LIMIT 1`** — 6 ocorrências (linhas ~132, 140, 213, 266, 273 e 316).
No Oracle a sintaxe é `FETCH FIRST 1 ROWS ONLY` (suportada desde o 12c):

```sql
-- Antes (Postgres):           -- Depois (Oracle):
... ORDER BY id LIMIT 1        ... ORDER BY id FETCH FIRST 1 ROWS ONLY
```

> **Dica:** para manter o projeto rodando em dev (Postgres) e prod (Oracle)
> com o mesmo código, essas 6 consultas podem ser reescritas via SQLAlchemy
> Core (`select(...).order_by(...).limit(1)`), que gera a sintaxe certa
> para cada banco automaticamente. O item (a) não tem forma portável — a
> tabela-mutex funciona **nos dois** bancos, então dá para adotar de vez.

### 5.3. O que NÃO precisa mudar

- **Modelos (`models.py`)** — tipos padrão do SQLAlchemy, todos portáveis.
- **Rotas e camadas `banco_*.py`** — usam só o ORM (`.ilike()` vira
  `LOWER(...) LIKE LOWER(...)` no Oracle automaticamente).
- **Alembic** — continua existindo **só para o Postgres de dev**. Mudanças
  de estrutura seguem o fluxo do
  [COMO_ALTERAR_O_BANCO.md](../COMO_ALTERAR_O_BANCO.md): aplica no dev com
  Alembic → manda o SQL traduzido para a TI aplicar no Oracle.
- **N8N, robôs Selenium, templates** — não tocam o banco diretamente.

---

## 6. Fase 5 — Validação

### 6.1. Conferência de contagens (TI)

Depois da carga, comparar com a tabela da Seção 4.3 (ou com o cabeçalho do
arquivo `.sql` gerado, que traz as contagens do dia):

```sql
SELECT 'usuarios' t, COUNT(*) n FROM cm_hub_aut_usuarios
UNION ALL SELECT 'submissoes',         COUNT(*) FROM cm_hub_aut_submissoes
UNION ALL SELECT 'links_ficha',        COUNT(*) FROM cm_hub_aut_links_ficha
UNION ALL SELECT 'execucoes',          COUNT(*) FROM cm_hub_aut_execucoes
UNION ALL SELECT 'fila_execucao',      COUNT(*) FROM cm_hub_aut_fila_execucao
UNION ALL SELECT 'notas_categorias',   COUNT(*) FROM cm_hub_aut_notas_categorias
UNION ALL SELECT 'notas_unidades',     COUNT(*) FROM cm_hub_aut_notas_unidades
UNION ALL SELECT 'notas_fornecedores', COUNT(*) FROM cm_hub_aut_notas_fornecedores
UNION ALL SELECT 'notas',              COUNT(*) FROM cm_hub_aut_notas
UNION ALL SELECT 'chamados',           COUNT(*) FROM cm_hub_aut_chamados
UNION ALL SELECT 'chamados_anexos',    COUNT(*) FROM cm_hub_aut_chamados_anexos
UNION ALL SELECT 'chamados_historico', COUNT(*) FROM cm_hub_aut_chamados_historico
UNION ALL SELECT 'notificacoes',       COUNT(*) FROM cm_hub_aut_notificacoes
UNION ALL SELECT 'faq_perguntas',      COUNT(*) FROM cm_hub_aut_faq_perguntas;
```

E confirmar que os JSONs chegaram válidos (deve retornar 0 linhas):

```sql
SELECT id FROM cm_hub_aut_usuarios  WHERE permissoes IS NOT NULL AND permissoes IS NOT JSON;
SELECT id FROM cm_hub_aut_execucoes WHERE detalhes   IS NOT NULL AND detalhes   IS NOT JSON;
```

### 6.2. Smoke test da aplicação (Leonardo)

1. `python app.py` no servidor apontando para o Oracle → o app sobe sem erro.
2. **Login** com um usuário existente (valida `usuarios` + hash de senha).
3. **Home** → cards aparecem conforme as permissões (valida o JSON `permissoes`).
4. **Monitor de Cadastros** → lista as 6 submissões (valida `submissoes`).
5. **Controle de Notas** → Kanban carrega categorias/unidades/nota (valida o módulo de notas).
6. **Central de Suporte** → FAQ aparece (valida `faq_perguntas`).
7. **Criar um chamado de teste** → primeiro INSERT via app; conferir que o
   id gerado é `max(id)+1` (valida o reset das IDENTITY).
8. **Disparar um robô simples** (ex.: consulta CNPJ ou MDF) → valida a fila
   (`fila_execucao` + mutex) e o registro em `execucoes`.

---

## 7. Checklist consolidado

**TI (banco):**
- [ ] Usuário/schema `HUB_AUT` criado (charset do PDB = AL32UTF8)
- [ ] DDL das 14 tabelas executado (ESTRUTURA_BANCO_ORACLE.md, Seção 3)
- [ ] Tabela-mutex `cm_hub_aut_fila_mutex` criada e populada (Seção 5.2a)
- [ ] SYNONYMs criados (Seção 3 deste doc)
- [ ] Arquivo `dados_hub_oracle.sql` executado + `COMMIT`
- [ ] Contagens conferem (Seção 6.1)

**Leonardo (aplicação):**
- [ ] `dados_hub_oracle.sql` gerado no dia da migração e entregue à TI (canal seguro)
- [ ] `pip install oracledb` + `requirements.txt` atualizado
- [ ] `utils/fila.py` adaptado (mutex + FETCH FIRST) e testado
- [ ] `.env` do servidor com `DATABASE_URL` do Oracle e `AMBIENTE=prod`
- [ ] N8N migrado (pasta `~/.n8n` — ver [migração_pc_hub.md](../migração_pc_hub.md), passo 10)
- [ ] Smoke test completo (Seção 6.2)
- [ ] Cópias do arquivo de dados apagadas após a carga

---

## 8. Riscos e pontos de atenção

| Risco                                   | Mitigação                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------------- |
| Acentuação corrompida (charset)         | PDB em AL32UTF8; arquivo `.sql` gerado em UTF-8; conferir um registro com acento após a carga |
| Colisão de ids após a carga             | `ALTER ... START WITH LIMIT VALUE` no fim do arquivo gerado (automático)               |
| Fila trava/duplica robô no Oracle       | Adaptação do `utils/fila.py` (Seção 5.2) **antes** de apontar o app para o Oracle      |
| Hashes de senha expostos                | Arquivo fora do Git; transferência segura; apagar após a carga                        |
| Schema Oracle desatualizar com o tempo  | Fluxo do [COMO_ALTERAR_O_BANCO.md](../COMO_ALTERAR_O_BANCO.md) (toda migration nova → SQL traduzido para a TI) |
| Banco criado com versão antiga do doc   | Seção 5 do ESTRUTURA_BANCO_ORACLE.md (atualização incremental)                        |
