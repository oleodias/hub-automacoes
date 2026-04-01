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
from selenium.webdriver.support.ui import Select

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

        # Nome Fantasia (Com Fallback para Razão Social e trava de 20 caracteres do ERP)
        campo_fantasia = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoaFantasia")))
        campo_fantasia.clear()
        
        # Tenta pegar o nome fantasia, se vier vazio ou nulo, pega a Razão Social
        nome_fantasia_api = dados_cliente.get('nome_fantasia', '')
        if not nome_fantasia_api:
            nome_fantasia_api = dados_cliente.get('razao_social', '')
            
        nome_fantasia_cortado = str(nome_fantasia_api)[:20]
        campo_fantasia.send_keys(nome_fantasia_cortado)

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

        for _ in range(3):
            try:
                campo_ativ = wait.until(EC.element_to_be_clickable((By.ID, "subFrmPsJuridicas:lovPsAtividadesPsJuridicas_txtCod")))
                driver.execute_script("arguments[0].focus(); arguments[0].click();", campo_ativ)
                time.sleep(0.5)

                campo_ativ.send_keys(Keys.CONTROL + "a")
                campo_ativ.send_keys(Keys.BACKSPACE)
                time.sleep(0.3)

                campo_ativ.send_keys(codigo_atividade)
                campo_ativ.send_keys(Keys.TAB)
                
                print("   - ⏳ Sistema processando a atividade... Aguardando.")
                time.sleep(3.5) # Aumentamos esse tempo para o ERP respirar e sair do loading!
                break
            except Exception as e:
                print("   - ⚠️ Falha ao digitar atividade. Tentando novamente...")
                time.sleep(1)

        # ── FASE 2: ENDEREÇO ───────────────────────────────
        print("> 📍 Preenchendo Endereço (Fase 2/4)...")

        # --- CEP ---
        for _ in range(4): # Aumentei para 4 tentativas para garantir
            try:
                campo_cep = wait.until(EC.element_to_be_clickable((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtCep")))
                
                driver.execute_script("arguments[0].focus(); arguments[0].click();", campo_cep)
                time.sleep(0.5)

                campo_cep.send_keys(Keys.CONTROL + "a")
                campo_cep.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                
                cep_limpo = limpar_cnpj(dados_cliente.get('cep', ''))
                campo_cep.send_keys(cep_limpo)
                campo_cep.send_keys(Keys.TAB)
                
                print("   - ⏳ Sistema processando o CEP... Aguardando.")
                time.sleep(2) # Respiro para o ERP puxar rua e bairro sozinho
                break
            except Exception as e:
                print("   - ⚠️ CEP ainda não está clicável. Aguardando ERP liberar a tela...")
                time.sleep(2)

        # ================================================================
        # LÓGICA INTELIGENTE DE ENDEREÇO (VÁLVULA DE ESCAPE - 50 CARACTERES)
        # ================================================================
        print("   - 📏 Calculando tamanho do endereço...")
        
        logradouro = str(dados_cliente.get('logradouro', '')).strip()
        numero = str(dados_cliente.get('numero', '')).strip()
        complemento = str(dados_cliente.get('complemento', '')).strip()

        # Montando o texto completo ideal
        texto_completo = logradouro
        if numero:
            texto_completo += f", {numero}"
        if complemento:
            texto_completo += f" - {complemento}"

        endereco_principal = ""
        texto_referencia = ""

        # PLANO A: Cabe tudo!
        if len(texto_completo) <= 50:
            endereco_principal = texto_completo
            print(f"      ✅ Endereço curto ({len(texto_completo)} chars). Caberá tudo no campo principal.")
        
        # PLANO B e C: Estourou o limite!
        else:
            print(f"      ⚠️ Endereço longo ({len(texto_completo)} chars). Acionando válvula de escape...")
            texto_sem_comp = logradouro
            if numero:
                texto_sem_comp += f", {numero}"
            
            # PLANO B: Tirar o complemento resolve?
            if len(texto_sem_comp) <= 50:
                endereco_principal = texto_sem_comp
                texto_referencia = complemento
                print("      🔄 Complemento movido para o campo de Referência.")
            
            # PLANO C: Logradouro é gigante! (Caso Extremo)
            else:
                endereco_principal = logradouro[:50] # Poda a rua nos 50 cravados
                texto_ref_temp = f"Num: {numero}"
                if complemento:
                    texto_ref_temp += f" - {complemento}"
                texto_referencia = texto_ref_temp[:50] # Garante que referência também não estoure
                print("      🚨 Rua muito longa! Logradouro isolado. Num e Comp movidos para Referência.")

        # --- Digitando o Endereço Principal ---
        for _ in range(3):
            try:
                campo_endereco = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesEndereco")))
                campo_endereco.send_keys(Keys.CONTROL + "a")
                campo_endereco.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                campo_endereco.send_keys(endereco_principal)
                break
            except:
                time.sleep(1)

        # --- Digitando a Referência (Válvula de Escape) ---
        if texto_referencia:
            for _ in range(3):
                try:
                    campo_ref = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesReferencia")))
                    campo_ref.send_keys(Keys.CONTROL + "a")
                    campo_ref.send_keys(Keys.BACKSPACE)
                    time.sleep(0.5)
                    campo_ref.send_keys(texto_referencia)
                    break
                except:
                    time.sleep(1)

        # --- Digitando o Bairro ---
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
        
        # 🛡️ TRAVA INTELIGENTE PARA O RIO GRANDE DO SUL
        if uf.upper() == 'RS':
            print("   - ℹ️ Estado é RS. O sistema preenche a região automaticamente! Pulando campo...")
        else:
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
            {"nome": "SIMFRETE", "email_xml": "ciamed@simfrete.com", "email_danfe": "ciamed@simfrete.com"},
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
                
            # REGRA DO RESPONSÁVEL TÉCNICO (Código 39)
            elif c.get('codigo') == "39":
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

        # ================================================================
        # FASE 6: PREENCHIMENTO DA ABA DE OBSERVAÇÕES
        # ================================================================
        print("> 📝 Analisando e adicionando Observações...")

        # 1. Criando a "Lista de Tarefas" do robô
        observacoes_para_adicionar = []

        # -- OBSERVAÇÃO 1: Fixo (Roche) --
        observacoes_para_adicionar.append({
            "codigo": "300",
            "texto": "FATURISTA: QUANDO ITEM ROCHE ENVIAR LAUDO."
        })

        # -- OBSERVAÇÃO 2: CNAE Limpo --
        cnae_cru = str(dados_cliente.get('cnae_principal_descricao', ''))
        
        # Lógica para limpar os números (ex: "4771-7/02 - Comércio" vira "Comércio")
        if " - " in cnae_cru:
            cnae_limpo = cnae_cru.split(" - ", 1)[1].strip().upper()
        else:
            import re
            cnae_limpo = re.sub(r'^[\d\.\-\/\s]+', '', cnae_cru).strip().upper()

        if cnae_limpo:
            observacoes_para_adicionar.append({
                "codigo": "150",
                "texto": cnae_limpo
            })

        # -- OBSERVAÇÃO 3: Regra de Faturamento (Condicional) --
        regra_faturamento = str(dados_cliente.get("regra_faturamento", "")).upper()
        if "CAIXA" in regra_faturamento:
            observacoes_para_adicionar.append({
                "codigo": "200",
                "texto": "OBRIGATÓRIO FATURAR PEDIDO EM CAIXA!"
            })
        else:
            print("   - ℹ️ Regra Unitário detectada. Ignorando observação de Caixa.")

        # 2. O Loop Trator: O Ritual de Inserção
        for obs in observacoes_para_adicionar:
            print(f"   - ➕ Inserindo Observação [{obs['codigo']}]: {obs['texto'][:30]}...")
            try:
                # PASSO A: Clicar em Adicionar
                btn_add_obs = wait.until(EC.element_to_be_clickable((By.ID, "btnAdicionarObservacoes")))
                driver.execute_script("arguments[0].click();", btn_add_obs)
                time.sleep(1.5) # Espera a janela de cadastro abrir

                # PASSO B: Preencher Código e dar TAB
                campo_cod_obs = wait.until(EC.presence_of_element_located((By.ID, "subFrm_observacoes:lovCodTipoObservacao_txtCod")))
                campo_cod_obs.clear()
                campo_cod_obs.send_keys(obs['codigo'])
                campo_cod_obs.send_keys(Keys.TAB)
                time.sleep(1) # Respiro para o ERP carregar a descrição do código

                # PASSO C: Forçar clique na área de texto e digitar
                campo_txt_obs = wait.until(EC.presence_of_element_located((By.ID, "subFrm_observacoes:txtObservacao")))
                
                # O TRUQUE DO JS AQUI: Foca e clica antes de enviar o texto
                driver.execute_script("arguments[0].focus(); arguments[0].click();", campo_txt_obs)
                time.sleep(0.5)
                
                campo_txt_obs.clear()
                campo_txt_obs.send_keys(obs['texto'])

                # PASSO D: Clicar em APLICAR para concluir esta observação
                btn_aplicar_obs = driver.find_element(By.ID, "subFrm_observacoes:btnAplicar_observacoes")
                driver.execute_script("arguments[0].click();", btn_aplicar_obs)
                
                # PASSO E: Esperar o ERP processar antes de recomeçar o loop!
                print("      ⏳ Aguardando sistema salvar...")
                time.sleep(1.8) # Tempo fundamental para a grid atualizar
                
                print("      ✅ Observação salva com sucesso!")

            except Exception as e:
                print(f"      ⚠️ Erro ao cadastrar observação {obs['codigo']}: {e}")
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1.5)

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
                
                print(f"   - Clique adicional {i+1}/1 realizado.")
                time.sleep(0.8) # Respiro para o ERP carregar a nova tela
                
            except Exception as e:
                print(f"   - ⚠️ Erro no clique adicional: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        print("> 🚧 Chegamos na Fase! Robô parado para conferência...")
        time.sleep(0.7)

        

        # ================================================================
        # FASE 7: PREENCHIMENTO DA ABA CLIENTE (OPERAÇÃO E CONSUMIDOR)
        # ================================================================
        print("> 🏢 Analisando regras para Aba Cliente...")

        # O robô precisa clicar na aba "CLIENTE" lá em cima no menu do ERP
        # (Lembre de colocar o ID correto do botão da aba aqui se não for esse)
        # btn_aba_cliente = wait.until(EC.element_to_be_clickable((By.ID, "ID_DA_ABA_CLIENTE")))
        # driver.execute_script("arguments[0].click();", btn_aba_cliente)
        # time.sleep(1.5)

        cnae_desc = str(dados_cliente.get('cnae_principal_descricao', '')).lower()
        tem_cebas = str(dados_cliente.get('tem_cebas', ''))

        codigo_operacao = ""
        valor_consumidor = ""

        # A Lógica do CEBAS
        if "varejista" in cnae_desc:
            print("   - Regra: VAREJISTA detectado.")
            codigo_operacao = "223"
            valor_consumidor = "1" # Não
        elif "atacadista" in cnae_desc:
            print("   - Regra: ATACADISTA detectado.")
            codigo_operacao = "224"
            valor_consumidor = "1" # Não
        else:
            print("   - Regra: OUTROS. Verificando CEBAS...")
            if tem_cebas == "SIM":
                print("   - CEBAS: ATIVO.")
                codigo_operacao = "240"
                valor_consumidor = "0" # Sim
            else:
                print("   - CEBAS: INATIVO.")
                codigo_operacao = "220"
                valor_consumidor = "0" # Sim

        try:
            # 1. Preenchendo Operação
            print(f"   - ✍️ Preenchendo Operação: {codigo_operacao}")
            campo_oper = wait.until(EC.presence_of_element_located((By.ID, "subFrmPsClientes:lovCodOper_txtCod")))
            campo_oper.clear()
            campo_oper.send_keys(codigo_operacao)
            campo_oper.send_keys(Keys.TAB)
            time.sleep(1.5)

            # 2. Selecionando o Consumidor Final
            print(f"   - 🖱️ Marcando Consumidor Final: {'Não' if valor_consumidor == '1' else 'Sim'}")
            dropdown_consumidor = Select(wait.until(EC.presence_of_element_located((By.ID, "subFrmPsClientes:cboIndConsumidor"))))
            dropdown_consumidor.select_by_value(valor_consumidor)
            time.sleep(1)

            print("      ✅ Dados da aba Cliente preenchidos com sucesso!")

        except Exception as e:
            print(f"      ⚠️ Erro ao preencher Aba Cliente: {e}")

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
                time.sleep(0.8) # Respiro para o ERP carregar a nova tela
                
            except Exception as e:
                print(f"   - ⚠️ Erro no clique adicional: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        # ================================================================
        # FASE 8: PREENCHIMENTO DA ABA DE REPRESENTANTES
        # ================================================================
        print("> 🤝 Adicionando Representante...")

        # Puxa o nome do representante que veio da ficha (célula BD248)
        representante = str(dados_cliente.get('representante', '')).strip()

        # Só tenta adicionar se realmente existir um representante na ficha
        if representante:
            try:
                # 1. Clicar no botão Adicionar
                btn_add_rep = wait.until(EC.element_to_be_clickable((By.ID, "btnAdicionar_clientesRep")))
                driver.execute_script("arguments[0].click();", btn_add_rep)
                time.sleep(1.5) # Espera a janelinha abrir

                # 2. Preencher o nome do representante e dar TAB
                print(f"   - ✍️ Preenchendo nome: {representante}")
                campo_rep = wait.until(EC.presence_of_element_located((By.ID, "subFrm_clientesRep:lovCodPessoaRep_txtDesc")))
                campo_rep.clear()
                campo_rep.send_keys(representante)
                
                # Dá o TAB para o ERP Ciamed puxar o cadastro interno do representante
                campo_rep.send_keys(Keys.TAB)
                time.sleep(1.5) # Respiro fundamental para o sistema autocompletar o campo

                # 3. Clicar em Aplicar
                btn_aplicar_rep = driver.find_element(By.ID, "subFrm_clientesRep:btnAplicar_clientesRep")
                driver.execute_script("arguments[0].click();", btn_aplicar_rep)
                time.sleep(1.2) # Tempo para a grid salvar e atualizar
                
                print("      ✅ Representante salvo com sucesso!")

            except Exception as e:
                print(f"      ⚠️ Erro ao adicionar representante: {e}")
                # Dá um ESC para fechar a janelinha caso o ERP não encontre o nome
                webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
        else:
            print("   - ℹ️ Nenhum representante informado na ficha. Pulando esta etapa.")

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
                time.sleep(0.8) # Respiro para o ERP carregar a nova tela
                
            except Exception as e:
                print(f"   - ⚠️ Erro no clique adicional: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        # ================================================================
        # FASE 9: ABA COMPLEMENTO (DADOS COMPLEMENTARES)
        # ================================================================
        print("> 🧩 Preenchendo a Aba de Complementos...")

        try:
            # 1. Forçar a expansão da aba clicando direto no título via JS
            print("   - 🔽 Expandindo a aba de complementos (clicando no título)...")
            
            # Usamos o XPath para caçar exatamente o <span> que tem esse texto
            titulo_expandir = wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='Informações complementares - Complementar']")))
            
            # A martelada do clique ninja direto no texto!
            driver.execute_script("arguments[0].click();", titulo_expandir)
            
            time.sleep(1.5) # Tempo essencial para a animação de "descer" a aba terminar

            # ... (o resto do código continua igual, indo para a Caixinha 1 e 2) ...

            # 2. Preencher a Caixinha 1 (Opção Fixa: SIM - SIM)
            print("   - ✍️ Preenchendo opção fixa (SIM - SIM)...")
            dropdown_fixo = Select(wait.until(EC.presence_of_element_located((By.ID, "subFrmColunasCompl:txtVlrColuna_3"))))
            dropdown_fixo.select_by_value("1") # 1 = SIM - SIM
            time.sleep(0.5)

            # 3. Preencher a Caixinha 2 (Opção Dinâmica: Captação do HTML)
            forma_captacao = str(dados_cliente.get('forma_captacao', ''))
            
            if forma_captacao:
                print(f"   - 🎯 Preenchendo forma de captação (Código: {forma_captacao})...")
                dropdown_dinamico = Select(wait.until(EC.presence_of_element_located((By.ID, "subFrmColunasCompl:txtVlrColuna_6"))))
                dropdown_dinamico.select_by_value(forma_captacao)
                time.sleep(0.5)
            else:
                print("   - ⚠️ Atenção: Forma de captação não foi recebida do site!")

            print("      ✅ Aba de Complementos preenchida com sucesso!")

        except Exception as e:
            print(f"      ⚠️ Erro ao preencher Aba de Complementos: {e}")

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
                
                print(f"   - Clique adicional {i+1}/1 realizado.")
                time.sleep(0.8) # Respiro para o ERP carregar a nova tela
                
            except Exception as e:
                print(f"   - ⚠️ Erro no clique adicional: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        print("> 🚧 Chegamos na Fase! Robô parado para conferência...")
        time.sleep(0.7)

        # ================================================================
        # FASE 10: ABA MÁSCARAS (A LÓGICA PURA DO VENDEDOR)
        # ================================================================
        print("> 🎭 Preenchendo Aba de Máscaras (Modo Padrão Simples)...")

        # --- Ação 1: Código CNAE ---
        print("   - ✍️ Preenchendo [Pessoas - Codigo CNAE]...")
        try:
            for _ in range(3):
                try:
                    xpath_cnae = "//td[contains(., 'Pessoas - Codigo CNAE')]/a[contains(@class, 'OraLink')]"
                    link_cnae = wait.until(EC.presence_of_element_located((By.XPATH, xpath_cnae)))
                    driver.execute_script("arguments[0].click();", link_cnae)
                    time.sleep(1.5) 
                    break
                except:
                    time.sleep(1)

            # Pulo para o Iframe
            iframe_cnae = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "af_dialog_content")))
            driver.switch_to.frame(iframe_cnae)
            time.sleep(1.5) 

            # Limpar e formatar o CNAE
            cnae_cru = str(dados_cliente.get('cnae_principal_descricao', ''))
            if " - " in cnae_cru:
                cnae_numeros = cnae_cru.split(" - ")[0]
            else:
                cnae_numeros = cnae_cru
            import re
            cnae_apenas_digitos = re.sub(r'\D', '', cnae_numeros)

            # LÓGICA DO VENDEDOR: Clica, Apaga, Digita, TAB
            campo_cnae = wait.until(EC.element_to_be_clickable((By.ID, "txtVlr_0")))
            campo_cnae.click()
            time.sleep(0.5)
            campo_cnae.send_keys(Keys.CONTROL + "a")
            campo_cnae.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            # Aqui vamos injetar de forma limpa
            campo_cnae.send_keys(cnae_apenas_digitos)
            time.sleep(0.5)
            campo_cnae.send_keys(Keys.TAB)
            time.sleep(1) 

            # Gravar
            btn_gravar = wait.until(EC.element_to_be_clickable((By.ID, "btnGravar")))
            btn_gravar.click()
            time.sleep(2) 
            
            driver.switch_to.default_content()
            time.sleep(1) 
            print(f"      ✅ CNAE [{cnae_apenas_digitos}] salvo!")
            
        except Exception as e:
            print(f"      ⚠️ Erro ao preencher CNAE: {e}")
            # Se deu erro, clica em Fechar para não bugar a próxima janela!
            try:
                btn_fechar = driver.find_element(By.ID, "btnFechar")
                btn_fechar.click()
                time.sleep(1)
            except:
                pass
            driver.switch_to.default_content() 


        # --- Ação 2: Tipos Clientes ---
        print("   - ✍️ Preenchendo [Pessoas - Tipos Clientes]...")
        try:
            for _ in range(3):
                try:
                    xpath_tipos = "//td[contains(., 'Pessoas - Tipos Clientes')]/a[contains(@class, 'OraLink')]"
                    link_tipos = wait.until(EC.presence_of_element_located((By.XPATH, xpath_tipos)))
                    driver.execute_script("arguments[0].click();", link_tipos)
                    time.sleep(1.5)
                    break
                except:
                    time.sleep(1)

            # Pulo para o Iframe
            iframe_tipos = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "af_dialog_content")))
            driver.switch_to.frame(iframe_tipos)
            time.sleep(1.5)

            # LÓGICA DO VENDEDOR
            campo_tipos = wait.until(EC.element_to_be_clickable((By.ID, "lovNiveis_0_txtCod")))
            campo_tipos.click()
            time.sleep(0.5)
            campo_tipos.send_keys(Keys.CONTROL + "a")
            campo_tipos.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            campo_tipos.send_keys("10")
            time.sleep(0.5)
            campo_tipos.send_keys(Keys.TAB)
            time.sleep(1)

            # Gravar
            btn_gravar = wait.until(EC.element_to_be_clickable((By.ID, "btnGravar")))
            btn_gravar.click()
            time.sleep(2)
            
            driver.switch_to.default_content()
            time.sleep(1)
            print("      ✅ Tipo Cliente [10] salvo!")
            
        except Exception as e:
            print(f"      ⚠️ Erro ao preencher Tipo Cliente: {e}")
            try:
                btn_fechar = driver.find_element(By.ID, "btnFechar")
                btn_fechar.click()
                time.sleep(1)
            except:
                pass
            driver.switch_to.default_content()


        # --- Ação 3: Vendedor ---
        print("   - ✍️ Preenchendo [VENDEDOR]...")
        vendedor = str(dados_cliente.get('vendedor', '')).strip()
        if vendedor:
            try:
                for _ in range(3):
                    try:
                        xpath_vendedor = "//td[contains(., 'VENDEDOR')]/a[contains(@class, 'OraLink')]"
                        link_vendedor = wait.until(EC.presence_of_element_located((By.XPATH, xpath_vendedor)))
                        driver.execute_script("arguments[0].click();", link_vendedor)
                        time.sleep(1.5)
                        break
                    except:
                        time.sleep(1)

                # Pulo para o Iframe
                iframe_vendedor = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "af_dialog_content")))
                driver.switch_to.frame(iframe_vendedor)
                time.sleep(1.5)

                # LÓGICA DO VENDEDOR (A Original!)
                campo_vendedor = wait.until(EC.element_to_be_clickable((By.ID, "txtVlr_0")))
                campo_vendedor.click()
                time.sleep(0.5)
                campo_vendedor.send_keys(Keys.CONTROL + "a")
                campo_vendedor.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                
                campo_vendedor.send_keys(vendedor)
                time.sleep(0.5)
                campo_vendedor.send_keys(Keys.TAB)
                time.sleep(1)

                # Gravar
                btn_gravar = wait.until(EC.element_to_be_clickable((By.ID, "btnGravar")))
                btn_gravar.click()
                time.sleep(2)
                
                driver.switch_to.default_content()
                time.sleep(1)
                print(f"      ✅ Vendedor [{vendedor}] salvo!")
                
            except Exception as e:
                print(f"      ⚠️ Erro ao preencher Vendedor: {e}")
                try:
                    btn_fechar = driver.find_element(By.ID, "btnFechar")
                    btn_fechar.click()
                    time.sleep(1)
                except:
                    pass
                driver.switch_to.default_content()
        else:
            print("   - ℹ️ Nenhum vendedor informado na ficha. Pulando etapa.")

        # ================================================================
        # TRANSIÇÃO PARA A PRÓXIMA FASE (MAIS 3 CLIQUES)
        # ================================================================
        print("> ⏩ Avançando mais duas abas...")
        
        # Garante que o topo da página está visível
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        for i in range(3):
            try:
                # Localiza o botão "Próximo" novamente para evitar erros de página
                btn_proximo = wait.until(EC.presence_of_element_located((By.ID, "btnWizardProximoCab")))
                
                # Clique via JavaScript (mais seguro para o ERP Ciamed)
                driver.execute_script("arguments[0].click();", btn_proximo)
                
                print(f"   - Clique adicional {i+1}/3 realizado.")
                time.sleep(0.8) # Respiro para o ERP carregar a nova tela
                
            except Exception as e:
                print(f"   - ⚠️ Erro no clique adicional: {e}")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

        # ================================================================
        # FASE FINAL: GRAVAR CADASTRO E CAPTURAR PROTOCOLO
        # ================================================================
        print("> 🏁 Reta final: Salvando o cadastro do cliente...")

        try:
            # 1. Clicar no botão principal de Gravar (O botão verde gigante)
            btn_gravar_final = wait.until(EC.presence_of_element_located((By.ID, "btnCrudGravar")))
            driver.execute_script("arguments[0].click();", btn_gravar_final)
            print("   - 💾 Botão Gravar clicado! Aguardando o ERP processar (isso pode levar alguns segundos)...")

            # 2. Aguardar e capturar o Número do Protocolo
            espera_longa = WebDriverWait(driver, 20) 
            caixa_protocolo = espera_longa.until(EC.visibility_of_element_located((By.CLASS_NAME, "protocolo_panel_numero")))
            
            codigo_cliente = caixa_protocolo.text.strip()
            print(f"\n> 🏆 SUCESSO! Cliente cadastrado com o código: {codigo_cliente} 🏆\n")

            # 3. Clicar no botão OK da janela de protocolo para limpar a tela
            btn_ok = wait.until(EC.presence_of_element_located((By.ID, "btnProtocolo")))
            driver.execute_script("arguments[0].click();", btn_ok)
            time.sleep(2) # Respiro final para a tela fechar
            
            print("> 🛑 Execução do robô finalizada com êxito!")

        except Exception as e:
            print(f"> ❌ ERRO FATAL: Falha ao tentar salvar o cliente ou capturar o protocolo final.")
            print(f"Detalhes do erro: {e}")

        # Final do robô
        return {"status": "Sucesso", "msg": "Cadastro salvo e finalizado com sucesso!"}
    
    except Exception as e:
        print(f"> ❌ Erro Crítico: {e}")
        return {"status": "Erro", "msg": str(e)}

    finally:
        # Comente a linha abaixo se quiser que o navegador fique aberto para conferir
        # driver.quit()
        print("> 🏁 Fim da execução.")


# ── TESTE DE BANCADA ───────────────────────────────────
if __name__ == "__main__":
    print("🧪 Iniciando Teste de Bancada...")
    dados_teste = {
        "cnpj_limpo": "00000000000191",
        "razao_social": "EMPRESA DE TESTE LTDA",
        "nome_fantasia": "TESTE FANTASIA",
        "inscricao_estadual": "ISENTO",
        "cnae_principal_descricao": "4771-7/02 - Comércio varejista de medicamentos",        
        "cep": "01001000",
        "logradouro": "Praça da Sé",
        "numero": "123",
        "complemento": "Sala 1",
        "bairro": "Sé",
        "uf": "SP"
    }
    executar(dados_teste)