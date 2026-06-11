# Hub de Automações — Ciamed

Aplicação web que centraliza e aciona as automações (robôs/RPA) dos setores
administrativo e fiscal da Ciamed. Em vez de rodar scripts soltos no terminal,
os colaboradores autorizados disparam e acompanham as rotinas por uma interface
web — cadastro de itens/NCM, MDF, fornecedores, lançamento de notas, fichas de
clientes e uma central de suporte.

## Stack

- **Backend:** Python 3.11 + Flask (blueprints)
- **Banco:** PostgreSQL (dev) / Oracle (homologação e produção), via SQLAlchemy + Alembic
- **Automação (RPA):** Selenium WebDriver (Chromium)
- **Workflows:** N8N
- **Servidor (produção):** Docker + Gunicorn atrás do Nginx
- **Frontend:** HTML, CSS, JavaScript, Bootstrap

## Começo rápido (desenvolvimento)

```bash
# 1) Suba os apoios locais (banco Postgres + N8N)
docker compose up -d

# 2) Crie e preencha o .env
cp .env.dev.example .env        # gere a FLASK_SECRET_KEY indicada no arquivo

# 3) Instale as dependências
python -m venv venv && source venv/bin/activate   # no Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4) Crie a estrutura do banco e os dados-base
alembic upgrade head
python scripts/seed_tudo.py
python criar_admin.py

# 5) Rode o Hub
python app.py                   # http://localhost:5000
```

## Documentação

Toda a documentação detalhada está na pasta [`docs/`](docs/):

| Documento | Para quê |
|-----------|----------|
| [docs/AMBIENTES.md](docs/AMBIENTES.md) | Como funcionam Dev, Homologação e Produção |
| [docs/DEPLOY_LINUX.md](docs/DEPLOY_LINUX.md) | Subir e atualizar o Hub no servidor (Docker) |
| [docs/BANCO_DE_DADOS.md](docs/BANCO_DE_DADOS.md) | Postgres, Oracle, schemas e migrations |
| [docs/BANCO_DE_DADOS_ORACLE.md](docs/BANCO_DE_DADOS_ORACLE.md) | DDL e mapeamento de tipos para o Oracle |
| [docs/VARIAVEIS_AMBIENTE.md](docs/VARIAVEIS_AMBIENTE.md) | O que cada variável do `.env` faz |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Como as peças se conectam |
| [docs/CONTRIBUINDO.md](docs/CONTRIBUINDO.md) | Padrões, branches e como mexer no projeto |

Histórico de mudanças em [CHANGELOG.md](CHANGELOG.md).

---
*Mantido pela equipe da Ciamed.*
