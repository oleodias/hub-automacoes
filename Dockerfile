# ══════════════════════════════════════════════════════════════
# Dockerfile — Hub de Automações Ciamed
# ══════════════════════════════════════════════════════════════
# "Receita" que monta a imagem do Hub: o sistema operacional, o
# Python, as bibliotecas, o navegador dos robôs e o código.
# A MESMA imagem roda nos 3 ambientes (dev/homolog/prod) — o que
# muda é só o arquivo .env de cada um.
#
# O BANCO NÃO entra aqui: o Hub se conecta ao Postgres/Oracle pela
# rede, pelo DATABASE_URL.
#
# Para montar a imagem:   docker compose build hub
# ══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Evita perguntas interativas do apt e deixa o Python "falar na hora"
# (logs aparecem no terminal sem ficar presos num buffer).
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Sao_Paulo

# ── Navegador para os robôs (Selenium) ───────────────────────
# Os robôs (RPA) abrem um navegador de verdade para operar o ERP.
# Instalamos o Chromium e o seu driver, mais as fontes, para as
# páginas renderizarem certo. CHROME_BIN aponta o executável.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-liberation \
        tzdata \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# ── Dependências Python ──────────────────────────────────────
# Copiamos só o requirements primeiro: assim o Docker reaproveita
# esta camada (cache) e não reinstala tudo a cada mudança de código.
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==23.0.0

# ── Código da aplicação ──────────────────────────────────────
# Copiamos por último (muda com frequência). O cwd é /app porque os
# robôs em automacoes/ usam imports "soltos" que dependem da raiz.
COPY . .

# Porta interna onde o Gunicorn escuta (o Nginx fala com ela).
EXPOSE 8000

# Script que sobe o servidor (ver entrypoint.sh).
ENTRYPOINT ["/app/entrypoint.sh"]
