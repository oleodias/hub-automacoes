import sys
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Evita problemas de acentuação no console do Windows
sys.stdout.reconfigure(encoding='utf-8')

def limpar_cnpj(cnpj):
    # Remove tudo que não for número (pontos, barras, traços)
    return re.sub(r'\D', '', str(cnpj))

def descobrir_regiao(uf):
    # Dicionário de tradução UF -> Código da Região
    mapa_regioes = {
        'PR': '1', 'SC': '1', 'RS': '1',
        'SP': '2', 'RJ': '2', 'MG': '2', 'ES': '2',
        'MS': '3', 'MT': '3', 'GO': '3', 'DF': '3',
        'BA': '4', 'PI': '4', 'MA': '4', 'CE': '4', 'RN': '4', 'PB': '4', 'PE': '4', 'AL': '4', 'SE': '4',
        'AC': '5', 'RO': '5', 'AM': '5', 'RR': '5', 'PA': '5', 'AP': '5', 'TO': '5'
    }
    return mapa_regioes.get(uf.upper(), '')

def fazer_login(driver):
    url = "http://192.168.200.252:8585/NLWeb/site/9000/emp/1"
    usuario = "LEONARDO DIA"
    senha = "123"
    wait = WebDriverWait(driver, 20)

    try:
        print("🔐 Acessando portal ERP Ciamed...")
        driver.get(url)

        wait.until(EC.element_to_be_clickable((By.ID, "txtUsername"))).send_keys(usuario)
        driver.find_element(By.ID, "txtPassword").send_keys(senha)
        driver.find_element(By.ID, "cmdLogin").click()
        
        # Tratamento de sessões (se já tiver login aberto)
        try:
            wait_iframe = WebDriverWait(driver, 5)
            wait_iframe.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "_blank")))
            wait_iframe.until(EC.element_to_be_clickable((By.ID, "btn1"))).click()
            driver.switch_to.default_content()
        except:
            driver.switch_to.default_content()

        # Tratamento de justificativa de encerramento
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
        
        print("🎊 Login realizado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return False
    
# --- NAVEGAÇÃO VIA FAVORITOS ---
def navegar_via_favoritos(driver):
    print("> ⭐ NAVEGAÇÃO: Acessando via Favoritos...")
    try:
        wait = WebDriverWait(driver, 20)
        driver.switch_to.default_content()
        btn_estrela = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'tab-header-menu-favoritos')]")))
        btn_estrela.click()
        time.sleep(1.5)
        xpath_link = "//ul[@id='header-menu-favoritos']//a[contains(text(), 'Pessoas geral')]"
        link_pessoasgeral = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_link)))
        link_pessoasgeral.click()
        time.sleep(4) 
        return True
    except Exception as e:
        print(f"> ❌ Erro na navegação: {e}")
        return False

