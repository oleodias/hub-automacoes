import os
import time
import xml.etree.ElementTree as ET
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÃO DE CAMINHOS ---
PATH_BASE = os.path.dirname(os.path.abspath(__file__))
PATH_XML = os.path.join(PATH_BASE, 'XML_Entrada')

def ler_ncms_do_xml():
    if not os.path.exists(PATH_XML): os.makedirs(PATH_XML)
    arquivos = [f for f in os.listdir(PATH_XML) if f.lower().endswith('.xml')]
    if not arquivos:
        print("❌ Nenhum XML encontrado na pasta XML_Entrada.")
        return []
    
    tree = ET.parse(os.path.join(PATH_XML, arquivos[0]))
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    ncms = []
    for det in tree.getroot().findall('.//nfe:det', ns):
        prod = det.find('nfe:prod', ns)
        ncm = prod.find('nfe:NCM', ns).text
        ncms.append(ncm)
    return list(set(ncms)) # Retorna NCMs sem duplicatas

# --- FUNÇÕES DO SISTEMA (BASEADAS NO SEU SCRIPT FUNCIONAL) ---
def iniciar_sistema(driver):
    driver.get("http://192.168.200.252:8585/NLWeb/site/9000/emp/1")
    print("\n" + "!"*50)
    print("PASSO 1: Faça login no sistema NL.")
    print("PASSO 2: Na Home, volte aqui e aperte ENTER.")
    print("!"*50)
    input()

def navegar_ate_ncm_preciso(driver):
    try:
        wait = WebDriverWait(driver, 10)
        print("🖱️ Navegando até a Tabela de NCM...")
        passos = [
            '//*[@id="main-menu"]/li[1]/a', 
            '//*[@id="main-menu"]/li[1]/ul/li[3]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[7]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[7]/ul/li[3]/a'
        ]
        for xpath in passos:
            elemento = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", elemento)
            time.sleep(0.8)
        print("✅ Tela de NCM atingida.")
    except Exception as e:
        print(f"❌ Erro na navegação: {e}")

def pesquisar_ncm_no_nl(driver, ncm_alvo):
    try:
        wait = WebDriverWait(driver, 10)
        print(f"🔍 Verificando NCM {ncm_alvo}...")
        
        # Abre filtros
        btn_filtro = wait.until(EC.presence_of_element_located((By.ID, "btn_nlPanelOcultarMostrar_")))
        driver.execute_script("arguments[0].click();", btn_filtro)
        time.sleep(1)
        
        # Limpa e preenche
        driver.find_element(By.ID, "txtCodNbm_inicial").clear()
        driver.find_element(By.ID, "txtCodNbm_inicial").send_keys(ncm_alvo)
        driver.find_element(By.ID, "txtCodNbm_final").clear()
        driver.find_element(By.ID, "txtCodNbm_final").send_keys(ncm_alvo)
        
        # Lupa
        btn_busca = driver.find_element(By.ID, "search_cmdSearch")
        driver.execute_script("arguments[0].click();", btn_busca)
        time.sleep(4)
        
        resultado_xpath = '//*[@id="tabIeCodigosNbm"]/table[2]/tbody/tr[2]/td'
        texto_resultado = driver.find_element(By.XPATH, resultado_xpath).text
        
        return "Nenhum resultado encontrado" in texto_resultado
    except:
        return False

def buscar_descricao_systax(driver, ncm_alvo):
    try:
        print(f"🌐 Buscando descrição para {ncm_alvo} no Systax...")
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[1])
        driver.get(f"https://www.systax.com.br/classificacaofiscal/ncm/{ncm_alvo}")
        
        wait = WebDriverWait(driver, 10)
        h1 = wait.until(EC.visibility_of_element_located((By.TAG_NAME, 'h1')))
        texto = h1.text
        desc = texto.split(" - ")[1].strip().upper() if " - " in texto else texto.upper()
        
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return desc
    except:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return None

def realizar_cadastro_completo(driver, ncm_alvo, descricao):
    try:
        wait = WebDriverWait(driver, 10)
        print(f"🚀 Cadastrando {ncm_alvo}...")

        btn_novo = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="panelGroupFooterRight"]/button')))
        driver.execute_script("arguments[0].click();", btn_novo)
        time.sleep(2)

        driver.find_element(By.ID, "txtCodNbm").send_keys(ncm_alvo)
        driver.find_element(By.ID, "txtCodNbmEditado").send_keys(ncm_alvo)
        driver.find_element(By.ID, "txtCodNcmNfe").send_keys(ncm_alvo)
        driver.find_element(By.ID, "txtDesNbm").send_keys(descricao)

        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "tabGruposFiscais"))
        time.sleep(1.5)

        btn_add = wait.until(EC.presence_of_element_located((By.ID, "btnAdicionar_mdGrupos")))
        driver.execute_script("arguments[0].click();", btn_add)
        time.sleep(1.5)

        campo_grupo = wait.until(EC.presence_of_element_located((By.ID, "subFrm_mdGrupos:lovCodGrFiscal_txtCod")))
        campo_grupo.send_keys("5" + Keys.TAB)
        time.sleep(1.5)

        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "subFrm_mdGrupos:btnAplicar_mdGrupos"))
        time.sleep(1)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "btnCrudGravar"))
        
        print(f"✨ NCM {ncm_alvo} GRAVADO!")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Erro no cadastro: {e}")

# --- EXECUÇÃO ---
ncms_para_processar = ler_ncms_do_xml()

if ncms_para_processar:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()

    iniciar_sistema(driver)
    navegar_ate_ncm_preciso(driver)

    for ncm in ncms_para_processar:
        if pesquisar_ncm_no_nl(driver, ncm):
            desc = buscar_descricao_systax(driver, ncm)
            if desc:
                realizar_cadastro_completo(driver, ncm, desc)
            else:
                print(f"🛑 Pulando {ncm}: Descrição não encontrada.")
        else:
            print(f"🌕 NCM {ncm} já existe. Pulando...")
    
    print("\n✅ Processamento de NCMs finalizado!")