// ══════════════════════════════════════════════════════════════
// agenda_relatorios.js — Code node do n8n (o "cérebro" da agenda)
// ──────────────────────────────────────────────────────────────
// Roda no início do workflow (depois do Schedule Trigger). Decide
// QUAIS laboratórios disparam HOJE, com QUAL período de venda, e já
// anexa os E-MAILS de cada um. A saída alimenta:
//   1) POST {hub}/relatorios/iniciar  → { envios: [...] }
//   2) o loop de e-mail (emailSend SMTP) por lab, usando o manifesto.
//
// Fonte da verdade: planilha "ENVIO DE RELATÓRIOS - VENDAS/ESTOQUE".
//
// ⚠️ DOIS PONTOS A CONFIRMAR (ver constantes abaixo):
//   • REGRA_TIPO1: a planilha diz "1º DIA ÚTIL"; antes tínhamos falado
//     "todo dia 1º (mesmo fim de semana)". Default aqui = 1º dia útil.
//   • SEMANA_ANTERIOR: seg→dom (default) ou seg→sex? (Bayer/Roche)
//
// OBS.: o ESTOQUE não tem filtro de data — é a foto atual. A coluna
// "PERÍODO ESTOQUE" da planilha só explica POR QUE se envia naquele dia
// (rodar no 1º dia útil ≈ "como o mês fechou"). Por isso o robô não
// recebe período de estoque, só o período de VENDA.
// ══════════════════════════════════════════════════════════════

// ── Config: e-mails por laboratório (lab_id casa com o Hub/LABS) ──
const EMAILS = {
  bayer:        ["operacoescomerciaisbhp@bayer.com", "elias.zanatta@bayer.com", "paula.yokomizo@bayer.com"],
  csl:          ["csl@wfbconsultoria.com.br", "Rafael.Esteves@csl.com.au"],
  fresenius:    ["jailton.silva@fresenius-kabi.com"],
  glaxo:        ["alexandre.x.mitsuda@gsk.com"],
  organon:      ["rodrigo.blas@organon.com"],
  roche:        ["brasil.operacoescomerciais@roche.com", "joao.pessoa@roche.com"],
  sandoz_rs_sc: ["marcelo.novelli@sandoz.com", "isaque.fedrigo@sandoz.com"],
  sandoz_sp:    ["roger.damian@sandoz.com"],
  sankyo:       ["marcio.honorati@daiichisankyo.com", "pedro.mota@daiichisankyo.com", "alexandre.jesus@daiichisankyo.com"],
  sun_geral:    ["Gisele.Lemos@sunpharma.com", "Ana.ferreira@sunpharma.com"],
  sun_13082:    ["Cecilia.Castro@sunpharma.com", "Edgar.Lopes@sunpharma.com"],
  united:       ["leonardo.rossi@knighttx.com"],
  // Labs do setor público (adicionados 2026-07):
  apsen:        ["airton.lima@apsen.com.br", "Gabriela.Teixeira@apsen.com.br"],
  mappel_quifa: ["jeferson.squefi@interplayers.com.br"],
};

const NOMES = {
  bayer: "Bayer", csl: "CSL", fresenius: "Fresenius", glaxo: "Glaxo",
  organon: "Organon", roche: "Roche", sandoz_rs_sc: "Sandoz RS/SC",
  sandoz_sp: "Sandoz SP", sankyo: "Sankyo", sun_geral: "Sun Geral",
  sun_13082: "Sun Item 13082", united: "United",
  apsen: "Apsen", mappel_quifa: "Mappel / Quifa",
};

// Responsáveis internos que recebem CÓPIA OCULTA (BCC) de cada envio.
// ⚠️ PREENCHER (ex.: a colega que gera hoje + quem monitora).
const RESPONSAVEIS_BCC = [];

// ── MODO TESTE ──────────────────────────────────────────────────
// Enquanto MODO_TESTE = true, NENHUM e-mail vai aos laboratórios:
// todos os relatórios são redirecionados para EMAIL_TESTE (sem BCC).
// Os avisos de conclusão/erro vão para EMAIL_AVISOS.
// Para ir a PRODUÇÃO, basta trocar MODO_TESTE para false.
const MODO_TESTE = true;
const EMAIL_TESTE = "leonardodiascaumo@gmail.com";  // destino dos relatórios em teste
const EMAIL_AVISOS = "ti6@ciamedrs.com.br";         // avisos de conclusão/erro (robô)
const EMAIL_COLEGA = "leonardodiascaumo@gmail.com"; // colega que confere os envios (aviso por lab)

