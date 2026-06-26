# Como alterar o banco de dados do Hub

Guia prático para quando o Hub precisar de uma **coluna nova**, uma **tabela
nova** ou qualquer mudança na estrutura do banco. Pensado para copiar e colar.

---

## Visão geral (leia isto primeiro)

Existem **dois bancos** na nossa vida:

| Banco | Onde fica | Quem atualiza |
|-------|-----------|----------------|
| **PostgreSQL** | seu PC / Hub (desenvolvimento) | **você**, com o Alembic (semi-automático) |
| **Oracle** | servidor da empresa | a **TI**, manualmente |

O **Alembic** (a ferramenta de "migrations") cuida **só do PostgreSQL**. Ele
**não** mexe no Oracle da empresa. Por isso toda mudança tem dois lados: você
aplica no Postgres e depois **avisa a TI** para aplicar a mesma coisa no Oracle.

> Antes de qualquer comando: abra o terminal na pasta do projeto e **ative o
> ambiente Python** (igual ao `SETUP_BANCO_NOVO.md`):
> ```powershell
> venv\Scripts\activate
> ```

---

## Passo a passo: adicionar/alterar uma coluna ou tabela

### 1. Edite o `models.py`

Cada tabela é uma classe; cada coluna é uma linha. Para **adicionar uma coluna**,
basta acrescentar uma linha na classe certa. Exemplo — adicionar `telefone` ao
usuário:

```python
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id    = db.Column(db.Integer, primary_key=True)
    nome  = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # ↓ coluna nova
    telefone = db.Column(db.String(20), nullable=True)
```

> Para uma **tabela nova**, crie uma classe nova seguindo o padrão das que já
> existem **e** adicione o nome dela na linha de `import` do
> `migrations/env.py` (aquela lista grande de modelos). Sem isso o Alembic não
> "enxerga" a tabela.

### 2. Gere a migration (o Alembic faz sozinho)

```powershell
alembic revision --autogenerate -m "adiciona telefone em usuarios"
```

Isso compara o `models.py` com o banco e **cria um arquivo novo** em
`migrations/versions/` já com o comando da mudança.

### 3. Confira o arquivo gerado

Abra o arquivo novo em `migrations/versions/` e dê uma olhada. Você deve ver algo
como `op.add_column('usuarios', ...)`. É só pra ter certeza de que ele gerou o
que você esperava (o autogenerate acerta quase sempre, mas vale conferir).

### 4. Aplique no seu PostgreSQL

```powershell
alembic upgrade head
```

Pronto — a coluna agora existe no seu banco local.

### 5. Salve no Git

```powershell
git add models.py migrations/versions/
git commit -m "adiciona telefone em usuarios"
```

> **Sempre commite o arquivo de migration.** É ele que mantém o histórico de
> tudo que mudou no banco, em ordem e datado.

---

## Como mandar a mudança para a TI (Oracle)

Você **não** manda o banco inteiro de novo. Manda **só a diferença** — o
pedacinho de SQL da mudança.

### Veja o SQL exato da mudança

Para ver o comando que o Alembic vai rodar (sem aplicar), use o modo `--sql`:

```powershell
alembic upgrade head --sql
```

Isso imprime o SQL na tela. **Atenção:** ele sai em sintaxe **PostgreSQL** —
você precisa traduzir para Oracle antes de passar para a TI.

### Tradução rápida PostgreSQL → Oracle

| PostgreSQL | Oracle |
|------------|--------|
| `varchar(n)` | `VARCHAR2(n CHAR)` |
| `integer` | `NUMBER(10)` |
| `boolean` | `NUMBER(1)` (0/1) |
| `text` | `CLOB` |
| `timestamp` | `TIMESTAMP` |
| `numeric(p,s)` | `NUMBER(p,s)` |
| `json` | `CLOB` + `CHECK (coluna IS JSON)` |

> Referência completa dos tipos e do schema Oracle: **`ESTRUTURA_BANCO_ORACLE.md`**.

### Exemplo prático

A mudança do `telefone` acima vira, para a TI:

```sql
ALTER TABLE usuarios ADD telefone VARCHAR2(20 CHAR);
```

É esse trechinho que você manda para os colegas rodarem no Oracle. 👍

> **Dica de organização:** mantenha um histórico dessas mudanças num lugar só
> (uma mensagem fixa, um arquivo, um e-mail acumulado) para a TI sempre saber o
> que é novo desde a última vez.

---

## Comandos de referência rápida

| Comando | O que faz |
|---------|-----------|
| `alembic upgrade head` | Aplica todas as mudanças pendentes no banco |
| `alembic current` | Mostra em que versão o banco está agora |
| `alembic history` | Lista o histórico de todas as migrations |
| `alembic revision --autogenerate -m "..."` | Cria uma migration nova a partir do `models.py` |
| `alembic upgrade head --sql` | Mostra o SQL sem aplicar (útil pra traduzir pro Oracle) |
| `alembic downgrade -1` | Desfaz a última migration (cuidado!) |

---

## Erros comuns

- **"command not found: alembic"** → você esqueceu de ativar o ambiente:
  `venv\Scripts\activate`.
- **Erro de conexão / "could not connect"** → a `DATABASE_URL` não está
  configurada no `.env` (veja `SETUP_BANCO_NOVO.md`, passo 4).
- **A migration não apareceu** → você criou uma tabela nova mas esqueceu de
  adicionar o nome dela no `import` do `migrations/env.py`.
- **Funcionou no seu PC mas sumiu depois** → você esqueceu de **commitar** o
  arquivo de `migrations/versions/`. Sempre faça o `git commit`.

---

### Arquivos relacionados
- **`ESTRUTURA_BANCO_ORACLE.md`** — schema completo em Oracle (referência da TI)
- **`SETUP_BANCO_NOVO.md`** — instalar o Hub e o banco do zero
- **`scripts/consultar_estrutura_postgres.sql`** — consultas para inspecionar o banco no pgAdmin
