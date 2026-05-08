# Hub de Automações - Ciamed

Sistema centralizado para orquestrar automações RPA nos setores administrativo e fiscal da Ciamed. A plataforma oferece uma interface web onde colaboradores (sem conhecimento técnico) disparam e monitoram robôs que interagem diretamente com o ERP.

---

## Funcionalidades

### Cadastro de Clientes
- **Ficha digital pública**: Vendedores externos preenchem dados sem precisar de login
- **Enriquecimento automático**: Integração com API CNPJ.ws (Receita Federal) pré-preenche razão social, endereço, CNAE e inscrição estadual
- **Fluxo de aprovação**: Farmacêutica aprova ou reprova via e-mail antes de qualquer cadastro
- **Robô RPA**: Após aprovação, o Selenium navega pelo ERP e cadastra o cliente automaticamente
- **Monitor de cadastros**: Dashboard com filtros por status, tipo, data e busca textual, com exportação para Excel

### Cadastro de Itens (2 Fases)
- **Fase 1 – NCM**: Lê arquivo XML, consulta itens existentes no ERP e processa a classificação NCM via Systax/Portal
- **Fase 2 – ERP**: Cadastra os itens novos com descrição, NCM, preço e categoria
- **Fila de execução**: Garante que apenas um robô rode por vez, exibindo feedback em tempo real para quem aguarda

### Relatório MDF-e
- Acessa o ERP via Selenium, filtra por período e exporta o Manifesto Eletrônico de Documento Fiscal em planilha Excel

### Cadastro de Fornecedor
- Automação completa do preenchimento de fornecedores no ERP com validação e tratamento de erros

### Consulta de CNPJ
- Endpoint público que consome a API CNPJ.ws e retorna dados cadastrais completos para pré-preenchimento de formulários

### Painel Administrativo
- Gestão de usuários (criar, editar, desativar) e controle granular de permissões por módulo
- Histórico de execuções com duração, status e detalhes de cada robô disparado

---

## Stack Tecnológica

| Camada | Tecnologias |
|---|---|
| **Backend** | Python 3, Flask, Blueprints |
| **Banco de Dados** | PostgreSQL, SQLAlchemy ORM, Alembic |
| **Automação RPA** | Selenium WebDriver, webdriver-manager |
| **Processamento** | Pandas, OpenPyXL |
| **Frontend** | HTML5, CSS3, Bootstrap 5, JavaScript Vanilla |
| **Integração** | N8N (webhooks), CNPJ.ws (Receita Federal) |
| **Infraestrutura** | Docker, Docker Compose |
| **Utilitários** | python-dotenv, requests, BeautifulSoup4 |

---

## Arquitetura

```
hub-automacoes/
├── app.py                  # Ponto de entrada Flask
├── models.py               # Modelos: Usuario, Submissao, Execucao
├── extensions.py           # Instâncias centrais (db, etc.)
├── banco_cadastros.py      # Operações de banco de dados
├── routes/                 # Blueprints Flask (auth, clientes, itens, mdf, fornecedor, cnpj, admin)
├── automacoes/
│   ├── main.py             # Orquestrador principal dos robôs
│   ├── login_navegacao.py  # Inicialização do navegador e login no ERP
│   ├── motor_xml.py        # Extração de dados de arquivos XML
│   ├── fase1_ncm.py        # Fase 1: processamento de NCM
│   ├── fase2_item.py       # Fase 2: cadastro de itens no ERP
│   ├── robo_mdf.py         # Geração de relatório MDF-e
│   ├── robo_fornecedor.py  # Cadastro de fornecedores
│   └── clientes/
│       ├── cadastro_novo.py        # Robô de cadastro de novo cliente
│       └── cadastro_reativacao.py  # Robô de reativação de cliente
├── utils/
│   ├── auth.py             # Decoradores de autenticação e permissão
│   ├── fila.py             # Gerenciamento de filas thread-safe
│   ├── cnpj_ws.py          # Integração com API CNPJ.ws
│   └── rastreio.py         # Registro de execuções dos robôs
├── templates/              # 29 templates Jinja2
├── static/                 # CSS, JS, imagens, áudio, vídeos, dados JSON
├── migrations/             # Migrações Alembic
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Fluxos Principais

**Cadastro de novo cliente**
```
Vendedor preenche ficha → CNPJ.ws enriquece dados → N8N notifica farmacêutica
→ Aprovação por e-mail → N8N dispara webhook → Robô Selenium cadastra no ERP
```

**Cadastro de itens**
```
Usuário faz upload de XML → Entra na fila → Fase 1 processa NCM
→ Fase 2 cadastra itens no ERP → Log em tempo real via SSE
```

---

## Configuração

### Pré-requisitos
- Python 3.10+
- Docker e Docker Compose
- Google Chrome instalado

### Instalação

```bash
# 1. Suba o banco de dados e o N8N
docker-compose up -d

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# 5. Crie o primeiro usuário administrador
python criar_admin.py

# 6. Inicie a aplicação
python app.py
```

### Variáveis de Ambiente (`.env`)

```env
AMBIENTE=dev                          # dev | prod
FLASK_SECRET_KEY=sua_chave_secreta
DATABASE_URL=postgresql://usuario:senha@localhost:5432/hub_automacoes
N8N_WEBHOOK_CADASTRO=http://localhost:5678/webhook/...
NLWEB_URL=https://url-do-erp
NLWEB_USER=usuario_erp
NLWEB_PASS=senha_erp
```

---

## Autenticação e Permissões

- Cargos: `admin` (acesso total) e `operador` (acesso por módulo)
- Controle de horário de funcionamento: segunda a sexta, 8h–18h
- Rotas públicas (sem login): ficha de cliente, consulta CNPJ, endpoints N8N e confirmação por e-mail
- Permissões granulares armazenadas como JSON no banco por usuário

---

## Inovação

Este projeto foi inteiramente concebido com **Inteligência Artificial Generativa** — toda a lógica dos robôs, a estrutura do servidor e o design da interface foram criados colaborativamente com IA, demonstrando como essa tecnologia pode construir soluções corporativas robustas em tempo recorde.

---

*Desenvolvido por Leonardo Dias.*
