import os
import time
import datetime
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÃO DE CAMINHOS E LOGS ---
# Sobe um nível (sai da pasta automacoes e vai para a raiz)
PATH_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATH_XML = os.path.join(PATH_BASE, 'XML_Entrada')
PATH_LOGS = os.path.join(PATH_BASE, 'Logs')

if not os.path.exists(PATH_LOGS): os.makedirs(PATH_LOGS)
ARQUIVO_LOG = os.path.join(PATH_LOGS, f"log_cadastro_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

def registrar(mensagem):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    linha = f"[{timestamp}] {mensagem}"
    print(linha) # Isso é o que aparece no terminal do site!
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

def ler_fila_json():
    arquivo_fila = os.path.join(PATH_XML, 'fila_de_cadastro.json')
    if not os.path.exists(arquivo_fila):
        registrar("❌ ERRO: Arquivo fila_de_cadastro.json não encontrado.")
        return []
    try:
        with open(arquivo_fila, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        registrar(f"❌ ERRO ao ler o JSON: {e}")
        return []

# --- FUNÇÕES DE APOIO ---
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

def navegar_para_cadastro_inicial(driver, usar_mouse=False):
    try:
        driver.switch_to.default_content()
        caminhos = [
            '//*[@id="main-menu"]/li[1]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[2]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[2]/ul/li[1]/a'
        ]
        if usar_mouse:
            actions = ActionChains(driver)
            for xpath in caminhos:
                el = driver.find_element(By.XPATH, xpath)
                actions.move_to_element(el).pause(0.3)
            btn_final = driver.find_element(By.XPATH, caminhos[-1])
            actions.click(btn_final).perform()
        else:
            for xpath in caminhos:
                el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.5)
    except: pass

def voltar_ao_inicio_seguro(driver):
    try:
        registrar("🏠 Voltando para a tela inicial via Logo (Soft Reset)...")
        # 1. Garante que o robô não está preso dentro de nenhum iframe (janela interna)
        driver.switch_to.default_content() 
        
        # 2. Localiza o link que envelopa a logo (dentro da div brand-holder)
        wait = WebDriverWait(driver, 10)
        logo_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".brand-holder a")))
        
        # 3. O "Tiro Certo": Força o clique com JavaScript, infalível!
        driver.execute_script("arguments[0].click();", logo_link)
        
        # 4. Dá tempo para a tela do NL Web processar o fechamento das janelas e carregar a Home
        time.sleep(3)
        registrar("✅ Tela inicial carregada e limpa!")
        
    except Exception as e:
        registrar(f"⚠️ Falha ao tentar clicar na logo para resetar a tela: {e}")

# --- PLANO B ---
def consolidar_cadastro_plano_b(driver, descricao_item, codigo_esperado):
    try:
        registrar(f"⚠️ Iniciando validação no PLANO B para o código: {codigo_esperado}")
        
        # 1. Voltar e Recarregar
        driver.find_element(By.ID, "btnCrudVoltar").click()
        time.sleep(2)
        try: driver.switch_to.alert.accept()
        except: pass

        navegar_para_cadastro_inicial(driver, usar_mouse=True)
        
        # 2. Aguarda a lista geral carregar
        registrar("⏳ Aguardando lista geral carregar...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//td[@headers='tabIeItens:colCodItem']"))
        )

        # 3. Garante que a barra de filtros está aberta
        campo_pesquisa = driver.find_element(By.ID, "txtDesItem")
        if not campo_pesquisa.is_displayed():
            driver.execute_script("document.getElementById('btn_nlPanelOcultarMostrar_').click();")
            time.sleep(1.5)

        # 4. Pesquisa pela descrição
        preencher_campo_seguro(driver, "txtDesItem", descricao_item)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "search_cmdSearch")) 
        time.sleep(4) # Tempo para o sistema filtrar

        # --- AQUI ENTRA A TRAVA DE SEGURANÇA QUE VOCÊ PEDIU ---
        registrar(f"🔍 Varrendo resultados para encontrar o código {codigo_esperado}...")
        
        # Captura todas as células da coluna "Código"
        coluna_codigos = driver.find_elements(By.XPATH, "//td[@headers='tabIeItens:colCodItem']")
        
        linha_correta = -1 # Variável para guardar o índice da linha
        
        for index, celula in enumerate(coluna_codigos):
            if celula.text.strip() == str(codigo_esperado):
                linha_correta = index
                registrar(f"🎯 Código {codigo_esperado} encontrado na linha {index + 1}!")
                break
        
        if linha_correta != -1:
            # 5. CLIQUE NO ITEM CORRETO (Usando o índice que encontramos)
            # O ID do link de cadastro segue o padrão tabIeItens:INDICE:lnkCadastro
            id_link_especifico = f"tabIeItens:{linha_correta}:lnkCadastro"
            
            # Clica primeiro na linha para garantir o foco (opcional mas seguro)
            celula.click()
            time.sleep(1)
            
            # Clica no botão de edição (engrenagem) daquela linha específica
            driver.find_element(By.ID, id_link_especifico).click()
            time.sleep(2)
            
            # 6. CONSOLIDAÇÃO FINAL
            driver.find_element(By.ID, "btnCrudGravar").click()
            limpar_popups_persistente(driver, "btn1")
            registrar(f"✨ SUCESSO! Item {codigo_esperado} consolidado com segurança.")
        else:
            registrar(f"❌ ERRO CRÍTICO: O código {codigo_esperado} não foi encontrado na lista de resultados!")

    except Exception as e:
        registrar(f"❌ Erro no Plano B: {e}")

