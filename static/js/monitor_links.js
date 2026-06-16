/* ══════════════════════════════════════════════════════════════
   LINKS GERADOS — JS
   Arquivo: static/js/monitor_links.js
   Obs.: window.IS_ADMIN é definido no template (monitor_links.html).
   Só o admin do Hub pode excluir links de fato (operador vê o botão,
   mas recebe orientação para contatar o admin).
══════════════════════════════════════════════════════════════ */

let TODOS = [];

const BADGE = {
  ativo: { txt: "Ativo", cls: "badge-ativo" },
  usado: { txt: "Usado", cls: "badge-usado" },
  expirado: { txt: "Expirado", cls: "badge-expirado" },
};

function fmtCnpj(c) {
  if (!c) return "—";
  return c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

async function carregarLinks() {
  const p = new URLSearchParams();
  const busca = document.getElementById("fBusca").value.trim();
  const status = document.getElementById("fStatus").value;
  const de = document.getElementById("fDataDe").value;
  const ate = document.getElementById("fDataAte").value;
  if (busca) p.set("busca", busca);
  if (status) p.set("status", status);
  if (de) p.set("data_de", de);
  if (ate) p.set("data_ate", ate);

  document.getElementById("linksBody").innerHTML =
    `<tr><td colspan="8" class="loading-cell"><i class="fa-solid fa-circle-notch fa-spin"></i> Carregando…</td></tr>`;
  try {
    const res = await fetch("/api/monitor_links?" + p.toString());
    const data = await res.json();
    TODOS = data.links || [];
    atualizarStats(data.stats || {});
    renderizar(TODOS);
  } catch (e) {
    document.getElementById("linksBody").innerHTML =
      `<tr><td colspan="8" class="loading-cell erro">Erro ao carregar.</td></tr>`;
  }
}

function atualizarStats(s) {
  document.getElementById("stTotal").textContent = s.total || 0;
  document.getElementById("stAtivo").textContent = s.ativo || 0;
  document.getElementById("stUsado").textContent = s.usado || 0;
  document.getElementById("stExpirado").textContent = s.expirado || 0;
}

function renderizar(lista) {
  const body = document.getElementById("linksBody");
  const contador = document.getElementById("contador");
  if (contador) {
    contador.textContent =
      lista.length + (lista.length === 1 ? " link" : " links");
  }
  if (!lista.length) {
    body.innerHTML =
      `<tr><td colspan="8" class="loading-cell">Nenhum link encontrado.</td></tr>`;
    return;
  }
  body.innerHTML = lista
    .map((l) => {
      const b = BADGE[l.status] || BADGE.expirado;
      const tipo =
        l.tipo === "REATIVACAO"
          ? `<span class="badge-tipo">🔄 Reativação</span>`
          : `<span class="badge-tipo">🆕 Novo</span>`;
      let acoes = "";
      if (l.status === "ativo") {
        acoes = `<button class="btn-mini" onclick="copiarLink('${l.token}')"><i class="fa-solid fa-copy"></i> Copiar link</button>`;
      } else if (l.status === "usado") {
        acoes = `<span class="ficha-enviada"><i class="fa-solid fa-circle-check"></i> Ficha enviada</span>`;
      }
      // Botão Excluir aparece para todos; só admin exclui de fato.
      acoes += `<button class="btn-mini btn-icon danger" title="Excluir link" onclick="excluirLink(${l.id})"><i class="fa-solid fa-trash"></i></button>`;
      return `
      <tr>
        <td class="td-data">${l.created_at || "—"}</td>
        <td>${l.gerado_por_nome || "—"}</td>
        <td class="td-cnpj">${fmtCnpj(l.cnpj_cliente)}</td>
        <td>${l.vendedor || "—"}</td>
        <td>${tipo}</td>
        <td class="td-data">${l.expira_em || "—"}</td>
        <td><span class="badge ${b.cls}"><span class="dot"></span>${b.txt}</span></td>
        <td><div class="acoes-cell">${acoes}</div></td>
      </tr>`;
    })
    .join("");
}

async function excluirLink(id) {
  if (!window.IS_ADMIN) {
    alert(
      "🔒 Apenas um administrador do Hub pode excluir links.\n" +
        "Contate o administrador para remover este link.",
    );
    return;
  }
  if (!confirm("Excluir definitivamente este link? Esta ação não pode ser desfeita."))
    return;
  try {
    const res = await fetch("/api/links/" + id, { method: "DELETE" });
    if (res.ok) {
      carregarLinks();
    } else {
      alert("❌ Não foi possível excluir o link.");
    }
  } catch (e) {
    alert("❌ Erro de conexão ao excluir.");
  }
}

function copiarLink(token) {
  const url =
    window.location.origin + "/ficha_cliente?t=" + encodeURIComponent(token);
  const ta = document.createElement("textarea");
  ta.value = url;
  document.body.appendChild(ta);
  ta.select();
  try {
    document.execCommand("copy");
    alert("✅ Link copiado!");
  } catch (e) {
    prompt("Copie o link:", url);
  }
  document.body.removeChild(ta);
}

function limparFiltros() {
  document.getElementById("fBusca").value = "";
  document.getElementById("fStatus").value = "";
  document.getElementById("fDataDe").value = "";
  document.getElementById("fDataAte").value = "";
  carregarLinks();
}

document.addEventListener("DOMContentLoaded", carregarLinks);