// ══════════════════════════════════════════════════════════════
// preparar_envios.js — Code node do n8n (pós /relatorios/iniciar)
// ──────────────────────────────────────────────────────────────
// Junta o MANIFESTO do robô (itens: id, lab_id, arquivos) com os
// ENVIOS da agenda (emails, período) pelo campo "id". Produz UM item
// por laboratório, pronto para o loop de download + emailSend.
//
// Requisitos de nomes dos nós (ajuste se os seus tiverem outro nome):
//   • "Agenda"      → Code node agenda_relatorios.js
//   • "Iniciar Robo"→ HTTP Request que chamou POST /relatorios/iniciar
//
// Saída (1 item por lab):
//   { id, lab_id, lab_nome, to, bcc, subject, exec, arquivos: [...] }
//   → o exec + cada "arquivo" alimentam GET /relatorios/download
// ══════════════════════════════════════════════════════════════

const agenda = $('Agenda').first().json;
const resp = $('Iniciar Robo').first().json || {};
const manifesto = resp.resultado || {};
const itens = manifesto.itens || [];
const exec = manifesto.exec || '';

// Indexa os envios da agenda por id (para pegar emails/período de cada lab).
const porId = {};
for (const e of (agenda.envios || [])) porId[e.id] = e;

const saida = [];
for (const it of itens) {
  const env = porId[it.id] || {};
  const periodo = env.periodo_ini
    ? `${env.periodo_ini} a ${env.periodo_fim}`
    : 'estoque atual';
  saida.push({
    json: {
      id: it.id,
      lab_id: it.lab_id,
      lab_nome: it.nome || env.lab_nome || it.lab_id,
      to: (env.emails || []).join('; '),
      bcc: (env.bcc || []).join('; '),
      subject: `Relatório Vendas/Estoque — ${it.nome || env.lab_nome || it.lab_id} (${periodo})`,
      exec,
      arquivos: it.arquivos || [],
    },
  });
}

return saida;