# --- FLUXO PRINCIPAL ---
# --- FLUXO PRINCIPAL ---
def executar_cadastro(driver, item, is_ultimo=False):    
    try:
        # 1. Seleciona o item base
        preencher_campo_seguro(driver, "lovCodItem_txtCod", "13886")
        time.sleep(4) # Aumentado levemente para garantir carga da grade
        
        xpath_linha = "/html/body/form[1]/div[3]/div[1]/section/div[2]/div[2]/table/tbody/tr[2]/td[2]/div/div/table[2]/tbody/tr[2]/td[1]"
        
        # Uso de JS para evitar o "Click Intercepted" logo de cara
        linha = driver.find_element(By.XPATH, xpath_linha)
        driver.execute_script("arguments[0].click();", linha)
        
        time.sleep(1.5)
        btn_cadastro = driver.find_element(By.ID, "tabIeItens:0:lnkCadastro")
        driver.execute_script("arguments[0].click();", btn_cadastro)
        
        # Aguarda a tela de edição carregar
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "btnCrudDuplicar")))
        time.sleep(2)
        
        # 2. Duplicação (Nova Lógica do Menu Flutuante)
        registrar("🔄 Abrindo menu flutuante de opções...")
        
        # Etapa 6: Clica no botão flutuante (...) usando a classe específica dele
        btn_flutuante = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'nl-btn-speed-dial')]"))
        )
        driver.execute_script("arguments[0].click();", btn_flutuante)
        
        # Espera estratégica para a animação das opções "pularem" na tela
        time.sleep(1.5) 
        
        # Etapa 7: Clica na opção de Duplicar que acabou de aparecer
        registrar("📋 Acionando a duplicação do item...")
        btn_duplicar = driver.find_element(By.ID, "btnCrudDuplicar")
        driver.execute_script("arguments[0].click();", btn_duplicar)
        
        # Espera o sistema começar a processar a duplicação antes de tentar fechar os pop-ups
        time.sleep(1.5)

        
        # Limpezas iniciais
        limpar_popups_persistente(driver, "btn1")
        limpar_popups_persistente(driver, "btn1")
        
        # Aguarda o novo código aparecer no campo
        time.sleep(2) 
        try:
            cod_novo = driver.find_element(By.ID, "txtCodItem").get_attribute("value").replace(".", "")
            registrar(f"🔢 CÓDIGO ATRIBUÍDO: {cod_novo}")
        except: pass

        # --- MOMENTO CRÍTICO: Preenchimento dos dados ---
        # Adicionei um pequeno respiro aqui para evitar que o NL bloqueie a digitação
        time.sleep(1.5) 

        preencher_campo_seguro(driver, "txtDesItem", item['desc'])
        preencher_campo_seguro(driver, "txtCodEan", item['ean'])
        preencher_campo_seguro(driver, "lovCodUm_txtCod", item['unid'])
        preencher_campo_seguro(driver, "lovCodNbm_txtCod", item['ncm'])
        
        limpar_popups_persistente(driver, "btn2")
        
        preencher_campo_seguro(driver, "lovCodTipo_txtCod", "07")
        preencher_campo_seguro(driver, "lovCodGrFiscal_txtCod", "05")
        
        # 3. Gravação
        btn_gravar = driver.find_element(By.ID, "btnCrudGravar")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_gravar)
        btn_gravar.click()
        
        limpar_popups_persistente(driver, "btn1")
        
       # 4. Finalização e Protocolo
        try:
            wait_protocolo = WebDriverWait(driver, 15)
            wait_protocolo.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'protocolo_panel_numero')]")))
            
            elemento_numero = driver.find_element(By.XPATH, "//div[contains(@class, 'protocolo_panel_numero')]")
            cod_final = elemento_numero.text.strip()
            
            registrar(f"✨ SUCESSO! Item cadastrado e vinculado ao código: {cod_final}")
            
            btn_ok = driver.find_element(By.ID, "btnProtocolo")
            driver.execute_script("arguments[0].click();", btn_ok)
            time.sleep(2)
            
            # --- VERIFICA SE É O ÚLTIMO ANTES DE RESETAR ---
            if not is_ultimo:
                voltar_ao_inicio_seguro(driver)
                navegar_para_cadastro_inicial(driver, usar_mouse=True)
            else:
                registrar("✅ Fim da fila! Último item cadastrado. Mantendo a tela atual.")
            
        except Exception as e:
            registrar(f"⚠️ Falha ao capturar protocolo, acionando Plano B preventivo...")
            driver.switch_to.default_content()
            
            # PASSANDO O cod_novo PARA O PLANO B:
            consolidar_cadastro_plano_b(driver, item['desc'], cod_novo)
            
            if not is_ultimo:
                voltar_ao_inicio_seguro(driver)
                navegar_para_cadastro_inicial(driver, usar_mouse=True)
            else:
                registrar("✅ Fim da fila! Último item salvo no Plano B. Mantendo a tela atual.")

    except Exception as e:
        registrar(f"❌ Erro Crítico durante a digitação: {e}")
        
        if not is_ultimo:
            voltar_ao_inicio_seguro(driver)
            try:
                navegar_para_cadastro_inicial(driver, usar_mouse=True)
            except: pass
        
