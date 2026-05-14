# ══════════════════════════════════════════════════════════════
# scripts/seed_dados_notas.py
# ══════════════════════════════════════════════════════════════
# Popula as tabelas centros_custo e operacoes_nota a partir dos
# arquivos .txt em scripts/dados/.
#
# Uso:
#   python scripts/seed_dados_notas.py            → adiciona só os novos
#   python scripts/seed_dados_notas.py --limpar   → apaga tudo e refaz
# ══════════════════════════════════════════════════════════════

import os
import sys
import argparse

# Adiciona a raiz do projeto no path (pra conseguir importar app, models, etc)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models import CentroCusto, OperacaoNota

# ── Caminhos dos arquivos de origem ─────────────────────────
PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados')
ARQUIVO_CC  = os.path.join(PASTA_DADOS, 'lista_cc.txt')
ARQUIVO_OP  = os.path.join(PASTA_DADOS, 'lista_operacoes.txt')


# ══════════════════════════════════════════════════════════════
# PARSER DE CENTROS DE CUSTO
# ══════════════════════════════════════════════════════════════
# Estrutura do arquivo:
#   '01100 - Auxiliares'           → grupo (5 dígitos) → IGNORA
#   '01100001 - Portaria...'       → CC selecionável (8 dígitos) → SALVA
#   '02 - Ciamed SP'               → empresa (2 dígitos) → atualiza contexto
#
# A primeira empresa (01) não tem header no arquivo — começa direto
# com '01100 - Auxiliares', então usamos 'Ciamed RS' como padrão inicial.
# ══════════════════════════════════════════════════════════════

def parsear_centros_custo():
    """Lê lista_cc.txt e retorna lista de dicts {codigo, descricao, empresa}."""
    centros = []
    empresa_atual = 'Ciamed RS'   # padrão para o primeiro bloco (código 01)

    with open(ARQUIVO_CC, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or ' - ' not in linha:
                continue

            # Separa só na PRIMEIRA ocorrência de ' - ' (descrição pode ter outros traços)
            codigo, descricao = linha.split(' - ', 1)
            codigo    = codigo.strip()
            descricao = descricao.strip()

            if not codigo.isdigit():
                continue

            # Classifica pela quantidade de dígitos
            if len(codigo) == 2:
                # Header de empresa — atualiza contexto e segue
                empresa_atual = descricao
            elif len(codigo) == 8:
                # Centro de custo selecionável
                centros.append({
                    'codigo':    codigo,
                    'descricao': descricao,
                    'empresa':   empresa_atual,
                })
            # len 5 (grupo) → ignora silenciosamente

    return centros


# ══════════════════════════════════════════════════════════════
# PARSER DE OPERAÇÕES
# ══════════════════════════════════════════════════════════════
# Estrutura do arquivo:
#   '100 - COMPRA DE MERCADORIAS PARA REVENDA'
#   '1.000 - 999 - ESTORNO...'   ← preservar código '1.000' exato
# ══════════════════════════════════════════════════════════════

def parsear_operacoes():
    """Lê lista_operacoes.txt e retorna lista de dicts {codigo, descricao}."""
    operacoes = []

    with open(ARQUIVO_OP, encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or ' - ' not in linha:
                continue

            codigo, descricao = linha.split(' - ', 1)
            codigo    = codigo.strip()
            descricao = descricao.strip()

            if not codigo:
                continue

            operacoes.append({
                'codigo':    codigo,
                'descricao': descricao,
            })

    return operacoes


# ══════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════

def executar(limpar=False):
    """Popula o banco com centros de custo e operações."""

    # Garante que estamos no app context do Flask (pra ter acesso ao db)
    with app.app_context():

        if limpar:
            print('🧹 Limpando tabelas antigas...')
            db.session.query(CentroCusto).delete()
            db.session.query(OperacaoNota).delete()
            db.session.commit()

        # ── Centros de Custo ──────────────────────────────────
        print(f'\n📂 Lendo {ARQUIVO_CC}...')
        ccs = parsear_centros_custo()
        print(f'   → {len(ccs)} centros de custo encontrados.')

        novos_cc = 0
        for cc in ccs:
            existente = CentroCusto.query.filter_by(codigo=cc['codigo']).first()
            if existente:
                # Já existe: atualiza descrição e empresa caso tenham mudado
                existente.descricao = cc['descricao']
                existente.empresa   = cc['empresa']
            else:
                db.session.add(CentroCusto(**cc))
                novos_cc += 1

        # ── Operações ─────────────────────────────────────────
        print(f'\n📂 Lendo {ARQUIVO_OP}...')
        ops = parsear_operacoes()
        print(f'   → {len(ops)} operações encontradas.')

        novas_op = 0
        for op in ops:
            existente = OperacaoNota.query.filter_by(codigo=op['codigo']).first()
            if existente:
                existente.descricao = op['descricao']
            else:
                db.session.add(OperacaoNota(**op))
                novas_op += 1

        db.session.commit()

        print('\n✅ Seed concluído!')
        print(f'   - Centros de custo: {novos_cc} novos, {len(ccs) - novos_cc} atualizados')
        print(f'   - Operações:        {novas_op} novas, {len(ops) - novas_op} atualizadas')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Popula centros de custo e operações.')
    parser.add_argument('--limpar', action='store_true',
                        help='Apaga todas as linhas antes de inserir (cuidado!)')
    args = parser.parse_args()

    executar(limpar=args.limpar)