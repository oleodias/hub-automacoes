# automacoes/clientes/cadastro_cep.py
import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from automacoes.clientes.navegacao_erp import fazer_login

sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────
# HELPERS
# Espelhados de propósito dos outros robôs de cliente (cadastro_novo /
# cadastro_reativacao) para esse robô ficar autocontido. Se um dia
# centralizarmos, é só mover para automacoes/clientes/helpers.py.
# ─────────────────────────────────────────────────────────────

def limpar_e_preencher(driver, campo, valor):
    """
    Limpeza ROBUSTA + envio do valor. Combina 3 estratégias para vencer
    a teimosia do Oracle ADF: zerar via JS, Ctrl+A e Backspace.
    Use SEMPRE no lugar de send_keys direto.
    """
    try:
        campo.click()
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].value = '';", campo)
    except Exception:
        pass
    campo.send_keys(Keys.CONTROL + "a")
    campo.send_keys(Keys.BACKSPACE)
    time.sleep(0.2)
    if valor not in (None, ""):
        campo.send_keys(str(valor))


# ─────────────────────────────────────────────────────────────
# NAVEGAÇÃO ATÉ A TELA "CIDADES" (via Favoritos)
# Diferente do navegar_via_favoritos do navegacao_erp.py, que leva
# para "Pessoas geral". Aqui o atalho é o "Cidades".
# ─────────────────────────────────────────────────────────────

def navegar_para_cidades(driver):
    """Acessa a tela de Cidades diretamente pelos favoritos."""
    print("⭐ NAVEGAÇÃO: Acessando 'Cidades' via Favoritos...")
    try:
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()

        # ── ESPERA ATIVA PELO BOTÃO DE FAVORITOS ──
        # Logo após o login o ERP ainda termina de renderizar o cabeçalho.
        # Em vez de um sleep fixo, ficamos "vigiando" o botão da estrela:
        # assim que ele estiver presente E clicável, o robô segue na hora.
        xpath_estrela = "//a[contains(@onclick, 'tab-header-menu-favoritos')]"
        print("   ⏳ Aguardando o botão de Favoritos ficar disponível...")
        wait_estrela = WebDriverWait(driver, 30)
        btn_estrela = wait_estrela.until(
            EC.element_to_be_clickable((By.XPATH, xpath_estrela))
        )
        print("   ✅ Botão de Favoritos disponível. Clicando...")

        # Clica na estrela de favoritos
        driver.execute_script("arguments[0].click();", btn_estrela)
        time.sleep(1.5)

        # Clica no atalho "Cidades" dentro do dropdown.
        # O <a> tem um <button> de lixeira aninhado, por isso usamos
        # contains(normalize-space(.), 'Cidades') em vez de text() exato.
        xpath_link = (
            "//a[contains(@class, 'OraLink') and "
            "contains(normalize-space(.), 'Cidades')]"
        )
        link_cidades = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link)))
        driver.execute_script("arguments[0].click();", link_cidades)
        time.sleep(1.5)

        print("📍 Chegamos na tela de Cidades!")
        return True

    except Exception as e:
        print(f"❌ Erro na navegação por favoritos (Cidades): {e}")
        return False


# ─────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────

