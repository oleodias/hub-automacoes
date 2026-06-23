# ══════════════════════════════════════════════════════════════
# gerar_relatorios.py — Robô RPA dos relatórios aos laboratórios
# ──────────────────────────────────────────────────────────────
# Gera no NL (NLWeb/APEX) os dois relatórios — Análise de Estoque e
# Demanda Fornecedor — baixa em CSV, converte para .xlsx e devolve um
# MANIFESTO mapeando lab_id -> arquivos. O envio dos e-mails é do n8n.
#
# Contrato (espelha automacoes/clientes/cadastro_novo.executar):
#   entrada: job = {
#       "tipo": 1,                       # informativo
#       "modo_fantasma": True,
#       "envios": [
#           {"lab_id": "bayer", "periodo_ini": "01/05/2026", "periodo_fim": "31/05/2026"},
#           ...
#       ]
#   }
#   saída: {
#       "status": "Sucesso" | "Sucesso com avisos" | "Erro",
#       "msg": "...",
#       "pasta": "/abs/caminho/da/execucao",
#       "itens": [{"lab_id": "bayer", "nome": "Bayer", "arquivos": ["estoque_privado.xlsx", "venda_*.xlsx"]}],
#       "avisos": [...]
#   }
#
# Otimização (dedup): cada combinação única é gerada UMA vez —
#   • estoque por setor (privado/público);
#   • venda por (modelo + operação + período).
# Assim o estoque privado sai 1x (todos reusam) e a venda Sandoz 1x.
# ══════════════════════════════════════════════════════════════
import os
import re
import sys
import json
import time
import shutil
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# Login/navegador reaproveitados do robô de cadastro (não reescrevemos login).
from automacoes.clientes.navegacao_erp import iniciar_navegador, fazer_login
from automacoes.relatorios.labs_config import ESTOQUE, DEMANDA, LABS
from automacoes.relatorios import pos_processamento

# Pasta-base onde cada execução cria sua subpasta de downloads.
PASTA_BASE = os.getenv("RELATORIOS_DOWNLOAD_DIR", os.path.join(os.getcwd(), "downloads_relatorios"))
TIMEOUT_PADRAO = 30
TIMEOUT_DOWNLOAD = 180


# ─────────────────────────── Helpers de UI ───────────────────────────
def _js_click(driver, elemento):
    """Clique forçado via JS — padrão do projeto p/ não falhar no NL."""
    driver.execute_script("arguments[0].click();", elemento)


def _set_valor(driver, item_id, valor):
    """Define o valor de um item APEX (<select>/<input>) de forma robusta.

    Usa a API do próprio APEX — apex.item(id).setValue() — que inicializa o
    widget e dispara as cascatas/refresh corretamente, sem depender de clique
    nem do item já estar focado (o dispatchEvent "cru" só pega depois que o
    widget foi ativado). Faz fallback para value+events e, em <select>, para
    o Select nativo do Selenium.
    """
    el = WebDriverWait(driver, TIMEOUT_PADRAO).until(
        EC.presence_of_element_located((By.ID, item_id))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    ok = driver.execute_script(
        """
        var id = arguments[0], val = arguments[1];
        var el = document.getElementById(id);
        if (!el) { return false; }
        if (window.apex && apex.item) {            // caminho oficial do APEX
            try { apex.item(id).setValue(val); } catch (e) {}
        }
        el.value = val;                            // garante o value no DOM
        el.dispatchEvent(new Event('input',  {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        if (window.jQuery) {                       // APEX escuta via jQuery
            try { jQuery(el).trigger('change'); } catch (e) {}
        }
        return el.value === String(val);
        """,
        item_id, valor,
    )
    if not ok and el.tag_name.lower() == "select":  # rede de segurança
        try:
            Select(el).select_by_value(str(valor))
        except Exception:  # noqa: BLE001
            pass
    return el


def _selecionar_modelo(driver, item_id, value=None, label=None):
    """Seleciona o 'saved report' por VALUE (preferido) ou por NOME (label).

    Por label: procura a <option> cujo texto contenha o trecho informado e
    resolve o value real em tempo de execução — útil quando o relatório foi
    criado depois (não temos o value) ou quando o número visível muda.
    """
    el = WebDriverWait(driver, TIMEOUT_PADRAO).until(
        EC.presence_of_element_located((By.ID, item_id))
    )
    if not value and label:
        alvo = next(
            (op for op in Select(el).options if label.lower() in op.text.lower()),
            None,
        )
        if alvo is None:
            raise ValueError(f"Modelo '{label}' não encontrado no select {item_id}.")
        value = alvo.get_attribute("value")
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
        el, value,
    )
    return value


