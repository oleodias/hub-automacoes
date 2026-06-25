// ══════════════════════════════════════════════════════════════
// formatar_erro.js — Code node do n8n (ramo de ERRO do robô)
// ──────────────────────────────────────────────────────────────
// Roda quando "Robô OK?" é FALSE. Lê o resultado ESTRUTURADO do robô
// (em "Iniciar Robo".resultado: etapa, lab, periodo, progresso,
// explicacao, sugestao, detalhe_tecnico) e monta um e-mail HTML claro
// (identidade Ciamed) para o nó "Avisos (erro)".
// Saída: { to, subject, html }.
// ══════════════════════════════════════════════════════════════

const ini = $("Iniciar Robo").first().json || {};
const res = ini.resultado ? ini.resultado : ini;          // tolera as duas formas
const ag = $("Agenda").first().json || {};

const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const etapa     = res.etapa || "";
const lab       = res.lab || "";
const periodo   = res.periodo || "";
const progresso = res.progresso || "";
const explic    = res.explicacao || res.msg || "Ocorreu um erro durante a execução do robô.";
const sugestao  = res.sugestao || "Rode novamente; se persistir, avise o desenvolvedor.";
const detalhe   = res.detalhe_tecnico || res.msg || "";
const execId    = res.exec || (res.pasta ? String(res.pasta).split(/[\\/]/).pop() : "");
const quando    = ag.data_ref || "";

const linha = (rot, val) => val
  ? `<tr><td style="padding:5px 0;color:#6E6E6E;width:130px;vertical-align:top;">${esc(rot)}</td><td style="padding:5px 0;">${esc(val)}</td></tr>`
  : "";

const html = `<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f6f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#333;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;border:1px solid #e6e9ec;">
        <tr><td style="background:#00B3B2;padding:16px 22px;">
          <div style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:4px;line-height:1;">CIAMED</div>
          <div style="color:#e6f7f7;font-size:12px;margin-top:5px;">Aviso automático · Robô de Relatórios</div>
        </td></tr>
        <tr><td style="background:#FCEBEB;border-left:4px solid #A32D2D;padding:12px 18px;">
          <div style="color:#A32D2D;font-size:15px;font-weight:bold;">O robô parou antes de concluir os envios</div>
          <div style="color:#7a3030;font-size:13px;margin-top:2px;">Nenhum e-mail foi enviado aos laboratórios nesta execução.</div>
        </td></tr>
        <tr><td style="padding:18px 22px 6px;">
          <table role="presentation" width="100%" style="font-size:13px;border-collapse:collapse;">
            ${linha("Quando", quando)}
            ${linha("Etapa", etapa)}
            ${linha("Laboratório", lab)}
            ${linha("Período", periodo)}
            ${linha("Progresso", progresso)}
            ${execId ? `<tr><td style="padding:5px 0;color:#6E6E6E;vertical-align:top;">Execução</td><td style="padding:5px 0;font-family:monospace;font-size:12px;">${esc(execId)}</td></tr>` : ""}
          </table>
        </td></tr>
        <tr><td style="padding:8px 22px;">
          <div style="font-size:13px;color:#00B3B2;font-weight:bold;margin-bottom:4px;">O que aconteceu</div>
          <div style="font-size:13px;line-height:1.5;">${esc(explic)}</div>
          <div style="font-size:13px;color:#00B3B2;font-weight:bold;margin:12px 0 4px;">O que fazer</div>
          <div style="font-size:13px;line-height:1.5;">${esc(sugestao)}</div>
        </td></tr>
        ${detalhe ? `<tr><td style="padding:10px 22px 18px;">
          <div style="font-size:11px;color:#8A8A8A;margin-bottom:4px;">Detalhe técnico (para a TI)</div>
          <div style="font-family:monospace;font-size:11px;color:#555;background:#f4f6f8;border:1px solid #eee;border-radius:4px;padding:8px 10px;word-break:break-word;">${esc(detalhe)}</div>
        </td></tr>` : ""}
        <tr><td style="padding:12px 22px;border-top:1px solid #eee;">
          <p style="margin:0;font-size:12px;color:#8A8A8A;line-height:1.5;">Mensagem automática do Hub de Automações — Ciamed.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;

const subject = `⚠️ Robô de relatórios falhou — ${[lab, etapa].filter(Boolean).join(" · ") || quando}`;

return [{ json: { to: ag.email_avisos || "", subject, html } }];
