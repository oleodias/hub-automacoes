# ══════════════════════════════════════════════════════════════
# routes/notas.py — Controle de Notas Fiscais (Kanban)
# ══════════════════════════════════════════════════════════════
# FASE 0 — apenas drop-in visual:
#   - Renderiza a página do Kanban dentro do Hub
#   - Dados ainda vêm do mock.js + localStorage do navegador
#
# FASES SEGUINTES (a implementar):
#   - Modelos (FornecedorRecorrente, Nota) + migrações
#   - Endpoints REST que substituem o mock por dados do PostgreSQL
#   - Tela de Cadastro de Fornecedores Recorrentes
#   - Tela de Panorama (heatmap fornecedor × mês)
# ══════════════════════════════════════════════════════════════

from flask import Blueprint, render_template
from utils.auth import permissao_required

notas_bp = Blueprint('notas', __name__)


@notas_bp.route('/notas')
@permissao_required('notas')
def kanban_notas():
    """Tela principal do Kanban — renderiza o React app embutido."""
    return render_template('notas_kanban.html')
