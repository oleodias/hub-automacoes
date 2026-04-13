# automacoes/clientes/cadastro_reativacao.py
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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoAlertPresentException
from selenium.webdriver.support.ui import Select

from automacoes.clientes.navegacao_erp import fazer_login, navegar_via_favoritos

sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────
# HELPERS — espelhados do cadastro_novo.py de propósito.
# Mantenho aqui pra esse robô ficar autocontido. Se quisermos
# centralizar no futuro, é só mover pra automacoes/clientes/helpers.py
# e importar nos dois robôs.
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# HELPER NOVO — vai ser o "carro-chefe" da reativação.
# Toda etapa do robô usa esse helper pra obedecer a regra global
# "limpar antes de preencher". Funciona até em campos com máscara
# do Oracle ADF, onde o .clear() padrão do Selenium falha silenciosamente.
# ─────────────────────────────────────────────────────────────

def limpar_e_preencher(driver, campo, valor):
    """
    Limpeza ROBUSTA + envio do valor. Combina 3 estratégias para vencer
    a teimosia do Oracle ADF: zerar via JS, Ctrl+A e Backspace.
    Use SEMPRE no lugar de send_keys direto na reativação.
    """
    try:
        campo.click()
    except Exception:
        pass
    try:
        driver.execute_script("arguments[0].value = '';", campo)
    except Exception:
        pass
    campo.send_keys(Keys.CONTROL + "a")
    campo.send_keys(Keys.BACKSPACE)
    time.sleep(0.2)
    if valor not in (None, ""):
        campo.send_keys(str(valor))


# ─────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────

