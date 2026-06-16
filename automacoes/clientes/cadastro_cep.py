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
# para "Pessoas geral". Aqui usamos os atalhos "Cidades" e "Bairros".
# ─────────────────────────────────────────────────────────────

def navegar_via_favorito(driver, nome_opcao):
    """
    Abre o menu de Favoritos e clica na opção `nome_opcao` (ex: "Cidades",
    "Bairros"). Serve para a navegação inicial E para trocar de tela no
    meio do fluxo (depois de gravar a cidade, voltar e ir para Bairros).
    """
    print(f"⭐ NAVEGAÇÃO: Acessando '{nome_opcao}' via Favoritos...")
    try:
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()

        # ── ESPERA ATIVA PELO BOTÃO DE FAVORITOS ──
        # Logo após o login (ou após voltar de um cadastro) o ERP ainda
        # termina de renderizar o cabeçalho. Em vez de um sleep fixo,
        # ficamos "vigiando" o botão da estrela: assim que ele estiver
        # presente E clicável, o robô segue na hora.
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

        # Clica no atalho dentro do dropdown.
        # O <a> tem um <button> de lixeira aninhado, por isso usamos
        # contains(normalize-space(.), nome) em vez de text() exato.
        xpath_link = (
            f"//a[contains(@class, 'OraLink') and "
            f"contains(normalize-space(.), '{nome_opcao}')]"
        )
        link = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link)))
        driver.execute_script("arguments[0].click();", link)
        time.sleep(1.5)

        print(f"📍 Chegamos na tela de {nome_opcao}!")
        return True

    except Exception as e:
        print(f"❌ Erro na navegação por favoritos ({nome_opcao}): {e}")
        return False


# ─────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────

