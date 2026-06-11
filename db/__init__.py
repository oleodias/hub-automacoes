# ══════════════════════════════════════════════════════════════
# db/ — Camada de acesso a dados do Hub
# ══════════════════════════════════════════════════════════════
# Este pacote reúne os módulos que falam com o banco em nome de
# cada funcionalidade, mantendo a raiz do projeto mais limpa:
#
#   db/banco_cadastros.py  → submissões de cadastro de clientes
#   db/banco_links.py      → links de ficha (token de acesso)
#   db/banco_notas.py      → lançamento de notas
#
# Uso (a partir de qualquer rota):
#     from db import banco_notas
#     banco_notas.minha_funcao(...)
#
# Observação: estes módulos usam o ORM (SQLAlchemy) e seguem os
# models automaticamente — não há SQL "cru" com nome de tabela aqui.
# ══════════════════════════════════════════════════════════════
