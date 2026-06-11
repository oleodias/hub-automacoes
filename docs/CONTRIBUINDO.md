# Contribuindo

Guia para mexer no Hub com segurança, mesmo sem ser especialista.

## Branches (versões do código)

| Branch | Para quê |
|--------|----------|
| `main` | Código que está em **produção**. Só recebe o que já passou em homologação. |
| `homologacao` | Código em **teste** no servidor de homologação. |
| `claude/...` ou `feature/...` | Onde você desenvolve uma mudança específica. |

Fluxo:

```
cria uma branch a partir da main → desenvolve → testa no DEV
   → abre PR para 'homologacao' → testa em HOMOLOGAÇÃO
   → quando aprovado, vai para 'main' → publica em PRODUÇÃO
```

Nunca edite arquivos direto no servidor. Sempre: altera no PC, `push`, e o
servidor faz `git pull` (veja [DEPLOY_LINUX.md](DEPLOY_LINUX.md)).

## Rodar no seu PC (dev)

```bash
docker compose up -d                 # sobe Postgres + N8N locais
cp .env.dev.example .env             # preencha a FLASK_SECRET_KEY
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_tudo.py
python app.py                        # http://localhost:5000
```

## Commits

- Mensagens claras, em português, no imperativo: "Corrige...", "Adiciona...".
- Um commit por ideia (não misture mudanças sem relação).

## Adicionar uma migration (mudança no banco)

Quando mudar `models.py` (nova tabela/coluna), gere a migration:

```bash
alembic revision -m "descricao curta da mudanca"
# edite o arquivo gerado em migrations/versions/ (upgrade e downgrade)
alembic upgrade head                 # aplica no seu Postgres de dev
```

Lembre-se: **toda tabela usa o prefixo `cm_hub_aut_`**. No Oracle, a estrutura é
tratada junto com a TI (o Alembic não roda lá). Veja
[BANCO_DE_DADOS.md](BANCO_DE_DADOS.md).

## Adicionar um seed (dado-base)

Crie um script em `scripts/` e chame-o a partir de `scripts/seed_tudo.py`. Faça
o seed **idempotente** (rodar de novo não duplica) — veja os exemplos existentes.

## ⚠️ Aviso importante sobre a pasta `automacoes/`

Os robôs em `automacoes/` usam **imports "soltos"** (ex.: `import cadastro_ncm`)
que dependem de a aplicação rodar **a partir da raiz do projeto**. Por isso:

- **Não** mova nem renomeie arquivos dentro de `automacoes/` sem testar cada robô
  afetado — uma falha só aparece **na hora de rodar** aquele robô, não na subida.
- Reorganizar essa pasta em um pacote é uma melhoria **futura**, que exige rodar
  cada robô para validar. Foi deixada de fora de propósito.

## Convenções gerais

- Código e comentários em **português**.
- O `.editorconfig` cuida do estilo (UTF-8, fim de linha **LF**, indentação).
  Mantê-lo evita o clássico problema de arquivos do Windows quebrarem no Linux.
- Segredos **nunca** no Git: use o `.env` (já ignorado).
