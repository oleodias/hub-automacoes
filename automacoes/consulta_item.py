import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

def pausar_para_ver(mensagem):
    """Pausa dramática para o Leonardo ver o que está acontecendo."""
    print(f"   👀 {mensagem} (Aguardando 3s...)")
    time.sleep(3)

def verificar_se_encontrou(driver):
    time.sleep(2)
    fonte = driver.page_source
    if "Nenhum registro encontrado" in fonte or "Nenhum resultado encontrado" in fonte:
        return False
    return True

def capturar_codigo_item(driver):
    try:
        elem = driver.find_element(By.CSS_SELECTOR, "td[headers*='colCodItem']")
        return elem.text.strip()
    except:
        return None

def garantir_barra_aberta(driver):
    try:
        driver.execute_script("document.getElementById('btn_nlPanelOcultarMostrar_').click();")
        time.sleep(1)
    except:
        pass

def buscar_itens_no_sistema(driver, lista_itens_xml):
    wait = WebDriverWait(driver, 15)
    itens_para_cadastrar = []
    
    # Memória: O item anterior usou EAN?
    teve_ean_anteriormente = False 

    print("\n🔎 INICIANDO CONSULTA EM CÂMERA LENTA...")

    for i, item in enumerate(lista_itens_xml, 1):
        # 1. Pega a descrição original e tira as aspas
        descricao_bruta = item['desc'].replace("'", "") 
        
        # 2. Limpa o EAN (de 8 a 15 números) do começo da frase
        descricao_limpa = re.sub(r'^\d{8,15}\s*-?\s*', '', descricao_bruta).strip()
        
        # 3. A MÁGICA AQUI: Atualiza o item original para que o JSON receba limpo!
        item['desc'] = descricao_limpa
        
        # 4. Define as variáveis para o robô usar na pesquisa
        descricao = item['desc']
        ean = item['ean']
        tem_ean_atual = bool(ean and str(ean).strip() != "")
        item_encontrado = False 
        
        print(f"\n--- 📦 Processando Item {i} ---")
        # ... o resto do código continua igual ...
        
        # 1. TRANSIÇÃO: Garantir barra aberta e LIMPAR DESCRIÇÃO ANTERIOR
        # Isso garante que a tela comece limpa, independente se vamos usar EAN ou Descrição agora.
        garantir_barra_aberta(driver)
        
        try:
            # Sempre limpa o campo de descrição antes de começar o próximo
            campo_desc_lateral = driver.find_element(By.ID, "txtDesItem")
            driver.execute_script("arguments[0].value = '';", campo_desc_lateral)
        except:
            pass
            
        pausar_para_ver("Tela limpa e preparada para o Item " + str(i))

        # 2. LIMPEZA ESPECIAL DE MODAL (Se o anterior era EAN e este não é)
        if teve_ean_anteriormente and not tem_ean_atual:
            print("   🧹 Transição EAN -> Sem EAN detectada.")
            try:
                # Abre Avançada só para limpar
                btn_avancada = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Avançada')]")))
                btn_avancada.click()
                pausar_para_ver("Abri modal para limpar")
                
                iframe = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "af_dialog_content")))
                driver.switch_to.frame(iframe)
                
                # Clica na Borracha dentro do modal
                btn_borracha = driver.find_element(By.CSS_SELECTOR, "#panelGroupFooterLeft button.btn_limpar_icon")
                driver.execute_script("arguments[0].click();", btn_borracha)
                pausar_para_ver("Cliquei na borracha interna")
                
                driver.switch_to.default_content()
                
                # Clica no X para fechar
                btn_fechar_x = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.af_dialog_close-icon")))
                driver.execute_script("arguments[0].click();", btn_fechar_x)
                pausar_para_ver("Fechei o modal no X")
                
            except Exception as e:
                print(f"   ⚠️ Erro na limpeza: {e}")
                driver.switch_to.default_content()

        # =========================================================================
        # INÍCIO DA PESQUISA REAL
        # =========================================================================

        # --- FLUXO A: TEM EAN ---
        if tem_ean_atual:
            print(f"   🔢 Pesquisando EAN: {ean}")
            try:
                # Abre Modal
                btn_avancada = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/form[1]/div[3]/div[3]/div/div[3]/div[1]/button[2]")
                ))
                btn_avancada.click()
                pausar_para_ver("Modal de EAN aberto")
                
                iframe = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "af_dialog_content")))
                driver.switch_to.frame(iframe)
                
                # Preenche EANs
                seletor = wait.until(EC.presence_of_element_located((By.ID, "cboTipOperadorString_105")))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", seletor)
                Select(seletor).select_by_value("between")
                
                campo_ini = driver.find_element(By.ID, "txtDesConteudoIni_105")
                campo_fim = driver.find_element(By.ID, "txtDesConteudoFim_105")
                driver.execute_script("arguments[0].removeAttribute('disabled')", campo_fim)
                
                campo_ini.clear() 
                campo_ini.send_keys(ean)
                campo_fim.clear()
                campo_fim.send_keys(ean)
                pausar_para_ver("EANs preenchidos")
                
                # Clica Lápis -> Executar SQL
                btn_lapis = driver.find_element(By.CSS_SELECTOR, "#panelGroupFooterLeft button.btn_edit_icon")
                driver.execute_script("arguments[0].click();", btn_lapis)
                pausar_para_ver("Cliquei no Lápis")
                
                wait.until(EC.visibility_of_element_located((By.ID, "txtCustomWhere")))
                btn_exec_sql = driver.find_element(By.CSS_SELECTOR, ".dialog_content .btn_executar_icon")
                driver.execute_script("arguments[0].click();", btn_exec_sql)
                pausar_para_ver("Executei o SQL")

                driver.switch_to.default_content()
                
                # Validar
                if verificar_se_encontrou(driver):
                    cod = capturar_codigo_item(driver)
                    print(f"   ✅ ENCONTRADO (EAN)! Cód: {cod}")
                    item_encontrado = True
                else:
                    print(f"   ⚠️ EAN falhou. Indo para Descrição...")
                    # Se falhou, limpamos o filtro geral
                    driver.execute_script("document.getElementById('search_cmdReset').click();")
                    pausar_para_ver("Limpei filtro geral (Borracha externa)")

            except Exception as e:
                print(f"   ❌ Erro EAN: {e}")
                driver.switch_to.default_content()
                driver.execute_script("document.getElementById('search_cmdReset').click();")

        # --- FLUXO B: BUSCA POR DESCRIÇÃO ---
        if not item_encontrado:
            print(f"   📝 Pesquisando Descrição: {descricao}")
            try:
                garantir_barra_aberta(driver)
                
                campo_desc = wait.until(EC.presence_of_element_located((By.ID, "txtDesItem")))
                # Garante que está limpo antes de digitar
                driver.execute_script("arguments[0].value = '';", campo_desc)
                driver.execute_script(f"arguments[0].value = '{descricao}';", campo_desc)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", campo_desc)
                pausar_para_ver("Descrição preenchida")
                
                # Clica Lupa
                driver.execute_script("document.getElementById('search_cmdSearch').click();")
                pausar_para_ver("Cliquei na Lupa")
                
                if verificar_se_encontrou(driver):
                    cod = capturar_codigo_item(driver)
                    print(f"   ✅ ENCONTRADO (Desc)! Cód: {cod}")
                else:
                    print("   ❌ NÃO ENCONTRADO. Vai para Cadastro.")
                    itens_para_cadastrar.append(item)
            
            except Exception as e:
                print(f"   ❌ Erro Descrição: {e}")
                itens_para_cadastrar.append(item)

        # Atualiza a memória
        teve_ean_anteriormente = tem_ean_atual
        print("-" * 30)

    return itens_para_cadastrar