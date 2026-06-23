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
};

const NOMES = {
  bayer: "Bayer", csl: "CSL", fresenius: "Fresenius", glaxo: "Glaxo",
  organon: "Organon", roche: "Roche", sandoz_rs_sc: "Sandoz RS/SC",
  sandoz_sp: "Sandoz SP", sankyo: "Sankyo", sun_geral: "Sun Geral",
  sun_13082: "Sun Item 13082", united: "United",
};

// Responsáveis internos que recebem CÓPIA OCULTA (BCC) de cada envio.
// ⚠️ PREENCHER (ex.: a colega que gera hoje + quem monitora).
const RESPONSAVEIS_BCC = [];

// ── Quem dispara em cada tipo + qual a regra de período da VENDA ──
// regra_periodo ∈ {mes_anterior, semana_anterior, mes_ate_ultima_sexta, mes_ate_ultima_quarta}
const TIPO1_PRIMEIRO_DIA_UTIL = [   // todos os 12, venda = todo mês anterior
  "bayer", "csl", "fresenius", "glaxo", "organon", "roche",
  "sandoz_rs_sc", "sandoz_sp", "sankyo", "sun_geral", "sun_13082", "united",
];
const TIPO2_SEGUNDA = {
  bayer: "semana_anterior", roche: "semana_anterior",
  csl: "mes_ate_ultima_sexta", fresenius: "mes_ate_ultima_sexta",
  glaxo: "mes_ate_ultima_sexta", sun_geral: "mes_ate_ultima_sexta",
};
const TIPO3_QUINTA = { sun_13082: "mes_ate_ultima_quarta" };

// ── PARÂMETROS A CONFIRMAR ──
const REGRA_TIPO1 = "primeiro_dia_util"; // ou "dia_1"
const SEMANA_ANTERIOR = "seg_dom";        // ou "seg_sex"

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
  if (regra === "mes_ate_ultima_sexta") {
    return [new Date(hoje.getFullYear(), hoje.getMonth(), 1), ultimoDiaSemanaAntes(hoje, 5)];
  }
  if (regra === "mes_ate_ultima_quarta") {
    return [new Date(hoje.getFullYear(), hoje.getMonth(), 1), ultimoDiaSemanaAntes(hoje, 3)];
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
    emails: EMAILS[lab_id] || [],
    bcc: RESPONSAVEIS_BCC,
  };
}

// ─────────────────────────────── main ───────────────────────────────
// Atenção ao fuso: assume o servidor do n8n em America/Sao_Paulo.
const hoje = new Date();
const w = hoje.getDay(); // 0=Dom..6=Sab

const ehTipo1 = REGRA_TIPO1 === "dia_1"
  ? hoje.getDate() === 1
  : fmt(hoje) === fmt(primeiroDiaUtilDoMes(hoje));
const ehTipo2 = w === 1; // segunda
const ehTipo3 = w === 4; // quinta

const candidatos = [];
if (ehTipo1) for (const lab of TIPO1_PRIMEIRO_DIA_UTIL) candidatos.push(novoEnvio(lab, 1, "mes_anterior", hoje));
if (ehTipo2) for (const [lab, regra] of Object.entries(TIPO2_SEGUNDA)) candidatos.push(novoEnvio(lab, 2, regra, hoje));
if (ehTipo3) for (const [lab, regra] of Object.entries(TIPO3_QUINTA)) candidatos.push(novoEnvio(lab, 3, regra, hoje));

// Só seguem os envios com período válido; os inválidos ficam reportados à parte.
const envios = candidatos.filter((e) => e.valido);
const ignorados = candidatos.filter((e) => !e.valido).map((e) => ({ id: e.id, motivo: "periodo_invalido" }));

return [{
  json: {
    data_ref: fmt(hoje),
    tem_disparo: envios.length > 0,
    tipos: { tipo1: ehTipo1, tipo2: ehTipo2, tipo3: ehTipo3 },
    qtd_envios: envios.length,
    envios,
    ignorados,
  },
}];
