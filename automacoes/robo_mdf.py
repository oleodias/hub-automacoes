import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- EMOJIS ---
import sys
sys.stdout.reconfigure(encoding='utf-8')

# --- CAPTURA DE DATAS EXTERNAS ---
import sys
# Se o servidor mandou as datas, usamos elas. Se não, usamos uma padrão.
data_inicio_global = sys.argv[1] if len(sys.argv) > 1 else "01/01/2026"
data_fim_global = sys.argv[2] if len(sys.argv) > 2 else "31/01/2026"

# --- 1. CONFIGURAÇÃO ---
chrome_options = Options()
chrome_options.add_experimental_option("detach", True)

# 👻 --- ADICIONE O MODO FANTASMA AQUI ---
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1920,1080")
# ----------------------------------------

dados_para_planilha = []
NOME_ARQUIVO = "Relatorio_MDFs_Março.xlsx"
URL_SISTEMA = "http://192.168.200.252:8585/NLWeb/site/9000/emp/1"

# Inicia o Navegador
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.maximize_window()

# --- FUNÇÕES DE APOIO E LOGIN ---

def salvar_dados():
    if dados_para_planilha:
        df = pd.DataFrame(dados_para_planilha)
        df.to_excel(NOME_ARQUIVO, index=False)
        print(f"   💾 Planilha atualizada: {NOME_ARQUIVO}")

def preencher_campo_seguro(id_campo, valor):
    try:
        campo = driver.find_element(By.ID, id_campo)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.5)
        campo.clear()
        campo.send_keys(valor + Keys.TAB)
        time.sleep(1.5)
    except: pass

def desmarcar_checkbox(xpath):
    try:
        elemento = driver.find_element(By.XPATH, xpath)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
        elemento.click()
    except: pass

def fazer_login(driver):
    """Realiza o login automático e trata as sessões abertas."""
    usuario = "LEONARDO DIA"
    senha = "123"
    wait = WebDriverWait(driver, 20)

    try:
        print("🌐 Acessando sistema...")
        driver.get(URL_SISTEMA)

        # 1. Login Inicial
        wait.until(EC.element_to_be_clickable((By.ID, "txtUsername"))).send_keys(usuario)
        driver.find_element(By.ID, "txtPassword").send_keys(senha)
        driver.find_element(By.ID, "cmdLogin").click()
        
        # --- TRATAMENTO DE SESSÕES ATIVAS ---
        try:
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
        print("🎊 Login automático realizado com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro no login automático: {e}")
        return False

# --- 2. NAVEGAÇÃO ---

def navegar_e_filtrar():
    try:
        print("\n🚀 Acessando o menu via Favoritos...")
        wait = WebDriverWait(driver, 15)
        
        # 1. Clicar no atalho de Favoritos (Ícone de Estrela)
        btn_favoritos = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'tab-header-menu-favoritos')]")))
        driver.execute_script("arguments[0].click();", btn_favoritos)
        time.sleep(1.5) 
        
        # 2. Clicar na opção "Gerencia NFe - Saída"
        btn_opcao_nfe = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Gerencia NFe - Saída') and contains(@class, 'OraLink')]")))
        driver.execute_script("arguments[0].click();", btn_opcao_nfe)
        time.sleep(1)
        
        print("🔍 Aplicando filtros iniciais...")
        time.sleep(4)
        
        preencher_campo_seguro("lovCodGrUnidades_txtCod", "0")
        # DENTRO DA FUNÇÃO navegar_e_filtrar()
        # Procure onde você preenche as datas e troque por:

        preencher_campo_seguro("dtaPeriodo_inicial", data_inicio_global)
        preencher_campo_seguro("dtaPeriodo_final", data_fim_global)

        checks = ['//*[@id="chkIndNFe__xc_c"]/span', '//*[@id="chkIndNFCe__xc_c"]/span',
                  '//*[@id="chkIndCTe__xc_c"]/span', '//*[@id="chkIndNFSe__xc_c"]/span',
                  '//*[@id="chkIndSAT__xc_c"]/span']
        for c in checks: desmarcar_checkbox(c)

        btn_pesq = driver.find_element(By.XPATH, '/html/body/form[1]/div[3]/div[3]/div/div[3]/div[3]/button')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_pesq)
        time.sleep(1)
        btn_pesq.click()
        time.sleep(8)
        return True
    except Exception as e:
        print(f"❌ Erro na navegação: {e}")
        return False

