# ══════════════════════════════════════════════════════════════
# scripts/seed_faq.py — Popula o FAQ inicial da Central de Suporte
# ══════════════════════════════════════════════════════════════
# Uso:
#   python scripts/seed_faq.py
#
# Seguro para rodar múltiplas vezes: verifica se já existe antes
# de inserir (usa pergunta como chave de deduplicação).
# ══════════════════════════════════════════════════════════════

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app import app
from extensions import db
from models import FaqPergunta


FAQ_SEED = [
    # ── Cadastro de Itens ─────────────────────────────────────
    {
        'modulo': 'itens',
        'pergunta': 'A SEFAZ está retornando erro de comunicação. E agora?',
        'resposta': 'Esse erro geralmente ocorre por instabilidade no webservice da SEFAZ. Aguarde alguns minutos e tente novamente. Se persistir após 30 minutos, abra um chamado anexando o XML da nota.',
        'ordem': 1,
    },
    {
        'modulo': 'itens',
        'pergunta': 'O NCM não foi validado no sistema.',
        'resposta': 'O NCM precisa estar atualizado na tabela TIPI vigente. Verifique se o código tem 8 dígitos e se não está marcado como descontinuado. Em caso de dúvida, consulte o time fiscal ou abra um chamado.',
        'ordem': 2,
    },
    {
        'modulo': 'itens',
        'pergunta': 'Onde ficam salvos os XMLs baixados?',
        'resposta': 'Os XMLs são salvos automaticamente na pasta segura do servidor da Ciamed, organizados por mês. Não é necessário salvar manualmente no seu computador.',
        'ordem': 3,
    },

    # ── Relatório MDF-e ───────────────────────────────────────
    {
        'modulo': 'mdf',
        'pergunta': 'O relatório está mostrando dados de um período errado.',
        'resposta': 'O relatório usa o fuso horário do servidor (UTC-3). Confirme se o filtro de datas foi preenchido corretamente. As datas são inclusivas em ambos os extremos.',
        'ordem': 1,
    },
    {
        'modulo': 'mdf',
        'pergunta': 'Como exportar o relatório em Excel?',
        'resposta': 'Após gerar o relatório, clique no botão "Exportar" no canto superior direito e selecione "Excel (.xlsx)". O download começa automaticamente.',
        'ordem': 2,
    },

    # ── Cadastro de Fornecedor ────────────────────────────────
    {
        'modulo': 'fornecedor',
        'pergunta': 'O CNPJ não foi encontrado na consulta.',
        'resposta': 'O robô consulta a BrasilAPI. Se o CNPJ não foi encontrado, verifique se está ativo na Receita Federal. Em casos raros, a BrasilAPI pode estar fora do ar — tente novamente em 10 minutos.',
        'ordem': 1,
    },

    # ── Cadastro de Clientes ──────────────────────────────────
    {
        'modulo': 'clientes',
        'pergunta': 'O vendedor enviou a ficha mas ela não aparece no monitor.',
        'resposta': 'Verifique se o status da ficha está como "enviada". Fichas em rascunho não aparecem no monitor central. Se já está enviada, aguarde até 5 minutos para o monitor atualizar.',
        'ordem': 1,
    },
    {
        'modulo': 'clientes',
        'pergunta': 'O vendedor pode editar a ficha depois de enviar?',
        'resposta': 'Após o envio, apenas o time de cadastro pode editar a ficha. O vendedor pode adicionar comentários, mas não alterar campos críticos como CNPJ ou razão social.',
        'ordem': 2,
    },

    # ── Lançamento de Notas ───────────────────────────────────
    {
        'modulo': 'lancamento_notas',
        'pergunta': 'O que significa o status "a rever"?',
        'resposta': '"A rever" indica que o robô encontrou inconsistências (ex: NCM divergente, CFOP suspeito) e a nota precisa de validação manual antes de seguir para o ERP.',
        'ordem': 1,
    },
    {
        'modulo': 'lancamento_notas',
        'pergunta': 'Posso relançar uma nota cancelada?',
        'resposta': 'Sim, mas a nota cancelada precisa ser excluída primeiro do sistema. Use a opção "Limpar lançamento" antes de tentar novamente.',
        'ordem': 2,
    },

    # ── Geral ─────────────────────────────────────────────────
    {
        'modulo': 'geral',
        'pergunta': 'Esqueci minha senha do Hub.',
        'resposta': 'Entre em contato com o setor de TI. Um administrador pode resetar sua senha pelo Painel Admin > Gestão de Usuários.',
        'ordem': 1,
    },
    {
        'modulo': 'geral',
        'pergunta': 'Quem tem acesso ao Hub?',
        'resposta': 'O acesso é liberado pelo TI mediante solicitação do gestor da área. Cada colaborador tem permissão somente aos módulos do seu setor, definidas pelo administrador.',
        'ordem': 2,
    },
]


def seed():
    with app.app_context():
        inseridos = 0
        existentes = 0

        for faq in FAQ_SEED:
            # Verifica se já existe (mesma pergunta + módulo)
            existe = FaqPergunta.query.filter_by(
                modulo=faq['modulo'],
                pergunta=faq['pergunta'],
            ).first()

            if existe:
                existentes += 1
                continue

            nova = FaqPergunta(**faq)
            db.session.add(nova)
            inseridos += 1

        db.session.commit()
        print(f"✅ Seed FAQ concluído: {inseridos} inseridas, {existentes} já existiam.")


if __name__ == '__main__':
    seed()