def executar(dados):
    """
    Robô de Cadastro de CEP — Fase 1.

    A partir de uma cidade + UF (que futuramente virão de uma API de CEP),
    pesquisa a cidade na tela "Cidades" do ERP, seleciona a linha da UF
    correta e captura o código local interno do ERP (txtCodLocal).

    Entrada esperada (dict):
        cidade : str  — nome da cidade (obrigatório)
        uf     : str  — sigla do estado (obrigatório)
        cep    : str  — opcional, apenas para log/uso futuro

    Saída (dict):
        status        : "Sucesso" | "Sucesso com avisos" | "Erro"
        msg           : mensagem amigável
        avisos        : lista de pontos a revisar
        codigo_local  : código local interno do ERP (str) ou None
        codigo_cidade : código exibido na grid (str) ou None
    """
    cidade = str(dados.get('cidade', '')).strip()
    uf = str(dados.get('uf', '')).strip().upper()
    cep = str(dados.get('cep', '')).strip()

    print(f"> 🏙️ Iniciando Robô: CADASTRO DE CEP (cidade={cidade!r} uf={uf!r} cep={cep!r})...")

    # ── VALIDAÇÃO CRÍTICA: sem cidade/UF, nem abre o Chrome ──
    if not cidade or not uf:
        return {
            "status": "Erro",
            "msg": "Cidade e UF são obrigatórios. Execução abortada antes de abrir o ERP.",
            "avisos": [],
            "codigo_local": None,
            "codigo_cidade": None,
        }

    # ── LISTA DE AVISOS (mesma filosofia dos outros robôs) ──
    avisos = []

    def registrar_aviso(msg):
        avisos.append(msg)
        print(f"   🟡 AVISO ACUMULADO: {msg}")

    codigo_local_capturado = None
    codigo_cidade_capturado = None

    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # ── LOGIN ──────────────────────────────────────────
        if not fazer_login(driver):
            raise Exception("Falha no Login do ERP.")

        # ── NAVEGAÇÃO ATÉ "CIDADES" ────────────────────────
        if not navegar_para_cidades(driver):
            raise Exception("Falha na navegação até a tela de Cidades.")

        print(f"> ✅ Login + navegação OK. Pronto para buscar a cidade {cidade!r}/{uf}.")

        # ════════════════════════════════════════════════════
        # ETAPA 1 — PESQUISA DA CIDADE
        # ════════════════════════════════════════════════════
        print("> 🔎 ETAPA 1: Pesquisando a cidade...")

        # ── Passo 1.1: Abrir o painel de filtros ──
        try:
            btn_filtros = wait.until(
                EC.presence_of_element_located((By.ID, "btn_nlPanelOcultarMostrar_"))
            )
            driver.execute_script("arguments[0].click();", btn_filtros)
            time.sleep(1)
            print("   ✅ Painel de filtros aberto.")
        except Exception as e:
            raise Exception(f"Falha ao abrir o painel de filtros: {e}")

        # ── Passo 1.2: Digitar o nome da cidade + TAB ──
        try:
            campo_cidade = wait.until(
                EC.element_to_be_clickable((By.ID, "txtDesCidade"))
            )
            limpar_e_preencher(driver, campo_cidade, cidade)
            campo_cidade.send_keys(Keys.TAB)
            time.sleep(0.8)
            print(f"   ✅ Cidade {cidade!r} digitada no filtro.")
        except Exception as e:
            raise Exception(f"Falha ao preencher o campo de cidade: {e}")

        # ── Passo 1.3: Clicar na lupa (JS click obrigatório no ADF) ──
        try:
            btn_lupa = wait.until(
                EC.presence_of_element_located((By.ID, "search_cmdSearch"))
            )
            driver.execute_script("arguments[0].click();", btn_lupa)
            print("   ✅ Lupa clicada via JS. Aguardando o ERP buscar...")
            time.sleep(2.5)  # Respiro para o grid de resultado carregar
        except Exception as e:
            raise Exception(f"Falha ao clicar na lupa de busca: {e}")

        # ════════════════════════════════════════════════════
        # ETAPA 2 — MATCHING POR UF E ABERTURA DO CADASTRO
        # Nomes de cidade se repetem entre estados (ex: "Bom Jesus"),
        # então NÃO basta clicar no primeiro resultado: temos que achar
        # a linha cuja coluna de UF bate com a UF esperada.
        # ════════════════════════════════════════════════════
        print(f"> 🎯 ETAPA 2: Procurando a linha com UF = {uf}...")

        try:
            # Aguarda ao menos uma célula de UF aparecer (grid carregou)
            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//td[@headers='tabG1Cidades:colCodUf']")
            ))
        except TimeoutException:
            registrar_aviso("REVISAR — grid de resultado não carregou após a pesquisa")
            return {
                "status": "Erro",
                "msg": (
                    f"Nenhum resultado carregou para a cidade {cidade!r}. "
                    "Verifique o nome da cidade."
                ),
                "avisos": avisos,
                "codigo_local": None,
                "codigo_cidade": None,
            }

        # Coleta todas as células de UF do resultado
        celulas_uf = driver.find_elements(
            By.XPATH, "//td[@headers='tabG1Cidades:colCodUf']"
        )
        print(f"   🔍 {len(celulas_uf)} linha(s) de resultado encontradas.")

        celula_codigo_alvo = None
        for celula_uf in celulas_uf:
            uf_linha = (celula_uf.text or "").strip().upper()
            if uf_linha == uf:
                # Achou a UF certa. Sobe para o <tr> e pega a célula de código.
                try:
                    celula_codigo_alvo = driver.execute_script("""
                        var tdUf = arguments[0];
                        var tr = tdUf.closest('tr');
                        if (!tr) return null;
                        return tr.querySelector("td[headers='tabG1Cidades:colCodCidade']");
                    """, celula_uf)
                except Exception as e:
                    print(f"   ⚠️ Falha ao subir para a linha da UF {uf}: {e}")
                if celula_codigo_alvo is not None:
                    print(f"   ✅ Linha com UF {uf} encontrada.")
                    break

        if celula_codigo_alvo is None:
            registrar_aviso(f"REVISAR — nenhuma linha com UF {uf} para a cidade {cidade!r}")
            return {
                "status": "Erro",
                "msg": (
                    f"A cidade {cidade!r} foi pesquisada, mas nenhuma linha "
                    f"corresponde à UF {uf}. Verifique cidade/UF."
                ),
                "avisos": avisos,
                "codigo_local": None,
                "codigo_cidade": None,
            }

        # Guarda o código exibido na grid (apenas dígitos) antes de clicar
        codigo_cidade_capturado = re.sub(r'\D', '', celula_codigo_alvo.text or '') or None
        print(f"   🧾 Código da cidade na grid: {codigo_cidade_capturado}")

        # ── Clica na célula de código para abrir o cadastro (JS click) ──
        try:
            driver.execute_script("arguments[0].click();", celula_codigo_alvo)
            print("   ✅ Cadastro da cidade aberto. Aguardando carregar...")
            time.sleep(2)
        except Exception as e:
            raise Exception(f"Falha ao clicar no código da cidade: {e}")

        # ════════════════════════════════════════════════════
        # ETAPA 3 — CAPTURA DO CÓDIGO LOCAL (txtCodLocal)
        # ════════════════════════════════════════════════════
        print("> 🏆 ETAPA 3: Capturando o código local (txtCodLocal)...")

        try:
            campo_cod_local = wait.until(
                EC.presence_of_element_located((By.ID, "txtCodLocal"))
            )
            valor_bruto = campo_cod_local.get_attribute("value") or ""
            # Remove separadores de milhar (ex: "7.667" -> "7667")
            codigo_local_capturado = re.sub(r'\D', '', valor_bruto) or None

            if codigo_local_capturado:
                print(f"   🏆 CÓDIGO LOCAL CAPTURADO: {codigo_local_capturado} (bruto: {valor_bruto!r})")
            else:
                print(f"   ⚠️ Campo txtCodLocal vazio/sem número: {valor_bruto!r}")
                registrar_aviso("REVISAR — txtCodLocal vazio ou não numérico")
        except Exception as e:
            print(f"   ❌ Falha ao capturar o código local: {e}")
            registrar_aviso("REVISAR — não foi possível capturar o txtCodLocal")

        # ── Resultado final ──
        if codigo_local_capturado and not avisos:
            status_final = "Sucesso"
            msg_final = (
                f"Código local da cidade {cidade!r}/{uf} capturado: {codigo_local_capturado}."
            )
        elif codigo_local_capturado:
            status_final = "Sucesso com avisos"
            msg_final = (
                f"Código local {codigo_local_capturado} capturado, "
                f"mas com {len(avisos)} ponto(s) para revisar."
            )
        else:
            status_final = "Erro"
            msg_final = f"Não foi possível capturar o código local da cidade {cidade!r}/{uf}."

        return {
            "status": status_final,
            "msg": msg_final,
            "avisos": avisos,
            "codigo_local": codigo_local_capturado,
            "codigo_cidade": codigo_cidade_capturado,
        }

    except Exception as e:
        print(f"> ❌ Erro Crítico: {e}")
        return {
            "status": "Erro",
            "msg": str(e),
            "avisos": avisos,
            "codigo_local": codigo_local_capturado,
            "codigo_cidade": codigo_cidade_capturado,
        }

    finally:
        # Mantém o navegador aberto durante os primeiros testes pra conferência.
        # Quando o robô estiver estável, descomenta a linha abaixo.
        driver.quit()
        print("> 🏁 Fim da execução do robô de cadastro de CEP.")