// ── FORÇAR TESTE ────────────────────────────────────────────────
// Enquanto true, ignora as regras de data e emite 1 envio fixo (Bayer,
// mês anterior) — serve para testar o WORKFLOW INTEIRO no n8n em qualquer
// dia. Voltar para false em produção (aí volta a respeitar o calendário).
const FORCAR_TESTE = false;

// ── Quem dispara em cada tipo + qual a regra de período da VENDA ──
// regra_periodo ∈ {mes_anterior, semana_anterior, mes_ate_ultima_sexta, mes_ate_ultima_quarta}
const TIPO1_PRIMEIRO_DIA_UTIL = [   // todos os 14, venda = todo mês anterior
  "bayer", "csl", "fresenius", "glaxo", "organon", "roche",
  "sandoz_rs_sc", "sandoz_sp", "sankyo", "sun_geral", "sun_13082", "united",
  "apsen", "mappel_quifa",          // labs do setor público (mensais, mês anterior)
];
const TIPO2_SEGUNDA = {
  bayer: "semana_anterior", roche: "semana_anterior",
  csl: "mes_ate_ultima_sexta", fresenius: "mes_ate_ultima_sexta",
  glaxo: "mes_ate_ultima_sexta", sun_geral: "mes_ate_ultima_sexta",
};
const TIPO3_QUINTA = { sun_13082: "mes_ate_ultima_quarta" };

// ── PARÂMETROS (decididos com o Leonardo) ──
const REGRA_TIPO1 = "dia_1";        // dispara sempre no dia 1º, mesmo fim de semana
const SEMANA_ANTERIOR = "seg_sex";  // semana anterior = segunda a sexta

// ────────────────────────── helpers de data ──────────────────────────
function fmt(d) {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}
function addDias(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
function ehFimDeSemana(d) { const w = d.getDay(); return w === 0 || w === 6; }

function primeiroDiaUtilDoMes(ref) {
  let d = new Date(ref.getFullYear(), ref.getMonth(), 1);
  while (ehFimDeSemana(d)) d = addDias(d, 1); // sem feriados, conforme combinado
  return d;
}
function ultimoDiaSemanaAntes(ref, weekday) {
  // weekday: 1=seg ... 5=sex, 3=qua. Retorna a ocorrência mais recente ANTES de ref.
  let d = addDias(ref, -1);
  while (d.getDay() !== weekday) d = addDias(d, -1);
  return d;
}

function periodo(regra, hoje) {
  if (regra === "mes_anterior") {
    const ini = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
    const fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0); // último dia do mês anterior
    return [ini, fim];
  }
  if (regra === "semana_anterior") {
    // segunda desta semana → volta 7 dias = segunda passada
    const segDestaSemana = addDias(hoje, -((hoje.getDay() + 6) % 7));
    const segAnterior = addDias(segDestaSemana, -7);
    const fim = SEMANA_ANTERIOR === "seg_sex" ? addDias(segAnterior, 4) : addDias(segAnterior, 6);
    return [segAnterior, fim];
  }
  if (regra === "mes_ate_ultima_sexta" || regra === "mes_ate_ultima_quarta") {
    const weekday = regra === "mes_ate_ultima_sexta" ? 5 : 3; // 5=sexta, 3=quarta
    const dia1 = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    const fim = ultimoDiaSemanaAntes(hoje, weekday); // ocorrência mais recente antes de hoje
    if (fim >= dia1) return [dia1, fim];             // caso normal: 1º do mês → última sexta/quarta
    // Borda (1ª segunda/quinta do mês, sem essa data ainda no mês vigente):
    // usa a semana que antecede hoje = última semana do mês passado (seg → sexta/quarta).
    const segDestaSemana = addDias(hoje, -((hoje.getDay() + 6) % 7));
    return [addDias(segDestaSemana, -7), fim];
  }
  return [null, null];
}

function novoEnvio(lab_id, tipo, regra, hoje) {
  const [ini, fim] = periodo(regra, hoje);
  // Blindagem: período inválido (ex.: 1ª segunda do mês, sem sexta ainda no mês vigente).
  const valido = ini && fim && fim >= ini;
  return {
    id: `${lab_id}__T${tipo}`,            // chave p/ casar o manifesto do Hub com o e-mail
    lab_id,
    lab_nome: NOMES[lab_id],
    tipo,
    regra_periodo: regra,
    periodo_ini: valido ? fmt(ini) : "",
    periodo_fim: valido ? fmt(fim) : "",
    valido,
    emails: MODO_TESTE ? [EMAIL_TESTE] : (EMAILS[lab_id] || []),
    bcc: MODO_TESTE ? [] : RESPONSAVEIS_BCC,
    // referência: para quem iria em produção (útil p/ conferir no teste)
    emails_producao: EMAILS[lab_id] || [],
  };
}

