import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def iniciar_navegador(modo_fantasma= False):
    """Configura e abre o navegador Chrome."""
    print(f"🔌 Inicializando o navegador (Fantasma: {modo_fantasma})...")
    
    options = Options()
    
    # Se NÃO for modo fantasma, mantém a janela aberta no final (bom para testes)
    if not modo_fantasma:
        options.add_experimental_option("detach", True)
    
    # --- CONFIGURAÇÃO DO MODO FANTASMA ---
    if modo_fantasma:
        options.add_argument("--headless=new")
        # Força o navegador a carregar o CSS/Layout de um monitor Full HD.
        # Isso evita que o ERP da NLWeb "esconda" botões por achar que está num celular.
        options.add_argument("--window-size=1920,1080")
        
        # Evita detecção e melhora a performance em background
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Opcional: Define um "User-Agent" falso para o sistema achar que é um PC normal
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Inicia o serviço
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=options)
    
    # Só maximiza se não estiver no modo fantasma (no fantasma o window-size já resolve)
    if not modo_fantasma:
        driver.maximize_window()
        
    return driver

def fazer_login(driver):
    """Realiza o login automático e trata as sessões abertas."""
    url = "http://192.168.200.252:8585/NLWeb/site/9000/emp/1"
    usuario = "LEONARDO DIA"
    senha = "123"
    wait = WebDriverWait(driver, 20)

    try:
        print("🌐 Acessando sistema...")
        driver.get(url)

        # 1. Login Inicial
        wait.until(EC.element_to_be_clickable((By.ID, "txtUsername"))).send_keys(usuario)
        driver.find_element(By.ID, "txtPassword").send_keys(senha)
        driver.find_element(By.ID, "cmdLogin").click()
        
        # --- TRATAMENTO DE SESSÕES ATIVAS ---
        try:
            # Tenta clicar no 'SIM' do Iframe
            wait_iframe = WebDriverWait(driver, 5)
            wait_iframe.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "_blank")))
            wait_iframe.until(EC.element_to_be_clickable((By.ID, "btn1"))).click()
            driver.switch_to.default_content()
            print("✅ Confirmação de sessão (SIM) realizada.")
        except:
            driver.switch_to.default_content()

        # Loop para finalizar sessões (Estratégia Robusta)
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
            
            # Clicar em Continuar
            xpath_continuar = "//button[contains(., 'Continuar')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_continuar))).click()
        except:
            pass

        # Verificação do Menu Principal
        wait.until(EC.presence_of_element_located((By.ID, "main-menu")))
        print("🎊 Login realizado com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro no login automático: {e}")
        return False

def navegar_ate_destino(driver):
    """Navega pelo menu até a tela de Itens."""
    wait = WebDriverWait(driver, 20)
    print("📂 Iniciando Navegação pelo Menu...")
    
    caminho_menu = [
        '//*[@id="main-menu"]/li[1]/a',
        '//*[@id="main-menu"]/li[1]/ul/li[3]/a',
        '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[2]/a',
        '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[2]/ul/li[1]/a'
    ]

    for i, xpath in enumerate(caminho_menu):
        item_menu = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        item_menu.click()
        time.sleep(1.5)

    # Verificação final
    xpath_btn_avancada = "/html/body/form[1]/div[3]/div[3]/div/div[3]/div[1]/button[2]"
    wait.until(EC.presence_of_element_located((By.XPATH, xpath_btn_avancada)))
    print("📍 Chegamos na tela de destino!")