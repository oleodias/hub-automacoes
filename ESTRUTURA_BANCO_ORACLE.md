# Estrutura do Banco de Dados — Hub de Automações

Documento de referência para a equipe de TI criar o banco do Hub no
**Oracle** da empresa.

- **Banco atual:** PostgreSQL 16 (máquina de desenvolvimento)
- **Banco de destino:** Oracle Database 19c Standard Edition 2 (Release 19.0.0.0.0)
- **Total de tabelas:** 14
- **Origem do schema:** SQLAlchemy (`models.py`) + migrations Alembic
  (head atual: `b7c8d9e0f1a2`)
- **Última atualização deste documento:** 13/07/2026
- **Padrão de nomes:** todos os objetos usam o prefixo **`cm_hub_aut_`**
  (padrão da TI Ciamed)

> **Documentos complementares:**
> - **[docs/migracao_oracle.md](docs/migracao_oracle.md)** — plano completo da
>   migração (dados, adaptações da aplicação, checklist e validação).
> - **`scripts/exportar_dados_oracle.py`** — gera os `INSERT`s Oracle com os
>   dados atuais do Hub, prontos para executar após o DDL deste documento.

> ⚠️ **Mudança importante nesta versão (13/07/2026):** o módulo de
> **Lançamento de Notas** foi descontinuado (o sistema próprio da Ciamed já
> cobre esse processo). As tabelas `cm_hub_aut_lancamentos_notas`,
> `cm_hub_aut_centros_custo` e `cm_hub_aut_operacoes_nota`, presentes em
> versões anteriores deste documento, **não existem mais**. Se o banco Oracle
> já tiver sido criado com uma versão antiga, veja a **Seção 5** (atualização
> incremental).

Abaixo vai (1) o resumo de cada tabela, (2) o mapeamento de tipos
PostgreSQL → Oracle e (3) o **DDL pronto para rodar no Oracle**.

---

## 1. Lista das tabelas

| #   | Tabela                          | Função                                                                          |
| --- | ------------------------------- | ------------------------------------------------------------------------------- |
| 1   | `cm_hub_aut_usuarios`           | Usuários do Hub (login, cargo, permissões por módulo)                           |
| 2   | `cm_hub_aut_submissoes`         | Fichas cadastrais de clientes enviadas para análise                             |
| 3   | `cm_hub_aut_links_ficha`        | Links de ficha gerados (rastreio: quem gerou, p/ qual cliente, validade e uso)  |
| 4   | `cm_hub_aut_execucoes`          | Histórico de execução dos robôs (RPA)                                           |
| 5   | `cm_hub_aut_fila_execucao`      | Fila persistente "um robô por vez" (recursos `rpa` e `cadastro`)                |
| 6   | `cm_hub_aut_notas_categorias`   | Categorias de despesa (energia, água, etc.)                                     |
| 7   | `cm_hub_aut_notas_unidades`     | Unidades da empresa (Matriz, filiais)                                           |
| 8   | `cm_hub_aut_notas_fornecedores` | Fornecedores recorrentes (notas mensais)                                        |
| 9   | `cm_hub_aut_notas`              | Lançamento mensal de notas (Kanban de controle)                                 |
| 10  | `cm_hub_aut_chamados`           | Tickets de suporte abertos pelos usuários                                       |
| 11  | `cm_hub_aut_chamados_anexos`    | Arquivos anexados a um chamado                                                  |
| 12  | `cm_hub_aut_chamados_historico` | Timeline de eventos de um chamado                                               |
| 13  | `cm_hub_aut_notificacoes`       | Avisos para o usuário (sininho)                                                 |
| 14  | `cm_hub_aut_faq_perguntas`      | Perguntas frequentes por módulo                                                 |

> A tabela `alembic_version` (controle das migrations) existe **só no
> PostgreSQL de desenvolvimento** — no Oracle a estrutura é mantida
> manualmente pela TI, então ela **não precisa ser criada**.

### Relacionamentos (chaves estrangeiras)

