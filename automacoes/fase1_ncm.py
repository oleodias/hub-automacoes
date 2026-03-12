import os
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import motor_xml
import login_navegacao
import cadastro_ncm
import consulta_item

# --- CONFIGURAÇÃO DO CAMINHO ---
# Sobe um nível (sai de 'automacoes' e vai para a raiz)
PATH_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_XML = os.path.join(PATH_BASE, "XML_Entrada")

def acessar_tela_itens(driver):
    print("\n📍 Navegando para a tela de Cadastro de Itens...")
    try:
        driver.switch_to.default_content()
        caminhos = [
            '//*[@id="main-menu"]/li[1]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[2]/a',
            '//*[@id="main-menu"]/li[1]/ul/li[3]/ul/li[2]/ul/li[1]/a'
        ]
        
        for xpath in caminhos:
            el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", el)
            time.sleep(0.5)
            
        time.sleep(2)
        print("✅ Tela de Itens carregada.")
        return True
    except Exception as e:
        print(f"❌ Erro ao acessar tela de itens: {e}")
        return False

def executar_fase_1():
    print("\n🟢 === FASE 1: VALIDAÇÃO DE NCMs E TRIAGEM DE ITENS ===")
    
    if not os.path.exists(PASTA_XML): os.makedirs(PASTA_XML)
    arquivos = [f for f in os.listdir(PASTA_XML) if f.lower().endswith('.xml')]
    
    if not arquivos:
        return {"status": "Erro", "msg": "Nenhum XML encontrado."}

    arquivo_xml = os.path.join(PASTA_XML, arquivos[0])
    lista_itens = motor_xml.extrair_dados_xml(arquivo_xml)
    
    if not lista_itens:
        return {"status": "Erro", "msg": "Falha na leitura dos dados do XML."}
        
    lista_ncms = list(set([item['ncm'] for item in lista_itens]))
    
    # --- MUDANÇA AQUI: Pedindo para o login abrir no Modo Fantasma ---
    driver = login_navegacao.iniciar_navegador()
    
    try:
        login_navegacao.fazer_login(driver)
        cadastro_ncm.processar_ncms(driver, lista_ncms)
        
        if acessar_tela_itens(driver):
            itens_pendentes = consulta_item.buscar_itens_no_sistema(driver, lista_itens)
            
            arquivo_json = os.path.join(PASTA_XML, 'fila_de_cadastro.json')
            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(itens_pendentes, f, ensure_ascii=False, indent=4)
            
            # RETORNO INTELIGENTE
            return {
                "status": "Sucesso",
                "total_itens_xml": len(lista_itens),
                "ncms_unicos": len(lista_ncms),
                "itens_para_cadastrar": len(itens_pendentes),
                "itens_ja_existentes": len(lista_itens) - len(itens_pendentes),
                "arquivo": arquivos[0],
                "lista_itens": itens_pendentes # <--- NOVA LINHA ADICIONADA AQUI
            }
        else:
            return {"status": "Erro", "msg": "Tela de itens do ERP não abriu."}

    except Exception as e:
        return {"status": "Erro", "msg": str(e)}
    finally:
        if driver: driver.quit()

        # --- GATILHO PARA TESTE NO TERMINAL ---
if __name__ == "__main__":
    print("🚀 Teste direto no Prompt iniciado...")
    
    # Chama a função principal e guarda o que ela retorna
    resultado_final = executar_fase_1()
    
    # Imprime o dicionário na tela para você ver se deu tudo certo
    print("\n" + "="*50)
    print("🎯 RESULTADO DO RETORNO (O que vai para o site):")
    print(json.dumps(resultado_final, indent=4, ensure_ascii=False))
    print("="*50)

    