def executar(dados_cliente):
    """
    Função principal chamada pelo Flask quando o vendedor clica em
    "Iniciar Reativação" no Hub. Reativa um cliente já existente no
    ERP a partir do código NL recebido no payload.
    """
    print(f"> 🔁 Iniciando Robô: REATIVAÇÃO ({dados_cliente.get('razao_social')})...")

    # ── VALIDAÇÃO CRÍTICA: sem código NL, nem abre o Chrome ──
    codigo_nl = str(dados_cliente.get('codigo_nl', '')).strip()
    if not codigo_nl:
        return {
            "status": "Erro",
            "msg": "Código NL não informado. Reativação abortada antes de abrir o ERP.",
            "avisos": []
        }

    cnpj_formatado = limpar_cnpj(dados_cliente.get('cnpj_limpo', ''))

    # ── LISTA DE AVISOS ──
    # Combinado com você: o robô NÃO aborta quando uma etapa falha.
    # Em vez disso, ele acumula mensagens aqui e devolve no final
    # pra serem exibidas em amarelo no terminal do Hub.
    # Ex: ["REVISAR ABA CONTATOS", "REVISAR ABA TELEFONES"]
    avisos = []
    
    # ── Helper local: registra aviso E imprime no terminal ──
    def registrar_aviso(msg):
        avisos.append(msg)
        print(f"   🟡 AVISO ACUMULADO: {msg}")

    
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

        print(f"> ✅ Login + navegação OK. Pronto para buscar o cliente NL {codigo_nl}.")

        # ════════════════════════════════════════════════════
        # ETAPA 1 — ACESSO AO CADASTRO VIA CÓDIGO NL
        # ════════════════════════════════════════════════════
        print(f"> 🔎 ETAPA 1: Buscando cliente pelo código NL {codigo_nl}...")

        # ── Passo 1.1: Preencher o campo de código NL ──
        # O onchange do campo dispara NlLov.change(), que valida o código
        # no backend do ADF. Por isso usamos TAB DEPOIS de digitar — pra
        # garantir que essa validação rode ANTES de clicarmos na lupa.
        try:
            campo_cod = wait.until(
                EC.presence_of_element_located((By.ID, "lovPsPessoas_txtCod"))
            )
            limpar_e_preencher(driver, campo_cod, codigo_nl)
            campo_cod.send_keys(Keys.TAB)
            time.sleep(0.8)  # Respiro para o onchange do ADF processar
            print(f"   ✅ Código NL {codigo_nl} digitado e validado.")
        except Exception as e:
            raise Exception(f"Falha ao preencher o campo de código NL: {e}")

        # ── Passo 1.2: Clicar na lupa (JS click obrigatório no ADF) ──
        try:
            btn_lupa = wait.until(
                EC.presence_of_element_located((By.ID, "search_cmdSearch"))
            )
            driver.execute_script("arguments[0].click();", btn_lupa)
            print("   ✅ Lupa clicada via JS. Aguardando o ERP buscar...")
        except Exception as e:
            raise Exception(f"Falha ao clicar na lupa de busca: {e}")

        # ── Passo 1.3: Aguardar o grid de resultado (estratégia do cadastro_item.py) ──
        # A tela de busca do NLWeb não atribui IDs com padrão ":0" nas linhas
        # do resultado, então esperar por isso dava timeout. A solução que
        # funciona em produção é esperar pela CÉLULA específica via XPath
        # absoluto — mesmo jeito que o cadastro_item.py faz.
        xpath_linha_resultado = (
            "/html/body/form[1]/div[3]/div[1]/section/div[2]/div[2]"
            "/table/tbody/tr[2]/td[2]/div/div/table[2]/tbody/tr[2]/td[1]"
        )
        try:
            espera_grid = WebDriverWait(driver, 15)
            time.sleep(2.5)
            linha_resultado = espera_grid.until(
                EC.element_to_be_clickable((By.XPATH, xpath_linha_resultado))
            )
            print("   ✅ Grid de resultado carregou (linha encontrada).")
            time.sleep(1.5)  # Respiro extra para o grid estabilizar
        except Exception as e:
            raise Exception(
                f"Grid de resultado não carregou após a busca pelo NL {codigo_nl}. "
                f"Verifique se o código existe no ERP. Detalhes: {e}"
            )

        # ── Passo 1.4: Selecionar a linha + clicar em "Cadastro particionado" ──
        # Fluxo que funciona em produção (mesmo do cadastro_item.py):
        #   1) Clica na linha pra selecioná-la
        #   2) Espera 1s pro ADF processar a seleção
        #   3) Clica no link "Cadastro particionado" (ID estável)
        try:
            print("   🖱️ Clicando na linha do resultado...")
            linha_resultado.click()
            time.sleep(2.5)

            print("   🎯 Clicando em 'Cadastro particionado'...")
            link_cadastro = wait.until(
                EC.element_to_be_clickable((By.ID, "tabPsPessoas:0:lnkCadastroWizard"))
            )
            link_cadastro.click()
            time.sleep(2.5)
            print("   ✅ Cadastro particionado acessado.")
        except Exception as e:
            raise Exception(f"Falha ao clicar na linha ou no link Cadastro particionado: {e}")
        

        # ── Passo 1.5: Aguardar a tela do cadastro particionado carregar ──
        # ÂNCORA PROVISÓRIA: btnWizardProximoCab. Esse ID é usado pelo
        # cadastro_novo.py nas transições de fase, então sabemos que
        # existe no wizard. A premissa é que ele já apareça na primeira
        # tela do cadastro particionado. Se não funcionar nos testes,
        # trocamos por um elemento mais específico (te peço o HTML).
        try:
            wait.until(EC.presence_of_element_located((By.ID, "btnWizardProximoCab")))
            print("   ✅ Tela do Cadastro particionado carregada.")
            time.sleep(1)  # Respiro pro ADF terminar de renderizar tudo
        except Exception as e:
            raise Exception(
                f"Tela do Cadastro particionado não carregou (timeout em btnWizardProximoCab). "
                f"Pode ser que a âncora precise ser trocada. Detalhes: {e}"
            )

        print(f"> ✅ ETAPA 1 CONCLUÍDA! Cliente {codigo_nl} aberto no Cadastro particionado.")

        # ════════════════════════════════════════════════════
        # ETAPA 2 — PREENCHIMENTO DOS DADOS BÁSICOS
        # (Pessoa Jurídica + Inscrições + Endereços)
        # Regra global: LIMPAR antes de preencher TODOS os campos.
        # ════════════════════════════════════════════════════
        print("> ✍️ ETAPA 2: Atualizando Dados Básicos do cliente...")

        # ── DIFERENÇA-CHAVE PRA REATIVAÇÃO ──
        # No cadastro novo aqui tem o check `indCli` ("marcar como cliente").
        # Na reativação NÃO mexemos nesse checkbox: o cliente já é cliente,
        # então ele já está marcado. Mexer poderia desmarcar e gerar bug.

        # ── Razão Social ──
        try:
            campo_razao = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoa"))
            )
            limpar_e_preencher(driver, campo_razao, dados_cliente.get('razao_social', ''))
            print("   ✅ Razão social atualizada.")
        except Exception as e:
            print(f"   ⚠️ Falha ao atualizar razão social: {e}")
            registrar_aviso("REVISAR ABA PESSOA JURÍDICA — Razão Social")

        # ── Nome Fantasia (com fallback e trava de 20 chars) ──
        try:
            campo_fantasia = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:desPessoaFantasia"))
            )
            nome_fantasia_api = dados_cliente.get('nome_fantasia', '')
            if not nome_fantasia_api:
                nome_fantasia_api = dados_cliente.get('razao_social', '')
            nome_fantasia_cortado = str(nome_fantasia_api)[:20]
            limpar_e_preencher(driver, campo_fantasia, nome_fantasia_cortado)
            print(f"   ✅ Nome fantasia atualizado: {nome_fantasia_cortado}")
        except Exception as e:
            print(f"   ⚠️ Falha ao atualizar nome fantasia: {e}")
            registrar_aviso("REVISAR ABA PESSOA JURÍDICA — Nome Fantasia")

        # ── Inscrição Estadual (com retry e validação de ISENTO) ──
        ie = dados_cliente.get('inscricao_estadual', '')
        if ie and ie.upper() not in ["ISENTO", "ISENTO / NÃO ENCONTRADA", ""]:
            print(f"   📄 Inserindo Inscrição Estadual: {ie}")
            sucesso_ie = False
            for tentativa in range(3):
                try:
                    campo_ie = wait.until(
                        EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:numInscEst"))
                    )
                    limpar_e_preencher(driver, campo_ie, ie)
                    campo_ie.send_keys(Keys.TAB)
                    sucesso_ie = True
                    break
                except Exception:
                    time.sleep(1)
            if not sucesso_ie:
                registrar_aviso("REVISAR ABA PESSOA JURÍDICA — Inscrição Estadual")
        else:
            print("   ℹ️ IE Isenta ou não encontrada. Pulando campo.")

        # ── Atividade Ciamed (CNAE) ──
        # ⚠️ ATENÇÃO LEO: na reativação, esse campo SOBRESCREVE a atividade
        # antiga do cliente. Se a empresa mudou de varejista pra atacadista
        # (ou vice-versa), o robô vai ajustar. Se não quiser esse comportamento,
        # me avisa que eu condiciono pra só preencher se vier do payload.
        cnae_desc = dados_cliente.get('cnae_principal_descricao', '')
        codigo_atividade = definir_codigo_atividade(cnae_desc)
        print(f"   🧠 CNAE analisado. Aplicando atividade Ciamed: {codigo_atividade}")

        sucesso_ativ = False
        for tentativa in range(3):
            try:
                campo_ativ = wait.until(
                    EC.element_to_be_clickable((By.ID, "subFrmPsJuridicas:lovPsAtividadesPsJuridicas_txtCod"))
                )
                driver.execute_script("arguments[0].focus(); arguments[0].click();", campo_ativ)
                time.sleep(0.5)
                limpar_e_preencher(driver, campo_ativ, codigo_atividade)
                campo_ativ.send_keys(Keys.TAB)
                print("   ⏳ Sistema processando a atividade...")
                time.sleep(3.5)  # Tempo crítico — o ERP precisa respirar
                sucesso_ativ = True
                break
            except Exception:
                print("   ⚠️ Falha ao digitar atividade. Tentando novamente...")
                time.sleep(1)
        if not sucesso_ativ:
            registrar_aviso("REVISAR ABA PESSOA JURÍDICA — Atividade Ciamed")

        # ════════════════════════════════════════════════════
        # ETAPA 2.2 — ENDEREÇO
        # ════════════════════════════════════════════════════
        print("> 📍 ETAPA 2.2: Atualizando Endereço...")

        # ── CEP ──
        sucesso_cep = False
        for tentativa in range(4):
            try:
                campo_cep = wait.until(
                    EC.element_to_be_clickable((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtCep"))
                )
                driver.execute_script("arguments[0].focus(); arguments[0].click();", campo_cep)
                time.sleep(0.5)
                cep_limpo = limpar_cnpj(dados_cliente.get('cep', ''))
                limpar_e_preencher(driver, campo_cep, cep_limpo)
                campo_cep.send_keys(Keys.TAB)
                print("   ⏳ Sistema processando o CEP...")
                time.sleep(2)  # Respiro pro ERP puxar rua/bairro automaticamente
                sucesso_cep = True
                break
            except Exception:
                print("   ⚠️ CEP não clicável ainda. Aguardando ERP liberar...")
                time.sleep(2)
        if not sucesso_cep:
            registrar_aviso("REVISAR ABA ENDEREÇOS — CEP")

        # ── LÓGICA DE 50 CARACTERES (idêntica ao cadastro novo) ──
        print("   📏 Calculando tamanho do endereço...")
        logradouro = str(dados_cliente.get('logradouro', '')).strip()
        numero = str(dados_cliente.get('numero', '')).strip()
        complemento = str(dados_cliente.get('complemento', '')).strip()

        texto_completo = logradouro
        if numero:
            texto_completo += f", {numero}"
        if complemento:
            texto_completo += f" - {complemento}"

        endereco_principal = ""
        texto_referencia = ""

        # PLANO A: Cabe tudo
        if len(texto_completo) <= 50:
            endereco_principal = texto_completo
            print(f"      ✅ Endereço curto ({len(texto_completo)} chars). Cabe no campo principal.")
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
            # PLANO C: Logradouro é gigante (caso extremo)
            else:
                endereco_principal = logradouro[:50]
                texto_ref_temp = f"Num: {numero}"
                if complemento:
                    texto_ref_temp += f" - {complemento}"
                texto_referencia = texto_ref_temp[:50]
                print("      🚨 Rua muito longa! Logradouro isolado. Num e Comp vão para Referência.")

        # ── Endereço Principal ──
        sucesso_end = False
        for tentativa in range(3):
            try:
                campo_endereco = wait.until(
                    EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesEndereco"))
                )
                limpar_e_preencher(driver, campo_endereco, endereco_principal)
                sucesso_end = True
                break
            except Exception:
                time.sleep(1)
        if not sucesso_end:
            registrar_aviso("REVISAR ABA ENDEREÇOS — Logradouro")

        # ── Referência (válvula de escape) ──
        if texto_referencia:
            sucesso_ref = False
            for tentativa in range(3):
                try:
                    campo_ref = wait.until(
                        EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesReferencia"))
                    )
                    limpar_e_preencher(driver, campo_ref, texto_referencia)
                    sucesso_ref = True
                    break
                except Exception:
                    time.sleep(1)
            if not sucesso_ref:
                registrar_aviso("REVISAR ABA ENDEREÇOS — Referência")

        # ── Bairro ──
        sucesso_bairro = False
        for tentativa in range(3):
            try:
                campo_bairro = wait.until(
                    EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:enderecoPsJuridicas_txtDesBairro"))
                )
                limpar_e_preencher(driver, campo_bairro, dados_cliente.get('bairro', ''))
                sucesso_bairro = True
                break
            except Exception:
                time.sleep(1)
        if not sucesso_bairro:
            registrar_aviso("REVISAR ABA ENDEREÇOS — Bairro")

        # ── Região (com trava do RS) ──
        uf = dados_cliente.get('uf', '')
        if uf.upper() == 'RS':
            print("   ℹ️ Estado é RS. ERP preenche região automaticamente. Pulando.")
        else:
            codigo_regiao = descobrir_regiao(uf)
            sucesso_regiao = False
            for tentativa in range(3):
                try:
                    campo_regiao = wait.until(
                        EC.presence_of_element_located((By.ID, "subFrmPsJuridicas:lovPsRegioesPsJuridicas_txtCod"))
                    )
                    limpar_e_preencher(driver, campo_regiao, codigo_regiao)
                    campo_regiao.send_keys(Keys.TAB)
                    time.sleep(1.5)
                    sucesso_regiao = True
                    break
                except Exception:
                    time.sleep(1)
            if not sucesso_regiao:
                registrar_aviso("REVISAR ABA ENDEREÇOS — Região")

        print("> ✅ ETAPA 2 CONCLUÍDA! Dados básicos atualizados.")

        # ════════════════════════════════════════════════════
        # 🚧 TODO — TRANSIÇÃO DA ETAPA 2 PARA A ETAPA 3
        # No cadastro novo, depois de preencher os Dados Básicos +
        # Endereços, o robô clica em "Próximo" do wizard 1 ou 2 vezes
        # pra chegar na aba de Bloqueio. Eu preciso desse trecho exato
        # do cadastro_novo.py pra reproduzir aqui.
        # Por enquanto deixo um placeholder.
        # ════════════════════════════════════════════════════
        print("> ⏩ Avançando do Endereço para o Bloqueio...")
        # >>> COLAR AQUI A TRANSIÇÃO DO CADASTRO_NOVO.PY <
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

        # ════════════════════════════════════════════════════
        # ETAPA 3 — BLOQUEIO COM LÓGICA CONDICIONAL
        # Decisão vem do payload (preenchida pela farmacêutica no email):
        #   acao_bloqueio = "manter" | "alterar" | None
        #   valor_bloqueio = string com o código (usado só em "alterar")
        # ════════════════════════════════════════════════════
        print("> 🔒 ETAPA 3: Aplicando regras de Bloqueio...")

        acao_bloqueio = dados_cliente.get('acao_bloqueio')
        valor_bloqueio = dados_cliente.get('valor_bloqueio', '')
        VALOR_PADRAO_BLOQUEIO = "30"

        # Normaliza a ação pra evitar problemas com maiúsculas/espaços vindos do n8n
        if acao_bloqueio:
            acao_bloqueio = str(acao_bloqueio).strip().lower()
        print(f"   📋 Decisão da farmacêutica: acao={acao_bloqueio!r} valor={valor_bloqueio!r}")

        # ── Localiza o campo de motivo (sem mexer ainda) ──
        try:
            campo_motivo = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmBloqueio:lovPsMotivosBloqueio_txtCod"))
            )
            valor_atual = campo_motivo.get_attribute("value") or ""
            valor_atual = valor_atual.strip()
            print(f"   🔍 Valor atual do motivo no ERP: {valor_atual!r}")
        except Exception as e:
            print(f"   ❌ Falha ao localizar o campo de motivo de bloqueio: {e}")
            registrar_aviso("REVISAR ABA BLOQUEIO — Campo Motivo não encontrado")
            campo_motivo = None
            valor_atual = ""

        # ── Lógica das 3 decisões ──
        if campo_motivo is not None:
            try:
                if acao_bloqueio == "manter":
                    # Caso 1: MANTER BLOQUEIO
                    if valor_atual:
                        # Sub-caso 1.A: Já tem valor → NÃO MEXE (exceção à regra global)
                        print(f"   ✋ Decisão MANTER + campo já preenchido ({valor_atual}). Não alterando.")
                    else:
                        # Sub-caso 1.B: Campo vazio → preencher com fallback
                        print(f"   ➕ Decisão MANTER + campo vazio. Aplicando padrão {VALOR_PADRAO_BLOQUEIO}.")
                        limpar_e_preencher(driver, campo_motivo, VALOR_PADRAO_BLOQUEIO)
                        campo_motivo.send_keys(Keys.TAB)
                        time.sleep(0.5)

                elif acao_bloqueio == "alterar":
                    # Caso 2: ALTERAR BLOQUEIO
                    if valor_bloqueio:
                        print(f"   🔄 Decisão ALTERAR. Aplicando valor escolhido: {valor_bloqueio}")
                        limpar_e_preencher(driver, campo_motivo, str(valor_bloqueio).strip())
                        campo_motivo.send_keys(Keys.TAB)
                        time.sleep(0.5)
                    else:
                        # Inconsistência: pediu pra alterar mas não mandou o valor
                        print(f"   ⚠️ Decisão ALTERAR sem valor_bloqueio. Caindo no padrão {VALOR_PADRAO_BLOQUEIO}.")
                        registrar_aviso("REVISAR ABA BLOQUEIO — pediram ALTERAR mas valor não veio no payload")
                        limpar_e_preencher(driver, campo_motivo, VALOR_PADRAO_BLOQUEIO)
                        campo_motivo.send_keys(Keys.TAB)
                        time.sleep(0.5)

                else:
                    # Caso 3: NENHUMA opção marcada (None / vazio / qualquer outro valor)
                    print(f"   ➖ Sem decisão da farmacêutica. Aplicando padrão {VALOR_PADRAO_BLOQUEIO}.")
                    limpar_e_preencher(driver, campo_motivo, VALOR_PADRAO_BLOQUEIO)
                    campo_motivo.send_keys(Keys.TAB)
                    time.sleep(0.5)

                print("   ✅ Motivo de bloqueio resolvido.")
            except Exception as e:
                print(f"   ❌ Erro ao aplicar lógica de motivo de bloqueio: {e}")
                registrar_aviso("REVISAR ABA BLOQUEIO — Motivo")

        # ── Data do Bloqueio (SEMPRE data atual, em qualquer dos 3 casos) ──
        try:
            data_hoje = datetime.now().strftime("%d/%m/%Y")
            print(f"   📅 Definindo Data do Bloqueio: {data_hoje}")
            campo_data = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmBloqueio:txtDtaBloq"))
            )
            limpar_e_preencher(driver, campo_data, data_hoje)
            campo_data.send_keys(Keys.TAB)
            time.sleep(0.3)
            print("   ✅ Data do bloqueio atualizada.")
        except Exception as e:
            print(f"   ❌ Erro ao preencher data do bloqueio: {e}")
            registrar_aviso("REVISAR ABA BLOQUEIO — Data")

        print("> ✅ ETAPA 3 CONCLUÍDA! Bloqueio resolvido.")

        # ════════════════════════════════════════════════════
        # 🚧 TRANSIÇÃO WIZARD: Bloqueio → Contatos
        # (você implementa quantos cliques de "Próximo" forem necessários)
        # ════════════════════════════════════════════════════
        print("> ⏩ Avançando do Bloqueio para os Contatos...")
        # >>> COLAR AQUI A TRANSIÇÃO DO WIZARD <
        
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

        # ════════════════════════════════════════════════════
        # ETAPA 4 — RESET TOTAL DE CONTATOS
        # FASE A: Apagar todos os contatos existentes (popup nativo do browser)
        # FASE B: Recadastrar do zero com a lista nova
        # ════════════════════════════════════════════════════
        print("> 👥 ETAPA 4: Resetando contatos do cliente...")

        # ──────────────────────────────────────────────
        # FASE A — APAGAR TODOS OS CONTATOS EXISTENTES
        # ──────────────────────────────────────────────
        print("   🗑️ FASE A: Excluindo contatos antigos...")

        contatos_excluidos = 0
        LIMITE_SEGURANCA = 50  # Trava anti-loop-infinito
        wait_alert = WebDriverWait(driver, 5)

        for tentativa in range(LIMITE_SEGURANCA):
            try:
                # Re-localiza SEMPRE a partir do zero, porque o DOM
                # da grid é refeito pelo ADF a cada exclusão (stale element).
                # Usamos o índice :0 fixo: a premissa é que, ao apagar a
                # linha 0, a antiga linha 1 vira a nova linha 0.
                btn_remover = driver.find_element(
                    By.ID, "table_Contatos:0:btnRemover_Contatos"
                )
            except NoSuchElementException:
                # Não achou mais a linha 0 = grid vazia = trabalho concluído
                print(f"   ✅ Grid de contatos limpa. Total excluído: {contatos_excluidos}")
                break

            try:
                # Clica na lixeira via JS (regra global do ADF)
                driver.execute_script("arguments[0].click();", btn_remover)

                # Espera o confirm() nativo aparecer
                wait_alert.until(EC.alert_is_present())

                # Aceita o popup → ADF dispara o submit de exclusão
                driver.switch_to.alert.accept()

                # Respiro pra grid recarregar antes da próxima iteração
                time.sleep(1.5)

                contatos_excluidos += 1
                print(f"      🗑️ Contato {contatos_excluidos} excluído.")

            except NoAlertPresentException:
                print("      ⚠️ Cliquei no remover mas o popup não apareceu.")
                registrar_aviso("REVISAR ABA CONTATOS — popup de exclusão não apareceu")
                break  # Para o loop pra não travar o robô

            except TimeoutException:
                print("      ⚠️ Timeout esperando o popup de confirmação aparecer.")
                registrar_aviso("REVISAR ABA CONTATOS — timeout no popup de exclusão")
                break

            except Exception as e:
                print(f"      ⚠️ Erro inesperado ao excluir contato: {e}")
                registrar_aviso(f"REVISAR ABA CONTATOS — erro na exclusão após {contatos_excluidos} contatos")
                break
        else:
            # Esse else do for SÓ executa se o loop chegar a 50 sem break.
            # Significa que tem mais de 50 contatos OU o ADF está travado num loop.
            print("   ⚠️ Limite de segurança (50) atingido na exclusão de contatos!")
            registrar_aviso("REVISAR ABA CONTATOS — limite de 50 exclusões atingido")

        # ──────────────────────────────────────────────
        # FASE B — RECADASTRAR OS CONTATOS NOVOS
        # (lógica idêntica à do cadastro_novo.py)
        # ──────────────────────────────────────────────
        print("   ➕ FASE B: Cadastrando contatos novos...")

        # Monta a lista de contatos a partir do payload
        # (mesma estrutura usada no cadastro_novo.py: contatos_da_tela)
        email_nfe = dados_cliente.get('email_xml', '')
        contatos_para_cadastrar = dados_cliente.get('contatos_da_tela', [])

        if not contatos_para_cadastrar:
            print("   ℹ️ Nenhum contato novo no payload. Pulando recadastro.")
            registrar_aviso("REVISAR ABA CONTATOS — payload sem contatos novos para cadastrar")
        else:
            print(f"   📋 {len(contatos_para_cadastrar)} contato(s) para cadastrar.")

            for c in contatos_para_cadastrar:
                nome_contato = c.get('nome', '(sem nome)')
                print(f"      ➕ Cadastrando: {nome_contato}")
                try:
                    # 1. Clica em Adicionar
                    btn_add = wait.until(
                        EC.element_to_be_clickable((By.ID, "btnAdicionar_Contatos"))
                    )
                    driver.execute_script("arguments[0].click();", btn_add)
                    time.sleep(1.5)

                    # 2. Nome
                    campo_nome = wait.until(
                        EC.presence_of_element_located((By.ID, "subFrm_Contatos:contatoDesContato"))
                    )
                    limpar_e_preencher(driver, campo_nome, nome_contato)

                    # 3. Função (código)
                    if c.get('codigo'):
                        campo_funcao = driver.find_element(
                            By.ID, "subFrm_Contatos:contatoLovPsFuncoes_txtCod"
                        )
                        limpar_e_preencher(driver, campo_funcao, c.get('codigo'))
                        campo_funcao.send_keys(Keys.TAB)
                        time.sleep(0.5)

                    # 4. Telefone
                    if c.get('tel'):
                        campo_tel = driver.find_element(
                            By.ID, "subFrm_Contatos:contatoNumFone"
                        )
                        limpar_e_preencher(driver, campo_tel, c.get('tel'))

                    # 5. Email principal
                    if c.get('email'):
                        campo_email = driver.find_element(
                            By.ID, "subFrm_Contatos:contatoDesEmail"
                        )
                        limpar_e_preencher(driver, campo_email, c.get('email'))

                    # 6. Email XML
                    if c.get('email_xml'):
                        campo_email_xml = driver.find_element(
                            By.ID, "subFrm_Contatos:contatoDesEmailXML"
                        )
                        limpar_e_preencher(driver, campo_email_xml, c.get('email_xml'))

                    # 7. Email Danfe
                    if c.get('email_danfe'):
                        campo_email_danfe = driver.find_element(
                            By.ID, "subFrm_Contatos:contatoDesEmailDanfe"
                        )
                        limpar_e_preencher(driver, campo_email_danfe, c.get('email_danfe'))

                    # 8. Checkboxes (boleto / docs)
                    if c.get('check_boleto'):
                        chk_boleto = driver.find_element(
                            By.ID, "subFrm_Contatos:chkIndEnviarCotacao"
                        )
                        if not chk_boleto.is_selected():
                            driver.execute_script("arguments[0].click();", chk_boleto)

                    if c.get('check_docs'):
                        chk_docs = driver.find_element(
                            By.ID, "subFrm_Contatos:chkIndEmailDocs"
                        )
                        if not chk_docs.is_selected():
                            driver.execute_script("arguments[0].click();", chk_docs)

                    # 9. Aplicar (salva o contato na grid)
                    btn_aplicar = driver.find_element(
                        By.ID, "subFrm_Contatos:btnAplicar_Contatos"
                    )
                    driver.execute_script("arguments[0].click();", btn_aplicar)
                    time.sleep(2)

                    print(f"         ✅ {nome_contato} cadastrado.")

                except Exception as e:
                    print(f"         ⚠️ Erro ao cadastrar {nome_contato}: {e}")
                    registrar_aviso(f"REVISAR ABA CONTATOS — falha ao cadastrar '{nome_contato}'")
                    # Tenta fechar a janela aberta dando ESC, pra não travar o próximo
                    try:
                        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                    except Exception:
                        pass

        print("> ✅ ETAPA 4 CONCLUÍDA! Contatos resetados e recadastrados.")

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

        # ================================================================
        # ABA DE COMENTÁRIOS (REGRA DE FATURAMENTO)
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
                limpar_e_preencher(driver, campo_comentario, "FATURAR EM CAIXA!")
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

        # ════════════════════════════════════════════════════
        # 🚧 TRANSIÇÃO WIZARD: Contatos → Telefones
        # ════════════════════════════════════════════════════
        print("> ⏩ Avançando dos Contatos para os Telefones...")
        # >>> COLAR AQUI A TRANSIÇÃO DO WIZARD <
        
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


        # ════════════════════════════════════════════════════
        # ETAPA 5 — RESET TOTAL DE TELEFONES
        # FASE A: Apagar todos os telefones existentes (popup nativo)
        # FASE B: Recadastrar do payload (1 ou mais telefones)
        # ════════════════════════════════════════════════════
        print("> 📞 ETAPA 5: Resetando telefones do cliente...")

        # ──────────────────────────────────────────────
        # FASE A — APAGAR TODOS OS TELEFONES EXISTENTES
        # ──────────────────────────────────────────────
        print("   🗑️ FASE A: Excluindo telefones antigos...")

        # ⚠️ ID PROVISÓRIO: estou apostando no padrão `table_telefones:0:btnRemover_telefones`
        # por analogia com o ID dos contatos. Se na primeira execução der
        # NoSuchElementException JÁ na primeira iteração (sem nenhum telefone
        # excluído), me manda o HTML real do botão de lixeira e a gente troca.
        ID_BTN_REMOVER_TELEFONE = "table_telefones:0:btnRemover_telefones"

        telefones_excluidos = 0
        LIMITE_SEGURANCA = 50
        wait_alert = WebDriverWait(driver, 5)

        for tentativa in range(LIMITE_SEGURANCA):
            try:
                btn_remover = driver.find_element(By.ID, ID_BTN_REMOVER_TELEFONE)
            except NoSuchElementException:
                print(f"   ✅ Grid de telefones limpa. Total excluído: {telefones_excluidos}")
                break

            try:
                driver.execute_script("arguments[0].click();", btn_remover)
                wait_alert.until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                time.sleep(1.5)
                telefones_excluidos += 1
                print(f"      🗑️ Telefone {telefones_excluidos} excluído.")

            except NoAlertPresentException:
                print("      ⚠️ Cliquei no remover mas o popup não apareceu.")
                registrar_aviso("REVISAR ABA TELEFONES — popup de exclusão não apareceu")
                break

            except TimeoutException:
                print("      ⚠️ Timeout esperando o popup de confirmação.")
                registrar_aviso("REVISAR ABA TELEFONES — timeout no popup de exclusão")
                break

            except Exception as e:
                print(f"      ⚠️ Erro inesperado ao excluir telefone: {e}")
                registrar_aviso(f"REVISAR ABA TELEFONES — erro após {telefones_excluidos} exclusões")
                break
        else:
            print("   ⚠️ Limite de segurança (50) atingido na exclusão de telefones!")
            registrar_aviso("REVISAR ABA TELEFONES — limite de 50 exclusões atingido")

        # ──────────────────────────────────────────────
        # FASE B — RECADASTRAR OS TELEFONES NOVOS
        # Aceita 2 formatos no payload (compatibilidade):
        #   1) telefones_da_tela = [{"numero": "...", "descricao": "..."}, ...]  ← lista
        #   2) telefone_empresa = "..."                                          ← string única (legado)
        # Se vier os dois, a LISTA tem prioridade.
        # ──────────────────────────────────────────────
        print("   ➕ FASE B: Cadastrando telefones novos...")

        # Normaliza o input pra SEMPRE ser uma lista de dicts
        lista_telefones = []
        telefones_da_tela = dados_cliente.get('telefones_da_tela')
        if telefones_da_tela and isinstance(telefones_da_tela, list):
            # Caminho moderno: lista de dicts vinda do payload
            for t in telefones_da_tela:
                numero = t.get('numero', '').strip() if isinstance(t, dict) else str(t).strip()
                descricao = t.get('descricao', 'TELEFONE DA EMPRESA') if isinstance(t, dict) else 'TELEFONE DA EMPRESA'
                if numero:
                    lista_telefones.append({"numero": numero, "descricao": descricao})
        else:
            # Caminho legado: telefone único como string
            tel_legado = dados_cliente.get('telefone_empresa', '').strip()
            if tel_legado:
                lista_telefones.append({"numero": tel_legado, "descricao": "TELEFONE DA EMPRESA"})

        if not lista_telefones:
            print("   ℹ️ Nenhum telefone no payload. Pulando recadastro.")
            registrar_aviso("REVISAR ABA TELEFONES — payload sem telefones para cadastrar")
        else:
            print(f"   📋 {len(lista_telefones)} telefone(s) para cadastrar.")

            # Cadastra cada telefone com sequência incremental (1, 2, 3...)
            for indice, tel in enumerate(lista_telefones, start=1):
                numero = tel["numero"]
                descricao = tel["descricao"]
                print(f"      ➕ Cadastrando telefone {indice}: {numero}")

                try:
                    # 1. Adicionar
                    btn_add_tel = wait.until(
                        EC.element_to_be_clickable((By.ID, "btnAdicionar_telefones"))
                    )
                    driver.execute_script("arguments[0].click();", btn_add_tel)
                    time.sleep(1.5)

                    # 2. Sequência (incremental)
                    campo_seq = wait.until(
                        EC.presence_of_element_located((By.ID, "subFrm_telefones:telefonesNumSeq"))
                    )
                    limpar_e_preencher(driver, campo_seq, str(indice))

                    # 3. Descrição
                    campo_desc = driver.find_element(
                        By.ID, "subFrm_telefones:txtTelefonesDesFone"
                    )
                    limpar_e_preencher(driver, campo_desc, descricao)

                    # 4. Número
                    campo_num = driver.find_element(
                        By.ID, "subFrm_telefones:telefonesNumFone"
                    )
                    limpar_e_preencher(driver, campo_num, numero)

                    # 5. Aplicar
                    btn_aplicar_tel = driver.find_element(
                        By.ID, "subFrm_telefones:btnAplicar_telefones"
                    )
                    driver.execute_script("arguments[0].click();", btn_aplicar_tel)
                    time.sleep(2)

                    print(f"         ✅ Telefone {numero} cadastrado.")

                except Exception as e:
                    print(f"         ⚠️ Erro ao cadastrar telefone {numero}: {e}")
                    registrar_aviso(f"REVISAR ABA TELEFONES — falha ao cadastrar '{numero}'")
                    try:
                        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                    except Exception:
                        pass

        print("> ✅ ETAPA 5 CONCLUÍDA! Telefones resetados e recadastrados.")

        # ════════════════════════════════════════════════════
        # 🚧 TRANSIÇÃO WIZARD: Telefones → Observações
        # ════════════════════════════════════════════════════
        print("> ⏩ Avançando dos Telefones para as Observações...")
        # >>> COLAR AQUI A TRANSIÇÃO DO WIZARD <

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

                # ════════════════════════════════════════════════════
        # ════════════════════════════════════════════════════
        # FASE PRÉVIA — RESET SELETIVO DE OBSERVAÇÕES
        # Apaga as observações antigas EXCETO as que tiverem código "1".
        # A obs com código "1" é intocável (regra de negócio da Ciamed)
        # e deve ser preservada em toda reativação.
        #
        # Diferente dos loops de Contatos/Telefones, esse loop usa
        # ÍNDICE VARIÁVEL: quando pula uma linha, avança; quando apaga,
        # fica parado (porque a próxima linha vira a atual).
        # ════════════════════════════════════════════════════
        print("> 🗑️ Excluindo observações antigas (preservando código '1')...")

        CODIGO_OBS_INTOCAVEL = "1"
        observacoes_excluidas = 0
        observacoes_preservadas = 0
        LIMITE_SEGURANCA = 50
        wait_alert = WebDriverWait(driver, 5)

        indice_atual = 0  # Índice da linha que estou analisando

        for tentativa in range(LIMITE_SEGURANCA):
            id_btn_remover = f"table_observacoes:{indice_atual}:btnRemover_observacoes"

            try:
                btn_remover = driver.find_element(By.ID, id_btn_remover)
            except NoSuchElementException:
                # Não achou a linha com esse índice = acabaram as observações
                print(
                    f"   ✅ Grid de observações processada. "
                    f"Excluídas: {observacoes_excluidas} | Preservadas: {observacoes_preservadas}"
                )
                break

            # ── Lê o código da observação na linha atual ──
            # Estratégia: a partir do botão de remover, sobe pro <tr> pai
            # e procura dentro dele a célula com headers="table_observacoes:colCodObs"
            try:
                codigo_obs = driver.execute_script("""
                    var btn = arguments[0];
                    // Sobe a árvore até encontrar o <tr> pai
                    var tr = btn.closest('tr');
                    if (!tr) return null;
                    // Dentro da linha, procura a <td> da coluna de código
                    var cell = tr.querySelector('td[headers*="colCodObs"]');
                    return cell ? cell.textContent.trim() : null;
                """, btn_remover)

                print(f"      🔍 Linha {indice_atual}: código observação = {codigo_obs!r}")
            except Exception as e:
                print(f"      ⚠️ Não consegui ler o código da linha {indice_atual}: {e}")
                codigo_obs = None  # Tratamento defensivo

            # ── Decisão: pular ou apagar ──
            if codigo_obs == CODIGO_OBS_INTOCAVEL:
                print(f"      ✋ Código '{CODIGO_OBS_INTOCAVEL}' detectado. PRESERVANDO linha {indice_atual}.")
                observacoes_preservadas += 1
                indice_atual += 1  # Avança pro próximo índice (essa linha fica)
                continue

            # ── Apaga a linha ──
            try:
                driver.execute_script("arguments[0].click();", btn_remover)
                wait_alert.until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                time.sleep(1.5)
                observacoes_excluidas += 1
                print(f"      🗑️ Observação na linha {indice_atual} excluída. Total: {observacoes_excluidas}")
                # NÃO incrementa indice_atual: a próxima linha vira essa posição

            except NoAlertPresentException:
                print("      ⚠️ Cliquei no remover mas o popup não apareceu.")
                registrar_aviso("REVISAR ABA OBSERVAÇÕES — popup de exclusão não apareceu")
                break

            except TimeoutException:
                print("      ⚠️ Timeout esperando o popup de confirmação.")
                registrar_aviso("REVISAR ABA OBSERVAÇÕES — timeout no popup de exclusão")
                break

            except Exception as e:
                print(f"      ⚠️ Erro inesperado ao excluir observação: {e}")
                registrar_aviso(f"REVISAR ABA OBSERVAÇÕES — erro após {observacoes_excluidas} exclusões")
                break
        else:
            print("   ⚠️ Limite de segurança (50) atingido na exclusão de observações!")
            registrar_aviso("REVISAR ABA OBSERVAÇÕES — limite de 50 exclusões atingido")

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
                # PASSO B: Preencher Código e dar TAB
                campo_cod_obs = wait.until(EC.presence_of_element_located((By.ID, "subFrm_observacoes:lovCodTipoObservacao_txtCod")))
                limpar_e_preencher(driver, campo_cod_obs, obs['codigo'])
                campo_cod_obs.send_keys(Keys.TAB)
                time.sleep(1) # Respiro para o ERP carregar a descrição do código

                # PASSO C: Forçar clique na área de texto e digitar
                campo_txt_obs = wait.until(EC.presence_of_element_located((By.ID, "subFrm_observacoes:txtObservacao")))

                # O TRUQUE DO JS AQUI: Foca e clica antes de enviar o texto
                driver.execute_script("arguments[0].focus(); arguments[0].click();", campo_txt_obs)
                time.sleep(0.5)

                limpar_e_preencher(driver, campo_txt_obs, obs['texto'])

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

        # ════════════════════════════════════════════════════
        # ETAPA 7 — ABA CLIENTE (OPERAÇÃO + CONSUMIDOR + CEBAS)
        # Mesma matriz de regras do cadastro novo:
        #   Varejista        → operação 223, consumidor "Não"
        #   Atacadista       → operação 224, consumidor "Não"
        #   Outros + CEBAS   → operação 240, consumidor "Sim"
        #   Outros sem CEBAS → operação 220, consumidor "Sim"
        # Diferença pra reativação: clear robusto antes de cada preenchimento.
        # ════════════════════════════════════════════════════
        print("> 🏢 ETAPA 7: Atualizando regras da Aba Cliente...")

        cnae_desc = str(dados_cliente.get('cnae_principal_descricao', '')).lower()
        tem_cebas = str(dados_cliente.get('tem_cebas', ''))

        codigo_operacao = ""
        valor_consumidor = ""

        # ── Decisão da matriz de regras ──
        if "varejista" in cnae_desc:
            print("   📋 Regra aplicada: VAREJISTA")
            codigo_operacao = "223"
            valor_consumidor = "1"  # Não
        elif "atacadista" in cnae_desc:
            print("   📋 Regra aplicada: ATACADISTA")
            codigo_operacao = "224"
            valor_consumidor = "1"  # Não
        else:
            print("   📋 Regra aplicada: OUTROS — verificando CEBAS...")
            if tem_cebas == "SIM":
                print("      🟢 CEBAS: ATIVO")
                codigo_operacao = "240"
                valor_consumidor = "0"  # Sim
            else:
                print("      ⚪ CEBAS: INATIVO")
                codigo_operacao = "220"
                valor_consumidor = "0"  # Sim

        try:
            # ── 1. Operação ──
            print(f"   ✍️ Atualizando Operação: {codigo_operacao}")
            campo_oper = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmPsClientes:lovCodOper_txtCod"))
            )

            # Captura o valor antigo só pra logar (auditoria visual durante testes)
            valor_oper_antigo = campo_oper.get_attribute("value") or "(vazio)"
            print(f"      🔍 Operação antiga no ERP: {valor_oper_antigo}")

            limpar_e_preencher(driver, campo_oper, codigo_operacao)
            campo_oper.send_keys(Keys.TAB)
            time.sleep(1.5)  # Mesmo respiro do cadastro novo — ERP valida o código

            # ── 2. Consumidor Final ──
            # ⚠️ Aqui NÃO uso limpar_e_preencher — esse campo é um <select>
            # HTML nativo, não um <input> de texto. O Selenium.support.ui.Select
            # já faz a substituição da opção (limpa + seleciona em uma operação).
            label_consumidor = "Não" if valor_consumidor == "1" else "Sim"
            print(f"   🖱️ Marcando Consumidor Final: {label_consumidor}")

            elemento_select = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmPsClientes:cboIndConsumidor"))
            )
            dropdown_consumidor = Select(elemento_select)

            # Loga o valor antigo do dropdown pra auditoria
            try:
                opcao_antiga = dropdown_consumidor.first_selected_option.text
                print(f"      🔍 Consumidor antigo no ERP: {opcao_antiga}")
            except Exception:
                print("      🔍 Consumidor antigo: (não foi possível ler)")

            dropdown_consumidor.select_by_value(valor_consumidor)
            time.sleep(1)

            print("   ✅ Aba Cliente atualizada com sucesso!")

        except Exception as e:
            print(f"   ❌ Erro ao atualizar Aba Cliente: {e}")
            registrar_aviso("REVISAR ABA CLIENTE — Operação ou Consumidor")

        print("> ✅ ETAPA 7 CONCLUÍDA! Regras de Operação/CEBAS aplicadas.")

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

        # ════════════════════════════════════════════════════
        # FASE PRÉVIA — RESET TOTAL DE REPRESENTANTES
        # Apaga TODOS os representantes antigos antes de cadastrar
        # o novo. Mesma estratégia das Etapas 4 (Contatos), 5
        # (Telefones) e do reset de Observações. Sem isso, a
        # reativação duplicaria ou daria erro de duplicidade.
        # ════════════════════════════════════════════════════
        print("> 🗑️ Excluindo representantes antigos antes de recadastrar...")

        # ⚠️ ID PROVISÓRIO: apostando no padrão do ADF Ciamed (mesma
        # estratégia de Contatos/Telefones/Observações). Se quebrar
        # JÁ na primeira iteração sem nenhum representante excluído,
        # me manda o HTML real do botão de lixeira e eu troco o ID.
        ID_BTN_REMOVER_REP = "table_clientesRep:0:btnRemover_clientesRep"

        representantes_excluidos = 0
        LIMITE_SEGURANCA = 50
        wait_alert = WebDriverWait(driver, 5)

        for tentativa in range(LIMITE_SEGURANCA):
            try:
                btn_remover = driver.find_element(By.ID, ID_BTN_REMOVER_REP)
            except NoSuchElementException:
                print(f"   ✅ Grid de representantes limpa. Total excluído: {representantes_excluidos}")
                break

            try:
                driver.execute_script("arguments[0].click();", btn_remover)
                wait_alert.until(EC.alert_is_present())
                driver.switch_to.alert.accept()
                time.sleep(1.5)
                representantes_excluidos += 1
                print(f"      🗑️ Representante {representantes_excluidos} excluído.")

            except NoAlertPresentException:
                print("      ⚠️ Cliquei no remover mas o popup não apareceu.")
                registrar_aviso("REVISAR ABA REPRESENTANTES — popup de exclusão não apareceu")
                break

            except TimeoutException:
                print("      ⚠️ Timeout esperando o popup de confirmação.")
                registrar_aviso("REVISAR ABA REPRESENTANTES — timeout no popup de exclusão")
                break

            except Exception as e:
                print(f"      ⚠️ Erro inesperado ao excluir representante: {e}")
                registrar_aviso(f"REVISAR ABA REPRESENTANTES — erro após {representantes_excluidos} exclusões")
                break
        else:
            print("   ⚠️ Limite de segurança (50) atingido na exclusão de representantes!")
            registrar_aviso("REVISAR ABA REPRESENTANTES — limite de 50 exclusões atingido")

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
                limpar_e_preencher(driver, campo_rep, representante)
                
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


        # ════════════════════════════════════════════════════
        # ETAPA 6 — DATA DE REATIVAÇÃO (ABA COMPLEMENTOS)
        # Campo customizado do ERP: coluna complementar 7.
        # Sempre sobrescreve com a data ATUAL — registra a reativação
        # mais recente. Se já tinha data antiga, ela é substituída.
        # ════════════════════════════════════════════════════

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

        print("> 📅 ETAPA 6: Registrando Data de Reativação...")

        try:
            data_hoje = datetime.now().strftime("%d/%m/%Y")
            print(f"   📆 Data a registrar: {data_hoje}")

            campo_data_reativ = wait.until(
                EC.presence_of_element_located((By.ID, "subFrmColunasCompl:txtVlrColuna_7"))
            )
            limpar_e_preencher(driver, campo_data_reativ, data_hoje)

            # Dispara o onblur (NlFormat.date) pra validar a data agora
            # e não deixar pendência quando o robô avançar a aba.
            campo_data_reativ.send_keys(Keys.TAB)
            time.sleep(0.5)

            print(f"   ✅ Data de Reativação registrada: {data_hoje}")

        except Exception as e:
            print(f"   ❌ Erro ao registrar Data de Reativação: {e}")
            registrar_aviso("REVISAR ABA COMPLEMENTOS — Data de Reativação")

        print("> ✅ ETAPA 6 CONCLUÍDA! Data de reativação gravada.")

        # ════════════════════════════════════════════════════
        # 🚧 TRANSIÇÃO WIZARD
        # ════════════════════════════════════════════════════
        print("> ⏩ Avançando dos Complementos")
        # >>> COLAR AQUI A TRANSIÇÃO DO WIZARD <

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
            limpar_e_preencher(driver, campo_cnae, cnae_apenas_digitos)
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


        

        # ════════════════════════════════════════════════════
        # 🚧 TRANSIÇÃO WIZARD: Aba Cliente → tela final (botão Gravar)
        # No cadastro novo, depois da Aba Cliente vinham mais cliques
        # de "Próximo" pra chegar até a tela onde o botão Gravar fica.
        # Coloca aqui quantos forem necessários.
        # ════════════════════════════════════════════════════
        print("> ⏩ Avançando da Aba Cliente até a tela de Gravar...")
        # >>> COLAR AQUI A TRANSIÇÃO DO WIZARD <

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

    


        # ════════════════════════════════════════════════════
        # ETAPA 8 — FINALIZAÇÃO (GRAVAR + CAPTURAR CÓDIGO)
        # Diferenças cruciais em relação ao cadastro novo:
        #   - NÃO existe popup de protocolo no fim
        #   - O código do cliente é extraído da grid de pessoas,
        #     da célula numérica da linha 0 (a tela "volta" pra busca)
        # ════════════════════════════════════════════════════
        print("> 💾 ETAPA 8: Gravando reativação e capturando código...")

        codigo_cliente_capturado = None

        # ── Passo 8.1: Clicar em Gravar ──
        try:
            # ⚠️ ID PROVISÓRIO: btnCrudGravar é o ID padrão do botão de
            # gravação no Ciamed (mesmo padrão usado em cadastro_item.py).
            # Se quebrar com NoSuchElementException, me manda o HTML do
            # botão real e a gente troca.
            btn_gravar = wait.until(
                EC.element_to_be_clickable((By.ID, "btnCrudGravar"))
            )
            print("   💾 Clicando em Gravar...")
            driver.execute_script("arguments[0].click();", btn_gravar)
        except Exception as e:
            print(f"   ❌ Falha CRÍTICA ao clicar em Gravar: {e}")
            registrar_aviso("REVISAR FINALIZAÇÃO — botão Gravar não foi clicado")
            # Aqui eu NÃO faço raise. A reativação pode até ter sido aplicada,
            # só não conseguimos clicar no botão. Devolvo erro mas com avisos.
            return {
                "status": "Erro",
                "msg": "Não foi possível clicar em Gravar. Verifique manualmente se a reativação foi aplicada.",
                "avisos": avisos
            }

        # ── Passo 8.2: Aguardar o ERP processar e voltar pra grid ──
        print("   ⏳ Aguardando o ERP processar a gravação...")
        time.sleep(2)  # Respiro inicial pra animações/transições do ADF

        # Estratégia defensiva: tenta fechar qualquer popup nativo que
        # possa aparecer (mesmo que o prompt diga que não tem popup de
        # protocolo, pode ter um popup simples de confirmação).
        try:
            wait_alert_curto = WebDriverWait(driver, 3)
            wait_alert_curto.until(EC.alert_is_present())
            alert_text = driver.switch_to.alert.text
            print(f"   ℹ️ Popup detectado pós-gravação: {alert_text!r}")
            driver.switch_to.alert.accept()
            print("   ✅ Popup aceito.")
            time.sleep(1)
        except TimeoutException:
            # Caminho esperado: nenhum popup apareceu, segue o jogo
            print("   ℹ️ Nenhum popup pós-gravação (esperado).")
        except Exception as e:
            print(f"   ⚠️ Erro inesperado ao tentar fechar popup pós-gravação: {e}")

        # Espera pela tabela tabPsPessoas reaparecer (sinal de "voltei pra grid")
        try:
            wait_grid = WebDriverWait(driver, 20)
            wait_grid.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table[contains(@id, 'tabPsPessoas')]//tr[contains(@id, ':0')]")
                )
            )
            print("   ✅ Grid de pessoas reapareceu. Reativação gravada.")
            time.sleep(0.8)  # Estabiliza
        except Exception as e:
            print(f"   ⚠️ Grid não reapareceu após gravar: {e}")
            registrar_aviso("REVISAR FINALIZAÇÃO — grid não voltou após o Gravar")

        # ── Passo 8.3: Extrair o código do cliente da célula numérica ──
        # A célula que tem o código (ex: "8885") é uma <td> com classe
        # "af_column_cell-number" dentro da linha 0 da tabela tabPsPessoas.
        # O número está literalmente "solto" dentro da <td>, depois de
        # todos os <div> e <a> filhos. Por isso usamos JavaScript pra pegar
        # o último text node da célula — assim ignoramos o menu de links
        # ("Cadastro particionado", "Perfis", etc.) e capturamos só o número.
        try:
            print("   🔍 Extraindo código do cliente da grid...")

            # 1. Localiza a célula numérica da linha 0
            celula_codigo = driver.find_element(
                By.XPATH,
                "//table[contains(@id, 'tabPsPessoas')]"
                "//tr[contains(@id, ':0')]"
                "//td[contains(@class, 'af_column_cell-number')]"
            )

            # 2. Extrai o último text node via JavaScript
            #    (ignora os divs/links filhos, pega só o texto solto da <td>)
            codigo_extraido = driver.execute_script("""
                var cell = arguments[0];
                var textNodes = Array.from(cell.childNodes)
                    .filter(function(n) { return n.nodeType === Node.TEXT_NODE; })
                    .map(function(n) { return n.textContent.trim(); })
                    .filter(function(t) { return t.length > 0; });
                return textNodes.length > 0 ? textNodes[textNodes.length - 1] : null;
            """, celula_codigo)

            if codigo_extraido and codigo_extraido.strip().isdigit():
                codigo_cliente_capturado = codigo_extraido.strip()
                print(f"   🏆 CÓDIGO DO CLIENTE CAPTURADO: {codigo_cliente_capturado}")
            else:
                print(f"   ⚠️ Texto extraído não é numérico: {codigo_extraido!r}")
                registrar_aviso("REVISAR FINALIZAÇÃO — código extraído da grid não é numérico")

        except Exception as e:
            print(f"   ❌ Falha ao extrair código do cliente: {e}")
            registrar_aviso("REVISAR FINALIZAÇÃO — não foi possível capturar código do cliente")

        # ── Comparação de sanidade: o código capturado bate com o NL enviado? ──
        # Em uma reativação, o código capturado DEVE ser o mesmo que enviamos
        # como `codigo_nl`. Se for diferente, alguma coisa esquisita rolou
        # (talvez o ERP voltou pra um cliente diferente).
        if codigo_cliente_capturado and codigo_cliente_capturado != codigo_nl:
            print(
                f"   ⚠️ ALERTA: código capturado ({codigo_cliente_capturado}) "
                f"é diferente do NL enviado ({codigo_nl})!"
            )
            registrar_aviso(
                f"REVISAR FINALIZAÇÃO — código capturado ({codigo_cliente_capturado}) "
                f"diferente do NL enviado ({codigo_nl})"
            )

        print("> ✅ ETAPA 8 CONCLUÍDA! Reativação finalizada.")


        # Mensagem final adapta-se ao resultado: se teve avisos, indica
        # que precisa revisão; se não teve, é sucesso limpo.
        if avisos:
            status_final = "Sucesso com avisos"
            msg_final = (
                f"Reativação concluída para o NL {codigo_nl}, "
                f"mas com {len(avisos)} ponto(s) para revisar manualmente."
            )
        else:
            status_final = "Sucesso"
            msg_final = f"Reativação concluída para o NL {codigo_nl} sem nenhum aviso."

        return {
            "status": status_final,
            "msg": msg_final,
            "avisos": avisos,
            "codigo_cliente": codigo_cliente_capturado,  # ← chave nova
        }

    except Exception as e:
        print(f"> ❌ Erro Crítico: {e}")
        return {
            "status": "Erro",
            "msg": str(e),
            "avisos": avisos,
            "codigo_cliente": None,
        }

    finally:
        # Mantém o navegador aberto durante os primeiros testes pra você conferir.
        # Quando o robô estiver estável, descomenta a linha abaixo.
        # driver.quit()
        print("> 🏁 Fim da execução do robô de reativação.")