```
cm_hub_aut_usuarios ──┬─< cm_hub_aut_execucoes (usuario_id)
                      ├─< cm_hub_aut_chamados (usuario_id)
                      ├─< cm_hub_aut_chamados_historico (usuario_id)
                      └─< cm_hub_aut_notificacoes (usuario_id)

cm_hub_aut_chamados ──┬─< cm_hub_aut_chamados_anexos (chamado_id)
                      ├─< cm_hub_aut_chamados_historico (chamado_id)
                      └─< cm_hub_aut_notificacoes (chamado_id)

cm_hub_aut_notas_categorias ──┬─< cm_hub_aut_notas_fornecedores (categoria_id)
                              └─< cm_hub_aut_notas (categoria_id)

cm_hub_aut_notas_unidades ────┬─< cm_hub_aut_notas_fornecedores (unidade_id)
                              └─< cm_hub_aut_notas (unidade_id)

cm_hub_aut_notas_fornecedores ──< cm_hub_aut_notas (fornecedor_recorrente_id)

cm_hub_aut_usuarios   ··< cm_hub_aut_links_ficha (gerado_por_id)    -- referência lógica, sem FK
cm_hub_aut_submissoes ··< cm_hub_aut_links_ficha (submission_uuid)  -- referência lógica, sem FK

cm_hub_aut_fila_execucao      -- independente, sem FKs
```

> **Ordem de criação:** as tabelas-pai precisam existir antes das tabelas-filho.
> O DDL abaixo já está na ordem correta.

---

## 2. Mapeamento de tipos PostgreSQL → Oracle

| Tipo no código (SQLAlchemy) | PostgreSQL     | Oracle (usado no DDL)                          | Observação                               |
| --------------------------- | -------------- | ---------------------------------------------- | ---------------------------------------- |
| `Integer`                   | `INTEGER`      | `NUMBER(10)`                                   | inteiros comuns                          |
| `BigInteger`                | `BIGINT`       | `NUMBER(19)`                                   | usado no id da fila                      |
| `Integer` (PK auto)         | `SERIAL`       | `NUMBER(10) GENERATED BY DEFAULT AS IDENTITY`  | auto-incremento (Oracle 12c+)            |
| `String(n)`                 | `VARCHAR(n)`   | `VARCHAR2(n CHAR)`                             | `CHAR` para contar caracteres, não bytes |
| `Text`                      | `TEXT`         | `CLOB`                                         | texto longo                              |
| `Boolean`                   | `BOOLEAN`      | `NUMBER(1)` + `CHECK (col IN (0,1))`           | Oracle não tem BOOLEAN no SQL até 23c    |
| `DateTime`                  | `TIMESTAMP`    | `TIMESTAMP`                                    | data + hora                              |
| `Date`                      | `DATE`         | `DATE`                                         | só data                                  |
| `Numeric(p,s)`              | `NUMERIC(p,s)` | `NUMBER(p,s)`                                  | valores monetários (precisão exata)      |
| `JSON`                      | `JSON`         | `CLOB` + `CHECK (col IS JSON)`                 | ver nota abaixo                          |

> **Sobre o JSON:** o app guarda alguns campos como JSON (permissões do
> usuário, dados da ficha, detalhes da execução do robô, tipos de retenção
> etc.). No Oracle 19c o jeito suportado é **`CLOB` com a constraint
> `IS JSON`** (o tipo nativo `JSON` só existe a partir do 21c). Os campos
> JSON são:
> `cm_hub_aut_usuarios.permissoes` ·
> `cm_hub_aut_submissoes.dados_json/docs_enviados/motivos_reprovacao/erro_robo/n8n_payload` ·
> `cm_hub_aut_execucoes.detalhes` ·
> `cm_hub_aut_notas_fornecedores.retencoes_padrao` ·
> `cm_hub_aut_notas.retencoes`.

> **Sobre o auto-incremento:** `GENERATED BY DEFAULT AS IDENTITY` permite
> tanto o app inserir sem informar o id (o Oracle gera) quanto a carga
> inicial inserir ids explícitos (preservando os ids do PostgreSQL). Após a
> carga de dados é preciso **ressincronizar** o contador — o script de
> exportação já gera esses comandos (ver `docs/migracao_oracle.md`).

> **Sobre BOOLEAN:** representado como `NUMBER(1)` (0 = falso,
> 1 = verdadeiro) com `CHECK`. O valor padrão segue o que o app usa
> (ex.: `ativo` = 1).

---

## 3. DDL Oracle (pronto para executar)

