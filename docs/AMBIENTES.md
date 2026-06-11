# Ambientes (Dev, Homologação, Produção)

O Hub roda em **três ambientes**. Os três usam **o mesmo código e a mesma
imagem Docker** — o que muda é só o arquivo `.env` de cada um (principalmente
o banco que ele aponta).

```
┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     DEV      │     │   HOMOLOGAÇÃO   │     │    PRODUÇÃO     │
│   (seu PC)   │ ──▶ │   (servidor)    │ ──▶ │   (servidor)    │
│              │     │  dados de TESTE │     │  dados REAIS    │
│ Postgres     │     │ Oracle          │     │ Oracle          │
│ local        │     │ HUB_HOMOLOG     │     │ HUB_PROD        │
│ localhost    │     │ via Nginx/HTTPS │     │ via Nginx/HTTPS │
└──────────────┘     └─────────────────┘     └─────────────────┘
```

## Para que serve cada um

| Ambiente | Onde roda | Banco | Quem usa | Pode errar? |
|----------|-----------|-------|----------|-------------|
| **Dev** | Seu PC | PostgreSQL local | Você, desenvolvendo | Sim, à vontade |
| **Homologação** | Servidor | Oracle (schema `HUB_HOMOLOG`) | Você + TI, testando | Sim, é para isso |
| **Produção** | Servidor | Oracle (schema `HUB_PROD`) | Usuários reais | **Não** |

## A regra de ouro do fluxo

```
   desenvolve no DEV  →  testa em HOMOLOGAÇÃO  →  publica em PRODUÇÃO
```

Nunca edite arquivos direto no servidor. O caminho é sempre: alterar no seu PC,
enviar para o Git (`push`), e o servidor baixar a versão nova (`git pull`) e
reconstruir o container. Veja [DEPLOY_LINUX.md](DEPLOY_LINUX.md).

## Por que homologação e produção não se misturam

Homologação e produção podem usar o **mesmo servidor Oracle da empresa**, mas
cada uma tem o **seu próprio schema** (usuário Oracle): `HUB_HOMOLOG` e
`HUB_PROD`. Cada schema tem a sua cópia das tabelas, então um teste em
homologação **nunca** toca os dados reais de produção. É como dois apartamentos
no mesmo prédio: mesma estrutura, dados separados.

O Hub não muda entre os dois — só o `DATABASE_URL` (no `.env` de cada ambiente)
diz qual schema usar. Detalhes em [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md).

## Como acessar

- **Dev:** `http://localhost:5000` (no seu PC).
- **Homologação:** pelo domínio/IP de homologação do servidor (ex.:
  `https://homologacao.SEU-DOMINIO`), configurado no Nginx.
- **Produção:** pelo domínio principal (ex.: `https://hub.SEU-DOMINIO`).

## O que muda no comportamento do Hub por ambiente

O Hub lê a variável `AMBIENTE` (`dev`, `homolog` ou `prod`) e ajusta a segurança:

- **`dev`:** modo debug ligado; cookies sem exigência de HTTPS (o PC roda em HTTP).
- **`homolog` e `prod`:** debug desligado; cookies seguros, HSTS e leitura do IP
  real do cliente atrás do Nginx (ProxyFix) ligados.