def main():
    print("> 🚀 Iniciando Robô de Cadastro de Fornecedores...")
    
    # 1. Receber os dados do Frontend
    try:
        dados_json = sys.argv[1]
        fornecedor = json.loads(dados_json)
        print(f"> Dados recebidos para a Razão Social: {fornecedor.get('razao_social')}")
        cnpj_formatado = limpar_cnpj(fornecedor.get('cnpj', ''))
    except Exception as e:
        print(f"> ❌ Erro ao receber os dados do portal: {e}")
        print("[FIM_DO_PROCESSO]")
        return

    # 2. Configurar Navegador
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    # options.add_argument('--headless') # Descomente depois para rodar invisível
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    # 3. Fazer Login
    if not fazer_login(driver):
        driver.quit()
        print("[FIM_DO_PROCESSO]")
        return

    try:
        print("> 🗺️ Navegando até a tela de Cadastro de Pessoas...")
        
        # Chama a nova função de navegação
        if not navegar_via_favoritos(driver):
            raise Exception("Não foi possível acessar o menu de Favoritos.")
        
        # Clicar em "Novo" (Forçando via JavaScript)
        print("> 📄 Abrindo formulário de Novo Cadastro...")
        btn_novo = wait.until(EC.presence_of_element_located((By.ID, "btnNovo")))
        driver.execute_script("arguments[0].click();", btn_novo)
        
        # Aguardar pop-up do CNPJ e preencher
        print(f"> 🔍 Inserindo CNPJ ({cnpj_formatado}) para pesquisa...")
        campo_cnpj = wait.until(EC.visibility_of_element_located((By.ID, "subFrmPsPesquisaPessoa:codCompleto")))
        campo_cnpj.send_keys(cnpj_formatado)
        
        # Clicar em "Executar pesquisa" (Forçando via JavaScript)
        btn_pesquisar = driver.find_element(By.ID, "subFrmPsPesquisaPessoa:btnPesquisar")
        driver.execute_script("arguments[0].click();", btn_pesquisar)
        
        # Aguardar a tela principal carregar
        time.sleep(3) 
        
        # --- INÍCIO DOS 16 PASSOS DO CADASTRO ---
        print("> ✍️ Preenchendo a Ficha Cadastral (Fase 1/4)...")
        
        # Passo 1: Marcar Fornecedor (Forçado via JS)
        check_forn = wait.until(EC.presence_of_element_located((By.ID, "indForn")))
        if not check_forn.is_selected():
            driver.execute_script("arguments[0].click();", check_forn)
            time.sleep(0.5)

        # Passo 2: Razão Social
        campo_razao = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoa")))
        campo_razao.clear()
        campo_razao.send_keys(fornecedor.get('razao_social', ''))

        # Passo 3: Nome Fantasia
        campo_fantasia = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoaFantasia")))
        campo_fantasia.clear()
        campo_fantasia.send_keys(fornecedor.get('nome_fantasia', ''))

        # Passo 4: Inscrição Estadual (Automatizada e Validada)
        ie = fornecedor.get('inscricao_estadual', '')
        if ie:
            print(f"> 📄 Inserindo Inscrição Estadual: {ie}")
            for _ in range(3):
                try:
                    # Usando o ID que você forneceu:
                    campo_ie = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:numInscEst")))
                    
                    # Limpeza Bruta (JS + Teclado)
                    driver.execute_script("arguments[0].value = '';", campo_ie)
                    campo_ie.send_keys(Keys.CONTROL + "a")
                    campo_ie.send_keys(Keys.BACKSPACE)
                    time.sleep(0.3)
                    
                    # Digita a IE e dá TAB
                    campo_ie.send_keys(ie)
                    campo_ie.send_keys(Keys.TAB)
                    break
                except:
                    time.sleep(1)
        else:
            print("> ℹ️ Nenhuma IE ativa encontrada para este estado. Pulando campo...")

        # Passo 5: Atividade (14)
        campo_ativ = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:lovPsAtividadesPsJuridicas_txtCod")))
        campo_ativ.clear()
        campo_ativ.send_keys("14")
        campo_ativ.send_keys(Keys.TAB)

        print("> 📍 Preenchendo Endereço (Fase 2/4)...")

        # Passo 6: CEP (Limpando e digitando primeiro)
        for _ in range(3):
            try:
                campo_cep = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtCep")))
                campo_cep.send_keys(Keys.CONTROL + "a")
                campo_cep.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                cep_limpo = limpar_cnpj(fornecedor.get('cep', ''))
                campo_cep.send_keys(cep_limpo)
                campo_cep.send_keys(Keys.TAB) 
                time.sleep(3) # Espera o ERP carregar os dados automáticos
                break
            except:
                time.sleep(1)

        # Passo 7: Endereço (Limpando o que o ERP trouxe e corrigindo)
        endereco_completo = f"{fornecedor.get('logradouro', '')}, {fornecedor.get('numero', '')}, {fornecedor.get('complemento', '')}".strip(", ") 
        for _ in range(3): 
            try:
                campo_endereco = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesEndereco")))
                campo_endereco.send_keys(Keys.CONTROL + "a")
                campo_endereco.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                campo_endereco.send_keys(endereco_completo)
                break
            except:
                time.sleep(1)

        # Passo 8: Bairro (Limpeza Bruta via JS + Digitação)
        for _ in range(3):
            try:
                campo_bairro = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesBairro")))
                
                # 1. Força o campo a ficar vazio via JavaScript (O ERP não consegue bloquear isso)
                driver.execute_script("arguments[0].value = '';", campo_bairro)
                time.sleep(0.2)
                
                # 2. Reforça com o comando de teclado para o sistema "sentir" a mudança
                campo_bairro.send_keys(Keys.CONTROL + "a")
                campo_bairro.send_keys(Keys.BACKSPACE)
                time.sleep(0.5) 
                
                # 3. Digita o bairro correto da API
                print(f"> Corrigindo Bairro para: {fornecedor.get('bairro', '')}")
                campo_bairro.send_keys(fornecedor.get('bairro', ''))
                break
            except:
                time.sleep(1)

        # Passo 9: Região (Limpando e corrigindo)
        uf = fornecedor.get('uf', '')
        codigo_regiao = descobrir_regiao(uf)
        for _ in range(3):
            try:
                campo_regiao = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:lovPsRegioesPsJuridicas_txtCod")))
                campo_regiao.send_keys(Keys.CONTROL + "a")
                campo_regiao.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                campo_regiao.send_keys(codigo_regiao)
                campo_regiao.send_keys(Keys.TAB)
                time.sleep(1.5) # Espera o sistema validar a região
                break
            except:
                time.sleep(1)

        print("> ⏭️ Avançando formulário (Fase 3/4)...")

        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        # Passo 10: Clicar 10 vezes em Próximo (CORRIGIDO com busca contínua do botão)
        for i in range(10):
            btn_proximo = wait.until(EC.presence_of_element_located((By.ID, "btnWizardProximoCab")))
            driver.execute_script("arguments[0].click();", btn_proximo)
            time.sleep(0.8) # Tempo de respiro para o ERP girar a página

        # Passo 11: Tipo de Fornecedor (10)
        campo_tipo = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsFornecedores:lovCodTipoForn_txtCod")))
        campo_tipo.send_keys(Keys.CONTROL + "a")
        campo_tipo.send_keys(Keys.BACKSPACE)
        campo_tipo.send_keys("10")
        campo_tipo.send_keys(Keys.TAB)
        time.sleep(0.5)

        # Passo 12: Condição de Pagamento (33)
        campo_pgto = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsFornecedores:lovCodCondPgtoForn_txtCod")))
        campo_pgto.send_keys(Keys.CONTROL + "a")
        campo_pgto.send_keys(Keys.BACKSPACE)
        campo_pgto.send_keys("33")
        campo_pgto.send_keys(Keys.TAB)
        
        print("> 💾 Finalizando e Gravando (Fase 4/4)...")

        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        # Passo 13: Clicar 5 vezes em Próximo (CORRIGIDO)
        for i in range(5):
            btn_proximo = wait.until(EC.presence_of_element_located((By.ID, "btnWizardProximoCab")))
            driver.execute_script("arguments[0].click();", btn_proximo)
            time.sleep(0.8)

        # Passo 14: Gravar
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        btn_gravar = wait.until(EC.presence_of_element_located((By.ID, "btnCrudGravar")))
        driver.execute_script("arguments[0].click();", btn_gravar)

        # Passo 15: Capturar o Número do Protocolo
        print("> ⏳ Aguardando processamento do sistema...")
        caixa_protocolo = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "protocolo_panel_numero")))
        num_fornecedor = caixa_protocolo.text
        print(f"> 🎉 SUCESSO! Fornecedor cadastrado com o código: {num_fornecedor}")

        # Passo 16: Clicar no OK final
        btn_ok = wait.until(EC.presence_of_element_located((By.ID, "btnProtocolo")))
        driver.execute_script("arguments[0].click();", btn_ok)
        time.sleep(2)

    except Exception as e:
        print(f"> ❌ Erro durante a automação: {str(e)}")
    finally:
        time.sleep(3)
        driver.quit()
        print("[FIM_DO_PROCESSO]")

if __name__ == "__main__":
    main()