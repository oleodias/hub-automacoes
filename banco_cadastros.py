import sqlite3
import os
import json
from datetime import datetime

# ── CAMINHO DO BANCO ───────────────────────────────────────────────────────────
# Fica dentro de 'dados/', mesma pasta usada pelos chamados
DB_PATH = os.path.join('dados', 'cadastros.db')


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO — chame isso uma vez ao subir o Flask
# ══════════════════════════════════════════════════════════════════════════════

def init_db():
    """Cria a tabela 'submissoes' se ainda não existir."""
    os.makedirs('dados', exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS submissoes (
                uuid                TEXT PRIMARY KEY,
                cnpj                TEXT NOT NULL,
                razao_social        TEXT,
                tentativa           INTEGER DEFAULT 1,
                status              TEXT DEFAULT 'pendente',
                dados_json          TEXT,
                docs_enviados       TEXT DEFAULT '[]',
                motivos_reprovacao  TEXT DEFAULT '[]',
                created_at          TEXT,
                updated_at          TEXT
            )
        ''')
        conn.commit()
    print("✅ [BD] Banco de cadastros inicializado.")


# ══════════════════════════════════════════════════════════════════════════════
# OPERAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

def salvar_submissao(uuid, cnpj, razao_social, dados_json, docs_enviados):
    """
    Salva uma nova submissão (1ª tentativa).

    docs_enviados: lista com nomes dos campos que tiveram arquivo enviado.
    Exemplo: ['doc_alvara', 'doc_crt', 'doc_contrato']
    """
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            INSERT INTO submissoes
            (uuid, cnpj, razao_social, tentativa, status,
             dados_json, docs_enviados, motivos_reprovacao, created_at, updated_at)
            VALUES (?, ?, ?, 1, 'pendente', ?, ?, '[]', ?, ?)
        ''', (
            uuid, cnpj, razao_social,
            json.dumps(dados_json, ensure_ascii=False),
            json.dumps(docs_enviados),
            agora, agora
        ))
        conn.commit()
    print(f"✅ [BD] Submissão salva | UUID: {uuid} | Empresa: {razao_social}")


