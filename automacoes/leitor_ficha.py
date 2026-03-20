import openpyxl
import requests

def processar_ficha_cliente(caminho_arquivo):
    try:
        # 1. Carrega o Excel (data_only=True pega o valor e não a fórmula)
        wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
        planilha = wb.active

        # 2. Lendo a Chave Mestre (CNPJ) e limpando
        cnpj_cru = str(planilha['U76'].value or "").strip()
        cnpj_limpo = cnpj_cru.replace('.', '').replace('/', '').replace('-', '')

        if not cnpj_limpo:
            return {"erro": True, "mensagem": "CNPJ não encontrado na célula U76 da ficha."}

        # 3. Identificando o Tipo de Cadastro (Novo ou Reativação)
        is_novo = str(planilha['E237'].value or "").strip().upper() == 'X'
        is_reativacao = str(planilha['X237'].value or "").strip().upper() == 'X'
        
        tipo_cadastro = "NOVO" if is_novo else "REATIVACAO" if is_reativacao else "DESCONHECIDO"
        codigo_cliente = str(planilha['AG242'].value or "").strip() if tipo_cadastro == "REATIVACAO" else ""

        # 4. Lendo Regras de Faturamento (Blindagem Ciamed: Unitário é o padrão absoluto)
        fat_caixa = str(planilha['E197'].value or "").strip().upper() == 'X'
        fat_unitario = str(planilha['E202'].value or "").strip().upper() == 'X'
        
        # Se marcou APENAS Caixa, fica Caixa. Qualquer outra situação (marcou os dois, nenhum, ou só Unitário) fica Unitário.
        if fat_caixa and not fat_unitario:
            regra_faturamento = "Caixa"
        else:
            regra_faturamento = "Unitário"

        # 5. Montando o pacote de dados EXCEL
        dados = {
            "erro": False,
            "origem": "excel",
            "cnpj": cnpj_cru,
            "cnpj_limpo": cnpj_limpo,
            "tipo_cadastro": tipo_cadastro,
            "codigo_cliente": codigo_cliente,
            
            # Matriz de Contatos
            "email_xml": str(planilha['BM93'].value or "").strip(),
            
            "compras_nome": str(planilha['L99'].value or "").strip(),
            "compras_tel": str(planilha['AL99'].value or "").strip(),
            "compras_email": str(planilha['BM99'].value or "").strip(),
            
            "rec_nome": str(planilha['L103'].value or "").strip(),
            "rec_tel": str(planilha['AL103'].value or "").strip(),
            "rec_email": str(planilha['BM103'].value or "").strip(),
            
            "fin_nome": str(planilha['L107'].value or "").strip(),
            "fin_tel": str(planilha['AL107'].value or "").strip(),
            "fin_email": str(planilha['BM107'].value or "").strip(),
            
            "farma_nome": str(planilha['L111'].value or "").strip(),
            "farma_tel": str(planilha['AL111'].value or "").strip(),
            "farma_email": str(planilha['BM111'].value or "").strip(),
            
            # Comercial
            "regra_faturamento": regra_faturamento,
            "vendedor": str(planilha['T248'].value or "").strip(),
            "representante": str(planilha['BD248'].value or "").strip(),
            "captacao": str(planilha['R255'].value or "").strip()
        }

        # 6. ENRIQUECIMENTO FISCAL (API cnpj.ws)
        try:
            url_api = f'https://publica.cnpj.ws/cnpj/{cnpj_limpo}'
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url_api, headers=headers, timeout=45)
            
            if resp.status_code == 200:
                api_json = resp.json()
                
                # Pegando dados básicos da API
                dados["razao_social"] = api_json.get("razao_social", "")
                dados["nome_fantasia"] = api_json.get("estabelecimento", {}).get("nome_fantasia", "")
                
                # Endereço
                end = api_json.get("estabelecimento", {})
                dados["cep"] = end.get("cep", "")
                dados["logradouro"] = f"{end.get('tipo_logradouro', '')} {end.get('logradouro', '')}".strip()
                dados["numero"] = end.get("numero", "")
                dados["bairro"] = end.get("bairro", "")
                dados["cidade"] = end.get("cidade", {}).get("nome", "")
                dados["estado"] = end.get("estado", {}).get("sigla", "")
                
                # CNAE Principal
                dados["cnae_principal"] = end.get("atividade_principal", {}).get("descricao", "")
                
                # Filtrando Inscrições Estaduais (Apenas ATIVAS)
                ies_ativas = []
                for ie in end.get("inscricoes_estaduais", []):
                    if ie.get("ativo") == True:
                        ies_ativas.append(ie.get("inscricao_estadual"))
                
                # Se achou IEs ativas, junta com vírgula. Se não, avisa.
                dados["inscricao_estadual"] = ", ".join(ies_ativas) if ies_ativas else "Isento / Não encontrada"
                
            else:
                dados["aviso_api"] = f"Aviso: Não foi possível consultar a Receita Federal (Status {resp.status_code})"
                
        except Exception as e:
            dados["aviso_api"] = f"Aviso: Falha de comunicação com a Receita Federal ({str(e)})"

        return dados

    except Exception as e:
        return {"erro": True, "mensagem": f"Erro ao processar a planilha: {str(e)}"}