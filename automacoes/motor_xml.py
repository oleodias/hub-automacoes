import xml.etree.ElementTree as ET
import os

def extrair_dados_xml(caminho_arquivo):
    """
    Lê um arquivo XML de NFe e retorna uma lista de dicionários.
    Blindado contra erros de tags vazias (NoneType).
    """
    print(f"📂 Lendo arquivo: {caminho_arquivo}")
    
    try:
        if not os.path.exists(caminho_arquivo):
            print(f"❌ Erro: Arquivo não encontrado: {caminho_arquivo}")
            return []

        tree = ET.parse(caminho_arquivo)
        root = tree.getroot()

        # Namespace padrão da NFe
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        lista_itens = []

        # --- FUNÇÃO AUXILIAR PARA EVITAR O ERRO 'NONETYPE' ---
        def get_text(elemento_pai, tag_nome):
            """Busca a tag e retorna o texto limpo. Se for None, retorna string vazia."""
            el = elemento_pai.find(tag_nome, ns)
            if el is not None and el.text is not None:
                return el.text.strip()
            return ""
        # -----------------------------------------------------

        # Itera sobre cada tag <det> (que representa um item da nota)
        for i, det in enumerate(root.findall('.//nfe:det', ns), 1):
            prod = det.find('nfe:prod', ns)

            if prod is not None:
                # 1. Extração da Descrição
                descricao = get_text(prod, 'nfe:xProd').upper()
                if not descricao: descricao = "SEM DESCRIÇÃO"

                # 2. Extração do EAN (cEAN)
                ean = get_text(prod, 'nfe:cEAN')
                
                # Limpeza do EAN (remove "SEM GTIN" ou vazios)
                if not ean or ean.upper() == "SEM GTIN":
                    ean = None 

                # 3. Extração do NCM
                ncm = get_text(prod, 'nfe:NCM')

                # 4. Extração da Unidade (uCom)
                unidade = get_text(prod, 'nfe:uCom').upper()
                if not unidade: unidade = "UN"

                # Monta o objeto do item
                item = {
                    'index': i,
                    'desc': descricao,
                    'ean': ean,
                    'ncm': ncm,
                    'unid': unidade
                }
                
                lista_itens.append(item)
                # Opcional: Mostra no terminal o que leu para você conferir
                # print(f"   - Item {i}: {descricao} (NCM: {ncm})")

        print(f"✅ Sucesso! {len(lista_itens)} itens extraídos do XML.")
        return lista_itens

    except Exception as e:
        print(f"❌ Erro crítico ao ler XML: {e}")
        return []

# Bloco de teste rápido
if __name__ == "__main__":
    # Pega o primeiro XML da pasta XML_Entrada automaticamente para testar
    pasta = "XML_Entrada"
    if os.path.exists(pasta):
        arquivos = [f for f in os.listdir(pasta) if f.lower().endswith('.xml')]
        if arquivos:
            dados = extrair_dados_xml(os.path.join(pasta, arquivos[0]))
            for d in dados:
                print(d)
        else:
            print("Nenhum XML encontrado na pasta para teste.")