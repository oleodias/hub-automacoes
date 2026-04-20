# ══════════════════════════════════════════════════════════════
# utils/logging_config.py — Configuração de Logging do Hub
# ══════════════════════════════════════════════════════════════
# Configura o sistema de logging para:
#   1. Mostrar no terminal (como os prints faziam)
#   2. Salvar em arquivo rotativo (logs/hub_YYYY-MM-DD.log)
#
# Uso em qualquer arquivo do projeto:
#   import logging
#   logger = logging.getLogger(__name__)
#   logger.info("mensagem")
# ══════════════════════════════════════════════════════════════

import os
import logging
from logging.handlers import TimedRotatingFileHandler


def configurar_logging():
    """
    Configura o logging do Hub. Chame uma vez no app.py ao iniciar.

    Cria dois "destinos" para as mensagens de log:
      - Terminal: mostra tudo (nível DEBUG pra cima)
      - Arquivo:  salva WARNING pra cima (o que importa investigar depois)

    Os arquivos ficam em logs/ com rotação diária.
    Logs com mais de 30 dias são apagados automaticamente.
    """

    # Cria a pasta de logs se não existir
    os.makedirs('logs', exist_ok=True)

    # ── Formato das mensagens ─────────────────────────────────
    # Terminal: mais visual, com emojis
    formato_terminal = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(name)s — %(message)s',
        datefmt='%H:%M:%S'
    )

    # Arquivo: mais técnico, com data completa
    formato_arquivo = logging.Formatter(
        '%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ── Handler do Terminal ───────────────────────────────────
    # Mostra as mensagens no terminal (substitui os prints)
    handler_terminal = logging.StreamHandler()
    handler_terminal.setLevel(logging.DEBUG)
    handler_terminal.setFormatter(formato_terminal)

    # ── Handler do Arquivo ────────────────────────────────────
    # Salva em arquivo com rotação diária
    # - when='midnight': cria um arquivo novo a cada dia
    # - backupCount=30: mantém os últimos 30 dias
    # - encoding='utf-8': suporta emojis e acentos
    handler_arquivo = TimedRotatingFileHandler(
        filename='logs/hub.log',
        when='midnight',
        backupCount=30,
        encoding='utf-8',
    )
    handler_arquivo.setLevel(logging.INFO)
    handler_arquivo.setFormatter(formato_arquivo)
    handler_arquivo.suffix = '%Y-%m-%d'

    # ── Configurar o logger raiz ──────────────────────────────
    # O logger raiz é o "pai" de todos os loggers do projeto.
    # Qualquer logger.info() em qualquer arquivo passa por aqui.
    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(logging.DEBUG)

    # Remove handlers antigos (evita duplicação se chamar 2x)
    logger_raiz.handlers.clear()

    logger_raiz.addHandler(handler_terminal)
    logger_raiz.addHandler(handler_arquivo)

    # ── Silenciar bibliotecas barulhentas ─────────────────────
    # Sem isso, o SQLAlchemy e o Werkzeug despejam centenas de
    # linhas de debug que poluem o terminal e o arquivo.
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('alembic').setLevel(logging.INFO)

    logging.getLogger(__name__).info("Sistema de logging configurado com sucesso.")
