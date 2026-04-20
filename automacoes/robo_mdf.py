import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
from dotenv import load_dotenv

load_dotenv()

# Pega a pasta principal de execução para garantir que salve no lugar certo
DIRETORIO_ATUAL = os.getcwd()
NOME_ARQUIVO = os.path.join(DIRETORIO_ATUAL, "Relatorio_MDFs_Gerado.xlsx")

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

# Inicia o Navegador
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
driver.maximize_window()

# --- FUNÇÕES DE APOIO E LOGIN ---

def salvar_dados():
    if dados_para_planilha:
        try:
            df = pd.DataFrame(dados_para_planilha)
            df.to_excel(NOME_ARQUIVO, index=False)
            print(f"   💾 Planilha salva com sucesso em: {NOME_ARQUIVO}")
        except Exception as e:
            # Se faltar o openpyxl ou houver erro de permissão, agora aparecerá no log!
            print(f"   ❌ ERRO CRÍTICO ao gerar Excel (falta openpyxl?): {e}")

def preencher_campo_seguro(id_campo, valor):
    try:
        campo = driver.find_element(By.ID, id_campo)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", campo)
        time.sleep(0.5)
        campo.clear()
        campo.send_keys(valor + Keys.TAB)
        time.sleep(1.5)
    except: pass

def desmarcar_checkbox_js(id_checkbox):
    try:
        # A mágica do JS: Encontra o elemento pelo ID. Se ele existir e estiver marcado (checked), força o clique!
        script = f"""
        var cb = document.getElementById('{id_checkbox}');
        if (cb && cb.checked) {{
            cb.click();
        }}
        """
        driver.execute_script(script)
    except Exception as e:
        print(f"   ⚠️ Aviso: Não conseguiu interagir com o checkbox {id_checkbox}.")


def fazer_login(driver):
    """Realiza o login automático e trata as sessões abertas."""
    # Puxa os dados do .env
    url = os.getenv('NLWEB_URL')
    usuario = os.getenv('NLWEB_USER')
    senha = os.getenv('NLWEB_PASS')
    
    wait = WebDriverWait(driver, 20)

    try:
        print("🌐 Acessando sistema...")
        driver.get('NLWEB_URL')

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

        # 👇 NOVA LÓGICA DE CHECKBOXES VIA JS 👇
        print("   🧹 Desmarcando opções irrelevantes...")
        
        # Lista com os IDs exatos que você me mandou (incluindo o novo DCe)
        checks_para_desmarcar = [
            "chkIndNFe", 
            "chkIndNFCe", 
            "chkIndCTe", 
            "chkIndNFSe", 
            "chkIndSAT", 
            "chkIndDCe"
        ]
        
        for id_check in checks_para_desmarcar: 
            desmarcar_checkbox_js(id_check)
            time.sleep(0.3) # Uma pausa super rápida para o sistema processar cada clique
        # 👆 --------------------------------- 👆

        btn_pesq = driver.find_element(By.XPATH, '/html/body/form[1]/div[3]/div[3]/div/div[3]/div[3]/button')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_pesq)
        time.sleep(1)
        btn_pesq.click()
        time.sleep(6)
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
        
        time.sleep(5)
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
        
        # ⏳ A MÁGICA 1: Aumentamos o tempo de espera. Às vezes o sistema da NL/Oracle demora para renderizar a sub-tabela!
        print("   ⏳ Aguardando notas relacionadas carregarem...")
        time.sleep(4) 

        # 4. Coleta Notas e DATAS REAIS (da tabela interna)
        # 🔍 A MÁGICA 2: Deixamos o XPath mais "flexível", removendo o [2] fixo que pode quebrar o código
        linhas_notas = driver.find_elements(By.XPATH, '//*[@id="table_nswNotasNotas"]//tbody/tr')
        
        if len(linhas_notas) == 0:
            print("   ⚠️ Nenhuma linha encontrada na tabela de notas relacionadas!")

        for i, linha in enumerate(linhas_notas, start=1):
            try:
                # Usamos find_elements (no plural). Se não achar nada, ele retorna uma lista vazia em vez de dar erro!
                coluna_nota = linha.find_elements(By.XPATH, './/td[contains(@headers, "colNumNota")]')
                coluna_data = linha.find_elements(By.XPATH, './/td[contains(@headers, "colDtaEmissao")]')
                
                # Se ele encontrou a coluna da nota e a coluna da data nessa linha, aí sim ele extrai
                if coluna_nota and coluna_data:
                    num_nota = coluna_nota[0].text.strip()
                    data_real = coluna_data[0].text.strip()
                    
                    # Se o número da nota não estiver em branco
                    if num_nota:
                        print(f"   ✅ Nota {num_nota} | Data: {data_real}")
                        dados_para_planilha.append({
                            "Data Emissão": data_real,
                            "Número MDF": num_mdf,
                            "Nota Fiscal": num_nota,
                        })
            except Exception as e: 
                # Se acontecer algum erro bizarro e inesperado, ele avisa de forma curta
                print(f"   ⚠️ Ignorando linha com formato inesperado.")

        salvar_dados()

        # Voltar
        print("⬅️ Voltando...")
        btn_v = driver.find_element(By.ID, "btnVoltar")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_v)
        time.sleep(1)
        btn_v.click()
        time.sleep(6)
        return True

    except Exception as e:
        print(f"⚠️ Erro no registro {index-1}: {e}")
        return False

