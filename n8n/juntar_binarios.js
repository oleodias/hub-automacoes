// ══════════════════════════════════════════════════════════════
// juntar_binarios.js — Code node do n8n (depois do Download)
// ──────────────────────────────────────────────────────────────
// Reagrupa os arquivos baixados por laboratório: junta todos os
// binários de um mesmo lab num ÚNICO item, para o emailSend mandar
// um e-mail por lab com TODOS os anexos.
//
// Pareia cada download (na ordem) com o item correspondente do nó
// "Arquivos do lab" (Split Out) — n8n preserva ordem e contagem. Assim os
// metadados (to/bcc/subject) não dependem do HTTP repassar o json.
// (Se você usar o atalho com o Code "Explodir Arquivos", troque o nome abaixo.)
//
// No emailSend, configure o campo "Attachments" com a expressão:
//   {{ Object.keys($binary).join(',') }}
// para anexar dinamicamente todos os binários do item.
// ══════════════════════════════════════════════════════════════

// ⚠️ Trocar pela URL PÚBLICA da logo (precisa ser acessível pela internet,
// pois quem abre o e-mail está fora da rede). Ex.: logo no site da empresa.
const LOGO_URL = "https://SUA-LOGO-PUBLICA-AQUI/logo.png";

function montarHtml(g) {
  const itens = (g.arquivos || [])
    .map((a) => `<li style="margin:2px 0;">${a}</li>`)
    .join("");
  return `<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f6f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#333;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #e6e9ec;">
        <tr><td align="center" style="background:#00B3B2;padding:20px 24px;">
          <img src="${LOGO_URL}" alt="Ciamed" height="48" style="display:block;border:0;">
        </td></tr>
        <tr><td style="padding:28px 24px 8px;">
          <h2 style="margin:0 0 12px;font-size:18px;color:#00B3B2;">Relatório de Vendas / Estoque</h2>
          <p style="margin:0 0 12px;font-size:14px;line-height:1.5;">Prezados(as),</p>
          <p style="margin:0 0 16px;font-size:14px;line-height:1.5;">
            Segue em anexo o relatório referente a <strong>${g.lab_nome}</strong>.
          </p>
          <p style="margin:0 0 6px;font-size:13px;color:#6E6E6E;">Arquivos anexados:</p>
          <ul style="margin:0 0 16px;padding-left:20px;font-size:13px;color:#444;">${itens}</ul>
        </td></tr>
        <tr><td style="padding:16px 24px 24px;border-top:1px solid #eee;">
          <p style="margin:0;font-size:12px;color:#8A8A8A;line-height:1.5;">
            Mensagem automática do Hub de Automações — Ciamed.<br>
            Por favor, não responda a este e-mail.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;
}

const downloads = $input.all();
const explodidos = $('Arquivos do lab').all();

const grupos = {};
for (let i = 0; i < downloads.length; i++) {
  const meta = explodidos[i].json;
  const labId = meta.lab_id;

  if (!grupos[labId]) {
    grupos[labId] = {
      json: {
        lab_id: labId,
        lab_nome: meta.lab_nome,
        to: meta.to,
        bcc: meta.bcc,
        subject: meta.subject,
        arquivos: [],
      },
      binary: {},
    };
  }

  const g = grupos[labId];
  const bin = downloads[i].binary || {};
  for (const k of Object.keys(bin)) {
    const nome = `anexo_${Object.keys(g.binary).length}`;
    g.binary[nome] = bin[k];
    g.json.arquivos.push(meta.arquivo);
  }
}

// Monta o corpo HTML (com a lista de anexos completa) para cada lab.
const saida = Object.values(grupos);
for (const g of saida) {
  g.json.html = montarHtml(g.json);
}
return saida;
