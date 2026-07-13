# ══════════════════════════════════════════════════════════════
# scripts/exportar_dados_oracle.py — Exporta os dados do Hub
# (PostgreSQL local) como INSERTs prontos para o Oracle 19c.
# ══════════════════════════════════════════════════════════════
# Parte da migração para o servidor da empresa — ver:
#   docs/migracao_oracle.md        (plano completo)
#   ESTRUTURA_BANCO_ORACLE.md      (DDL das tabelas de destino)
#
# Uso (a partir da raiz do projeto, com o venv ativo):
#     python scripts/exportar_dados_oracle.py
#
# Gera: scripts/export_oracle/dados_hub_oracle.sql  (UTF-8)
#
# O arquivo gerado:
#   - insere TODAS as tabelas na ordem correta das FKs;
#   - preserva os ids originais do PostgreSQL;
#   - converte datas (TO_TIMESTAMP/TO_DATE), booleanos (0/1) e
#     JSON (literal CLOB) para a sintaxe do Oracle;
#   - quebra textos longos em pedaços TO_CLOB(...) || ... para não
#     estourar o limite de 4000 bytes de literal do Oracle;
#   - ressincroniza os contadores IDENTITY no final (START WITH
#     LIMIT VALUE) para o app não colidir com ids já carregados;
#   - termina com COMMIT.
#
# ⚠️ SENSÍVEL: o arquivo contém hashes de senha e dados de clientes.
#    A pasta scripts/export_oracle/ está no .gitignore — transfira
#    por canal seguro e apague as cópias depois da carga.
# ══════════════════════════════════════════════════════════════

import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal

# Raiz do projeto no path (este arquivo vive em scripts/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app                      # noqa: E402
from extensions import db                # noqa: E402
from sqlalchemy import inspect, text     # noqa: E402

# ── Configuração ─────────────────────────────────────────────

# Prefixo dos objetos no Oracle (padrão da TI Ciamed)
PREFIXO = 'cm_hub_aut_'

# Ordem de carga respeitando as FKs (pais antes dos filhos).
ORDEM_TABELAS = [
    'usuarios',
    'submissoes',
    'links_ficha',
    'execucoes',
    'fila_execucao',
    'notas_categorias',
    'notas_unidades',
    'notas_fornecedores',
    'notas',
    'chamados',
    'chamados_anexos',
    'chamados_historico',
    'notificacoes',
    'faq_perguntas',
]

# Tabelas cujo id é IDENTITY no Oracle (precisam do reset do contador).
TABELAS_IDENTITY = {
    'usuarios', 'links_ficha', 'execucoes', 'fila_execucao',
    'notas_fornecedores', 'notas', 'chamados', 'chamados_anexos',
    'chamados_historico', 'notificacoes', 'faq_perguntas',
}

PASTA_SAIDA  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export_oracle')
ARQUIVO_SAIDA = os.path.join(PASTA_SAIDA, 'dados_hub_oracle.sql')

# Limite prático de um literal VARCHAR2 no Oracle é 4000 bytes; acima
# disso o valor precisa virar CLOB (TO_CLOB + concatenação). Usamos
# margens folgadas porque caracteres acentuados ocupam mais de 1 byte.
TAMANHO_PEDACO   = 1000   # caracteres por pedaço de literal
LIMITE_VARCHAR   = 2000   # acima disso, embrulha em TO_CLOB


# ── Formatação de valores → literais Oracle ──────────────────

def _literal_texto(s: str) -> str:
    """
    Converte uma string Python num literal Oracle seguro:
      - aspas simples escapadas ('' );
      - quebras de linha viram CHR(10) (evita problemas no SQL*Plus);
      - textos longos são quebrados em pedaços concatenados, com
        TO_CLOB() no primeiro pedaço quando o total passa do limite.
    """
    s = s.replace('\r\n', '\n').replace('\r', '\n')

    pedacos = []
    for i, linha in enumerate(s.split('\n')):
        if i > 0:
            pedacos.append('CHR(10)')
        for j in range(0, len(linha), TAMANHO_PEDACO):
            trecho = linha[j:j + TAMANHO_PEDACO].replace("'", "''")
            pedacos.append(f"'{trecho}'")

    if not pedacos:
        # String vazia: no Oracle '' == NULL. Para o Hub tanto faz.
        return 'NULL'

    # TO_CLOB no primeiro literal promove a expressão inteira a CLOB,
    # liberando o resultado do limite de 4000 bytes.
    if len(s) > LIMITE_VARCHAR or len(pedacos) > 3:
        for k, p in enumerate(pedacos):
            if p.startswith("'"):
                pedacos[k] = f'TO_CLOB({p})'
                break

    return ' || '.join(pedacos)


