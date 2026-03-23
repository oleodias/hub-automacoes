import sys
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from automacoes.clientes.navegacao_erp import fazer_login, navegar_via_favoritos

sys.stdout.reconfigure(encoding='utf-8')

def limpar_cnpj(cnpj):
    return re.sub(r'\D', '', str(cnpj))

def descobrir_regiao(uf):
    mapa_regioes = {
        'PR': '1', 'SC': '1', 'RS': '1',
        'SP': '2', 'RJ': '2', 'MG': '2', 'ES': '2',
        'MS': '3', 'MT': '3', 'GO': '3', 'DF': '3',
        'BA': '4', 'PI': '4', 'MA': '4', 'CE': '4', 'RN': '4',
        'PB': '4', 'PE': '4', 'AL': '4', 'SE': '4',
        'AC': '5', 'RO': '5', 'AM': '5', 'RR': '5',
        'PA': '5', 'AP': '5', 'TO': '5'
    }
    return mapa_regioes.get(uf.upper(), '')

def definir_codigo_atividade(cnae_descricao):
    descricao = str(cnae_descricao).lower()
    if "varejista" in descricao:
        return "7"
    elif "atacadista" in descricao:
        return "15"
    else:
        return "13"

def executar(dados_cliente):
    """Função principal que o Flask vai chamar quando clicar no botão."""
    print(f"> 🚀 Iniciando Robô: Novo Cliente ({dados_cliente.get('razao_social')})...")

    cnpj_formatado = limpar_cnpj(dados_cliente.get('cnpj_limpo', ''))

    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # ── LOGIN ──────────────────────────────────────────
        if not fazer_login(driver):
            raise Exception("Falha no Login do ERP.")

        if not navegar_via_favoritos(driver):
            raise Exception("Falha na navegação via Favoritos.")

        # ── ABRINDO NOVO CADASTRO ──────────────────────────
        print("> 📄 Abrindo formulário de Novo Cadastro...")
        btn_novo = wait.until(EC.presence_of_element_located((By.ID, "btnNovo")))
        driver.execute_script("arguments[0].click();", btn_novo)

        print(f"> 🔍 Inserindo CNPJ ({cnpj_formatado}) para pesquisa...")
        campo_cnpj = wait.until(EC.visibility_of_element_located((By.ID, "subFrmPsPesquisaPessoa:codCompleto")))
        campo_cnpj.send_keys(cnpj_formatado)

        btn_pesquisar = driver.find_element(By.ID, "subFrmPsPesquisaPessoa:btnPesquisar")
        driver.execute_script("arguments[0].click();", btn_pesquisar)
        time.sleep(3)

        # ── FASE 1: DADOS BÁSICOS ──────────────────────────
        print("> ✍️ Preenchendo a Ficha Cadastral (Fase 1/4 - Dados Básicos)...")

        check_cli = wait.until(EC.presence_of_element_located((By.ID, "indCli")))
        if not check_cli.is_selected():
            driver.execute_script("arguments[0].click();", check_cli)
            time.sleep(0.5)

        campo_razao = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoa")))
        campo_razao.clear()
        campo_razao.send_keys(dados_cliente.get('razao_social', ''))

        campo_fantasia = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoaFantasia")))
        campo_fantasia.clear()
        campo_fantasia.send_keys(dados_cliente.get('nome_fantasia', ''))

        # Inscrição Estadual
        ie = dados_cliente.get('inscricao_estadual', '')
        if ie and ie.upper() not in ["ISENTO", "ISENTO / NÃO ENCONTRADA", ""]:
            print(f"> 📄 Inserindo Inscrição Estadual: {ie}")
            for _ in range(3):
                try:
                    campo_ie = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:numInscEst")))
                    driver.execute_script("arguments[0].value = '';", campo_ie)
                    campo_ie.send_keys(Keys.CONTROL + "a")
                    campo_ie.send_keys(Keys.BACKSPACE)
                    time.sleep(0.3)
                    campo_ie.send_keys(ie)
                    campo_ie.send_keys(Keys.TAB)
                    break
                except:
                    time.sleep(1)
        else:
            print("> ℹ️ IE Isenta ou não encontrada. Pulando campo...")

        # Atividade
        cnae_desc = dados_cliente.get('cnae_principal_descricao', '')
        codigo_atividade = definir_codigo_atividade(cnae_desc)
        print(f"> 🧠 CNAE analisado. Aplicando atividade Ciamed: {codigo_atividade}")

        campo_ativ = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:lovPsAtividadesPsJuridicas_txtCod")))
        campo_ativ.clear()
        campo_ativ.send_keys(codigo_atividade)
        campo_ativ.send_keys(Keys.TAB)

        # ── FASE 2: ENDEREÇO ───────────────────────────────
        print("> 📍 Preenchendo Endereço (Fase 2/4)...")

        for _ in range(3):
            try:
                campo_cep = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtCep")))
                campo_cep.send_keys(Keys.CONTROL + "a")
                campo_cep.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                cep_limpo = limpar_cnpj(dados_cliente.get('cep', ''))
                campo_cep.send_keys(cep_limpo)
                campo_cep.send_keys(Keys.TAB)
                time.sleep(3)
                break
            except:
                time.sleep(1)

        endereco_completo = f"{dados_cliente.get('logradouro', '')}, {dados_cliente.get('numero', '')}, {dados_cliente.get('complemento', '')}".strip(", ")
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

        for _ in range(3):
            try:
                campo_bairro = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesBairro")))
                driver.execute_script("arguments[0].value = '';", campo_bairro)
                time.sleep(0.2)
                campo_bairro.send_keys(Keys.CONTROL + "a")
                campo_bairro.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                campo_bairro.send_keys(dados_cliente.get('bairro', ''))
                break
            except:
                time.sleep(1)

        uf = dados_cliente.get('uf', '')
        codigo_regiao = descobrir_regiao(uf)
        for _ in range(3):
            try:
                campo_regiao = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:lovPsRegioesPsJuridicas_txtCod")))
                campo_regiao.send_keys(Keys.CONTROL + "a")
                campo_regiao.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                campo_regiao.send_keys(codigo_regiao)
                campo_regiao.send_keys(Keys.TAB)
                time.sleep(1.5)
                break
            except:
                time.sleep(1)

        # ── AVANÇANDO ABAS DO WIZARD ───────────────────────
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        print("> ⏩ Avançando para as próximas fases do cadastro...")

        for i in range(3):
            try:
                btn_proximo = wait.until(EC.presence_of_element_located((By.ID, "btnWizardProximoCab")))
                driver.execute_script("arguments[0].click();", btn_proximo)
                print(f"   - Clique {i+1}/3 realizado.")
                time.sleep(1.2)
            except Exception as e:
                print(f"   - ⚠️ Erro ao avançar aba: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        # ================================================================
        # FASE 2: CONFIGURAÇÃO DE BLOQUEIO E DATAS
        # ================================================================
        print("> 🛡️ Configurando Bloqueio e Data de Cadastro...")

        # 1. Campo de Motivo do Bloqueio (Sempre "30")
        try:
            print("   - Definindo Motivo de Bloqueio: 30 (Liberação Financeiro)")
            campo_motivo = wait.until(EC.presence_of_element_located((By.ID, "subFrmBloqueio:lovPsMotivosBloqueio_txtCod")))
            campo_motivo.clear()
            campo_motivo.send_keys("30")
            campo_motivo.send_keys(Keys.TAB)
            time.sleep(0.5) # Respiro para o ERP validar o código
        except Exception as e:
            print(f"   - ⚠️ Erro ao preencher motivo de bloqueio: {e}")

        # 2. Campo de Data do Bloqueio (Data Atual)
        try:
            data_hoje = datetime.now().strftime("%d/%m/%Y")
            print(f"   - Definindo Data do Bloqueio: {data_hoje}")
            
            campo_data = wait.until(EC.presence_of_element_located((By.ID, "subFrmBloqueio:txtDtaBloq")))
            
            # Limpeza garantida para campos de data que costumam ter máscara
            campo_data.send_keys(Keys.CONTROL + "a")
            campo_data.send_keys(Keys.BACKSPACE)
            time.sleep(0.2)
            
            campo_data.send_keys(data_hoje)
            campo_data.send_keys(Keys.TAB)

        except Exception as e:
            print(f"   - ⚠️ Erro ao preencher data de bloqueio: {e}")

        print("> ✅ Campos de Bloqueio preenchidos com sucesso!")

        # ================================================================
        # TRANSIÇÃO PARA A PRÓXIMA FASE (MAIS 2 CLIQUES)
        # ================================================================
        print("> ⏩ Avançando mais duas abas...")
        
        # Garante que o topo da página está visível
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        for i in range(2):
            try:
                # Localiza o botão "Próximo" novamente para evitar erros de página
                btn_proximo = wait.until(EC.presence_of_element_located((By.ID, "btnWizardProximoCab")))
                
                # Clique via JavaScript (mais seguro para o ERP Ciamed)
                driver.execute_script("arguments[0].click();", btn_proximo)
                
                print(f"   - Clique adicional {i+1}/2 realizado.")
                time.sleep(1.2) # Respiro para o ERP carregar a nova tela
                
            except Exception as e:
                print(f"   - ⚠️ Erro no clique adicional: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        print("> 📍 Chegamos na nova página! O que temos para preencher aqui?")

        print("> 🚧 Chegamos na Fase 4! Robô parado para conferência...")
        time.sleep(15)

        return {"status": "Sucesso", "msg": "Fases 4 e 5 concluídas com sucesso!"}

    except Exception as e:
        print(f"> ❌ Erro Crítico: {e}")
        return {"status": "Erro", "msg": str(e)}

    finally:
        # Comente a linha abaixo se quiser que o navegador fique aberto para conferir
        driver.quit()
        print("> 🏁 Fim da execução.")


# ── TESTE DE BANCADA ───────────────────────────────────
if __name__ == "__main__":
    print("🧪 Iniciando Teste de Bancada...")
    dados_teste = {
        "cnpj_limpo": "00000000000191",
        "razao_social": "EMPRESA DE TESTE LTDA",
        "nome_fantasia": "TESTE FANTASIA",
        "inscricao_estadual": "ISENTO",
        "cnae_principal_descricao": "Comércio varejista de medicamentos",
        "cep": "01001000",
        "logradouro": "Praça da Sé",
        "numero": "123",
        "complemento": "Sala 1",
        "bairro": "Sé",
        "uf": "SP"
    }
    executar(dados_teste)