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

        # ================================================================
        # FASE 3: PREENCHIMENTO DA GRID DE CONTATOS (LÓGICA EXATA)
        # ================================================================
        print("> 👥 Iniciando o cadastro de contatos na grid...")

        email_nfe = dados_cliente.get('email_xml', '')
        contatos_da_tela = dados_cliente.get('contatos_da_tela', [])

        # 1. Contatos OBRIGATÓRIOS
        contatos_para_cadastrar = [
            {"nome": "ENVIO XML TI", "email_xml": "xmlcliente@ciamedrs.com.br", "email_danfe": "xmlcliente@ciamedrs.com.br"},
            {"nome": "ENVIO NFE ELETRONICA", "email_xml": email_nfe, "email_danfe": email_nfe}
        ]

        # 2. A ÚNICA LÓGICA QUE IMPORTA: Filtra os contatos da tela e aplica as regras
        for c in contatos_da_tela:
            # Pula a linha se estiver totalmente em branco na página web
            if not c['nome'] and not c['email'] and not c['tel']:
                continue
            
            # REGRA DO FINANCEIRO (Código 50)
            if c.get('codigo') == "50":
                c['nome'] = str(c['nome']).strip() + " - ENVIO BOLETO"
                c['check_boleto'] = True
                
            # REGRA DO FARMACÊUTICO (Código 20)
            elif c.get('codigo') == "20":
                c['check_docs'] = True

            contatos_para_cadastrar.append(c)

        # 3. O Loop Trator: Digitando no ERP
        for c in contatos_para_cadastrar:
            print(f"   - ➕ Cadastrando: {c.get('nome')}")
            try:
                # Clica Adicionar
                btn_add = wait.until(EC.element_to_be_clickable((By.ID, "btnAdicionar_Contatos")))
                driver.execute_script("arguments[0].click();", btn_add)
                time.sleep(1.5)

                # Preenche NOME 
                campo_nome = wait.until(EC.presence_of_element_located((By.ID, "subFrm_Contatos:contatoDesContato")))
                campo_nome.clear()
                campo_nome.send_keys(c.get('nome', ''))

                # Preenche Função
                if c.get('codigo'):
                    campo_funcao = driver.find_element(By.ID, "subFrm_Contatos:contatoLovPsFuncoes_txtCod")
                    campo_funcao.clear()
                    campo_funcao.send_keys(c.get('codigo'))
                    campo_funcao.send_keys(Keys.TAB)
                    time.sleep(0.5)

                # Preenche Telefone e Email
                if c.get('tel'):
                    driver.find_element(By.ID, "subFrm_Contatos:contatoNumFone").send_keys(c.get('tel'))
                if c.get('email'):
                    driver.find_element(By.ID, "subFrm_Contatos:contatoDesEmail").send_keys(c.get('email'))

                # Preenche Emails Especiais (XML/DANFE)
                if c.get('email_xml'):
                    driver.find_element(By.ID, "subFrm_Contatos:contatoDesEmailXML").send_keys(c.get('email_xml'))
                if c.get('email_danfe'):
                    driver.find_element(By.ID, "subFrm_Contatos:contatoDesEmailDanfe").send_keys(c.get('email_danfe'))

                # MARCA AS CAIXINHAS (A Lógica Exigida)
                if c.get('check_boleto'):
                    chk_boleto = driver.find_element(By.ID, "subFrm_Contatos:chkIndEnviarCotacao")
                    if not chk_boleto.is_selected():
                        driver.execute_script("arguments[0].click();", chk_boleto)

                if c.get('check_docs'):
                    chk_docs = driver.find_element(By.ID, "subFrm_Contatos:chkIndEmailDocs")
                    if not chk_docs.is_selected():
                        driver.execute_script("arguments[0].click();", chk_docs)

                # Clica em APLICAR
                btn_aplicar = driver.find_element(By.ID, "subFrm_Contatos:btnAplicar_Contatos")
                driver.execute_script("arguments[0].click();", btn_aplicar)
                time.sleep(2)
                
                print("✅ Salvo!")

            except Exception as e:
                print(f"      ⚠️ Erro ao cadastrar {c.get('nome')}: {e}")
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)

        print("> 🏁 Todos os contatos adicionados com sucesso!")

        # ================================================================
        # TRANSIÇÃO PARA A PRÓXIMA FASE (MAIS 1 CLIQUES)
        # ================================================================
        print("> ⏩ Avançando mais duas abas...")
        
        # Garante que o topo da página está visível
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        for i in range(1):
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

        # ================================================================
        # FASE 4: ABA DE COMENTÁRIOS (REGRA DE FATURAMENTO)
        # ================================================================
        print("> 💬 Verificando regra de faturamento para comentários...")
        
        # Puxa a regra de faturamento que veio da tela web (ex: "Caixa" ou "Unitário")
        # Colocamos .upper() para não ter problema com letras maiúsculas/minúsculas
        regra_faturamento = str(dados_cliente.get("regra_faturamento", "")).upper()

        # O robô precisa clicar na aba "Comentários" antes de tudo!
        # Substitua 'ID_DA_ABA_COMENTARIOS' pelo ID real da aba lá em cima no menu do ERP
        # aba_comentarios = wait.until(EC.element_to_be_clickable((By.ID, "ID_DA_ABA_COMENTARIOS")))
        # driver.execute_script("arguments[0].click();", aba_comentarios)
        # time.sleep(1)

        if "CAIXA" in regra_faturamento:
            print("   - 📦 Regra: CAIXA. Adicionando comentário...")
            try:
                # 1. Clicar no botão Adicionar
                btn_add_comentario = wait.until(EC.element_to_be_clickable((By.ID, "btnAdicionar_Comentarios")))
                driver.execute_script("arguments[0].click();", btn_add_comentario)
                time.sleep(1.5) # Tempo para a janela flutuante abrir

                # 2. Escrever o texto no campo
                campo_comentario = wait.until(EC.presence_of_element_located((By.ID, "subFrm_Comentarios:comentarioDescricao")))
                campo_comentario.clear()
                campo_comentario.send_keys("FATURAR EM CAIXA!")

                # 3. Clicar em Aplicar
                btn_aplicar_comentario = driver.find_element(By.ID, "subFrm_Comentarios:btnAplicar_Comentarios")
                driver.execute_script("arguments[0].click();", btn_aplicar_comentario)
                time.sleep(1.5) # Esperar a grid salvar e fechar a janela
                
                print("      ✅ Comentário 'FATURAR EM CAIXA!' salvo com sucesso!")

            except Exception as e:
                print(f"      ⚠️ Erro ao adicionar comentário: {e}")
                # Dá um ESC para fechar a janelinha caso dê erro e não travar o robô
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
        else:
            print(f" - 🔄 Regra: {regra_faturamento if regra_faturamento else 'UNITÁRIO'}. Pulando adição de comentários.")

        # ================================================================
        # TRANSIÇÃO PARA A PRÓXIMA FASE (MAIS 1 CLIQUES)
        # ================================================================
        print("> ⏩ Avançando mais duas abas...")
        
        # Garante que o topo da página está visível
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        for i in range(1):
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

        # ================================================================
        # FASE 5: PREENCHIMENTO DA ABA DE TELEFONES
        # ================================================================
        print("> 📞 Cadastrando o telefone principal da empresa...")

        # Puxa o telefone que veio do pacote de dados (da API)
        telefone_empresa = dados_cliente.get('telefone_empresa', '')

        # O robô só vai tentar preencher se a API realmente tiver encontrado um telefone
        if telefone_empresa:
            try:
                # 1. Clicar no botão Adicionar
                btn_add_tel = wait.until(EC.element_to_be_clickable((By.ID, "btnAdicionar_telefones")))
                driver.execute_script("arguments[0].click();", btn_add_tel)
                time.sleep(1.5) # Espera a janelinha abrir

                # 2. Preencher a Sequência ("1")
                campo_seq = wait.until(EC.presence_of_element_located((By.ID, "subFrm_telefones:telefonesNumSeq")))
                campo_seq.clear()
                campo_seq.send_keys("1")

                # 3. Preencher a Descrição ("TELEFONE DA EMPRESA")
                campo_desc = driver.find_element(By.ID, "subFrm_telefones:txtTelefonesDesFone")
                campo_desc.clear()
                campo_desc.send_keys("TELEFONE DA EMPRESA")

                # 4. Preencher o Número do Telefone
                campo_num = driver.find_element(By.ID, "subFrm_telefones:telefonesNumFone")
                campo_num.clear()
                campo_num.send_keys(telefone_empresa)

                # 5. Clicar em Aplicar
                btn_aplicar_tel = driver.find_element(By.ID, "subFrm_telefones:btnAplicar_telefones")
                driver.execute_script("arguments[0].click();", btn_aplicar_tel)
                time.sleep(2) # Tempo para a grid salvar e atualizar
                
                print(f"      ✅ Telefone ({telefone_empresa}) cadastrado com sucesso!")

            except Exception as e:
                print(f"      ⚠️ Erro ao cadastrar o telefone: {e}")
                # Dá um ESC para fechar a janela caso algo dê errado
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
        else:
            print("   ⚠️ Telefone não informado pela API. Pulando o cadastro de telefone.")

        # ================================================================
        # TRANSIÇÃO PARA A PRÓXIMA FASE (MAIS 1 CLIQUES)
        # ================================================================
        print("> ⏩ Avançando mais duas abas...")
        
        # Garante que o topo da página está visível
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        for i in range(1):
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

        print("> 🚧 Chegamos na Fase! Robô parado para conferência...")
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