def _abrir_favorito(driver, invoker_code):
    """Abre a estrela de favoritos e clica no atalho pelo código invoker (estável)."""
    wait = WebDriverWait(driver, TIMEOUT_PADRAO)
    driver.switch_to.default_content()
    estrela = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[contains(@onclick, 'tab-header-menu-favoritos')]")))
    _js_click(driver, estrela)
    time.sleep(1.5)
    # Localiza o <a> do favorito pelo trecho do href: invoker(1,'N&L@....')
    link = wait.until(EC.presence_of_element_located(
        (By.XPATH, f"//a[contains(@href, \"{invoker_code}\")]")))
    _js_click(driver, link)
    time.sleep(2.5)


def _esperar_apex_pronto(driver, timeout=TIMEOUT_PADRAO):
    """Best-effort: espera o overlay de processamento do APEX sumir."""
    fim = time.time() + timeout
    seletor = ".u-Processing, .a-IRR-loading, #apex_wait_overlay, .apex_wait"
    while time.time() < fim:
        try:
            visiveis = [e for e in driver.find_elements(By.CSS_SELECTOR, seletor) if e.is_displayed()]
        except Exception:
            visiveis = []
        if not visiveis:
            return
        time.sleep(0.5)


def _baixar_csv(driver, cfg, pasta, destino_basename):
    """Abre Ações → Download → CSV, espera baixar e converte para .xlsx.

    Retorna o caminho do .xlsx final (com nome determinístico).
    """
    wait = WebDriverWait(driver, TIMEOUT_PADRAO)
    antes = set(os.listdir(pasta))

    # Ações
    botao_acoes = wait.until(EC.presence_of_element_located((By.ID, cfg["actions_button"])))
    _js_click(driver, botao_acoes)
    time.sleep(0.8)
    # Download (item do menu)
    item_download = wait.until(EC.presence_of_element_located((By.ID, cfg["download_menu_item"])))
    _js_click(driver, item_download)
    time.sleep(0.8)
    # CSV (dentro do diálogo)
    link_csv = wait.until(EC.presence_of_element_located((By.ID, cfg["download_csv"])))
    _js_click(driver, link_csv)

    caminho_csv = _esperar_download(pasta, antes)
    destino_xlsx = os.path.join(pasta, destino_basename + ".xlsx")
    _csv_para_xlsx(caminho_csv, destino_xlsx)
    try:
        os.remove(caminho_csv)  # mantém só o .xlsx final
    except OSError:
        pass
    print(f"> 💾 Gerado: {os.path.basename(destino_xlsx)}")
    return destino_xlsx


def _esperar_download(pasta, arquivos_antes, timeout=TIMEOUT_DOWNLOAD):
    """Espera surgir um arquivo novo e estável (sem .crdownload)."""
    fim = time.time() + timeout
    while time.time() < fim:
        atuais = set(os.listdir(pasta))
        novos = [a for a in (atuais - arquivos_antes) if not a.endswith(".crdownload")]
        if novos:
            caminho = os.path.join(pasta, novos[0])
            tamanho_1 = os.path.getsize(caminho)
            time.sleep(1.2)
            ainda_baixando = any(x.endswith(".crdownload") for x in os.listdir(pasta))
            if not ainda_baixando and os.path.getsize(caminho) == tamanho_1 and tamanho_1 > 0:
                return caminho
        time.sleep(0.5)
    raise TimeoutError("Download não foi concluído dentro do tempo limite.")


def _csv_para_xlsx(caminho_csv, destino_xlsx):
    """Converte o CSV do APEX em .xlsx (detecta separador/encoding)."""
    import pandas as pd

    df = None
    ultimo_erro = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(
                caminho_csv, sep=None, engine="python",
                dtype=str, encoding=enc, keep_default_na=False,
            )
            break
        except Exception as e:  # noqa: BLE001
            ultimo_erro = e
            df = None
    if df is None:
        raise ValueError(f"Falha ao ler o CSV baixado: {ultimo_erro}")
    df.to_excel(destino_xlsx, index=False)
    return destino_xlsx


