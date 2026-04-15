import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
from dotenv import load_dotenv

load_dotenv()

def iniciar_navegador(modo_fantasma=False):
    """Configura e abre o navegador Chrome."""
    print(f"🔌 Inicializando o navegador (Fantasma: {modo_fantasma})...")
    
    options = Options()
    
    if not modo_fantasma:
        options.add_experimental_option("detach", True)
    
    if modo_fantasma:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=options)
    
    if not modo_fantasma:
        driver.maximize_window()
        
    return driver

def fazer_login(driver):
    """Realiza o login automático e trata as sessões abertas."""
    # Puxa os dados do .env
    url = os.getenv('NLWEB_URL')
    usuario = os.getenv('NLWEB_USER')
    senha = os.getenv('NLWEB_PASS')
    
    wait = WebDriverWait(driver, 20)

    try:
        print("🌐 Acessando sistema...")
        driver.get(url)

        # Login Inicial
        wait.until(EC.element_to_be_clickable((By.ID, "txtUsername"))).send_keys(usuario)
        driver.find_element(By.ID, "txtPassword").send_keys(senha)
        driver.find_element(By.ID, "cmdLogin").click()
        
        # Tratamento do Iframe de Sessão Ativa
        try:
            wait_iframe = WebDriverWait(driver, 5)
            wait_iframe.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "_blank")))
            wait_iframe.until(EC.element_to_be_clickable((By.ID, "btn1"))).click()
            driver.switch_to.default_content()
            print("✅ Confirmação de sessão (SIM) realizada.")
        except:
            driver.switch_to.default_content()

        # Derrubando sessões presas (Motivo 'd')
        xpath_janela_motivo = "//label[contains(text(), 'Motivo')]"
        try:
            wait_short = WebDriverWait(driver, 5)
            wait_short.until(EC.visibility_of_element_located((By.XPATH, xpath_janela_motivo)))
            
            while True:
                botoes_finalizar = driver.find_elements(By.XPATH, "//button[contains(text(), 'Finalizar')]")
                if not botoes_finalizar:
                    break
                
                print(f"⏳ Finalizando sessão ({len(botoes_finalizar)} restantes)...")
                campo_motivo = driver.find_element(By.XPATH, "//label[contains(text(), 'Motivo')]/../..//input")
                campo_motivo.clear()
                campo_motivo.send_keys("d")
                botoes_finalizar[0].click()
                time.sleep(2) 
            
            xpath_continuar = "//button[contains(., 'Continuar')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_continuar))).click()
        except:
            pass

        wait.until(EC.presence_of_element_located((By.ID, "main-menu")))
        print("🎊 Login realizado com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro no login automático: {e}")
        return False

# --- NAVEGAÇÃO VIA FAVORITOS (VIA EXPRESSA) ---
def navegar_via_favoritos(driver):
    """Acessa a tela de Pessoas Geral diretamente pelos favoritos."""
    print("⭐ NAVEGAÇÃO: Acessando via Favoritos...")
    try:
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()
        
        # Clica na estrela
        btn_estrela = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'tab-header-menu-favoritos')]")))
        btn_estrela.click()
        time.sleep(1.5)
        
        # Clica no atalho de Clientes
        xpath_link = "//ul[@id='header-menu-favoritos']//a[contains(text(), 'Pessoas geral')]"
        link_pessoasgeral = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link)))
        link_pessoasgeral.click()
        time.sleep(4) 
        
        print("📍 Chegamos na tela de Pessoas Geral!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na navegação por favoritos: {e}")
        return False