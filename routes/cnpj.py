# ══════════════════════════════════════════════════════════════
# routes/cnpj.py — Consultas de CNPJ
# ══════════════════════════════════════════════════════════════

import requests
from flask import Blueprint, render_template, jsonify
from utils.auth import permissao_required

cnpj_bp = Blueprint('cnpj', __name__)


@cnpj_bp.route('/consulta_cnpj/<cnpj>')
def consulta_cnpj(cnpj):
    try:
        headers  = {'User-Agent': 'Mozilla/5.0'}
        url      = f'https://publica.cnpj.ws/cnpj/{cnpj}'
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data   = response.json()
            estabs = data.get('estabelecimento', {})
            uf_fornecedor = estabs.get('estado', {}).get('sigla')
            lista_ie      = estabs.get('inscricoes_estaduais', [])
            ie_ativa      = ""
            for item in lista_ie:
                if item.get('estado', {}).get('sigla') == uf_fornecedor and item.get('ativo') is True:
                    ie_ativa = item.get('inscricao_estadual')
                    break
            simples    = data.get('simples') or {}
            status_mei = "SIM" if simples.get('mei') == 'Sim' else "NÃO"
            resultado  = {
                'razao_social':    data.get('razao_social'),
                'nome_fantasia':   estabs.get('nome_fantasia'),
                'cnpj':            cnpj,
                'inscricao_estadual': ie_ativa,
                'mei':             status_mei,
                'logradouro':      f"{estabs.get('tipo_logradouro', '')} {estabs.get('logradouro', '')}".strip(),
                'numero':          estabs.get('numero'),
                'complemento':     estabs.get('complemento'),
                'bairro':          estabs.get('bairro'),
                'cep':             estabs.get('cep'),
                'uf':              uf_fornecedor,
                'municipio':       estabs.get('cidade', {}).get('nome'),
                'cnae_fiscal':     estabs.get('atividade_principal', {}).get('id'),
                'cnae_fiscal_descricao': estabs.get('atividade_principal', {}).get('descricao'),
                'data_inicio_atividade': estabs.get('data_inicio_atividade'),
                'descricao_identificador_matriz_filial': "MATRIZ" if estabs.get('tipo') == "Matriz" else "FILIAL",
                'codigo_natureza_juridica': data.get('natureza_juridica', {}).get('id'),
                'natureza_juridica': data.get('natureza_juridica', {}).get('descricao')
            }
            return jsonify(resultado)
        else:
            msg = "CNPJ não encontrado ou erro na API."
            if response.status_code == 429:
                msg = "Muitas consultas! Aguarde 1 minuto."
            return jsonify({'erro': True, 'message': msg}), response.status_code
    except Exception as e:
        return jsonify({'erro': True, 'message': str(e)}), 500


@cnpj_bp.route('/api/cnpj_completo/<cnpj>')
def api_cnpj_completo(cnpj):
    try:
        cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
        headers    = {'User-Agent': 'Mozilla/5.0'}
        url        = f'https://publica.cnpj.ws/cnpj/{cnpj_limpo}'
        response   = requests.get(url, headers=headers, timeout=45)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            msg = "CNPJ não encontrado."
            if response.status_code == 429:
                msg = "Muitas consultas! Aguarde 1 minuto e tente novamente."
            return jsonify({'erro': True, 'message': msg}), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({'erro': True, 'message': "A API demorou muito. Tente novamente!"}), 504
    except Exception as e:
        return jsonify({'erro': True, 'message': f"Erro de comunicação: {str(e)}"}), 500


@cnpj_bp.route('/consulta_cnpj_completa')
@permissao_required('cnpj')
def consulta_cnpj_completa():
    return render_template('consulta_cnpj.html')