def _slug(texto):
    return re.sub(r"[^A-Za-z0-9]+", "", str(texto))


# ─────────────────────── Geração de cada relatório ───────────────────────
def gerar_analise_estoque(driver, setor, pasta):
    """Tela A — gera a Análise de Estoque para um setor (privado/publico)."""
    print(f"> 📦 Análise de Estoque — setor: {setor}")
    wait = WebDriverWait(driver, TIMEOUT_PADRAO)
    wait.until(EC.presence_of_element_located((By.ID, ESTOQUE["item_marcador"])))

    _set_valor(driver, ESTOQUE["item_filtro"], ESTOQUE["filtro_setor"][setor])
    time.sleep(0.5)
    _set_valor(driver, ESTOQUE["saved_reports"], ESTOQUE["modelo_value"])
    time.sleep(0.8)
    _js_click(driver, driver.find_element(By.ID, ESTOQUE["btn_consultar"]))
    _esperar_apex_pronto(driver)
    time.sleep(1.5)

    return _baixar_csv(driver, ESTOQUE, pasta, f"estoque_{setor}")


def gerar_demanda(driver, modelo_value, modelo_label, operacao, data_ini, data_fim, pasta):
    """Tela B — gera a Demanda Fornecedor para (modelo, operação, período)."""
    rotulo = modelo_value or modelo_label
    print(f"> 🧾 Demanda Fornecedor — modelo {rotulo} | op {operacao} | {data_ini}→{data_fim}")
    wait = WebDriverWait(driver, TIMEOUT_PADRAO)
    wait.until(EC.presence_of_element_located((By.ID, DEMANDA["item_marcador"])))

    _set_valor(driver, DEMANDA["data_ini"], data_ini)
    _set_valor(driver, DEMANDA["data_fim"], data_fim)
    _set_valor(driver, DEMANDA["operacao"], operacao)
    time.sleep(0.4)
    _selecionar_modelo(driver, DEMANDA["saved_reports"], value=modelo_value, label=modelo_label)
    time.sleep(0.8)
    _js_click(driver, driver.find_element(By.ID, DEMANDA["btn_consultar"]))
    _esperar_apex_pronto(driver)
    time.sleep(1.5)

    nome = f"venda_{_slug(rotulo)}_{operacao}_{_slug(data_ini)}_{_slug(data_fim)}"
    return _baixar_csv(driver, DEMANDA, pasta, nome)


def aplicar_pos_processamento(caminho_venda, lab, pasta):
    """Aplica os hooks do lab (ex.: Fresenius) gerando um arquivo próprio."""
    caminho = caminho_venda
    for nome_hook in lab.get("pos", []):
        func = pos_processamento.HOOKS.get(nome_hook)
        if not func:
            continue
        destino = os.path.join(pasta, f"venda_{_slug(lab['nome'])}_{nome_hook}.xlsx")
        caminho = func(caminho, destino)
    return caminho