```sql
-- ════════════════════════════════════════════════════════════════
-- Hub de Automações — Schema Oracle 19c
-- Ordem respeita as dependências de chave estrangeira.
-- Gerado a partir do schema PostgreSQL em 13/07/2026
-- (alembic head b7c8d9e0f1a2).
-- ════════════════════════════════════════════════════════════════

-- ── 1. usuarios ─────────────────────────────────────────────────
CREATE TABLE cm_hub_aut_usuarios (
    id          NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    nome        VARCHAR2(150 CHAR)  NOT NULL,
    email       VARCHAR2(150 CHAR)  NOT NULL,
    senha_hash  VARCHAR2(256 CHAR)  NOT NULL,
    cargo       VARCHAR2(20 CHAR)   DEFAULT 'operador',
    permissoes  CLOB,
    ativo       NUMBER(1)      DEFAULT 1,
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_usuarios       PRIMARY KEY (id),
    CONSTRAINT uq_cm_hub_aut_usuarios_email UNIQUE (email),
    CONSTRAINT ck_cm_hub_aut_usuarios_ativo CHECK (ativo IN (0,1)),
    CONSTRAINT ck_cm_hub_aut_usuarios_perm  CHECK (permissoes IS JSON)
);

-- ── 2. submissoes ───────────────────────────────────────────────
CREATE TABLE cm_hub_aut_submissoes (
    uuid               VARCHAR2(36 CHAR)  NOT NULL,
    cnpj               VARCHAR2(20 CHAR)  NOT NULL,
    razao_social       VARCHAR2(255 CHAR),
    tentativa          NUMBER(10)    DEFAULT 1,
    status             VARCHAR2(20 CHAR)  DEFAULT 'pendente',
    dados_json         CLOB,
    docs_enviados      CLOB,
    motivos_reprovacao CLOB,
    erro_robo          CLOB,
    envio_n8n          VARCHAR2(20 CHAR)  DEFAULT 'enviado',  -- 'enviado' | 'falhou'
    n8n_erro           CLOB,                                  -- erro do último envio ao N8N
    n8n_payload        CLOB,                                  -- dados p/ reenvio (JSON)
    created_at         TIMESTAMP,
    updated_at         TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_submissoes PRIMARY KEY (uuid),
    CONSTRAINT ck_cm_hub_aut_subm_dados    CHECK (dados_json IS JSON),
    CONSTRAINT ck_cm_hub_aut_subm_docs     CHECK (docs_enviados IS JSON),
    CONSTRAINT ck_cm_hub_aut_subm_motivos  CHECK (motivos_reprovacao IS JSON),
    CONSTRAINT ck_cm_hub_aut_subm_erro     CHECK (erro_robo IS JSON),
    CONSTRAINT ck_cm_hub_aut_subm_payload  CHECK (n8n_payload IS JSON)
);

-- ── 3. links_ficha ──────────────────────────────────────────────
CREATE TABLE cm_hub_aut_links_ficha (
    id              NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    token           VARCHAR2(64 CHAR)   NOT NULL,   -- segredo que vai na URL (?t=)
    cnpj_cliente    VARCHAR2(14 CHAR)   NOT NULL,   -- CNPJ do cliente (só dígitos)
    gerado_por_id   NUMBER(10),                     -- usuário que gerou (ref. lógica)
    gerado_por_nome VARCHAR2(150 CHAR),
    vendedor        VARCHAR2(255 CHAR),
    representante   VARCHAR2(255 CHAR),
    captacao        VARCHAR2(50 CHAR),
    tipo            VARCHAR2(20 CHAR),              -- 'NOVO' | 'REATIVACAO'
    codigo_nl       VARCHAR2(50 CHAR),
    created_at      TIMESTAMP,
    expira_em       TIMESTAMP      NOT NULL,        -- created_at + 7 dias
    usado_em        TIMESTAMP,                      -- quando uma ficha foi enviada pelo link
    submission_uuid VARCHAR2(36 CHAR),              -- ficha gerada (ref. lógica → cm_hub_aut_submissoes.uuid)
    cnpj_divergente NUMBER(1)      DEFAULT 0,
    CONSTRAINT pk_cm_hub_aut_links_ficha       PRIMARY KEY (id),
    CONSTRAINT uq_cm_hub_aut_links_ficha_token UNIQUE (token),
    CONSTRAINT ck_cm_hub_aut_links_ficha_div   CHECK (cnpj_divergente IN (0,1))
);

-- ── 4. execucoes ────────────────────────────────────────────────
CREATE TABLE cm_hub_aut_execucoes (
    id           NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    usuario_id   NUMBER(10),
    usuario_nome VARCHAR2(150 CHAR)  DEFAULT 'Sistema',
    robo         VARCHAR2(50 CHAR)   NOT NULL,
    status       VARCHAR2(20 CHAR)   DEFAULT 'executando',
    inicio       TIMESTAMP,
    fim          TIMESTAMP,
    duracao_seg  NUMBER(10),
    detalhes     CLOB,
    created_at   TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_execucoes       PRIMARY KEY (id),
    CONSTRAINT fk_cm_hub_aut_execucoes_user  FOREIGN KEY (usuario_id) REFERENCES cm_hub_aut_usuarios(id),
    CONSTRAINT ck_cm_hub_aut_execucoes_det   CHECK (detalhes IS JSON)
);

-- ── 5. fila_execucao ────────────────────────────────────────────
-- Fila persistente que garante "um robô por vez" mesmo com vários
-- workers. Recursos: 'rpa' (robôs de itens/MDF/fornecedor) e
-- 'cadastro' (fluxo de clientes com N8N). A coluna resume_url guarda
-- a URL que acorda o Wait node do N8N (só na fila de cadastro).
CREATE TABLE cm_hub_aut_fila_execucao (
    id          NUMBER(19)     GENERATED BY DEFAULT AS IDENTITY,
    token       VARCHAR2(36 CHAR)   NOT NULL,
    recurso     VARCHAR2(30 CHAR)   NOT NULL,                       -- 'rpa' | 'cadastro'
    status      VARCHAR2(20 CHAR)   DEFAULT 'aguardando' NOT NULL,  -- 'aguardando' | 'executando'
    resume_url  CLOB,
    criado_em   TIMESTAMP      NOT NULL,
    iniciado_em TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_fila_execucao       PRIMARY KEY (id),
    CONSTRAINT uq_cm_hub_aut_fila_execucao_token UNIQUE (token)
);
CREATE INDEX ix_cm_hub_aut_fila_exec_rec_status
    ON cm_hub_aut_fila_execucao (recurso, status);

-- ── 6. notas_categorias ─────────────────────────────────────────
CREATE TABLE cm_hub_aut_notas_categorias (
    id         VARCHAR2(50 CHAR)   NOT NULL,
    nome       VARCHAR2(100 CHAR)  NOT NULL,
    ordem      NUMBER(10)     DEFAULT 0,
    ativa      NUMBER(1)      DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_notas_categorias PRIMARY KEY (id),
    CONSTRAINT ck_cm_hub_aut_ncat_ativa CHECK (ativa IN (0,1))
);

-- ── 7. notas_unidades ───────────────────────────────────────────
CREATE TABLE cm_hub_aut_notas_unidades (
    id         VARCHAR2(20 CHAR)   NOT NULL,
    nome       VARCHAR2(100 CHAR)  NOT NULL,
    short      VARCHAR2(10 CHAR)   NOT NULL,
    ordem      NUMBER(10)     DEFAULT 0,
    ativa      NUMBER(1)      DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_notas_unidades PRIMARY KEY (id),
    CONSTRAINT ck_cm_hub_aut_nuni_ativa CHECK (ativa IN (0,1))
);

-- ── 8. notas_fornecedores ───────────────────────────────────────
CREATE TABLE cm_hub_aut_notas_fornecedores (
    id               NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    fornecedor       VARCHAR2(200 CHAR)  NOT NULL,
    cnpj             VARCHAR2(20 CHAR),
    categoria_id     VARCHAR2(50 CHAR)   NOT NULL,
    unidade_id       VARCHAR2(20 CHAR)   NOT NULL,
    dia_esperado     NUMBER(10)     NOT NULL,
    retencao_padrao  NUMBER(1)      DEFAULT 0,
    retencoes_padrao CLOB,                          -- lista JSON: ["inss","iss",...]
    valor_medio      NUMBER(12,2),
    iniciado_em      VARCHAR2(7 CHAR),              -- 'AAAA-MM'
    observacoes      CLOB,
    ativo            NUMBER(1)      DEFAULT 1,
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_notas_fornecedores  PRIMARY KEY (id),
    CONSTRAINT fk_cm_hub_aut_nforn_categoria FOREIGN KEY (categoria_id) REFERENCES cm_hub_aut_notas_categorias(id),
    CONSTRAINT fk_cm_hub_aut_nforn_unidade   FOREIGN KEY (unidade_id)   REFERENCES cm_hub_aut_notas_unidades(id),
    CONSTRAINT ck_cm_hub_aut_nforn_ret    CHECK (retencao_padrao IN (0,1)),
    CONSTRAINT ck_cm_hub_aut_nforn_retpad CHECK (retencoes_padrao IS JSON),
    CONSTRAINT ck_cm_hub_aut_nforn_ativo  CHECK (ativo IN (0,1))
);

-- ── 9. notas ────────────────────────────────────────────────────
CREATE TABLE cm_hub_aut_notas (
    id                       NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    mes                      NUMBER(10)     NOT NULL,
    ano                      NUMBER(10)     NOT NULL,
    fornecedor_recorrente_id NUMBER(10),
    fornecedor               VARCHAR2(200 CHAR)  NOT NULL,
    cnpj                     VARCHAR2(20 CHAR),
    categoria_id             VARCHAR2(50 CHAR)   NOT NULL,
    unidade_id               VARCHAR2(20 CHAR)   NOT NULL,
    dia_esperado             NUMBER(10)     NOT NULL,
    recebida_em              DATE,
    nf_numero                VARCHAR2(50 CHAR),
    valor_liquido            NUMBER(12,2),
    retencao                 NUMBER(1)      DEFAULT 0,
    retencoes                CLOB,                    -- lista JSON: ["inss","iss",...]
    observacoes              CLOB,
    avulsa                   NUMBER(1)      DEFAULT 0,
    created_at               TIMESTAMP,
    updated_at               TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_notas PRIMARY KEY (id),
    CONSTRAINT fk_cm_hub_aut_notas_categoria  FOREIGN KEY (categoria_id) REFERENCES cm_hub_aut_notas_categorias(id),
    CONSTRAINT fk_cm_hub_aut_notas_unidade    FOREIGN KEY (unidade_id)   REFERENCES cm_hub_aut_notas_unidades(id),
    CONSTRAINT fk_cm_hub_aut_notas_forn_rec   FOREIGN KEY (fornecedor_recorrente_id) REFERENCES cm_hub_aut_notas_fornecedores(id),
    CONSTRAINT ck_cm_hub_aut_notas_retencao  CHECK (retencao IN (0,1)),
    CONSTRAINT ck_cm_hub_aut_notas_retencoes CHECK (retencoes IS JSON),
    CONSTRAINT ck_cm_hub_aut_notas_avulsa    CHECK (avulsa IN (0,1))
);
CREATE INDEX ix_cm_hub_aut_notas_mes_ano         ON cm_hub_aut_notas (mes, ano);
CREATE INDEX ix_cm_hub_aut_notas_unidade_mes_ano ON cm_hub_aut_notas (unidade_id, mes, ano);

-- ── 10. chamados ────────────────────────────────────────────────
CREATE TABLE cm_hub_aut_chamados (
    id         NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    protocolo  VARCHAR2(20 CHAR)   NOT NULL,
    usuario_id NUMBER(10)     NOT NULL,
    modulo     VARCHAR2(50 CHAR)   DEFAULT 'geral',
    prioridade VARCHAR2(20 CHAR)   DEFAULT 'media',
    assunto    VARCHAR2(255 CHAR)  NOT NULL,
    mensagem   CLOB           NOT NULL,
    status     VARCHAR2(20 CHAR)   DEFAULT 'pendente',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_chamados      PRIMARY KEY (id),
    CONSTRAINT uq_cm_hub_aut_chamados_prot UNIQUE (protocolo),
    CONSTRAINT fk_cm_hub_aut_chamados_user FOREIGN KEY (usuario_id) REFERENCES cm_hub_aut_usuarios(id)
);

-- ── 11. chamados_anexos ─────────────────────────────────────────
CREATE TABLE cm_hub_aut_chamados_anexos (
    id            NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    chamado_id    NUMBER(10)     NOT NULL,
    nome_arquivo  VARCHAR2(255 CHAR)  NOT NULL,
    caminho       VARCHAR2(500 CHAR)  NOT NULL,
    tipo_mime     VARCHAR2(100 CHAR),
    tamanho_bytes NUMBER(10),
    created_at    TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_chamados_anexos  PRIMARY KEY (id),
    CONSTRAINT fk_cm_hub_aut_chanexos_chamado FOREIGN KEY (chamado_id) REFERENCES cm_hub_aut_chamados(id)
);

-- ── 12. chamados_historico ──────────────────────────────────────
CREATE TABLE cm_hub_aut_chamados_historico (
    id              NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    chamado_id      NUMBER(10)     NOT NULL,
    usuario_id      NUMBER(10),
    tipo            VARCHAR2(30 CHAR)   NOT NULL,
    status_anterior VARCHAR2(20 CHAR),
    status_novo     VARCHAR2(20 CHAR),
    mensagem        CLOB,
    created_at      TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_chamados_historico PRIMARY KEY (id),
    CONSTRAINT fk_cm_hub_aut_chhist_chamado FOREIGN KEY (chamado_id) REFERENCES cm_hub_aut_chamados(id),
    CONSTRAINT fk_cm_hub_aut_chhist_user    FOREIGN KEY (usuario_id) REFERENCES cm_hub_aut_usuarios(id)
);

-- ── 13. notificacoes ────────────────────────────────────────────
CREATE TABLE cm_hub_aut_notificacoes (
    id         NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    usuario_id NUMBER(10)     NOT NULL,
    chamado_id NUMBER(10),
    tipo       VARCHAR2(30 CHAR)   NOT NULL,
    titulo     VARCHAR2(255 CHAR)  NOT NULL,
    lida       NUMBER(1)      DEFAULT 0,
    created_at TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_notificacoes  PRIMARY KEY (id),
    CONSTRAINT fk_cm_hub_aut_notif_user    FOREIGN KEY (usuario_id) REFERENCES cm_hub_aut_usuarios(id),
    CONSTRAINT fk_cm_hub_aut_notif_chamado FOREIGN KEY (chamado_id) REFERENCES cm_hub_aut_chamados(id),
    CONSTRAINT ck_cm_hub_aut_notif_lida CHECK (lida IN (0,1))
);

-- ── 14. faq_perguntas ───────────────────────────────────────────
CREATE TABLE cm_hub_aut_faq_perguntas (
    id         NUMBER(10)     GENERATED BY DEFAULT AS IDENTITY,
    modulo     VARCHAR2(50 CHAR)   NOT NULL,
    pergunta   VARCHAR2(500 CHAR)  NOT NULL,
    resposta   CLOB           NOT NULL,
    ordem      NUMBER(10)     DEFAULT 0,
    ativo      NUMBER(1)      DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT pk_cm_hub_aut_faq_perguntas PRIMARY KEY (id),
    CONSTRAINT ck_cm_hub_aut_faq_ativo CHECK (ativo IN (0,1))
);
CREATE INDEX ix_cm_hub_aut_faq_perguntas_modulo ON cm_hub_aut_faq_perguntas (modulo);
```

