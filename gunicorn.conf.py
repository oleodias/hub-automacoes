# ══════════════════════════════════════════════════════════════
# gunicorn.conf.py — Configuração do servidor de produção
# ══════════════════════════════════════════════════════════════
# O Gunicorn é o servidor que roda o Flask em produção (no lugar do
# servidor embutido, que é só para dev). O Nginx fica na frente dele.
# ══════════════════════════════════════════════════════════════

import os

# Onde o Gunicorn escuta. 0.0.0.0:8000 = aceita conexões de dentro da
# rede do Docker (o Nginx, em outro container/host, fala com esta porta).
bind = "0.0.0.0:8000"

# ── Número de "trabalhadores" (workers) ──────────────────────
# IMPORTANTE: a fila dos robôs (utils/fila.py) já é segura com vários
# workers, porque a "vez" é controlada no banco com trava (lock). Ainda
# assim, mantemos POUCOS workers — os robôs são pesados (abrem navegador)
# e não adianta ter muitos processos web disputando a mesma máquina.
# Ajustável pelo .env (WEB_CONCURRENCY); padrão conservador: 3.
workers = int(os.getenv("WEB_CONCURRENCY", "3"))

# Tempo (segundos) até o Gunicorn matar um worker travado. Folgado
# porque algumas telas (upload de XML/planilha) podem demorar.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Reaproveita conexões e recicla workers de tempos em tempos (evita
# vazamento de memória em processos de vida longa).
max_requests = 1000
max_requests_jitter = 100

# Logs no terminal do container (o Docker captura e guarda).
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
