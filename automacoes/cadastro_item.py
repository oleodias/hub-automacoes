import os
import time
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURAÇÃO DE LOGS ---
PATH_BASE = os.path.dirname(os.path.abspath(__file__))
PATH_LOGS = os.path.join(PATH_BASE, 'Logs')
if not os.path.exists(PATH_LOGS): os.makedirs(PATH_LOGS)
ARQUIVO_LOG = os.path.join(PATH_LOGS, f"log_cadastro_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def registrar(mensagem):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    linha = f"[{timestamp}] {mensagem}"
    print(linha)
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

# --- FUNÇÕES DE APOIO (IDÊNTICAS AO SEU CÓDIGO ANTIGO) ---
def preencher_campo_seguro(driver, id_campo, valor):
    try:
        wait = WebDriverWait(driver, 10)
        campo = wait.until(EC.element_to_be_clickable((By.ID, id_campo)))
        driver.execute_script("arguments[0].value = '';", campo)
        campo.clear()
        campo.send_keys(str(valor) + Keys.TAB)
        time.sleep(0.4)
    except: pass

def limpar_popups_persistente(driver, botao_id="btn1"):
    for i in range(3):
        try:
            time.sleep(1.5)
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                driver.switch_to.frame(iframes[0])
                driver.find_element(By.ID, botao_id).click()
                driver.switch_to.default_content()
            else: break
        except:
            driver.switch_to.default_content()
            break

# --- NAVEGAÇÃO VIA FAVORITOS ---
def navegar_via_favoritos(driver):
    registrar("⭐ NAVEGAÇÃO: Acessando via Favoritos...")
    try:
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()
        btn_estrela = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'tab-header-menu-favoritos')]")))
        btn_estrela.click()
        time.sleep(1.5)
        xpath_link = "//ul[@id='header-menu-favoritos']//a[contains(text(), 'Cadastro')]"
        link_cadastro = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link)))
        link_cadastro.click()
        time.sleep(4) 
        return True
    except: return False

# --- PLANO B (IDÊNTICO AO SEU CÓDIGO ANTIGO) ---
def consolidar_cadastro_plano_b(driver, descricao_item):
    try:
        registrar(f"🛠️ PLANO B: {descricao_item}")
        driver.find_element(By.ID, "btnCrudVoltar").click()
        time.sleep(2)
        try: driver.switch_to.alert.accept()
        except: pass

        # Volta via Favoritos
        navegar_via_favoritos(driver)
        
        preencher_campo_seguro(driver, "txtDesItem", descricao_item)
        # No plano B o código antigo usava clique na lupa
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "search_cmdSearch")) 
        time.sleep(4) 

        xpath_grade = "/html/body/form[1]/div[3]/div[1]/section/div[2]/div[2]/table/tbody/tr[2]/td[2]/div/div/table[2]/tbody/tr[2]/td[1]"
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_grade))).click()
        time.sleep(1)
        driver.find_element(By.ID, "tabIeItens:0:lnkCadastro").click()
        time.sleep(2)
        driver.find_element(By.ID, "btnCrudGravar").click()
        limpar_popups_persistente(driver, "btn1")
        registrar(f"✅ Consolidado via Plano B.")
    except Exception as e:
        registrar(f"❌ Erro no Plano B: {e}")

# --- FLUXO PRINCIPAL (IDÊNTICO AO SEU EXECUTAR_CADASTRO ANTIGO) ---
def iniciar_cadastro(driver, itens_para_cadastrar):
    if not itens_para_cadastrar: return
    if not navegar_via_favoritos(driver): return

    for item in itens_para_cadastrar:
        try:
            registrar(f"🚀 Iniciando: {item['desc']}")
            driver.switch_to.default_content()

            # 1. Busca Modelo (Lógica exata do antigo: SEM clicar na lupa)
            preencher_campo_seguro(driver, "lovCodItem_txtCod", "13794")
            time.sleep(2.5) # Tempo exato do seu código
            
            xpath_linha = "/html/body/form[1]/div[3]/div[1]/section/div[2]/div[2]/table/tbody/tr[2]/td[2]/div/div/table[2]/tbody/tr[2]/td[1]"
            driver.find_element(By.XPATH, xpath_linha).click()
            time.sleep(1)
            driver.find_element(By.ID, "tabIeItens:0:lnkCadastro").click()
            time.sleep(2.5)
            
            # 2. Duplicar
            driver.find_element(By.XPATH, '//*[@id="panelGroupFooterRight"]/span/button').click()
            time.sleep(0.5)
            driver.find_element(By.ID, "btnCrudDuplicar").click()
            limpar_popups_persistente(driver, "btn1")
            limpar_popups_persistente(driver, "btn1")
            
            # 3. Preenchimento (Valor + TAB unificados)
            preencher_campo_seguro(driver, "txtDesItem", item['desc'])
            preencher_campo_seguro(driver, "txtCodEan", item['ean'])
            preencher_campo_seguro(driver, "lovCodUm_txtCod", item['unid'])
            preencher_campo_seguro(driver, "lovCodNbm_txtCod", item['ncm'])
            limpar_popups_persistente(driver, "btn2")
            preencher_campo_seguro(driver, "lovCodTipo_txtCod", "07")
            preencher_campo_seguro(driver, "lovCodGrFiscal_txtCod", "05")
            
            # 4. Gravar e Protocolo (Lógica exata do seu antigo)
            driver.find_element(By.ID, "btnCrudGravar").click()
            time.sleep(4)
            
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                driver.switch_to.frame(iframes[0])
                try:
                    cod_final = driver.find_element(By.XPATH, '//*[@id="divContent"]/table[1]/tbody/tr/td[2]/div').text
                    registrar(f"✨ CONFIRMADO: {cod_final}")
                    driver.find_element(By.ID, "btnProtocolo").click()
                    driver.switch_to.default_content()
                    time.sleep(2)
                    # Recarrega para o próximo item
                    navegar_via_favoritos(driver)
                except:
                    driver.switch_to.default_content()
                    consolidar_cadastro_plano_b(driver, item['desc'])
            else:
                consolidar_cadastro_plano_b(driver, item['desc'])

            registrar("-" * 50)

        except Exception as e:
            registrar(f"❌ Erro: {e}")
            navegar_via_favoritos(driver)

    registrar("🏁 PROCESSO CONCLUÍDO.")