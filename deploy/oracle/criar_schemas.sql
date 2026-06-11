-- ════════════════════════════════════════════════════════════════
-- criar_schemas.sql — Cria os schemas do Hub no Oracle (MODELO p/ a TI)
-- ════════════════════════════════════════════════════════════════
-- Este é um MODELO para a equipe de TI/DBA da empresa. Ele cria DOIS
-- usuários (no Oracle, "usuário" = "schema" = espaço com tabelas
-- próprias), de modo que os dados de TESTE e os dados REAIS fiquem
-- fisicamente separados no MESMO servidor Oracle (Topologia A):
--
--     Servidor Oracle (um só)
--       ├─ HUB_HOMOLOG  → dados de teste
--       └─ HUB_PROD     → dados reais
--
-- O Hub não muda entre os dois: só o DATABASE_URL (qual usuário conecta)
-- é diferente. As 17 tabelas (com o prefixo cm_hub_aut_) são criadas
-- DENTRO de cada schema, a partir do DDL em docs/BANCO_DE_DADOS_ORACLE.md.
--
-- ATENÇÃO TI:
--   • Revise nomes de tablespace, quotas e senhas conforme o padrão da casa.
--   • Troque as SENHAS abaixo por senhas fortes (uma para cada schema).
--   • Rode este script conectado como um usuário administrativo (ex.: SYSTEM),
--     no PDB correto.
-- ════════════════════════════════════════════════════════════════


-- ── 1) Schema de HOMOLOGAÇÃO ────────────────────────────────────
CREATE USER HUB_HOMOLOG IDENTIFIED BY "TROCAR_SENHA_HOMOLOG"
    DEFAULT TABLESPACE USERS
    TEMPORARY TABLESPACE TEMP
    QUOTA UNLIMITED ON USERS;

-- Permissões mínimas para a aplicação criar e operar suas tabelas.
GRANT CREATE SESSION         TO HUB_HOMOLOG;
GRANT CREATE TABLE           TO HUB_HOMOLOG;
GRANT CREATE SEQUENCE        TO HUB_HOMOLOG;
GRANT CREATE VIEW            TO HUB_HOMOLOG;


-- ── 2) Schema de PRODUÇÃO ───────────────────────────────────────
CREATE USER HUB_PROD IDENTIFIED BY "TROCAR_SENHA_PROD"
    DEFAULT TABLESPACE USERS
    TEMPORARY TABLESPACE TEMP
    QUOTA UNLIMITED ON USERS;

GRANT CREATE SESSION         TO HUB_PROD;
GRANT CREATE TABLE           TO HUB_PROD;
GRANT CREATE SEQUENCE        TO HUB_PROD;
GRANT CREATE VIEW            TO HUB_PROD;


-- ════════════════════════════════════════════════════════════════
-- PRÓXIMO PASSO (para cada schema, SEPARADAMENTE):
--   1) Conecte-se como o usuário (ex.: HUB_HOMOLOG) e rode o DDL das
--      tabelas de docs/BANCO_DE_DADOS_ORACLE.md.
--   2) Repita conectado como HUB_PROD.
-- Assim cada schema fica com a sua própria cópia das 17 tabelas
-- cm_hub_aut_*, sem misturar os dados.
--
-- IMPORTANTE: os schemas NÃO devem enxergar as tabelas um do outro.
-- Não conceda SELECT/INSERT cruzado entre HUB_HOMOLOG e HUB_PROD.
-- ════════════════════════════════════════════════════════════════
