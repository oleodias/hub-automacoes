# ══════════════════════════════════════════════════════════════
# pos_processamento.py — Ajustes na planilha após o download
# ──────────────────────────────────────────────────────────────
# Hooks por laboratório, aplicados SOBRE o .xlsx de venda já gerado
# (ver gerar_relatorios.aplicar_pos_processamento).
#
# Fresenius (fresenius_desconto): o relatório traz o "Pr Cx" LÍQUIDO do
# desconto e uma coluna "Vlr Desconto" à parte. A regra do lab é mostrar o
# preço CHEIO → somar "Vlr Desconto" de volta em "Pr Cx", linha a linha.
# Onde o desconto é 0 a linha fica intacta.
# DEPOIS de somar, a coluna "Vlr Desconto" é REMOVIDA do arquivo final: o
# desconto é um acordo interno Ciamed↔cliente e NÃO pode ser exposto ao
# laboratório. A remoção acontece mesmo em casos de borda (confidencialidade).
#
# ⚠️ Formato dos números: o robô grava o xlsx como TEXTO em pt-BR
# ("2.898,5729" = ponto de milhar, vírgula decimal). Por isso convertemos
# pt-BR → float p/ somar e devolvemos em pt-BR (4 casas) só nas linhas
# alteradas, preservando o texto original das demais.
# ══════════════════════════════════════════════════════════════
import shutil

import pandas as pd


# ── Helpers de número pt-BR ──────────────────────────────────────
def _num_ptbr(texto):
    """'2.898,5729' → 2898.5729. Retorna None se vazio/não numérico."""
    s = str(texto).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")   # tira milhar, vírgula→ponto
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_ptbr(valor, casas=4):
    """2988.2195 → '2.988,2195' (ponto de milhar, vírgula decimal)."""
    s = f"{valor:,.{casas}f}"                   # formato US: '2,988.2195'
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _achar_coluna(df, alvo):
    """Acha a coluna pelo nome, ignorando caixa e espaços nas pontas."""
    alvo = alvo.strip().lower()
    for c in df.columns:
        if str(c).strip().lower() == alvo:
            return c
    return None


# ── Hook: Fresenius ──────────────────────────────────────────────
def fresenius_desconto(caminho_entrada, caminho_saida):
    """Soma 'Vlr Desconto' em 'Pr Cx' (líquido → cheio) e REMOVE a coluna
    'Vlr Desconto' do arquivo final — o desconto é acordo interno Ciamed↔cliente
    e não pode chegar ao laboratório."""
    df = pd.read_excel(caminho_entrada, dtype=str, keep_default_na=False)

    col_desc = _achar_coluna(df, "vlr desconto")
    col_prcx = _achar_coluna(df, "pr cx")

    # Sem a coluna de desconto não há o que somar nem o que esconder: copia como está.
    if not col_desc:
        print(f"> ⚠️ [pos] fresenius_desconto: coluna 'Vlr Desconto' não encontrada "
              f"(pr_cx={col_prcx!r}). Arquivo copiado SEM alteração.")
        shutil.copyfile(caminho_entrada, caminho_saida)
        return caminho_saida

    # Passo 1 — soma o desconto de volta no Pr Cx (só se o Pr Cx existir).
    if col_prcx:
        valores = df[col_prcx].tolist()
        alteradas = 0
        for i in range(len(df)):
            desconto = _num_ptbr(df.at[i, col_desc])
            if not desconto:                    # 0, vazio ou não numérico → mantém
                continue
            preco = _num_ptbr(df.at[i, col_prcx])
            if preco is None:                   # Pr Cx ilegível → não mexe
                continue
            valores[i] = _fmt_ptbr(preco + desconto, 4)
            alteradas += 1
        df[col_prcx] = valores
        print(f"> ✏️ [pos] fresenius_desconto: desconto somado em '{col_prcx}' "
              f"em {alteradas} de {len(df)} linha(s).")
    else:
        # Sem o Pr Cx não dá para somar — mas a coluna de desconto ainda assim
        # PRECISA sumir (confidencialidade). Avisa ALTO: os preços podem estar
        # líquidos (sem o desconto somado).
        print(f"> ⚠️ [pos] fresenius_desconto: coluna 'Pr Cx' não encontrada — "
              f"desconto NÃO foi somado; ainda assim vou remover 'Vlr Desconto'. "
              f"CONFIRA o relatório (preços podem estar líquidos).")

    # Passo 2 — remove a coluna 'Vlr Desconto' do arquivo final (SEMPRE).
    df = df.drop(columns=[col_desc])

    df.to_excel(caminho_saida, index=False)
    print(f"> 🗑️ [pos] fresenius_desconto: coluna '{col_desc}' removida do arquivo final.")
    return caminho_saida


# Registro nome -> função (usado por gerar_relatorios.aplicar_pos_processamento)
HOOKS = {
    "fresenius_desconto": fresenius_desconto,
}
