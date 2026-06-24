# Workflow n8n — Relatórios aos Laboratórios

Orquestra o robô do Hub e envia os relatórios por e-mail. Espelha o
padrão do fluxo de **Cadastro de Clientes** (fila + Wait/resume + token).

## 🚀 Importar pronto (`fluxo_relatorios.json`)
Há um workflow **importável** no diretório: `n8n/fluxo_relatorios.json`.
No n8n: *Workflows → Import from File*. Depois ajuste **3 coisas**:
1. **URL do Hub** — trocar `http://localhost:5000` nos 4 nós HTTP.
2. **Token** — trocar `TROQUE_PELO_N8N_HUB_TOKEN` no header `X-Hub-Token` (= `N8N_HUB_TOKEN`).
3. **Credencial Gmail (OAuth2)** — religar os nós **"Enviar ao lab"** e
   **"Avisos (erro)"** (tipo `Gmail`) à sua conta Gmail. O remetente é a
   própria conta autenticada (não há `fromEmail` a setar).

> O importável usa os **Code nodes já testados** (`preparar_envios` /
> `explodir_arquivos` / `juntar_binarios`) para o encanamento de dados —
> é o caminho **confiável**. A versão 100% nativa (Split Out + Merge),
> mais granular, está descrita abaixo para você refatorar **no canvas**,
> trocando um nó por vez e validando cada passo (mais seguro). Os dois
> Code nodes de regra/binário (`Agenda`, `Juntar Binários`) permanecem.

## ⚠️ MODO TESTE (ligado)
No topo do `agenda_relatorios.js` está `MODO_TESTE = true`. Enquanto isso:
- **Todos** os relatórios dos laboratórios vão para `leonardodiascaumo@gmail.com`
  (nenhum lab real recebe nada) — campo `to` já sai redirecionado.
- **Avisos** de conclusão/erro vão para `ti6@ciamedrs.com.br`
  (exposto na saída como `{{$('Agenda').first().json.email_avisos}}`).
- A lista real de cada lab fica preservada em `emails_producao` (só para conferência).

Para ir a **produção**: trocar `MODO_TESTE` para `false` (e preencher `RESPONSAVEIS_BCC`).

## Variáveis / credenciais a configurar no n8n
- **Config Hub**: `hub_url` (ex.: `http://localhost:5000`) — como no cadastro.
- **Header `X-Hub-Token`** em todas as chamadas ao Hub = `N8N_HUB_TOKEN` do `.env` do Hub.
- **Credencial Gmail (OAuth2)** nos nós "Enviar ao lab" e "Avisos (erro)".
- **BCC** dos responsáveis: definido em `RESPONSAVEIS_BCC` no Code "Agenda".

## Filosofia: nós separados e visíveis
Cada etapa é um **nó nativo próprio** (Set, IF, Split Out, Merge, Aggregate…),
para a manutenção ser feita olhando o canvas, sem abrir código. Sobram só
**dois** Code nodes — de propósito, porque são os únicos pontos onde código é
mais claro que 10 nós nativos encadeados:
- **`Agenda (regras)`** → o "livro de regras" de datas/períodos. Mexer nas
  regras = editar **um** lugar documentado.
- **`Juntar binários`** → manipulação de binários (anexos), que os nós nativos
  fazem de forma frágil. (Há alternativa nativa com **Aggregate** — ver nota.)

## Cadeia de nós

### Bloco 1 — Decisão
| # | Nó | Tipo | Config |
|---|----|------|--------|
| 1 | **Schedule** | Schedule Trigger | diário ~06:30 (America/Sao_Paulo) |
| 2 | **Agenda (regras)** | Code | cola `agenda_relatorios.js` → 1 item com `envios[]` |
| 3 | **Tem disparo?** | IF | `{{$json.tem_disparo}}` é `true` (false → encerra) |

### Bloco 2 — Rodar o robô (fila + Wait, igual ao cadastro)
| # | Nó | Tipo | Config |
|---|----|------|--------|
| 4 | **Payload do robô** | Set/Edit Fields | `tipo` = `{{$json.tipos}}` · `envios` = `{{$json.envios}}` |
| 5 | **Fila: Entrar** | HTTP Request | `POST {{hub}}/relatorios/fila/entrar` · body `{"resume_url":"{{$execution.resumeUrl}}"}` · header token |
| 6 | **Vez na fila** | Wait | resume: **On Webhook Call** |
| 7 | **Robô: Iniciar** | HTTP Request | `POST {{hub}}/relatorios/iniciar` · body `{"tipo":"{{$('Payload do robô').first().json.tipo}}","envios":{{ JSON.stringify($('Payload do robô').first().json.envios) }}}` · **timeout ~600000 ms** · header token |
| 8 | **Fila: Liberar** | HTTP Request | `POST {{hub}}/relatorios/fila/liberar_proximo` · header token |
| 9 | **Robô OK?** | IF | `{{$('Robô: Iniciar').first().json.status}}` == `sucesso` (false → Bloco 5 avisos) |

