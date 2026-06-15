# Changelog

Todas as mudanças relevantes do Hub. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não publicado]

### Link da ficha acessível para clientes externos

#### Adicionado
- **`PUBLIC_BASE_URL`:** domínio público usado para montar os links de ficha
  enviados a clientes fora da rede (antes o link herdava o IP interno do
  operador e não abria de fora). Documentada em `docs/VARIAVEIS_AMBIENTE.md` e
  nos `.env.*.example`.
- **Bloco Nginx de fichas** em `deploy/nginx.conf.example`: domínio público
  (`fichas.SEU-DOMINIO`) que expõe **apenas** as rotas da ficha
  (`/ficha_cliente`, `/receber_ficha`, `/api/ficha/`, `/api/cnpj_completo/`) e
  os estáticos — o resto do Hub responde 404 e segue só na rede interna.
- **Guia `docs/LINK_FICHA_PUBLICO.md`:** passo a passo de infraestrutura (DNS,
  HTTPS, Nginx, `.env`) para o link funcionar fora da rede, com validação e
  problemas comuns. Referenciado em `docs/DEPLOY_LINUX.md`.

#### Alterado
- **Geração do link** (`/api/gerar_link_ficha`) agora devolve a URL completa
  montada com a base pública; o front (`cadastro_clientes.js`) usa essa URL e só
  cai no `origin` do navegador quando a base não está configurada (dev).

### Profissionalização da infraestrutura (Windows → servidor Linux/Docker)

#### Adicionado
- **Infra Docker multi-ambiente:** `Dockerfile` (app + Chromium + Gunicorn),
  `.dockerignore`, `entrypoint.sh`, `gunicorn.conf.py` e arquivos de compose
  para **dev**, **homologação** e **produção** (a mesma imagem nos três; muda só
  o `.env`).
- **Caminho Oracle preparado:** driver `oracledb` (modo thin) no
  `requirements.txt`; conexão via `DATABASE_URL` (`oracle+oracledb://...`);
  modelo `deploy/oracle/criar_schemas.sql` para criar os schemas `HUB_HOMOLOG` e
  `HUB_PROD` (isolamento de dados teste × produção no mesmo Oracle).
- **Deploy assistido:** `deploy/atualizar.sh` (git pull + rebuild) e
  `deploy/nginx.conf.example` (proxy reverso com HTTPS).
- **Documentação** em `docs/` (Ambientes, Deploy Linux, Banco de Dados,
  Variáveis de Ambiente, Arquitetura, Contribuindo) e `CHANGELOG.md`.
- **`.editorconfig`** (força fim de linha LF — Windows → Linux).

#### Alterado
- **Prefixo padrão da empresa `cm_hub_aut_`** aplicado às 17 tabelas, em todos os
  ambientes (migration `e5f6a7b8c9d0`; `models.py` e `utils/fila.py` atualizados).
- **Homologação** passou a ter as mesmas travas de segurança de produção
  (cookies seguros, HSTS, ProxyFix); só o `dev` roda solto em HTTP.
- **Organização da raiz:** camada de dados movida para o pacote `db/`
  (`banco_cadastros`, `banco_links`, `banco_notas`); `seed_notas.py` movido para
  `scripts/`.
- `README.md` reescrito (prático, com índice da documentação).
- `ESTRUTURA_BANCO_ORACLE.md` → `docs/BANCO_DE_DADOS_ORACLE.md`.

#### Corrigido
- Nome do arquivo de áudio `somnotificação.wav` → `somnotificacao.wav` (a cedilha
  quebrava o som no Linux; o template já esperava o nome sem acento).
- Planilha CEBAS movida para `data/` e caminho ajustado em `utils/cebas.py`.

#### Removido
- `automacoes/cadastroncm.py` (duplicata morta de `cadastro_ncm.py`).
- `static/img/flecha cinza.png` (sem referências; nome com espaço).
- `.env.example` genérico (substituído pelos três `.env.*.example`) e
  `SETUP_BANCO_NOVO.md` (conteúdo absorvido por `docs/`).

#### A fazer (combinado com a TI, em homologação)
- Adaptar a fila dos robôs (`utils/fila.py`) para o Oracle (substituir
  `pg_advisory_xact_lock`/`hashtext`) e incluir a tabela `cm_hub_aut_fila_execucao`
  no DDL do Oracle. Detalhes em `docs/BANCO_DE_DADOS.md` (seção 2.3).
