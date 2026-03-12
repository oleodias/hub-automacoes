import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# --- NOVA NAVEGAÇÃO: VIA FAVORITOS ---
def navegar_para_ncm_via_favoritos(driver):
    """
    Acessa a tela de Códigos NCM diretamente pelo menu de Favoritos.
    Substitui a antiga navegação por hover.
    """
    print("⭐ NAVEGAÇÃO NCM: Acessando via Favoritos...")
    try:
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()

        # 1. Clica no Botão da Estrela (Favoritos)
        try:
            # O seletor busca o link que abre a tab dos favoritos
            btn_estrela = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'tab-header-menu-favoritos')]")))
            btn_estrela.click()
            time.sleep(1.5) # Aguarda o menu dropdown abrir
        except Exception as e:
            print(f"   ⚠️ Erro ao clicar na estrela: {e}")
            return False

        # 2. Clica na opção "Códigos NCM"
        try:
            # Busca o link exato dentro da lista de favoritos
            xpath_link = "//ul[@id='header-menu-favoritos']//a[contains(text(), 'Códigos NCM')]"
            link_ncm = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link)))
            link_ncm.click()
            print("   ✅ Clique em 'Códigos NCM' realizado.")
        except Exception as e:
            print(f"   ⚠️ Erro ao achar o link 'Códigos NCM': {e}")
            return False

        # 3. Aguarda carregamento da tela
        time.sleep(3)
        print("✅ Tela de NCM Carregada.")
        return True

    except Exception as e:
        print(f"❌ Erro crítico na navegação NCM: {e}")
        return False

# --- VERIFICAÇÃO (Mantendo seus IDs originais) ---
def verificar_existencia_ncm(driver, ncm_alvo):
    try:
        # Abre filtros se estiver fechado
        try:
            btn_filtro = driver.find_element(By.ID, "btn_nlPanelOcultarMostrar_")
            driver.execute_script("arguments[0].click();", btn_filtro)
            time.sleep(1)
        except: pass

        # Limpa filtros (Borracha) - Garante que o NCM anterior saia do campo
        try:
            driver.execute_script("document.getElementById('search_cmdReset').click();")
            time.sleep(1)
        except: pass
        
        # Preenche filtros com o NCM atual
        driver.find_element(By.ID, "txtCodNbm_inicial").send_keys(ncm_alvo)
        driver.find_element(By.ID, "txtCodNbm_final").send_keys(ncm_alvo)
        
        # Clica na Lupa para pesquisar
        driver.execute_script("document.getElementById('search_cmdSearch').click();")
        time.sleep(3)
        
        # Verifica resultado na tela
        fonte = driver.page_source
        if "Nenhum registro encontrado" in fonte or "Nenhum resultado encontrado" in fonte:
            return False # Não existe (precisa cadastrar)
        else:
            return True # Já existe
            
    except Exception as e:
        print(f"   ⚠️ Erro ao verificar NCM: {e}")
        return False

# --- BUSCA EXTERNA (Systax) ---
def buscar_descricao_systax(driver, ncm_alvo):
    """Abre nova aba, busca no Systax e retorna a descrição."""
    try:
        print(f"🌐 Buscando descrição no Systax para: {ncm_alvo}")
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1]) # Vai para a última aba
        
        driver.get(f"https://www.systax.com.br/classificacaofiscal/ncm/{ncm_alvo}")
        
        wait = WebDriverWait(driver, 10)
        # Tenta pegar o H1 ou title, ajustado para evitar erro se a página mudar
        try:
            h1 = wait.until(EC.visibility_of_element_located((By.TAG_NAME, 'h1')))
            texto = h1.text
            # Tratamento da string
            desc = texto.split(" - ")[1].strip().upper() if " - " in texto else texto.upper()
        except:
            desc = "DESCRIÇÃO GENÉRICA NCM"

        driver.close()
        driver.switch_to.window(driver.window_handles[0]) # Volta para o sistema NL
        return desc
    except:
        print(f"⚠️ Erro na busca Systax para {ncm_alvo}.")
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return "DESCRIÇÃO GENÉRICA NCM" 

