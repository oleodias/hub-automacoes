# Workflow n8n — Relatórios aos Laboratórios

Orquestra o robô do Hub e envia os relatórios por e-mail. Espelha o
padrão do fluxo de **Cadastro de Clientes** (fila + Wait/resume + token).

## Variáveis / credenciais a configurar no n8n
- **Config Hub**: `hub_url` (ex.: `http://localhost:5000`) — como no cadastro.
- **Header `X-Hub-Token`** em todas as chamadas ao Hub = `N8N_HUB_TOKEN` do `.env` do Hub.
- **Credencial SMTP** (a mesma "SMTP account" do cadastro).
- **BCC** dos responsáveis: definido em `RESPONSAVEIS_BCC` no Code "Agenda".

## Cadeia de nós

| # | Nó | Tipo | Config principal |
|---|----|------|------------------|
| 1 | **Schedule** | Schedule Trigger | diário ~06:30 (America/Sao_Paulo) |
| 2 | **Agenda** | Code | cola `agenda_relatorios.js` |
| 3 | **IF tem_disparo** | IF | `{{$json.tem_disparo}}` é `true` |
| 4 | **Fila Entrar** | HTTP Request | `POST {{hub}}/relatorios/fila/entrar` · JSON `{"resume_url":"{{$execution.resumeUrl}}"}` · header token |
| 5 | **Wait Robô** | Wait | resume: **On Webhook Call** |
| 6 | **Iniciar Robo** | HTTP Request | `POST {{hub}}/relatorios/iniciar` · JSON `{"tipo":"{{$('Agenda').first().json.tipos}}","envios":{{ JSON.stringify($('Agenda').first().json.envios) }}}` · **timeout ~600000 ms** · header token |
| 7 | **Fila Liberar** | HTTP Request | `POST {{hub}}/relatorios/fila/liberar_proximo` · header token |
| 8 | **Preparar Envios** | Code | cola `preparar_envios.js` (1 item por lab) |
| 9 | **Explodir Arquivos** | Code | cola `explodir_arquivos.js` (1 item por arquivo) |
| 10 | **Download** | HTTP Request | `GET {{hub}}/relatorios/download?exec={{$json.exec}}&arquivo={{$json.arquivo}}` · header token · **Response Format: File** (binário no campo `data`) |
| 11 | **Juntar Binários** | Code | cola `juntar_binarios.js` (reagrupa por lab) |
| 12 | **Enviar E-mail** | Send Email (SMTP) | To `{{$json.to}}` · BCC `{{$json.bcc}}` · Subject `{{$json.subject}}` · **Attachments** `{{ Object.keys($binary).join(',') }}` |
| 13 | **Resumo** (opcional) | Send Email | aviso interno de conclusão/erros |

### Observações
- **Ordem 4→5→6→7**: igual ao cadastro — o Hub coloca na fila, acorda o Wait
  quando é a vez (resume_url), o robô roda no `/iniciar` e devolve o manifesto,
  e o `/liberar_proximo` libera a fila.
- O `/iniciar` responde **sempre 200**; trate `status` (`sucesso`/`erro_robo`)
  num **IF** após o nó 6 para decidir entre seguir ao envio ou avisar erro.
- Os arquivos são **vários `.xlsx` soltos** por lab (Sun Geral = 4, demais = 2).
- Fuso: o Code "Agenda" assume o servidor do n8n em **America/Sao_Paulo**.

## Arquivos deste diretório (cole no respectivo Code node)
- `agenda_relatorios.js` — decide disparos do dia + períodos + e-mails.
- `preparar_envios.js` — junta manifesto do robô × e-mails (por `id`).
- `explodir_arquivos.js` — 1 item por arquivo (para o Download).
- `juntar_binarios.js` — reagrupa os binários por lab (para o e-mail).