---

## 4. Observações importantes

> **Compatibilidade confirmada:** o DDL acima foi validado para
> **Oracle 19c Standard Edition 2**. Todas as escolhas de tipo já são as
> recomendadas para essa versão — não é preciso adaptar a estrutura.

1. **Auto-incremento (IDENTITY):** `GENERATED BY DEFAULT AS IDENTITY` é
   suportado nativamente no 19c (recurso disponível desde o 12c). **Nenhuma
   SEQUENCE/TRIGGER manual é necessária.** Após a carga inicial de dados
   (que insere os ids vindos do PostgreSQL), rode os `ALTER TABLE ... MODIFY
   (id GENERATED ... START WITH LIMIT VALUE)` que o script de exportação
   gera — isso ressincroniza o contador para `max(id)+1`.

2. **Campos JSON:** no 19c o tipo `JSON` nativo **ainda não existe** (só a
   partir do 21c), por isso os campos JSON estão como `CLOB` +
   `CHECK (... IS JSON)`, que é exatamente a forma suportada pelo 19c.
   **Manter como está.** O SQLAlchemy (dialeto Oracle) lê e grava esses
   campos normalmente.

3. **Boolean:** mapeado como `NUMBER(1)` (0 = falso, 1 = verdadeiro) com
   `CHECK`, pois o 19c não tem tipo `BOOLEAN` em SQL (só no 23c). O
   SQLAlchemy converte True/False ↔ 1/0 automaticamente no dialeto Oracle.

