# Link da ficha acessível pelo cliente externo (domínio público)

Guia para deixar o **link da ficha** funcionando para clientes **fora da rede
da empresa**. É um processo de **infraestrutura**, feito **uma única vez** por
ambiente (homologação e produção). A parte de código já está pronta no Hub.

> **Por que isso é preciso?** Quem gera o link é o operador, que acessa o Hub
> pelo endereço **interno** (ex.: `http://192.168.x.x`). Sem este processo, o
> link nasce com esse endereço interno e **só abre dentro da rede** — o cliente
> lá fora recebe o link e não consegue acessar. Aqui damos ao Hub um **endereço
> público** (com HTTPS) só para as telas da ficha.

---

## Como vai ficar (visão geral)

```
   CLIENTE (internet, 4G)                   REDE INTERNA DA EMPRESA
            │                                        │
            ▼                                        ▼
  https://fichas.SEU-DOMINIO  ──▶  Nginx  ──▶  Hub (127.0.0.1:8000)
            │                        │
            │                        ├─ libera SÓ: /ficha_cliente,
            │                        │   /receber_ficha, /api/ficha/,
            │                        │   /api/cnpj_completo/, /static/
            │                        └─ todo o resto → 404 (login, admin,
            │                            monitor ficam só na rede interna)
```

O domínio público **não** abre o Hub inteiro: ele expõe **apenas** as rotas que
a ficha precisa. Login, administração e monitor continuam acessíveis só pela
rede interna, pelo domínio de sempre.

---

## Pré-requisitos

- [ ] Hub já rodando no servidor com Nginx + HTTPS (ver [DEPLOY_LINUX.md](DEPLOY_LINUX.md)).
- [ ] **IP público** do servidor (o que a internet enxerga — **não** é o `192.168.x.x`).
- [ ] Acesso ao **painel do domínio** da empresa (Registro.br, Cloudflare, etc.).
- [ ] Portas **80** e **443** liberadas no firewall/roteador até o servidor.
- [ ] Acesso **SSH** ao servidor (e ao `certbot`).

---

## Passo 1 — Criar o subdomínio (DNS)

No painel do domínio da empresa, crie um registro **A**:

| Campo | Valor |
|-------|-------|
| Tipo | `A` |
| Nome | `fichas` (produção) / `fichas-homolog` (homologação) |
| Aponta para | IP **público** do servidor |

Resultado: `fichas.SEU-DOMINIO.com.br` passa a "encontrar" o servidor.

> A propagação do DNS pode levar de minutos a algumas horas. Confira com:
> ```bash
> nslookup fichas.SEU-DOMINIO.com.br
> ```
> Só siga para o Passo 2 quando o domínio já responder com o IP do servidor.

---

## Passo 2 — Emitir o certificado HTTPS (cadeado)

Gratuito, via Let's Encrypt. No servidor:

```bash
sudo certbot --nginx -d fichas.SEU-DOMINIO.com.br
```

Se o `certbot` não existir:

```bash
sudo apt install certbot python3-certbot-nginx
```

> Só funciona **depois** que o DNS (Passo 1) já aponta para o servidor — o
> certbot precisa provar que o domínio é seu acessando-o pela internet.

---

## Passo 3 — Ativar o bloco do Nginx (só as rotas da ficha)

O modelo já vem pronto em [`deploy/nginx.conf.example`](../deploy/nginx.conf.example)
(bloco **"FICHAS (domínio PÚBLICO para clientes externos)"**). Ele libera
apenas:

- `/ficha_cliente` — a página da ficha;
- `/receber_ficha` — o envio da ficha;
- `/api/ficha/` — pré-preenchimento no modo correção;
- `/api/cnpj_completo/` — consulta de CNPJ enquanto o cliente preenche;
- `/static/` — CSS, JS e imagens.

Todo o resto responde **404** nesse domínio.

1. Copie esse bloco para a config real do Nginx (ex.: `/etc/nginx/sites-available/hub`).
2. Troque **todos** os `SEU-DOMINIO.com.br` pelo domínio real.
3. Confira a porta do `proxy_pass`: **8000** (produção) ou **8010** (homologação).
4. Teste e recarregue:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Passo 4 — Avisar o Hub o endereço público (`.env`)

No `.env` do ambiente, preencha a variável que monta o link:

```bash
# Produção
nano .env.producao
# adicione/ajuste:
PUBLIC_BASE_URL=https://fichas.SEU-DOMINIO.com.br
```

Reinicie o container para ele ler a nova variável:

```bash
docker compose -f docker-compose.prod.yml up -d
```

> **Importante:** sem barra `/` no fim. Em **dev** deixe `PUBLIC_BASE_URL` vazia
> — aí o link usa o endereço do próprio navegador (localhost), suficiente para
> testar localmente. Detalhes em [VARIAVEIS_AMBIENTE.md](VARIAVEIS_AMBIENTE.md).

---

## Como validar

1. Gere um link pela tela de cadastro de clientes, como sempre.
2. O link deve sair como
   `https://fichas.SEU-DOMINIO.com.br/ficha_cliente?t=...`
   (e **não** mais `http://192.168.x.x/...`).
3. Abra esse link **pelo celular no 4G, sem o Wi-Fi da empresa**.
   - Se a ficha **carregar**, está valendo para o cliente externo.
4. Tente abrir `https://fichas.SEU-DOMINIO.com.br/login` no mesmo celular.
   - Tem que dar **404** — é a prova de que só as telas da ficha estão expostas.

---

## Resumo de quem faz o quê

| Passo | Onde | Feito por |
|-------|------|-----------|
| 1. DNS | Painel do domínio | TI / rede |
| 2. HTTPS (certbot) | SSH no servidor | Quem administra o servidor |
| 3. Nginx | SSH no servidor | Quem administra o servidor |
| 4. `.env` + reiniciar | SSH no servidor | Quem administra o servidor |

A parte de **código** já está pronta no repositório — os passos acima são
configuração de servidor, feitos uma vez por ambiente.

---

## Problemas comuns

| Sintoma | Provável causa |
|---------|----------------|
| Link ainda sai com `192.168.x.x` | `PUBLIC_BASE_URL` vazia ou container não reiniciado após editar o `.env`. |
| Cliente vê "site não seguro" / cadeado quebrado | Certificado não emitido (Passo 2) ou domínio errado no Nginx. |
| Ficha não abre de fora, mas abre na rede | DNS não aponta para o IP público, ou portas 80/443 fechadas no firewall. |
| `/login` abre no domínio público | Bloco do Nginx incompleto — confira o `location / { return 404; }`. |
| Upload de documentos da ficha falha | `client_max_body_size` baixo no Nginx (use ~50M). |
| Consulta de CNPJ não funciona na ficha | Faltou liberar `/api/cnpj_completo/` no bloco do Nginx. |

---

## Recomendação de segurança (opcional, mas aconselhável)

Ao expor `/receber_ficha` na internet aberta, essa rota passa a receber tráfego
de qualquer um. Vale avaliar:

- **Limite de taxa (rate limit)** nessa rota, para evitar envios automatizados
  em massa (hoje o `@limiter.limit` está só no login).
- **CAPTCHA** na ficha, pelo mesmo motivo.

O link já é protegido por **token de uso único** com validade de 7 dias, amarrado
ao CNPJ — então um link vazado expira e não serve para outro cliente. As medidas
acima são uma camada extra contra abuso da rota pública.
