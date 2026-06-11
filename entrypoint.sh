#!/bin/sh
# ══════════════════════════════════════════════════════════════
# entrypoint.sh — o que roda quando o container do Hub sobe
# ══════════════════════════════════════════════════════════════
# De propósito, este script faz UMA coisa só: subir o servidor web
# (Gunicorn). Ele NÃO mexe no banco automaticamente.
#
# Por quê? Aplicar migrations (mudar a estrutura do banco) é uma
# decisão deliberada, feita à mão, e que no Oracle nem usa o
# Alembic (lá o schema vem do DDL da TI). Rodar isso sozinho a cada
# subida seria arriscado. Veja docs/DEPLOY_LINUX.md para o passo a
# passo de migrations e seeds.
# ══════════════════════════════════════════════════════════════
set -e

echo "🚀 Subindo o Hub de Automações (Gunicorn)..."

# 'exec' faz o Gunicorn virar o processo principal do container,
# para que ele receba corretamente os sinais de parar/reiniciar.
exec gunicorn --config gunicorn.conf.py app:app
