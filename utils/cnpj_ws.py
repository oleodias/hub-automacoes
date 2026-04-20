# ══════════════════════════════════════════════════════════════
# utils/cnpj_ws.py — Enriquecimento de dados via CNPJ.ws
# ══════════════════════════════════════════════════════════════
# Consulta a Receita Federal (via cnpj.ws) e devolve campos
# quebrados (cep, logradouro, numero, ie, cnae, etc).
#
# FILOSOFIA: a API é um BÔNUS, não um REQUISITO.
# Se ela falhar, devolve dict com strings vazias e o fluxo
# continua normalmente.
# ══════════════════════════════════════════════════════════════

import requests

import logging
logger = logging.getLogger(__name__)

def consultar_cnpj_ws(cnpj_limpo):
    """
    Consulta a API cnpj.ws e devolve um dict com os campos enriquecidos.
    Em caso de erro, devolve o mesmo dict mas com todos os valores vazios.
    Nunca levanta exceção.
    """
    dados_vazios = {
        "nome_fantasia":            "",
        "inscricao_estadual":       "",
        "cnae_principal_descricao": "",
        "cep":                      "",
        "logradouro":               "",
        "numero":                   "",
        "complemento":              "",
        "bairro":                   "",
        "uf":                       "",
        "_cnpj_ws_status":          "vazio",
    }

    if not cnpj_limpo or len(cnpj_limpo) != 14:
        logger.warning(f"[CNPJ.ws] CNPJ inválido ou vazio: {cnpj_limpo!r}")
        return dados_vazios

    try:
        url = f"https://publica.cnpj.ws/cnpj/{cnpj_limpo}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            print(f"⚠️ [CNPJ.ws] Status {resp.status_code} para CNPJ {cnpj_limpo}")
            dados_vazios["_cnpj_ws_status"] = f"http_{resp.status_code}"
            return dados_vazios

        api_json = resp.json()
        estab = api_json.get("estabelecimento", {}) or {}

        tipo_log = estab.get("tipo_logradouro", "") or ""
        nome_log = estab.get("logradouro", "") or ""
        logradouro = f"{tipo_log} {nome_log}".strip()

        complemento_sujo = estab.get("complemento") or ""
        complemento = " ".join(str(complemento_sujo).split())

        cnae_id = estab.get("atividade_principal", {}).get("id", "") or ""
        cnae_desc = estab.get("atividade_principal", {}).get("descricao", "") or ""
        cnae_completo = f"{cnae_id} - {cnae_desc}" if cnae_id else cnae_desc

        ies_ativas = []
        for ie in estab.get("inscricoes_estaduais", []) or []:
            if ie.get("ativo") is True:
                numero_ie = ie.get("inscricao_estadual")
                if numero_ie:
                    ies_ativas.append(numero_ie)
        ie_final = ", ".join(ies_ativas) if ies_ativas else "Isento / Não encontrada"

        dados_enriquecidos = {
            "nome_fantasia":            estab.get("nome_fantasia", "") or "",
            "inscricao_estadual":       ie_final,
            "cnae_principal_descricao": cnae_completo,
            "cep":                      estab.get("cep", "") or "",
            "logradouro":               logradouro,
            "numero":                   estab.get("numero", "") or "",
            "complemento":              complemento,
            "bairro":                   estab.get("bairro", "") or "",
            "uf":                       (estab.get("estado", {}) or {}).get("sigla", "") or "",
            "_cnpj_ws_status":          "ok",
        }
        logger.info(f"[CNPJ.ws] Dados extraídos para CNPJ {cnpj_limpo}")
        return dados_enriquecidos

    except requests.Timeout:
        print(f"⚠️ [CNPJ.ws] Timeout consultando CNPJ {cnpj_limpo}")
        dados_vazios["_cnpj_ws_status"] = "timeout"
        return dados_vazios

    except requests.ConnectionError as e:
        print(f"⚠️ [CNPJ.ws] Falha de conexão: {e}")
        dados_vazios["_cnpj_ws_status"] = "connection_error"
        return dados_vazios

    except Exception as e:
        print(f"⚠️ [CNPJ.ws] Erro inesperado: {e}")
        dados_vazios["_cnpj_ws_status"] = "erro_inesperado"
        return dados_vazios