def _literal(valor) -> str:
    """Converte qualquer valor Python para o literal SQL do Oracle."""
    if valor is None:
        return 'NULL'
    if isinstance(valor, bool):
        return '1' if valor else '0'
    if isinstance(valor, (int, Decimal)):
        return str(valor)
    if isinstance(valor, float):
        return repr(valor)
    if isinstance(valor, datetime):
        return ("TO_TIMESTAMP('" + valor.strftime('%Y-%m-%d %H:%M:%S.%f')
                + "', 'YYYY-MM-DD HH24:MI:SS.FF6')")
    if isinstance(valor, date):
        return "TO_DATE('" + valor.strftime('%Y-%m-%d') + "', 'YYYY-MM-DD')"
    if isinstance(valor, (dict, list)):
        # Colunas JSON: o psycopg2 devolve dict/list prontos. O json.dumps
        # já escapa quebras de linha (\n) DENTRO dos valores, então o
        # literal resultante fica numa linha só.
        return _literal_texto(json.dumps(valor, ensure_ascii=False,
                                         separators=(',', ':')))
    return _literal_texto(str(valor))


# ── Exportação ───────────────────────────────────────────────

def exportar():
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    with app.app_context():
        insp = inspect(db.engine)
        existentes = set(insp.get_table_names())

        faltando = [t for t in ORDEM_TABELAS if t not in existentes]
        if faltando:
            print(f'❌ Tabelas não encontradas no banco local: {faltando}')
            print('   Rode "alembic upgrade head" e tente de novo.')
            sys.exit(1)

        linhas_sql = []
        contagens  = {}

        for tabela in ORDEM_TABELAS:
            colunas = [c['name'] for c in insp.get_columns(tabela)]
            pk      = (insp.get_pk_constraint(tabela)['constrained_columns']
                       or [colunas[0]])

            ordem = ', '.join(f'"{c}"' for c in pk)
            rows = db.session.execute(
                text(f'SELECT * FROM "{tabela}" ORDER BY {ordem}')
            ).mappings().all()
            contagens[tabela] = len(rows)

            linhas_sql.append('')
            linhas_sql.append(f'-- ── {PREFIXO}{tabela} '
                              f'({len(rows)} linha(s)) {"─" * 20}')
            if not rows:
                linhas_sql.append(f'-- (sem dados)')
                continue

            cols_sql = ', '.join(colunas)
            for row in rows:
                valores = ', '.join(_literal(row[c]) for c in colunas)
                linhas_sql.append(
                    f'INSERT INTO {PREFIXO}{tabela} ({cols_sql}) '
                    f'VALUES ({valores});'
                )

        # ── Reset dos contadores IDENTITY ────────────────────
        linhas_sql.append('')
        linhas_sql.append('-- ── Ressincroniza os contadores IDENTITY '
                          '(max(id)+1) ──────────')
        for tabela in ORDEM_TABELAS:
            if tabela in TABELAS_IDENTITY:
                linhas_sql.append(
                    f'ALTER TABLE {PREFIXO}{tabela} MODIFY '
                    f'(id GENERATED BY DEFAULT AS IDENTITY '
                    f'(START WITH LIMIT VALUE));'
                )

        linhas_sql.append('')
        linhas_sql.append('COMMIT;')

        # ── Cabeçalho com o retrato da exportação ────────────
        total = sum(contagens.values())
        cab = [
            '-- ════════════════════════════════════════════════════════',
            '-- Hub de Automações — carga de dados PostgreSQL → Oracle 19c',
            f'-- Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}',
            f'-- Total de linhas: {total}',
            '--',
            '-- Contagens por tabela (conferir após a carga):',
        ]
        for t in ORDEM_TABELAS:
            cab.append(f'--   {PREFIXO}{t:<22} {contagens[t]:>5}')
        cab += [
            '--',
            '-- Pré-requisitos: DDL do ESTRUTURA_BANCO_ORACLE.md já executado.',
            '-- Executar conectado como o usuário dono das tabelas (HUB_AUT).',
            '-- ════════════════════════════════════════════════════════',
            'SET DEFINE OFF;',
        ]

        with open(ARQUIVO_SAIDA, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(cab + linhas_sql) + '\n')

    print(f'✅ Exportação concluída: {ARQUIVO_SAIDA}')
    print(f'   {total} linha(s) em {len(ORDEM_TABELAS)} tabela(s).')
    for t in ORDEM_TABELAS:
        if contagens[t]:
            print(f'   - {t}: {contagens[t]}')
    print('\n⚠️  O arquivo contém hashes de senha e dados de clientes.')
    print('   Transfira por canal seguro e apague as cópias após a carga.')


if __name__ == '__main__':
    exportar()
