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

return Object.values(grupos);
