# ══════════════════════════════════════════════════════════════
# utils/rastreio.py — Registro de Execuções de Robôs
# ══════════════════════════════════════════════════════════════
# Uso nas rotas:
#
#   exec_id = iniciar_execucao_robo('mdf')        → cria registro
#   finalizar_execucao_robo(exec_id, 'sucesso')   → fecha registro
#   finalizar_execucao_robo(exec_id, 'erro', {'erro': 'msg'})
#
# O usuario_id e usuario_nome são pegos automaticamente da sessão.
# ══════════════════════════════════════════════════════════════

import logging
from datetime import datetime
from flask import session
from extensions import db
from models import Execucao

logger = logging.getLogger(__name__)


def iniciar_execucao_robo(robo, detalhes=None, usuario_id=None, usuario_nome=None):
    """
    Cria um registro de execução com status 'executando'.
    Retorna o ID do registro para ser usado no finalizar.

    Parâmetros:
        robo           → chave do robô (ex: 'mdf', 'itens_fase1')
        detalhes       → dict opcional com dados extras
        usuario_id     → ID do usuário (se não informado, tenta pegar da sessão)
        usuario_nome   → nome do usuário (se não informado, tenta pegar da sessão)
    """
    # Tenta pegar da sessão apenas se não foi passado explicitamente
    if usuario_id is None:
        try:
            usuario_id = session.get('usuario_id')
        except RuntimeError:
            usuario_id = None

    if usuario_nome is None:
        try:
            usuario_nome = session.get('usuario_nome', 'Sistema')
        except RuntimeError:
            usuario_nome = 'Sistema'

    execucao = Execucao(
        usuario_id=usuario_id,
        usuario_nome=usuario_nome or 'Sistema',
        robo=robo,
        status='executando',
        inicio=datetime.now(),
        detalhes=detalhes or {},
    )

    db.session.add(execucao)
    db.session.commit()

    logger.info(
        f"[RASTREIO] Iniciado | Robô: {robo} | "
        f"Usuário: {execucao.usuario_nome} | ID: {execucao.id}"
    )

    return execucao.id


def finalizar_execucao_robo(exec_id, status='sucesso', detalhes=None):
    """
    Atualiza o registro de execução com o resultado final.

    Parâmetros:
        exec_id   → ID retornado por iniciar_execucao_robo()
        status    → 'sucesso', 'erro' ou 'aviso'
        detalhes  → dict opcional com dados extras (erro, avisos, etc)
    """
    execucao = db.session.get(Execucao, exec_id)
    if not execucao:
        logger.warning(f"[RASTREIO] Execução ID {exec_id} não encontrada")
        return

    agora = datetime.now()
    execucao.status = status
    execucao.fim = agora
    execucao.duracao_seg = int((agora - execucao.inicio).total_seconds())

    if detalhes:
        # Merge: mantém o que já tinha e adiciona o novo
        dados_atuais = execucao.detalhes or {}
        dados_atuais.update(detalhes)
        execucao.detalhes = dados_atuais

    db.session.commit()

    # Formata duração para o log
    mins = execucao.duracao_seg // 60
    segs = execucao.duracao_seg % 60
    duracao_fmt = f"{mins}min {segs}s" if mins > 0 else f"{segs}s"

    logger.info(
        f"[RASTREIO] Finalizado | Robô: {execucao.robo} | "
        f"Status: {status} | Duração: {duracao_fmt} | "
        f"Usuário: {execucao.usuario_nome}"
    )