# --- 4. EXECUÇÃO PRINCIPAL ---

# Tenta fazer o login primeiro
if fazer_login(driver):
    
    # Se o login der certo, tenta navegar e filtrar
    if navegar_e_filtrar():

        # 👇 --- NOVA MÁGICA DA PAGINAÇÃO (MOSTRAR TUDO) --- 👇
        try:
            print("   📂 Verificando se é necessário expandir a tabela para mostrar tudo...")
            script_paginacao = """
            var select = document.getElementById('tabNswNotasGerencia-nb__xc_c');
            if(select) {
                // Força o valor para "all" (Mostrar Tudo)
                select.value = 'all';
                // Dispara o evento 'change' igualzinho a um clique humano real para o sistema carregar os dados
                select.dispatchEvent(new Event('change'));
                return true;
            }
            return false; // Retorna falso se não achar o botão
            """
            expandiu = driver.execute_script(script_paginacao)
            
            if expandiu:
                print("   ✅ Opção 'Mostrar Tudo' ativada! Aguardando o sistema recarregar a lista gigante...")
                time.sleep(4) # Tempo de paciência para o NL trazer todas as notas extras
            else:
                print("   ℹ️ Dropdown não encontrado (Provavelmente 20 registros ou menos). Seguindo o fluxo normal...")
        except Exception as e:
            print(f"   ⚠️ Aviso ao tentar expandir paginação (pode ser ignorado): {e}")
        # 👆 ----------------------------------------------- 👆
        
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
                linha_atual = i + 1 
                print(f"\n🔄 Registro {i} de {qtd_registros}...")
                
                if not extrair_notas_da_linha(linha_atual): 
                    break
            
            # --- NOVA VALIDAÇÃO ---
            if not dados_para_planilha:
                print("\n❌ ALERTA: O robô leu as linhas, mas não encontrou NENHUMA nota válida para extrair. A planilha NÃO foi criada.")
            else:
                print(f"\n✅ SUCESSO! Relatório finalizado.")
        else:
            print("\n🏁 Processo finalizado: Nada para fazer.")
        
        driver.quit() # Adicionado para fechar o Chrome após o sucesso
else:
    print("\n❌ Processo abortado devido a falha no login.")
    driver.quit()

# O SINAL DE FUMAÇA PARA O SERVIDOR WEB (ESTRITAMENTE OBRIGATÓRIO AQUI)
print("[FIM_DO_PROCESSO]")