4. **Charset do banco:** o Hub grava acentuação (português) em praticamente
   todas as tabelas. O ideal é o banco/PDB usar **AL32UTF8**. Os `VARCHAR2`
   estão declarados com semântica **CHAR** justamente para o limite contar
   caracteres (e não bytes), igual ao PostgreSQL.

5. **Nomes de tabela × aplicação:** o app (SQLAlchemy) usa os nomes **sem**
   o prefixo (`usuarios`, `notas`, ...). Para o app funcionar no Oracle com
   as tabelas prefixadas, a forma mais simples é criar **SYNONYMs** no
   schema de conexão — o script pronto está em
   [docs/migracao_oracle.md](docs/migracao_oracle.md), Seção 4.

6. **Datas:** `created_at`/`updated_at` são preenchidos pela aplicação
   (Python), não pelo banco. Se a TI quiser default no banco, dá para
   adicionar `DEFAULT SYSTIMESTAMP` — inofensivo para o app.

7. **Dados iniciais:** além da estrutura, o Hub precisa dos dados atuais
   (usuários, fichas, execuções, categorias/unidades do Kanban, FAQ).
   O script `scripts/exportar_dados_oracle.py` gera o arquivo de `INSERT`s
   com **tudo que existe hoje** no banco de desenvolvimento, já na ordem
   correta das FKs. Ver `docs/migracao_oracle.md`.

