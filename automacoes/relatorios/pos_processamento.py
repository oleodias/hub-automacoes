# ══════════════════════════════════════════════════════════════
# pos_processamento.py — Ajustes na planilha após o download
# ──────────────────────────────────────────────────────────────
# Fase posterior. Por ora só o gancho do Fresenius está previsto:
# somar o valor de "Vlr desconto" dentro de "Pr CX". A regra exata
# ainda será detalhada — este stub apenas COPIA o arquivo para um
# destino específico do lab, sem transformar, para não travar o fluxo.
# ══════════════════════════════════════════════════════════════
import shutil


def fresenius_desconto(caminho_entrada, caminho_saida):
    """Fresenius: somar 'Vlr desconto' em 'Pr CX'. (Implementação real pendente.)"""
    print("> ℹ️ [pos] fresenius_desconto: regra ainda não implementada — copiando arquivo sem alterar.")
    shutil.copyfile(caminho_entrada, caminho_saida)
    return caminho_saida


# Registro nome -> função (usado por gerar_relatorios.aplicar_pos_processamento)
HOOKS = {
    "fresenius_desconto": fresenius_desconto,
}