// ─────────────────────────────── main ───────────────────────────────
// Atenção ao fuso: assume o servidor do n8n em America/Sao_Paulo.
// ── DISPARO MANUAL (Form Trigger "Disparo Manual") ────────────────────
// Se o workflow foi iniciado pelo formulário, chega um lab_id no input:
// monta UM envio para o lab escolhido e ignora o calendário. Reusa os
// mapas EMAILS/NOMES e RESPEITA o MODO_TESTE (mesma segurança do automático).
// Período em branco => mês anterior inteiro.
let _manual = null;
try {
  const _itens = $input.all();
  if (_itens.length && _itens[0].json && _itens[0].json.lab_id) _manual = _itens[0].json;
} catch (_e) { _manual = null; }

if (_manual) {
  const hojeM = new Date();
  const lab_id = String(_manual.lab_id || "").trim();
  const conhecido = Object.prototype.hasOwnProperty.call(NOMES, lab_id);
  let pini = String(_manual.periodo_ini || "").trim();
  let pfim = String(_manual.periodo_fim || "").trim();
  if (!pini && !pfim) {                       // vazio => mês anterior inteiro
    const [a, b] = periodo("mes_anterior", hojeM);
    pini = fmt(a); pfim = fmt(b);
  }
  const reData = /^\d{2}\/\d{2}\/\d{4}$/;
  const valido = conhecido && reData.test(pini) && reData.test(pfim);
  const envio = {
    id: `${lab_id}__M`,
    lab_id,
    lab_nome: NOMES[lab_id] || lab_id,
    tipo: "M",
    regra_periodo: "manual",
    periodo_ini: valido ? pini : "",
    periodo_fim: valido ? pfim : "",
    valido,
    emails: MODO_TESTE ? [EMAIL_TESTE] : (EMAILS[lab_id] || []),
    bcc: MODO_TESTE ? [] : RESPONSAVEIS_BCC,
    emails_producao: EMAILS[lab_id] || [],
  };
  const enviosM = valido ? [envio] : [];
  const ignoradosM = valido ? [] : [{ id: envio.id, motivo: conhecido ? "periodo_invalido" : "lab_desconhecido" }];
  return [{
    json: {
      data_ref: fmt(hojeM),
      modo_teste: MODO_TESTE,
      forcar_teste: false,
      disparo_manual: true,
      email_avisos: EMAIL_AVISOS,
      email_colega: EMAIL_COLEGA,
      tem_disparo: enviosM.length > 0,
      tipos: { manual: true },
      qtd_envios: enviosM.length,
      envios: enviosM,
      ignorados: ignoradosM,
    },
  }];
}

const hoje = new Date();
const w = hoje.getDay(); // 0=Dom..6=Sab

const ehTipo1 = REGRA_TIPO1 === "dia_1"
  ? hoje.getDate() === 1
  : fmt(hoje) === fmt(primeiroDiaUtilDoMes(hoje));
const ehTipo2 = w === 1; // segunda
const ehTipo3 = w === 4; // quinta

const candidatos = [];
if (FORCAR_TESTE) {
  // Teste manual do workflow: força TODOS os 12 labs (Tipo 1, mês anterior),
  // independente do dia — serve para testar o fluxo inteiro de uma vez.
  for (const lab of TIPO1_PRIMEIRO_DIA_UTIL) candidatos.push(novoEnvio(lab, 1, "mes_anterior", hoje));
} else {
  if (ehTipo1) for (const lab of TIPO1_PRIMEIRO_DIA_UTIL) candidatos.push(novoEnvio(lab, 1, "mes_anterior", hoje));
  if (ehTipo2) for (const [lab, regra] of Object.entries(TIPO2_SEGUNDA)) candidatos.push(novoEnvio(lab, 2, regra, hoje));
  if (ehTipo3) for (const [lab, regra] of Object.entries(TIPO3_QUINTA)) candidatos.push(novoEnvio(lab, 3, regra, hoje));
}

// Só seguem os envios com período válido; os inválidos ficam reportados à parte.
const envios = candidatos.filter((e) => e.valido);
const ignorados = candidatos.filter((e) => !e.valido).map((e) => ({ id: e.id, motivo: "periodo_invalido" }));

return [{
  json: {
    data_ref: fmt(hoje),
    modo_teste: MODO_TESTE,
    forcar_teste: FORCAR_TESTE,
    email_avisos: EMAIL_AVISOS,
    email_colega: EMAIL_COLEGA,
    tem_disparo: envios.length > 0,
    tipos: { tipo1: ehTipo1, tipo2: ehTipo2, tipo3: ehTipo3 },
    qtd_envios: envios.length,
    envios,
    ignorados,
  },
}];