def executar(dados):
    """
    Robô de Cadastro de CEP.

    A partir de uma cidade + UF + bairro (que futuramente virão de uma API
    de CEP), o robô:
      1) pesquisa a cidade na tela "Cidades" e captura o código local (ERP);
      2) vai para a tela "Bairros" e procura o bairro daquele local;
      3) se o bairro já existe, captura o código do bairro;
         se não existe, cadastra um novo bairro e usa o código informado.

    Entrada esperada (dict):
        cidade             : str — nome da cidade (obrigatório)
        uf                 : str — sigla do estado (obrigatório)
        bairro             : str — nome do bairro (obrigatório p/ etapa Bairros)
        codigo_novo_bairro : str — número a usar SE precisar criar o bairro
        cep                : str — opcional, apenas para log/uso futuro

    Saída (dict):
        status        : "Sucesso" | "Sucesso com avisos" | "Erro"
        msg           : mensagem amigável
        avisos        : lista de pontos a revisar
        codigo_local  : código local interno do ERP (str) ou None
        codigo_cidade : código da cidade exibido na grid (str) ou None
        codigo_bairro : código do bairro (existente ou recém-criado) ou None
        bairro_criado : bool — True se o robô teve que criar o bairro
    """
    cidade = str(dados.get('cidade', '')).strip()
    uf = str(dados.get('uf', '')).strip().upper()
    bairro = str(dados.get('bairro', '')).strip()
    codigo_novo_bairro = re.sub(r'\D', '', str(dados.get('codigo_novo_bairro', '')))
    cep = str(dados.get('cep', '')).strip()

    # Nome do bairro como o ERP armazena: cortado em 20 caracteres (maxlength).
    # Usamos essa versão tanto na pesquisa quanto no matching da grade.
    LIMITE_BAIRRO = 20
    bairro_erp = bairro[:LIMITE_BAIRRO].strip()

    print(f"> 🏙️ Iniciando Robô: CADASTRO DE CEP (cidade={cidade!r} uf={uf!r} bairro={bairro!r} cep={cep!r})...")

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
    codigo_bairro_capturado = None
    bairro_criado = False

    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # ── LOGIN ──────────────────────────────────────────
        if not fazer_login(driver):
            raise Exception("Falha no Login do ERP.")

        # ── NAVEGAÇÃO ATÉ "CIDADES" ────────────────────────
        if not navegar_via_favorito(driver, "Cidades"):
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

        # Sem código local não dá pra seguir para Bairros (ele é a chave da busca).
        if not codigo_local_capturado:
            return {
                "status": "Erro",
                "msg": f"Não foi possível capturar o código local da cidade {cidade!r}/{uf}.",
                "avisos": avisos,
                "codigo_local": None,
                "codigo_cidade": codigo_cidade_capturado,
                "codigo_bairro": None,
                "bairro_criado": False,
            }

        print(f"> ✅ ETAPA 3 CONCLUÍDA! Código local: {codigo_local_capturado}")

        # ════════════════════════════════════════════════════
        # ETAPA 4 — SAIR DO CADASTRO DA CIDADE (botão Voltar)
        # ════════════════════════════════════════════════════
        print("> ↩️ ETAPA 4: Saindo do cadastro da cidade...")
        try:
            btn_voltar = wait.until(
                EC.element_to_be_clickable((By.ID, "btnCrudVoltar"))
            )
            driver.execute_script("arguments[0].click();", btn_voltar)
            time.sleep(1.5)

            # O onclick chama confirmarSaida(); como só LEMOS o campo (sem
            # alterar nada), normalmente não há popup. Mesmo assim, tratamos
            # defensivamente um possível confirm() nativo do browser.
            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                print("   ℹ️ Popup de confirmação de saída aceito.")
            except TimeoutException:
                pass

            print("   ✅ Saímos do cadastro da cidade.")
        except Exception as e:
            print(f"   ⚠️ Falha ao clicar em Voltar: {e}")
            registrar_aviso("REVISAR — não foi possível clicar no botão Voltar da cidade")

        # ════════════════════════════════════════════════════
        # ETAPA 5 — NAVEGAR ATÉ "BAIRROS"
        # ════════════════════════════════════════════════════
        if not navegar_via_favorito(driver, "Bairros"):
            raise Exception("Falha na navegação até a tela de Bairros.")

        # Sem nome de bairro não há o que pesquisar/cadastrar.
        if not bairro_erp:
            registrar_aviso("REVISAR — nenhum bairro informado no payload")
            return {
                "status": "Erro",
                "msg": "Cidade resolvida, mas nenhum bairro foi informado para a etapa de Bairros.",
                "avisos": avisos,
                "codigo_local": codigo_local_capturado,
                "codigo_cidade": codigo_cidade_capturado,
                "codigo_bairro": None,
                "bairro_criado": False,
            }

        # ════════════════════════════════════════════════════
        # ETAPA 6 — PESQUISA DO BAIRRO (por Local + Descrição)
        # ════════════════════════════════════════════════════
        print(f"> 🔎 ETAPA 6: Pesquisando o bairro {bairro_erp!r} no local {codigo_local_capturado}...")

        # ── Passo 6.1: Abrir o painel de filtros ──
        try:
            btn_filtros = wait.until(
                EC.presence_of_element_located((By.ID, "btn_nlPanelOcultarMostrar_"))
            )
            driver.execute_script("arguments[0].click();", btn_filtros)
            time.sleep(1)
            print("   ✅ Painel de filtros aberto.")
        except Exception as e:
            raise Exception(f"Falha ao abrir o painel de filtros (Bairros): {e}")

        # ── Passo 6.2: Preencher o campo "Local" (número bruto) + TAB ──
        # ⚠️ ID GERADO/PROVISÓRIO: "j_idt223" é um ID dinâmico do JSF/ADF e
        # pode mudar entre versões da tela. Se quebrar, me manda o HTML que
        # eu troco por um seletor estável.
        try:
            campo_local = wait.until(
                EC.element_to_be_clickable((By.ID, "j_idt223"))
            )
            limpar_e_preencher(driver, campo_local, codigo_local_capturado)
            campo_local.send_keys(Keys.TAB)
            time.sleep(0.8)
            print(f"   ✅ Local {codigo_local_capturado} preenchido no filtro.")
        except Exception as e:
            print(f"   ⚠️ Falha ao preencher o campo Local (id provisório j_idt223): {e}")
            registrar_aviso("REVISAR — campo Local do filtro de Bairros (id provisório)")

        # ── Passo 6.3: Preencher a Descrição (nome do bairro cortado em 20) + TAB ──
        # Buscamos pela versão cortada porque é assim que o ERP guarda o nome.
        try:
            campo_desc = wait.until(
                EC.element_to_be_clickable((By.ID, "txtDesBairro"))
            )
            limpar_e_preencher(driver, campo_desc, bairro_erp)
            campo_desc.send_keys(Keys.TAB)
            time.sleep(0.8)
            print(f"   ✅ Descrição {bairro_erp!r} preenchida no filtro.")
        except Exception as e:
            raise Exception(f"Falha ao preencher a Descrição do bairro: {e}")

        # ── Passo 6.4: Clicar na lupa ──
        try:
            btn_lupa = wait.until(
                EC.presence_of_element_located((By.ID, "search_cmdSearch"))
            )
            driver.execute_script("arguments[0].click();", btn_lupa)
            print("   ✅ Lupa clicada via JS. Aguardando resultados...")
            time.sleep(2.5)
        except Exception as e:
            raise Exception(f"Falha ao clicar na lupa de busca (Bairros): {e}")

        # ════════════════════════════════════════════════════
        # ETAPA 7 — MATCHING (Local exato + nome cortado em 20)
        # ════════════════════════════════════════════════════
        print("> 🎯 ETAPA 7: Conferindo se o bairro já existe...")

        bairro_alvo_norm = bairro_erp.upper()
        encontrou_bairro = False

        # A grid pode não trazer nenhuma linha (bairro inexistente).
        # Esperamos um pouco pela coluna de Local; se não vier, é "sem resultado".
        try:
            WebDriverWait(driver, 6).until(EC.presence_of_element_located(
                (By.XPATH, "//td[@headers='tabGeCepBai:colCodLocal']")
            ))
            celulas_local = driver.find_elements(
                By.XPATH, "//td[@headers='tabGeCepBai:colCodLocal']"
            )
            print(f"   🔍 {len(celulas_local)} linha(s) de resultado encontradas.")
        except TimeoutException:
            celulas_local = []
            print("   ℹ️ Nenhum resultado na grade de bairros.")

        for celula_local in celulas_local:
            local_linha = re.sub(r'\D', '', celula_local.text or '')
            if local_linha != codigo_local_capturado:
                continue  # bairro de outro local — ignora

            # Mesmo local: confere o nome (já cortado em 20 dos dois lados).
            try:
                info = driver.execute_script("""
                    var tdLocal = arguments[0];
                    var tr = tdLocal.closest('tr');
                    if (!tr) return null;
                    var des = tr.querySelector("td[headers='tabGeCepBai:colDesBairro']");
                    var cod = tr.querySelector("td[headers='tabGeCepBai:colCodBairro']");
                    return {
                        des: des ? des.textContent.trim() : null,
                        cod: cod ? cod.textContent.trim() : null
                    };
                """, celula_local)
            except Exception as e:
                print(f"   ⚠️ Falha ao ler a linha do resultado: {e}")
                info = None

            if not info:
                continue

            nome_grid = (info.get('des') or '').strip().upper()
            print(f"      🔍 Linha local={local_linha} bairro={nome_grid!r}")

            if nome_grid == bairro_alvo_norm:
                codigo_bairro_capturado = re.sub(r'\D', '', info.get('cod') or '') or None
                encontrou_bairro = True
                print(f"   ✅ Bairro JÁ EXISTE. Código capturado: {codigo_bairro_capturado}")
                break

        # ════════════════════════════════════════════════════
        # ETAPA 8 — CRIAR BAIRRO NOVO (se não encontrou)
        # ════════════════════════════════════════════════════
        if not encontrou_bairro:
            print("> ➕ ETAPA 8: Bairro não encontrado. Criando novo registro...")

            if not codigo_novo_bairro:
                registrar_aviso("REVISAR — bairro inexistente e sem 'codigo_novo_bairro' no payload")
                return {
                    "status": "Erro",
                    "msg": (
                        f"O bairro {bairro_erp!r} não existe no local {codigo_local_capturado} "
                        "e nenhum 'codigo_novo_bairro' foi informado para criá-lo."
                    ),
                    "avisos": avisos,
                    "codigo_local": codigo_local_capturado,
                    "codigo_cidade": codigo_cidade_capturado,
                    "codigo_bairro": None,
                    "bairro_criado": False,
                }

            try:
                # ── 8.1: Clicar em "Novo" ──
                btn_novo = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn_novo_icon')]"))
                )
                driver.execute_script("arguments[0].click();", btn_novo)
                time.sleep(1.5)
                print("   ✅ Tela de novo bairro aberta.")

                # ── 8.2: Preencher o "Local" (número bruto) ──
                # ⚠️ ID PROVISÓRIO: o HTML deste campo veio duplicado no prompt.
                # Estou apostando em "txtCodLocal" (mesmo padrão da tela de Cidades).
                # Se quebrar, me manda o HTML real do campo Local desta tela.
                try:
                    campo_local_novo = wait.until(
                        EC.element_to_be_clickable((By.ID, "txtCodLocal"))
                    )
                    limpar_e_preencher(driver, campo_local_novo, codigo_local_capturado)
                    campo_local_novo.send_keys(Keys.TAB)
                    time.sleep(0.8)
                    print(f"   ✅ Local {codigo_local_capturado} preenchido no novo bairro.")
                except Exception as e:
                    print(f"   ⚠️ Falha ao preencher Local do novo bairro (id provisório): {e}")
                    registrar_aviso("REVISAR — campo Local da tela de novo bairro (id provisório)")

                # ── 8.3: Preencher o código do bairro (numérico, do payload) ──
                campo_cod_bairro = wait.until(
                    EC.element_to_be_clickable((By.ID, "txtCodBairro"))
                )
                limpar_e_preencher(driver, campo_cod_bairro, codigo_novo_bairro)
                campo_cod_bairro.send_keys(Keys.TAB)
                time.sleep(0.5)
                print(f"   ✅ Código do bairro {codigo_novo_bairro} preenchido.")

                # ── 8.4: Preencher o nome do bairro (cortado em 20) ──
                campo_desc_novo = wait.until(
                    EC.element_to_be_clickable((By.ID, "txtDesBairro"))
                )
                limpar_e_preencher(driver, campo_desc_novo, bairro_erp)
                time.sleep(0.5)
                print(f"   ✅ Nome do bairro {bairro_erp!r} preenchido.")

                # ── 8.5: Gravar ──
                btn_gravar = wait.until(
                    EC.element_to_be_clickable((By.ID, "btnCrudGravar"))
                )
                driver.execute_script("arguments[0].click();", btn_gravar)
                print("   💾 Gravando novo bairro...")
                time.sleep(2)

                # Trata um possível popup nativo pós-gravação.
                try:
                    WebDriverWait(driver, 3).until(EC.alert_is_present())
                    alert_text = driver.switch_to.alert.text
                    print(f"   ℹ️ Popup pós-gravação: {alert_text!r}")
                    driver.switch_to.alert.accept()
                except TimeoutException:
                    pass

                codigo_bairro_capturado = codigo_novo_bairro
                bairro_criado = True
                print(f"   🏆 Bairro criado com sucesso. Código: {codigo_bairro_capturado}")

            except Exception as e:
                print(f"   ❌ Erro ao criar o bairro: {e}")
                registrar_aviso("REVISAR — falha ao criar o novo bairro")

        # ── Resultado final ──
        if codigo_bairro_capturado and not avisos:
            status_final = "Sucesso"
        elif codigo_bairro_capturado:
            status_final = "Sucesso com avisos"
        else:
            status_final = "Erro"

        origem = "criado" if bairro_criado else "já existente"
        if codigo_bairro_capturado:
            msg_final = (
                f"Bairro {bairro_erp!r} resolvido ({origem}). "
                f"Local: {codigo_local_capturado} | Código do bairro: {codigo_bairro_capturado}."
            )
            if avisos:
                msg_final += f" {len(avisos)} ponto(s) para revisar."
        else:
            msg_final = f"Não foi possível resolver o bairro {bairro_erp!r} no local {codigo_local_capturado}."

        return {
            "status": status_final,
            "msg": msg_final,
            "avisos": avisos,
            "codigo_local": codigo_local_capturado,
            "codigo_cidade": codigo_cidade_capturado,
            "codigo_bairro": codigo_bairro_capturado,
            "bairro_criado": bairro_criado,
        }

    except Exception as e:
        print(f"> ❌ Erro Crítico: {e}")
        return {
            "status": "Erro",
            "msg": str(e),
            "avisos": avisos,
            "codigo_local": codigo_local_capturado,
            "codigo_cidade": codigo_cidade_capturado,
            "codigo_bairro": codigo_bairro_capturado,
            "bairro_criado": bairro_criado,
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
    print("🧪 Iniciando Teste de Bancada — CADASTRO DE CEP...")
    print("=" * 60)

    dados_teste = {
        "cidade": "Caxias do Sul",   # ← TROCAR pela cidade que vai testar
        "uf": "RS",                  # ← sigla do estado correspondente
        "bairro": "Centro",          # ← nome do bairro (será cortado em 20)
        "codigo_novo_bairro": "99999",  # ← usado SÓ se o bairro não existir
        "cep": "95010000",           # opcional (uso futuro / log)
    }

    print(f"📋 Cidade: {dados_teste['cidade']}")
    print(f"📋 UF: {dados_teste['uf']}")
    print(f"📋 Bairro: {dados_teste['bairro']}")
    print(f"📋 Código novo bairro (se precisar criar): {dados_teste['codigo_novo_bairro']}")
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
    print(f"Código bairro: {resultado.get('codigo_bairro') or '(não capturado)'}")
    print(f"Bairro criado? {'Sim' if resultado.get('bairro_criado') else 'Não (já existia)'}")

    avisos_finais = resultado.get('avisos', [])
    if avisos_finais:
        print(f"\n⚠️ {len(avisos_finais)} AVISO(S) ACUMULADO(S):")
        for i, aviso in enumerate(avisos_finais, start=1):
            print(f"   {i}. {aviso}")
    else:
        print("\n✅ Nenhum aviso!")
    print("=" * 60)