# ─────────────────────────── Orquestração ───────────────────────────
def executar(job):
    """Ponto de entrada chamado pelo Hub (síncrono). Ver contrato no topo."""
    envios = job.get("envios", []) or []
    modo_fantasma = job.get("modo_fantasma", True)
    avisos = []

    # Valida lab_ids cedo (evita abrir navegador à toa).
    desconhecidos = [e.get("lab_id") for e in envios if e.get("lab_id") not in LABS]
    if desconhecidos:
        return {"status": "Erro", "msg": f"lab_id desconhecido(s): {desconhecidos}", "itens": []}
    if not envios:
        return {"status": "Erro", "msg": "Nenhum envio informado no job.", "itens": []}

    pasta = os.path.join(PASTA_BASE, datetime.now().strftime("exec_%Y%m%d_%H%M%S"))
    os.makedirs(pasta, exist_ok=True)
    print(f"> 🚀 Iniciando robô de relatórios — {len(envios)} envio(s). Pasta: {pasta}")

    driver = iniciar_navegador(modo_fantasma=modo_fantasma)
    # Direciona os downloads do Chrome para a pasta da execução (headless inclusive).
    try:
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": pasta})
    except Exception as e:  # noqa: BLE001
        avisos.append(f"Não foi possível fixar a pasta de download via CDP: {e}")

    try:
        if not fazer_login(driver):
            return {"status": "Erro", "msg": "Falha no login do NL.", "itens": [], "pasta": pasta}

        # ---- 1) ANÁLISE DE ESTOQUE (gera cada setor 1x) ----
        setores = []
        for e in envios:
            for s in LABS[e["lab_id"]]["estoque"]:
                if s not in setores:
                    setores.append(s)
        estoque_paths = {}
        if setores:
            _abrir_favorito(driver, ESTOQUE["favorito_invoker"])
            for setor in setores:
                estoque_paths[setor] = gerar_analise_estoque(driver, setor, pasta)

        # ---- 2) DEMANDA FORNECEDOR (gera cada combo único 1x) ----
        combos = {}  # (modelo_id, operacao, ini, fim) -> caminho
        _abrir_favorito(driver, DEMANDA["favorito_invoker"])
        for e in envios:
            lab = LABS[e["lab_id"]]
            modelo_id = lab["modelo_venda"] or lab.get("modelo_label")
            for operacao in lab["operacoes"]:
                chave = (modelo_id, operacao, e["periodo_ini"], e["periodo_fim"])
                if chave not in combos:
                    combos[chave] = gerar_demanda(
                        driver, lab["modelo_venda"], lab.get("modelo_label"), operacao,
                        e["periodo_ini"], e["periodo_fim"], pasta,
                    )

        # ---- 3) MANIFESTO (lab -> arquivos), com pós-processamento ----
        itens = []
        for e in envios:
            lab = LABS[e["lab_id"]]
            modelo_id = lab["modelo_venda"] or lab.get("modelo_label")
            arquivos = [os.path.basename(estoque_paths[s]) for s in lab["estoque"]]
            for operacao in lab["operacoes"]:
                chave = (modelo_id, operacao, e["periodo_ini"], e["periodo_fim"])
                caminho_venda = combos[chave]
                if lab.get("pos"):
                    caminho_venda = aplicar_pos_processamento(caminho_venda, lab, pasta)
                arquivos.append(os.path.basename(caminho_venda))
            itens.append({
                "id": e.get("id"),
                "lab_id": e["lab_id"],
                "nome": lab["nome"],
                "arquivos": arquivos,
            })

        status = "Sucesso com avisos" if avisos else "Sucesso"
        print("> ✅ Concluído.")
        return {"status": status, "msg": "Relatórios gerados.", "pasta": pasta,
                "itens": itens, "avisos": avisos}

    except Exception as e:  # noqa: BLE001
        print(f"> ❌ Erro durante a geração: {e}")
        return {"status": "Erro", "msg": str(e), "pasta": pasta, "itens": [], "avisos": avisos}
    finally:
        time.sleep(2)
        driver.quit()


def main():
    """Execução standalone p/ teste.

    Aceita o job de 3 formas (a 1ª que existir):
      • caminho de um arquivo .json:  python -m ...gerar_relatorios job.json
      • JSON inline:                  python -m ...gerar_relatorios '{"envios":[...]}'
      • via stdin:                    Get-Content job.json | python -m ...gerar_relatorios

    Dica PowerShell: prefira o ARQUIVO. O PowerShell remove as aspas duplas
    de JSON inline, o que quebra o parse ("Expecting property name ...").
    """
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if os.path.isfile(arg):                       # caminho de arquivo .json
                with open(arg, "r", encoding="utf-8") as f:
                    job = json.load(f)
            else:                                          # JSON inline
                job = json.loads(arg)
        elif not sys.stdin.isatty():                       # JSON via stdin (pipe)
            job = json.load(sys.stdin)
        else:
            job = {}
    except Exception as e:  # noqa: BLE001
        print(f"> ❌ Job inválido: {e}")
        print("   Dica (PowerShell): use um arquivo .json em vez de JSON inline.")
        print("[FIM_DO_PROCESSO]")
        return
    resultado = executar(job)
    print("[RESULTADO_JSON] " + json.dumps(resultado, ensure_ascii=False))
    print("[FIM_DO_PROCESSO]")


if __name__ == "__main__":
    main()
