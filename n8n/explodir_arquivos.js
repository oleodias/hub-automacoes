// ══════════════════════════════════════════════════════════════
// explodir_arquivos.js — Code node do n8n (antes do Download)
// ──────────────────────────────────────────────────────────────
// Recebe 1 item por laboratório (de "Preparar Envios") e emite 1 item
// por ARQUIVO, carregando os metadados do e-mail. Cada item alimenta o
// HTTP "Download": GET /relatorios/download?exec=<exec>&arquivo=<arquivo>
// ══════════════════════════════════════════════════════════════

const saida = [];
for (const it of $input.all()) {
  const j = it.json;
  for (let idx = 0; idx < (j.arquivos || []).length; idx++) {
    saida.push({
      json: {
        lab_id: j.lab_id,
        lab_nome: j.lab_nome,
        id: j.id,
        to: j.to,
        bcc: j.bcc,
        subject: j.subject,
        exec: j.exec,
        arquivo: j.arquivos[idx],
        idx,
      },
    });
  }
}
return saida;
