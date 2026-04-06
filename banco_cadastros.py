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