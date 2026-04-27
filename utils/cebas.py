# ══════════════════════════════════════════════════════════════
# utils/cebas.py — Consulta CEBAS contra planilha local
# ══════════════════════════════════════════════════════════════
# Verifica se um CNPJ possui certificação CEBAS consultando
# a planilha CEBAS_ATUALIZADO.xlsx pela COLUNA B (CNPJ Base).
#
# A busca é feita pelos 8 primeiros dígitos do CNPJ (a "base"),
# ignorando filial e dígito verificador. Assim, se a matriz
# tem CEBAS, todas as filiais também são reconhecidas.
#
# Exemplo:
#   CNPJ completo: 05.782.733/0001-49
#   CNPJ Base:     05782733 (8 primeiros dígitos)
#   Busca na coluna B da planilha por "05782733"
#
# A planilha é carregada UMA VEZ em memória e fica em cache
# até o Flask reiniciar.
#
# Uso:
#   from utils.cebas import consultar_cebas
#   resultado = consultar_cebas("05782733000149")  # → "SIM" ou "NAO"
# ══════════════════════════════════════════════════════════════

import os
import re
import openpyxl
import logging

logger = logging.getLogger(__name__)

# ── Cache em memória ──
_bases_cebas = None

# ── Caminho da planilha (raiz do projeto) ──
CAMINHO_PLANILHA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'CEBAS_ATUALIZADO_(27042026).xlsx')


def _carregar_planilha():
    """
    Lê a COLUNA B (CNPJ Base) da planilha CEBAS e monta um set
    de bases (8 dígitos, só números). Chamada uma única vez.
    """
    global _bases_cebas

    if not os.path.exists(CAMINHO_PLANILHA):
        logger.error(f"[CEBAS] Planilha não encontrada: {CAMINHO_PLANILHA}")
        _bases_cebas = set()
        return

    try:
        wb = openpyxl.load_workbook(CAMINHO_PLANILHA, data_only=True, read_only=True)
        ws = wb.active

        bases = set()
        # Coluna B = coluna 2 (CNPJ Base)
        for row in ws.iter_rows(min_row=3, min_col=2, max_col=2, values_only=True):
            valor = row[0]
            if valor:
                # Remove pontuação, deixa só dígitos
                base_limpa = re.sub(r'\D', '', str(valor))
                if len(base_limpa) >= 8:
                    bases.add(base_limpa[:8])

        wb.close()
        _bases_cebas = bases
        logger.info(f"[CEBAS] Planilha carregada com {len(bases)} bases de CNPJ.")

    except Exception as e:
        logger.error(f"[CEBAS] Erro ao carregar planilha: {e}")
        _bases_cebas = set()


def consultar_cebas(cnpj):
    """
    Recebe um CNPJ completo (com ou sem pontuação) e retorna "SIM" ou "NAO".
    A busca é feita pelos 8 primeiros dígitos (base do CNPJ).
    Nunca levanta exceção.
    """
    if _bases_cebas is None:
        _carregar_planilha()

    # Extrai só dígitos e pega os 8 primeiros (base)
    cnpj_limpo = re.sub(r'\D', '', str(cnpj or ''))

    if len(cnpj_limpo) < 8:
        logger.warning(f"[CEBAS] CNPJ inválido (menos de 8 dígitos): {cnpj!r}")
        return "NAO"

    base = cnpj_limpo[:8]
    resultado = "SIM" if base in _bases_cebas else "NAO"
    logger.info(f"[CEBAS] CNPJ {cnpj_limpo} (base {base}) → {resultado}")
    return resultado
