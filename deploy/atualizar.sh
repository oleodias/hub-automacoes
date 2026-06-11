#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
# atualizar.sh — "Botão" de atualização do Hub no servidor
# ══════════════════════════════════════════════════════════════
# Faz, em um comando só: baixa o código novo (git pull) e recria o
# container do Hub com a imagem atualizada.
#
# Uso (na pasta do projeto, no servidor):
#   ./deploy/atualizar.sh homolog     # atualiza a HOMOLOGAÇÃO
#   ./deploy/atualizar.sh prod        # atualiza a PRODUÇÃO
#
# Dica: teste SEMPRE em homologação antes de atualizar a produção.
# ══════════════════════════════════════════════════════════════
set -euo pipefail

AMBIENTE="${1:-}"

case "$AMBIENTE" in
    homolog)
        COMPOSE="docker-compose.homolog.yml"
        BRANCH="homologacao"
        ;;
    prod)
        COMPOSE="docker-compose.prod.yml"
        BRANCH="main"
        ;;
    *)
        echo "❌ Informe o ambiente: homolog ou prod"
        echo "   Ex.: ./deploy/atualizar.sh homolog"
        exit 1
        ;;
esac

echo "════════════════════════════════════════════════"
echo "  Atualizando o Hub — ambiente: $AMBIENTE"
echo "  Compose: $COMPOSE   |   Branch: $BRANCH"
echo "════════════════════════════════════════════════"

# 1) Baixa o código novo da branch do ambiente
echo "➡️  Baixando código novo (git pull origin $BRANCH)..."
git pull origin "$BRANCH"

# 2) Reconstroi a imagem e recria o container (sem derrubar à toa o que não mudou)
echo "➡️  Reconstruindo e subindo o container..."
docker compose -f "$COMPOSE" up -d --build

# 3) Mostra o status e os últimos logs
echo "➡️  Status:"
docker compose -f "$COMPOSE" ps
echo "➡️  Últimos logs (Ctrl+C para sair):"
docker compose -f "$COMPOSE" logs -f --tail=30

# LEMBRETE: se esta atualização incluiu mudança de estrutura do banco
# (migration nova) num banco PostgreSQL, rode o upgrade manualmente —
# veja docs/DEPLOY_LINUX.md. No Oracle, o schema é tratado com a TI.