### Bloco 3 — Casar manifesto × e-mails (tudo nativo)
| # | Nó | Tipo | Config |
|---|----|------|--------|
| 10 | **Itens do manifesto** | Split Out | campo `resultado.itens` → 1 item por lab |
| 11 | **Envios da agenda** | Split Out | campo `envios` (de `Agenda (regras)`) → 1 item por lab |
| 12 | **Casar por id** | Merge | modo **Combine → Combine by Matching Fields**, campo `id` (entrada 1 = nó 10, entrada 2 = nó 11) |
| 13 | **Dados do e-mail** | Set/Edit Fields | `to`=`{{$json.emails.join('; ')}}` · `bcc`=`{{$json.bcc.join('; ')}}` · `subject`=`Relatório Vendas/Estoque — {{$json.lab_nome}} ({{$json.periodo_ini}} a {{$json.periodo_fim}})` · `exec`=`{{$('Robô: Iniciar').first().json.resultado.exec}}` · `arquivos`=`{{$json.arquivos}}` |

### Bloco 4 — Baixar arquivos e enviar
> **Um Gmail por laboratório:** depois de juntar os anexos, um **Switch**
> roteia por `lab_id` e cada laboratório tem o **seu próprio node Gmail**
> (Bayer, CSL, …). Isso isola falhas (um lab não derruba os outros) e
> permite personalizar o e-mail de cada lab individualmente. Só dispara o
> Gmail do(s) lab(s) que vieram no dia.

| # | Nó | Tipo | Config |
|---|----|------|--------|
| 14 | **Arquivos do lab** | Split Out | campo `arquivos` · **Include Other Fields = All** → 1 item por arquivo (mantém `to/bcc/subject/exec/lab_id`) |
| 15 | **Download** | HTTP Request | `GET {{hub}}/relatorios/download?exec={{$json.exec}}&arquivo={{$json.arquivos}}` · header token · **Response Format: File** (binário em `data`) |
| 16 | **Juntar binários** | Code | cola `juntar_binarios.js` (reagrupa por lab; aponta para o nó **`Arquivos do lab`**) |
| 17 | **Rotear por lab** | Switch | regra por `{{$json.lab_id}}` (uma saída por laboratório) → cada saída vai pro Gmail do lab |
| 17a | **Gmail: Bayer / CSL / … / United** | **Gmail** (send), 1 por lab | To `{{$json.to}}` · BCC (options→bccList) `{{$json.bcc}}` · Subject `{{$json.subject}}` · **Attachments** (Attachment Binary→property) `{{ Object.keys($binary).join(',') }}` |

### Bloco 5 — Aviso interno
| # | Nó | Tipo | Config |
|---|----|------|--------|
| 18 | **Avisos** | **Gmail** (send) | To `{{$('Agenda').first().json.email_avisos}}` · Subject `Relatórios — {{$('Agenda').first().json.data_ref}}` · corpo com qtd/labs/erros |

### Observações
- **Ordem 5→6→7→8**: igual ao cadastro — entra na fila, o Wait acorda quando é
  a vez (resume_url), o robô roda no `/iniciar` e devolve o manifesto, e o
  `/liberar_proximo` libera o próximo.
- O `/iniciar` responde **sempre 200**; o nó 9 (**IF Robô OK?**) separa
  `sucesso` de erro.
- Arquivos = **vários `.xlsx` soltos** por lab (Sun Geral = 4, demais = 2).
- Fuso: o Code "Agenda" assume o servidor do n8n em **America/Sao_Paulo**.

#### Nota — alternativa 100% nativa ao "Juntar binários"
Dá para trocar o nó 16 por um **Aggregate** (opção *Include Binaries*) precedido
de um **Loop Over Items** (batch 1) por lab — assim cada lote agrega só os
anexos daquele lab. Mantive o Code por ser mais robusto contra colisão de nomes
de binário; se preferir zero código aqui, é só avisar que detalho o Aggregate.

## Atalho opcional (1 Code node no lugar do Bloco 3)
Se preferir condensar o Bloco 3 (nós 10–13) num único Code node, use
`preparar_envios.js` (faz a junção por `id` e monta `to/bcc/subject` de uma vez).
O `explodir_arquivos.js` é o equivalente em código do nó 14 (Split Out). Ficam
no repo como alternativa — o caminho recomendado é o nativo acima.

## Arquivos deste diretório
- `agenda_relatorios.js` — **(nó 2)** regras: disparos do dia + períodos + e-mails.
- `juntar_binarios.js` — **(nó 16)** reagrupa os binários por lab.
- `preparar_envios.js` — *(opcional)* condensa o Bloco 3 num Code node.
- `explodir_arquivos.js` — *(opcional)* equivalente em código do Split Out (nó 14).