# --- LOGIN ---
def fazer_login(driver):
    url = "http://192.168.200.252:8585/NLWeb/site/9000/emp/1"
    usuario = "LEONARDO DIA"
    senha = "123"
    wait = WebDriverWait(driver, 20)

    try:
        # MENSAGEM PADRONIZADA
        print("🔐 Acessando portal ERP Ciamed...")
        driver.get(url)

        wait.until(EC.element_to_be_clickable((By.ID, "txtUsername"))).send_keys(usuario)
        driver.find_element(By.ID, "txtPassword").send_keys(senha)
        driver.find_element(By.ID, "cmdLogin").click()
        
        # Tratamento de sessões
        try:
            wait_iframe = WebDriverWait(driver, 5)
            wait_iframe.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "_blank")))
            wait_iframe.until(EC.element_to_be_clickable((By.ID, "btn1"))).click()
            driver.switch_to.default_content()
        except:
            driver.switch_to.default_content()

        xpath_janela_motivo = "//label[contains(text(), 'Motivo')]"
        try:
            wait_short = WebDriverWait(driver, 5)
            wait_short.until(EC.visibility_of_element_located((By.XPATH, xpath_janela_motivo)))
            while True:
                botoes_finalizar = driver.find_elements(By.XPATH, "//button[contains(text(), 'Finalizar')]")
                if not botoes_finalizar: break
                campo_motivo = driver.find_element(By.XPATH, "//label[contains(text(), 'Motivo')]/../..//input")
                campo_motivo.clear()
                campo_motivo.send_keys("d")
                botoes_finalizar[0].click()
                time.sleep(2) 
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continuar')]"))).click()
        except: pass

        wait.until(EC.presence_of_element_located((By.ID, "main-menu")))
        
        # MENSAGEM PADRONIZADA
        print("🎊 Login realizado. Iniciando motor de busca de itens...")
        return True
    except:
        return False

# --- INÍCIO ---
itens_processar = ler_fila_json()

if itens_processar:
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    
    # --- 👻 MODO INVISÍVEL (HEADLESS) ATIVADO ---
    options.add_argument("--headless=new") 
    options.add_argument("--window-size=1920,1080") # Garante que o robô "enxergue" a tela inteira
    # --------------------------------------------
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window() # No modo headless isso não faz muita diferença, mas pode deixar aí!
    
    if fazer_login(driver):
        navegar_para_cadastro_inicial(driver, usar_mouse=False)

        # MUDANÇA: USANDO ENUMERATE PARA CONTAR OS ITENS (i)
        # --- MUDANÇA: ENSINANDO O ROBÔ A CONTAR ---
        total_itens = len(itens_processar) # Conta o total de itens na fila

        for i, item in enumerate(itens_processar, 1):
            is_ultimo = (i == total_itens) # Se o número atual for igual ao total, é o último!

            print("-" * 50)
            print(f"🚀 PROCESSANDO ITEM {i}/{total_itens}: {item.get('desc', 'N/A')}")
            print(f"🔢 EAN: {item.get('ean', 'N/A')} | NCM: {item.get('ncm', 'N/A')}")
            
            # Agora passamos a informação 'is_ultimo' para a função
            executar_cadastro(driver, item, is_ultimo)
        
        registrar("🏁 PROCESSO CONCLUÍDO.")