# --- 3. EXTRAÇÃO CORRIGIDA ---

def extrair_notas_da_linha(index):
    try:
        # 1. Abre a nota
        xpath_linha = f'//*[@id="tabNswNotasGerencia"]/table[2]/tbody/tr[{index}]/td[9]'
        botao_menu = driver.find_element(By.XPATH, xpath_linha)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao_menu)
        time.sleep(1)
        botao_menu.click()
        time.sleep(2)

        opcoes = driver.find_elements(By.XPATH, "//a[contains(text(), 'Nota saída')]")
        for opt in opcoes:
            if opt.is_displayed():
                driver.execute_script("arguments[0].click();", opt)
                break
        
        time.sleep(6)
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "tabTransporte"))).click()
        time.sleep(3)

        # 2. Captura MDF
        try:
            num_mdf = driver.find_element(By.ID, "txtNumNota").get_attribute("value")
            print(f"   📦 MDF: {num_mdf}")
        except: num_mdf = "N/A"

        # 3. Expandir Notas Relacionadas
        elemento_exp = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Notas relacionadas')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento_exp)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", elemento_exp)
        time.sleep(2)

        # 4. Coleta Notas e DATAS REAIS (da tabela interna)
        linhas_notas = driver.find_elements(By.XPATH, '//*[@id="table_nswNotasNotas"]/table[2]/tbody/tr')
        
        for i, linha in enumerate(linhas_notas, start=1):
            try:
                num_nota = linha.find_element(By.XPATH, f'.//td[contains(@headers, "colNumNota")]').text.strip()
                data_real = linha.find_element(By.XPATH, f'.//td[contains(@headers, "colDtaEmissao")]').text.strip()
                
                if num_nota:
                    print(f"   ✅ Nota {num_nota} | Data: {data_real}")
                    dados_para_planilha.append({
                        "Data Emissão": data_real,
                        "Número MDF": num_mdf,
                        "Nota Fiscal": num_nota,
                    })
            except: continue

        salvar_dados()

        # Voltar
        print("⬅️ Voltando...")
        btn_v = driver.find_element(By.ID, "btnVoltar")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_v)
        time.sleep(1)
        btn_v.click()
        time.sleep(8)
        return True

    except Exception as e:
        print(f"⚠️ Erro no registro {index-1}: {e}")
        return False

# --- 4. EXECUÇÃO PRINCIPAL ---

# Tenta fazer o login primeiro
if fazer_login(driver):
    
    # Se o login der certo, tenta navegar e filtrar
    if navegar_e_filtrar():
        
        # --- A MÁGICA DA CONTAGEM AUTOMÁTICA ENTRA AQUI ---
        try:
            print("🧮 Contando registros na tela...")
            # Espera a tabela aparecer na tela
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="tabNswNotasGerencia"]/table[2]/tbody/tr'))
            )
            
            # Pega todas as linhas e conta
            # A MÁGICA REFINADA
            linhas_tabela = driver.find_elements(By.XPATH, '//*[@id="tabNswNotasGerencia"]/table[2]/tbody/tr[@nlrowclick="true"]')            
            qtd_registros = len(linhas_tabela)
            
            print(f"🎯 Incrível! O robô identificou {qtd_registros} registros para processar.")
            
        except Exception as e:
            print("⚠️ Aviso: Não encontrei nenhum registro na tela ou a tabela demorou muito para carregar.")
            qtd_registros = 0
            
        # --------------------------------------------------

        # Se filtrou e achou registros, inicia o loop de extração
        if qtd_registros > 0:
            for i in range(1, qtd_registros + 1):
                linha_atual = i + 1 # Mantive a sua lógica original de pular a primeira linha invisível do cabeçalho
                print(f"\n🔄 Registro {i} de {qtd_registros}...")
                
                if not extrair_notas_da_linha(linha_atual): 
                    break

            print(f"\n✅ SUCESSO! Relatório finalizado em: {NOME_ARQUIVO}")
        else:
            print("\n🏁 Processo finalizado: Nada para fazer.")
        
        driver.quit() # Adicionado para fechar o Chrome após o sucesso
else:
    print("\n❌ Processo abortado devido a falha no login.")
    driver.quit()

# O SINAL DE FUMAÇA PARA O SERVIDOR WEB (ESTRITAMENTE OBRIGATÓRIO AQUI)
print("[FIM_DO_PROCESSO]")