def buscar_submissao(uuid):
    """
    Retorna dados de uma submissão pelo UUID.
    Retorna None se não encontrar.

    Campos já desserializados no retorno:
      - dados_json          → dict
      - docs_enviados       → list
      - motivos_reprovacao  → list de dicts {'tentativa', 'motivo', 'data'}
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT * FROM submissoes WHERE uuid = ?', (uuid,)).fetchone()
        if not row:
            return None
        dados = dict(row)
        dados['dados_json']         = json.loads(dados['dados_json'])
        dados['docs_enviados']      = json.loads(dados['docs_enviados'])
        dados['motivos_reprovacao'] = json.loads(dados['motivos_reprovacao'])
        return dados


def registrar_reprovacao(uuid, motivo):
    """
    Adiciona um motivo de reprovação ao histórico e muda o status para 'reprovado'.
    O histórico é acumulativo — cada tentativa reprovada fica registrada.
    Retorna True se encontrou o UUID, False caso contrário.
    """
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    sub   = buscar_submissao(uuid)

    if not sub:
        print(f"⚠️ [BD] UUID não encontrado para reprovação: {uuid}")
        return False

    motivos = sub['motivos_reprovacao']
    motivos.append({
        'tentativa': sub['tentativa'],
        'motivo':    motivo,
        'data':      agora
    })

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            UPDATE submissoes
            SET status = 'reprovado', motivos_reprovacao = ?, updated_at = ?
            WHERE uuid = ?
        ''', (json.dumps(motivos, ensure_ascii=False), agora, uuid))
        conn.commit()

    print(f"❌ [BD] Reprovação registrada | UUID: {uuid} | Tentativa: {sub['tentativa']}")
    return True


def incrementar_tentativa(uuid, dados_json, docs_enviados):
    """
    Atualiza a submissão com os dados da correção:
      - Incrementa o contador de tentativas
      - Volta o status para 'pendente'
      - Substitui dados_json e docs_enviados pelos novos valores
    Retorna o número da nova tentativa, ou None se UUID não existir.
    """
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    sub   = buscar_submissao(uuid)

    if not sub:
        print(f"⚠️ [BD] UUID não encontrado para incrementar: {uuid}")
        return None

    nova_tentativa = sub['tentativa'] + 1

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            UPDATE submissoes
            SET tentativa = ?, status = 'pendente',
                dados_json = ?, docs_enviados = ?, updated_at = ?
            WHERE uuid = ?
        ''', (
            nova_tentativa,
            json.dumps(dados_json, ensure_ascii=False),
            json.dumps(docs_enviados),
            agora, uuid
        ))
        conn.commit()

    print(f"🔄 [BD] Nova tentativa | UUID: {uuid} | Tentativa: {nova_tentativa}")
    return nova_tentativa


def atualizar_status(uuid, status):
    """
    Atualiza apenas o status de uma submissão.
    Status válidos: 'pendente', 'aprovado', 'reprovado'
    """
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'UPDATE submissoes SET status = ?, updated_at = ? WHERE uuid = ?',
            (status, agora, uuid)
        )
        conn.commit()
    print(f"📋 [BD] Status atualizado | UUID: {uuid} | Status: {status}")

# ══════════════════════════════════════════════════════════════════════════════
# ADICIONAR ESTAS DUAS FUNÇÕES NO FINAL DO banco_cadastros.py
# ══════════════════════════════════════════════════════════════════════════════

def listar_submissoes(status=None, tipo=None, busca=None, data_de=None, data_ate=None):
    """
    Retorna lista de todas as submissões com filtros opcionais.
    Usada pela tela de Monitor de Cadastros.

    Filtros:
      status   → 'pendente' | 'aprovado' | 'reprovado' | 'cadastrado'
      tipo     → 'NOVO' | 'REATIVACAO' (busca dentro do dados_json)
      busca    → texto livre para empresa ou CNPJ
      data_de  → string 'dd/mm/yyyy'
      data_ate → string 'dd/mm/yyyy'
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            'SELECT * FROM submissoes ORDER BY created_at DESC'
        ).fetchall()

    resultado = []
    for row in rows:
        dados = dict(row)
        try:
            dados['dados_json']         = json.loads(dados['dados_json'])
        except Exception:
            dados['dados_json']         = {}
        try:
            dados['docs_enviados']      = json.loads(dados['docs_enviados'])
        except Exception:
            dados['docs_enviados']      = []
        try:
            dados['motivos_reprovacao'] = json.loads(dados['motivos_reprovacao'])
        except Exception:
            dados['motivos_reprovacao'] = []

        d = dados['dados_json']

        # Filtro por status
        if status and dados.get('status') != status:
            continue

        # Filtro por tipo (dentro do dados_json)
        if tipo and d.get('tipo_cadastro') != tipo:
            continue

        # Filtro por busca (empresa ou CNPJ)
        if busca:
            b = busca.lower()
            empresa = (dados.get('razao_social') or '').lower()
            cnpj    = (dados.get('cnpj') or '').lower()
            if b not in empresa and b not in cnpj:
                continue

        # Filtro por data
        if data_de or data_ate:
            created = dados.get('created_at', '')  # formato 'dd/mm/yyyy HH:MM'
            try:
                partes = created.split(' ')[0].split('/')  # ['dd','mm','yyyy']
                data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"  # 'yyyy-mm-dd'
                if data_de:
                    de_iso = '-'.join(reversed(data_de.split('/'))) if '/' in data_de else data_de
                    if data_iso < de_iso:
                        continue
                if data_ate:
                    ate_iso = '-'.join(reversed(data_ate.split('/'))) if '/' in data_ate else data_ate
                    if data_iso > ate_iso:
                        continue
            except Exception:
                pass

        resultado.append(dados)

    return resultado


def stats_submissoes():
    """
    Retorna contagem por status para o painel de estatísticas.
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            'SELECT status, COUNT(*) as total FROM submissoes GROUP BY status'
        ).fetchall()

    contagem = {'total': 0, 'pendente': 0, 'aprovado': 0, 'reprovado': 0, 'cadastrado': 0}
    for row in rows:
        status = row[0] or 'pendente'
        qtd    = row[1]
        if status in contagem:
            contagem[status] += qtd
        contagem['total'] += qtd

    return contagem