# --- CADASTRO (Mantendo seus IDs originais) ---
def cadastrar_ncm(driver, ncm_alvo, descricao):
    try:
        wait = WebDriverWait(driver, 10)
        print(f"🚀 Cadastrando NCM: {ncm_alvo}")

        # Clica no botão Novo
        try:
            btn_novo = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="panelGroupFooterRight"]/button')))
            driver.execute_script("arguments[0].click();", btn_novo)
        except:
            # Tenta seletor alternativo se o xpath falhar
            btn_novo = driver.find_element(By.ID, "btnCrudNovo")
            driver.execute_script("arguments[0].click();", btn_novo)
            
        time.sleep(2)

        # Preenche campos
        preencher_campo(driver, "txtCodNbm", ncm_alvo)
        preencher_campo(driver, "txtCodNbmEditado", ncm_alvo)
        preencher_campo(driver, "txtCodNcmNfe", ncm_alvo)
        preencher_campo(driver, "txtDesNbm", descricao)

        # Aba Grupos Fiscais
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "tabGruposFiscais"))
        time.sleep(1.5)

        # Botão Adicionar Grupo
        btn_add = wait.until(EC.presence_of_element_located((By.ID, "btnAdicionar_mdGrupos")))
        driver.execute_script("arguments[0].click();", btn_add)
        time.sleep(1.5)

        # Preenche Grupo 05
        campo_grupo = wait.until(EC.presence_of_element_located((By.ID, "subFrm_mdGrupos:lovCodGrFiscal_txtCod")))
        campo_grupo.send_keys("05")
        time.sleep(0.5)
        campo_grupo.send_keys(Keys.TAB)
        time.sleep(1)

        # Botão Aplicar
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "subFrm_mdGrupos:btnAplicar_mdGrupos"))
        time.sleep(1.5)
        
        # Botão Salvar
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnCrudGravar"))
        time.sleep(3)
        
        print(f"✅ NCM {ncm_alvo} cadastrado com sucesso!")
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ Erro ao salvar NCM: {e}")
        driver.switch_to.default_content()

def preencher_campo(driver, id_el, valor):
    """Helper para preencher campos de texto"""
    try:
        el = driver.find_element(By.ID, id_el)
        el.clear()
        el.send_keys(str(valor))
    except: pass

# --- FLUXO PRINCIPAL ---
def processar_ncms(driver, lista_ncms_xml):
#Função principal chamada pelo main.py
    if not lista_ncms_xml:
        return

    print("\n" + "="*40)
    print("🛠️ INICIANDO VERIFICAÇÃO DE NCMS (Via Favoritos)")
    print("="*40)

    # 1. NAVEGA APENAS UMA VEZ PARA A TELA DE NCM
    if not navegar_para_ncm_via_favoritos(driver):
        print("❌ Falha ao acessar tela de NCM.")
        return

    # 2. LAÇO ÚNICO E LIMPO PARA VERIFICAR TODOS OS ITENS
    for i, ncm in enumerate(lista_ncms_xml, 1):
        if not ncm: continue 
        
        print(f"\n🔎 [{i}/{len(lista_ncms_xml)}] Verificando NCM: {ncm}")
        
        # Chama a sua função super robusta de pesquisa (ela limpa o anterior e digita o novo)
        if verificar_existencia_ncm(driver, ncm):
            print(f"   ✅ NCM já existe.")
        else:
            print(f"   ⚠️ NCM não cadastrado. Buscando dados...")
            descricao = buscar_descricao_systax(driver, ncm)
            cadastrar_ncm(driver, ncm, descricao)
            
    print("\n✅ Todos os NCMs foram processados. Partindo para os Itens...")