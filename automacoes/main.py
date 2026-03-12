import os
import time
import sys
from selenium.webdriver.common.by import By

# Importação dos seus módulos
import motor_xml
import login_navegacao
import consulta_item
import cadastro_ncm
import cadastro_item

# --- CONFIGURAÇÕES ---
PASTA_XML = "XML_Entrada"

def main():
    print("\n🤖 INICIANDO ROBÔ - FLUXO: 2 SESSÕES (NCM -> FECHA -> ITENS)")
    print("="*60)

    # 1. VERIFICAÇÃO DE ARQUIVOS
    if not os.path.exists(PASTA_XML):
        os.makedirs(PASTA_XML)
    
    arquivos = [f for f in os.listdir(PASTA_XML) if f.lower().endswith('.xml')]
    
    if not arquivos:
        print(f"❌ Nenhum arquivo XML encontrado na pasta '{PASTA_XML}'.")
        return

    arquivo_xml = os.path.join(PASTA_XML, arquivos[0])
    
    # 2. LEITURA DO XML
    lista_todos_itens = motor_xml.extrair_dados_xml(arquivo_xml)
    if not lista_todos_itens:
        print("❌ Falha na leitura do XML. Encerrando.")
        return

    # ==============================================================================
    # 🟢 SESSÃO 1: CONSULTA E RESOLUÇÃO DE NCM
    # ==============================================================================
    print("\n🌐 [SESSÃO 1] ABRINDO NAVEGADOR PARA TRIAGEM E NCM...")
    driver = login_navegacao.iniciar_navegador()
    
    itens_para_cadastrar = [] # Lista vazia para garantir escopo

    try:
        login_navegacao.fazer_login(driver)
        
        # Precisa navegar até a tela de itens para consultar o que falta
        print("📍 Navegando até a tela de Itens para consulta...")
        
        # AQUI estava o erro: chamamos a função nova (Favoritos) para chegar na tela
        if not cadastro_item.navegar_via_favoritos(driver):
            print("❌ Falha ao navegar para tela de itens na Sessão 1.")
            driver.quit()
            return
        
        # Realiza a Consulta
        print("\n🔎 INICIANDO CONSULTA DE ITENS...")
        itens_para_cadastrar = consulta_item.buscar_itens_no_sistema(driver, lista_todos_itens)
        
        print("\n" + "="*50)
        print(f"📊 RESUMO DA TRIAGEM:")
        print(f"   ✅ Itens já no sistema: {len(lista_todos_itens) - len(itens_para_cadastrar)}")
        print(f"   ⚠️ Itens PARA CADASTRAR: {len(itens_para_cadastrar)}")
        print("="*50)

        # Se não tiver nada para cadastrar, encerra aqui
        if not itens_para_cadastrar:
            print("🎉 Nada a fazer! Todos os itens já existem.")
            driver.quit()
            return

        # RESOLVE OS NCMS (Ainda na Sessão 1)
        lista_ncms = list(set([item['ncm'] for item in itens_para_cadastrar]))
        
        if lista_ncms:
            print(f"\n🔧 Verificando {len(lista_ncms)} NCM(s) necessários...")
            # O cadastro_ncm gerencia a ida e volta para o site do Systax/Portal
            cadastro_ncm.processar_ncms(driver, lista_ncms)

    except Exception as e:
        print(f"\n❌ ERRO NA SESSÃO 1: {e}")
        driver.quit()
        return

    # ==============================================================================
    # 🛑 LIMPEZA (PONTO CRÍTICO)
    # ==============================================================================
    print("\n🛑 [FIM DA SESSÃO 1] FECHANDO NAVEGADOR PARA LIMPEZA...")
    driver.quit() # Fecha tudo
    time.sleep(3) # Pausa dramática para o Windows liberar a memória

    # ==============================================================================
    # 🟢 SESSÃO 2: CADASTRO DE ITENS (SESSÃO LIMPA)
    # ==============================================================================
    print("\n🔄 [SESSÃO 2] ABRINDO NOVO NAVEGADOR PARA CADASTRO DE ITENS...")
    driver = login_navegacao.iniciar_navegador()
    
    try:
        login_navegacao.fazer_login(driver)
        
        # Inicia o cadastro.
        # OBS: A função iniciar_cadastro JÁ CHAMA o 'navegar_via_favoritos' internamente.
        cadastro_item.iniciar_cadastro(driver, itens_para_cadastrar)

    except Exception as e:
        print(f"\n❌ ERRO NA SESSÃO 2: {e}")
    finally:
        print("\n🏁 Processo finalizado.")
        # driver.quit() # Opcional: fechar no final

if __name__ == "__main__":
    main()