---

## 5. Atualização incremental (banco Oracle JÁ criado com versão antiga deste documento)

> Use esta seção **somente** se a TI já tiver criado o banco com uma versão
> anterior deste documento. Para instalações **do zero**, o DDL da Seção 3
> já contempla tudo — pule esta seção.

### 5.1. REMOVER o módulo Lançamento de Notas (descontinuado em 13/07/2026)

O módulo foi descontinuado (o sistema próprio da Ciamed já faz esse
trabalho). Se as tabelas existirem, podem ser dropadas — não há dados de
produção nelas:

```sql
DROP TABLE cm_hub_aut_lancamentos_notas;
DROP TABLE cm_hub_aut_operacoes_nota;
DROP TABLE cm_hub_aut_centros_custo;

-- FAQ do módulo descontinuado (se a tabela de FAQ já tiver sido populada)
DELETE FROM cm_hub_aut_faq_perguntas WHERE modulo = 'lancamento_notas';
COMMIT;
```

### 5.2. Tabela nova `cm_hub_aut_fila_execucao` (migration `a1b2c3d4e5f6`)

Fila persistente "um robô por vez". Use o bloco da Seção 3 (tabela nº 5).

### 5.3. Coluna nova em `cm_hub_aut_notas_fornecedores` (migration `e5f6a7b8c9d0`)

