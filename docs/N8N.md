# N8N — Acessar e criar automações

O N8N é o motor de **workflows** que orquestra parte das automações do Hub
(principalmente o fluxo de **cadastro de clientes**). Este guia explica onde
acessá-lo, como criar uma automação nova e como ela se conecta ao Hub.

## 1. Onde fica o N8N (cada ambiente tem o seu)

| Ambiente | Qual N8N | Como acessar | Para quê |
|----------|----------|--------------|----------|
| **Dev (seu PC)** | N8N **local** (Docker) | `http://localhost:5678` | **Criar e testar** fluxos sem risco |
| **Produção** | N8N **Cloud** da Ciamed | `https://ciamedrs.app.n8n.cloud` | Onde os fluxos rodam **de verdade** |
| **Homologação** | *a definir* (ver seção 5) | — | Testar no servidor antes da produção |

> O Hub no servidor **não** sobe um N8N próprio — ele conversa com o **N8N Cloud**
> que a Ciamed já tem. Por isso o `.env.producao` aponta para `ciamedrs.app.n8n.cloud`.

## 2. Acessar o N8N local (dev)

O N8N local já vem no `docker-compose.yml`. No seu PC:

```bash
docker compose up -d         # sobe Postgres + N8N locais
```

Abra **http://localhost:5678**. Na primeira vez, ele pede para criar uma conta —
use qualquer email/senha: é **só no seu PC** e não tem relação com a conta do
N8N Cloud.

## 3. Como criar uma automação nova (passo a passo)

```
1. Suba o N8N local:    docker compose up -d
2. Abra:                http://localhost:5678
3. Monte e TESTE o fluxo ali (à vontade, é local — nada afeta produção)
4. Quando estiver bom:  leve para o N8N Cloud (seção 4)
```

## 4. Levar o fluxo do dev para a produção (Cloud)

A forma mais simples e segura é **exportar e importar** o workflow:

1. No N8N local, abra o workflow → menu (•••) → **Download** (gera um arquivo `.json`).
2. No N8N Cloud (`ciamedrs.app.n8n.cloud`), use **Import from File** e selecione esse `.json`.
3. Reconfigure as **credenciais** no Cloud (senhas/tokens não viajam no export, por segurança).
4. **Ative** o workflow no Cloud.

> Guarde os arquivos `.json` de workflow num local privado (eles podem expor IPs
> internos e a estrutura dos fluxos). O `.gitignore` do projeto já bloqueia esses
> `.json` de irem para o Git.

## 5. Conectar o fluxo ao Hub (webhook + crachá)

Quando um fluxo do N8N chama o Hub (ou o Hub chama o fluxo), os dois se ligam por
**duas informações**, ambas no `.env` do Hub:

1. **URL do webhook** que o N8N fornece → vai em `N8N_WEBHOOK_CADASTRO` /
   `N8N_WEBHOOK_REPROCESSAR`.
2. **Crachá secreto** (`N8N_HUB_TOKEN`) → o **mesmo valor** nos dois lados. No N8N,
   em cada nó *HTTP Request* que chama o Hub, adicione o cabeçalho:
   `X-Hub-Token: <mesmo valor>`. Assim o Hub confia que a chamada veio mesmo do N8N.

Detalhes de cada variável em [VARIAVEIS_AMBIENTE.md](VARIAVEIS_AMBIENTE.md).

## 6. Decisão pendente: o N8N da homologação

No `.env.homolog.example` os webhooks ficam **em branco** de propósito — é uma
escolha de vocês com a TI:

- **Opção A — usar o mesmo N8N Cloud da produção:** mais simples, mas teste e
  produção dividem o mesmo N8N (cuidado para não disparar um fluxo real durante um teste).
- **Opção B — um N8N separado para teste:** mais seguro (isolamento total), mas é
  mais um serviço para a TI manter. Dá para subir um N8N de teste no servidor com
  Docker, nos moldes do `docker-compose.yml` do dev.

## 7. Migrar os workflows do PC antigo

O N8N guarda tudo (workflows + credenciais + **chave de criptografia**) na pasta
`.n8n`. Há dois caminhos:

### Caminho recomendado (limpo): exportar/importar
Use o **Download/Import** de cada workflow (como na seção 4) e recadastre as
credenciais. É o mais previsível.

### Caminho alternativo: copiar a pasta `.n8n` inteira
Preserva também as credenciais salvas, mas exige cuidado com a **encryption key**:

- No N8N **local via Docker**, esses dados ficam no volume `n8n_data` (não numa
  pasta visível do Windows). Copiar a pasta antiga para dentro do volume é
  trabalhoso — por isso, para o Docker, prefira o caminho de exportar/importar.
- Se o PC antigo rodava o N8N **instalado direto** (via `npm`, não Docker), os
  dados ficam em `C:\Users\SEU_USUARIO\.n8n`. Com o N8N **parado**, copie essa
  pasta **inteira** para o mesmo caminho no PC novo **antes** do primeiro start.
  A *encryption key* (no arquivo `config`) precisa vir junto, senão as
  credenciais salvas ficam ilegíveis.

## 8. Esqueceu o login do N8N local

Reseta a conta de dono **sem perder os workflows**. Com o N8N rodando via Docker:

```bash
docker compose exec n8n n8n user-management:reset
```

Depois, em `http://localhost:5678`, aparece de novo a tela de cadastro do dono —
defina email/senha novos.

> Se o N8N estiver instalado direto (sem Docker): pare-o e rode
> `n8n user-management:reset`, depois `n8n start`.
