# ══════════════════════════════════════════════════════════════
# utils/cep_api.py — Consulta de endereço a partir do CEP
# ══════════════════════════════════════════════════════════════
# Descobre cidade, UF, bairro, logradouro e código IBGE a partir
# de um CEP. Usa a BrasilAPI como fonte principal (que já agrega
# ViaCEP/Correios) e, se ela falhar, cai no ViaCEP direto.
#
# FILOSOFIA (igual ao cnpj_ws.py): a API é um BÔNUS, não um
# REQUISITO. Se tudo falhar, devolve dict com strings vazias e
# o fluxo continua. Nunca levanta exceção.
# ══════════════════════════════════════════════════════════════

import re
import requests

import logging
logger = logging.getLogger(__name__)


def _dados_vazios(status="vazio"):
    return {
        "cep":             "",
        "logradouro":      "",
        "bairro":          "",
        "cidade":          "",
        "uf":              "",
        "ibge":            "",
        "_cep_api_status": status,
    }


def _consultar_brasilapi(cep_limpo):
    """BrasilAPI v2 (agrega várias fontes + traz IBGE). Retorna dict ou None."""
    url = f"https://brasilapi.com.br/api/cep/v2/{cep_limpo}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    if resp.status_code != 200:
        print(f"⚠️ [BrasilAPI] Status {resp.status_code} para CEP {cep_limpo}")
        return None
    j = resp.json()
    return {
        "cep":             re.sub(r'\D', '', j.get("cep", "") or "") or cep_limpo,
        "logradouro":      (j.get("street") or "").strip(),
        "bairro":          (j.get("neighborhood") or "").strip(),
        "cidade":          (j.get("city") or "").strip(),
        "uf":              (j.get("state") or "").strip().upper(),
        "ibge":            str((j.get("location") or {}).get("ibge", "") or ""),
        "_cep_api_status": "ok",
    }


def _consultar_viacep(cep_limpo):
    """ViaCEP (fallback). Retorna dict ou None."""
    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    if resp.status_code != 200:
        print(f"⚠️ [ViaCEP] Status {resp.status_code} para CEP {cep_limpo}")
        return None
    j = resp.json()
    # ViaCEP devolve {"erro": true} quando o CEP não existe.
    if j.get("erro"):
        return None
    return {
        "cep":             re.sub(r'\D', '', j.get("cep", "") or "") or cep_limpo,
        "logradouro":      (j.get("logradouro") or "").strip(),
        "bairro":          (j.get("bairro") or "").strip(),
        "cidade":          (j.get("localidade") or "").strip(),
        "uf":              (j.get("uf") or "").strip().upper(),
        "ibge":            (j.get("ibge") or "").strip(),
        "_cep_api_status": "ok",
    }


def consultar_cep(cep):
    """
    Consulta um CEP e devolve um dict com cidade, UF, bairro, logradouro
    e código IBGE. Tenta a BrasilAPI primeiro e, se falhar, o ViaCEP.

    Em caso de erro/CEP inexistente, devolve o mesmo dict com valores
    vazios e um `_cep_api_status` indicando o que houve. Nunca levanta
    exceção (a API é bônus, não requisito).
    """
    cep_limpo = re.sub(r'\D', '', str(cep or ""))

    if len(cep_limpo) != 8:
        logger.warning(f"[CEP] CEP inválido ou vazio: {cep!r}")
        return _dados_vazios("cep_invalido")

    # 1ª tentativa: BrasilAPI
    try:
        dados = _consultar_brasilapi(cep_limpo)
        if dados and dados.get("cidade") and dados.get("uf"):
            logger.info(f"[CEP] {cep_limpo} resolvido via BrasilAPI")
            return dados
    except requests.Timeout:
        print(f"⚠️ [BrasilAPI] Timeout consultando CEP {cep_limpo}")
    except requests.ConnectionError as e:
        print(f"⚠️ [BrasilAPI] Falha de conexão: {e}")
    except Exception as e:
        print(f"⚠️ [BrasilAPI] Erro inesperado: {e}")

    # 2ª tentativa: ViaCEP (fallback)
    try:
        dados = _consultar_viacep(cep_limpo)
        if dados and dados.get("cidade") and dados.get("uf"):
            logger.info(f"[CEP] {cep_limpo} resolvido via ViaCEP (fallback)")
            return dados
    except requests.Timeout:
        print(f"⚠️ [ViaCEP] Timeout consultando CEP {cep_limpo}")
        return _dados_vazios("timeout")
    except requests.ConnectionError as e:
        print(f"⚠️ [ViaCEP] Falha de conexão: {e}")
        return _dados_vazios("connection_error")
    except Exception as e:
        print(f"⚠️ [ViaCEP] Erro inesperado: {e}")
        return _dados_vazios("erro_inesperado")

    # Nenhuma das duas trouxe cidade/UF
    print(f"⚠️ [CEP] Não foi possível resolver o CEP {cep_limpo} em nenhuma API.")
    return _dados_vazios("nao_encontrado")