# ─────────────────────────────────────────────────────────────
# TESTE DE BANCADA
# Roda direto no terminal:
#   python -m automacoes.clientes.cadastro_cep
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧪 Iniciando Teste de Bancada — CADASTRO DE CEP (Fase 1)...")
    print("=" * 60)

    dados_teste = {
        "cidade": "Caxias do Sul",  # ← TROCAR pela cidade que vai testar
        "uf": "RS",                 # ← sigla do estado correspondente
        "cep": "95010000",          # opcional (uso futuro / log)
    }

    print(f"📋 Cidade: {dados_teste['cidade']}")
    print(f"📋 UF: {dados_teste['uf']}")
    print(f"📋 CEP: {dados_teste.get('cep', '(vazio)')}")
    print("=" * 60)

    resultado = executar(dados_teste)

    print("\n" + "=" * 60)
    print("🏁 RESULTADO FINAL DO ROBÔ")
    print("=" * 60)
    print(f"Status: {resultado.get('status')}")
    print(f"Mensagem: {resultado.get('msg')}")
    print(f"Código local: {resultado.get('codigo_local') or '(não capturado)'}")
    print(f"Código cidade (grid): {resultado.get('codigo_cidade') or '(não capturado)'}")

    avisos_finais = resultado.get('avisos', [])
    if avisos_finais:
        print(f"\n⚠️ {len(avisos_finais)} AVISO(S) ACUMULADO(S):")
        for i, aviso in enumerate(avisos_finais, start=1):
            print(f"   {i}. {aviso}")
    else:
        print("\n✅ Nenhum aviso!")
    print("=" * 60)