```sql
ALTER TABLE cm_hub_aut_notas_fornecedores ADD (retencoes_padrao CLOB);
ALTER TABLE cm_hub_aut_notas_fornecedores
    ADD CONSTRAINT ck_cm_hub_aut_nforn_retpad CHECK (retencoes_padrao IS JSON);
```

### 5.4. Coluna nova em `cm_hub_aut_notas` (migration `b7c8d9e0f1a2`)

```sql
ALTER TABLE cm_hub_aut_notas ADD (retencoes CLOB);
ALTER TABLE cm_hub_aut_notas
    ADD CONSTRAINT ck_cm_hub_aut_notas_retencoes CHECK (retencoes IS JSON);
```

### 5.5. Itens de versões ainda mais antigas (aplicar apenas se faltarem)

- **Colunas de envio ao N8N em `cm_hub_aut_submissoes`** (migration `c3d4e5f6a7b8`):

  ```sql
  ALTER TABLE cm_hub_aut_submissoes ADD (
      envio_n8n   VARCHAR2(20 CHAR) DEFAULT 'enviado',
      n8n_erro    CLOB,
      n8n_payload CLOB
  );
  ALTER TABLE cm_hub_aut_submissoes
      ADD CONSTRAINT ck_cm_hub_aut_subm_payload CHECK (n8n_payload IS JSON);
  ```

- **Tabela `cm_hub_aut_links_ficha`** (migration `d4e5f6a7b8c9`): use o bloco
  da Seção 3 (tabela nº 3).

---

## Histórico deste documento

| Data       | Mudança                                                                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------- |
| 13/07/2026 | Removidas as 3 tabelas do Lançamento de Notas (módulo descontinuado); adicionadas `fila_execucao`, `notas_fornecedores.retencoes_padrao` e `notas.retencoes`; total de 16 → 14 tabelas; novo doc de migração em `docs/migracao_oracle.md`. |
| (anterior) | Prefixo `cm_hub_aut_` em todos os objetos (padrão TI); tabela `links_ficha`; colunas N8N em `submissoes`; compatibilidade 19c SE2 confirmada. |
