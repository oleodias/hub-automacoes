-- ════════════════════════════════════════════════════════════════
-- Consultas para inspecionar a estrutura do banco no pgAdmin 4
-- Banco: hub_automacoes (PostgreSQL)
--
-- Como usar:
--   1. No pgAdmin, selecione o banco "hub_automacoes"
--   2. Abra o Query Tool (Tools > Query Tool, ou o ícone de raio)
--   3. Cole a consulta desejada e rode (F5)
-- ════════════════════════════════════════════════════════════════


-- ── 1. Estrutura completa de TODAS as tabelas ──────────────────
-- Cada coluna de cada tabela: tipo, tamanho, obrigatoriedade e default.
SELECT
    c.table_name                                AS tabela,
    c.ordinal_position                          AS nº,
    c.column_name                               AS coluna,
    CASE
        WHEN c.data_type = 'character varying'
            THEN 'varchar(' || c.character_maximum_length || ')'
        WHEN c.data_type = 'numeric'
            THEN 'numeric(' || c.numeric_precision || ',' || c.numeric_scale || ')'
        ELSE c.data_type
    END                                         AS tipo,
    CASE WHEN c.is_nullable = 'NO' THEN 'NOT NULL' ELSE '' END AS obrigatorio,
    c.column_default                            AS valor_padrao
FROM information_schema.columns c
JOIN information_schema.tables t
      ON t.table_name = c.table_name
     AND t.table_schema = c.table_schema
WHERE c.table_schema = 'public'
  AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position;


-- ── 2. Resumo: tabelas + nº de colunas + nº de linhas ──────────
SELECT
    t.table_name                                              AS tabela,
    (SELECT COUNT(*) FROM information_schema.columns col
      WHERE col.table_name = t.table_name
        AND col.table_schema = 'public')                      AS qtd_colunas,
    s.n_live_tup                                              AS qtd_linhas_aprox
FROM information_schema.tables t
LEFT JOIN pg_stat_user_tables s
       ON s.relname = t.table_name
WHERE t.table_schema = 'public'
  AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name;


-- ── 3. Chaves primárias e estrangeiras (relacionamentos) ───────
SELECT
    tc.table_name                AS tabela,
    tc.constraint_type           AS tipo,
    kcu.column_name              AS coluna,
    ccu.table_name               AS referencia_tabela,
    ccu.column_name              AS referencia_coluna
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage ccu
      ON tc.constraint_name = ccu.constraint_name
     AND tc.constraint_type = 'FOREIGN KEY'
WHERE tc.table_schema = 'public'
  AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
ORDER BY tc.table_name, tc.constraint_type DESC;


-- ── 4. Índices de todas as tabelas ─────────────────────────────
SELECT
    tablename   AS tabela,
    indexname   AS indice,
    indexdef    AS definicao
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