# ─────────────────────────────────────────────────────────────
# TESTE DE BANCADA — REATIVAÇÃO COMPLETA
# Roda direto no terminal: python -m automacoes.clientes.cadastro_reativacao
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧪 Iniciando Teste de Bancada — REATIVAÇÃO COMPLETA...")
    print("=" * 60)

    dados_teste = {
        # ════════════════════════════════════════════════
        # 🔑 CAMPO CRÍTICO — sem isso o robô nem abre o Chrome
        # ════════════════════════════════════════════════
        "codigo_nl": "13477",  # ← TROCAR pelo NL do cliente que vai testar

        # ════════════════════════════════════════════════
        # ETAPA 2 — Dados Básicos + Endereço
        # ════════════════════════════════════════════════
        "cnpj_limpo": "02293129000160",
        "razao_social": "ESSE CAMPO DEU CERTO",
        "nome_fantasia": "ESSE TAMBEM",
        "inscricao_estadual": "ISENTO",  # ou um número real, ou "ISENTO / NÃO ENCONTRADA"
        "cnae_principal_descricao": "8630-5/02 - Atividade médica ambulatorial",
        "cep": "95960000",
        "logradouro": "Rua Antonio Bratti",
        "numero": "25",
        "complemento": "Casa",
        "bairro": "Centro",
        "uf": "PB",  # ⚠️ Se mudar pra "RS", o robô PULA o campo de região (trava do RS)

        # ════════════════════════════════════════════════
        # ETAPA 3 — Bloqueio (decisão da farmacêutica)
        # ════════════════════════════════════════════════
        # Casos possíveis:
        #   None        → fallback "30" (mais comum)
        #   "manter"    → preserva valor antigo se existir, senão "30"
        #   "alterar"   → usa o valor_bloqueio
        "acao_bloqueio": None,
        "valor_bloqueio": None,  # só usado quando acao_bloqueio == "alterar"

        # ════════════════════════════════════════════════
        # ABA COMENTÁRIOS — Regra de Faturamento
        # ════════════════════════════════════════════════
        # "CAIXA"    → adiciona comentário "FATURAR EM CAIXA!"
        # "UNITARIO" (ou qualquer outro) → pula
        "regra_faturamento": "CAIXA",

        # ════════════════════════════════════════════════
        # ETAPA 4 — Contatos (lista, vai virar loop)
        # ════════════════════════════════════════════════
        "email_xml": "nfe@doctorscenter.com.br",
        "contatos_da_tela": [
            {
                "nome": "CLAUD.ANE",
                "codigo": "39",  # 39 = docs (segundo o cadastro_novo)
                "tel": "83988887777",
                "email": "compras@doctorscenter.com.br",
                "check_boleto": False,
                "check_docs": True,
            },
            {
                "nome": "BERNARDO DZ",
                "codigo": "50",  # 50 = boleto
                "tel": "83988886666",
                "email": "financeiro@doctorscenter.com.br",
                "check_boleto": True,
                "check_docs": False,
            },
        ],

        # ════════════════════════════════════════════════
        # ETAPA 5 — Telefones (lista nova OU string legada)
        # ════════════════════════════════════════════════
        # Caminho moderno (lista) — descomenta pra testar:
        # "telefones_da_tela": [
        #     {"numero": "8333334444", "descricao": "TELEFONE DA EMPRESA"},
        #     {"numero": "8399998888", "descricao": "WHATSAPP COMPRAS"},
        # ],
        # Caminho legado (string única) — usado por padrão:
        "telefone_empresa": "8333334444",

        # ════════════════════════════════════════════════
        # ETAPA 7 — Aba Cliente (matriz CEBAS)
        # ════════════════════════════════════════════════
        # "tem_cebas" só importa quando o CNAE NÃO é varejista nem atacadista.
        # Valores aceitos: "SIM" → operação 240, qualquer outro → 220
        "tem_cebas": "NAO",

        # ════════════════════════════════════════════════
        # ABA REPRESENTANTES + MÁSCARAS
        # ════════════════════════════════════════════════
        "representante": "ALDOVANDO",  # vazio "" pra pular
        "vendedor": "CLAUDIANE",            # vazio "" pra pular

        # ════════════════════════════════════════════════
        # ABA COMPLEMENTOS — Forma de Captação (dropdown)
        # ════════════════════════════════════════════════
        # Esse valor precisa ser um dos códigos válidos do dropdown do ERP.
        # Se não souber, deixa vazio "" — o robô só pula esse campo.
        "forma_captacao": "WHATSAPP",
    }

    print(f"📋 Cliente NL: {dados_teste['codigo_nl']}")
    print(f"📋 Razão Social: {dados_teste['razao_social']}")
    print(f"📋 Ação Bloqueio: {dados_teste['acao_bloqueio'] or '(fallback 30)'}")
    print(f"📋 Regra Faturamento: {dados_teste['regra_faturamento']}")
    print(f"📋 Contatos no payload: {len(dados_teste.get('contatos_da_tela', []))}")
    print(f"📋 Telefone: {dados_teste.get('telefone_empresa', '(vazio)')}")
    print("=" * 60)

    resultado = executar(dados_teste)

    print("\n" + "=" * 60)
    print("🏁 RESULTADO FINAL DO ROBÔ")
    print("=" * 60)
    print(f"Status: {resultado.get('status')}")
    print(f"Mensagem: {resultado.get('msg')}")
    print(f"Código do cliente: {resultado.get('codigo_cliente') or '(não capturado)'}")

    avisos_finais = resultado.get('avisos', [])
    if avisos_finais:
        print(f"\n⚠️ {len(avisos_finais)} AVISO(S) ACUMULADO(S):")
        for i, aviso in enumerate(avisos_finais, start=1):
            print(f"   {i}. {aviso}")
    else:
        print("\n✅ Nenhum aviso! Reativação 100% limpa.")
    print("=" * 60)