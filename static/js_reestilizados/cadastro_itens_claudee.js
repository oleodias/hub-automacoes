// --- LÓGICA DO MÓDULO: CADASTRO DE ITENS (FISCAL) ---

function addLogLine(tipo, texto) {
  const body = document.getElementById("terminal");
  if (!body) return;
  const prefixos = { ok: "✓", error: "✗", warn: "!", info: "i", muted: "·", default: "›" };
  const agora = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const linha = document.createElement("div");
  linha.className = "log-line log-" + tipo;
  linha.innerHTML = `<span class="log-time">${agora}</span><span class="log-prefix">${prefixos[tipo] || "›"}</span><span class="log-text">${texto}</span>`;
  body.appendChild(linha);
  body.scrollTop = body.scrollHeight;
  const counter = document.getElementById("footerLines");
  if (counter) counter.textContent = body.querySelectorAll(".log-line").length;
}

function copiarLog() {
  const linhas = document.querySelectorAll("#terminal .log-text");
  const texto = Array.from(linhas).map((l) => l.textContent).join("\n");
  navigator.clipboard.writeText(texto).then(() => {
    const btn = document.getElementById("btnCopiarLog");
    if (!btn) return;
    btn.classList.add("copied");
    btn.childNodes[btn.childNodes.length - 1].textContent = " Copiado!";
    setTimeout(() => {
      btn.classList.remove("copied");
      btn.childNodes[btn.childNodes.length - 1].textContent = " Copiar log";
    }, 2200);
  });
}

function alternarTelaCheia() {
  const container = document.getElementById("container-do-log");
  if (container) container.classList.toggle("log-expandido");
}

// INTEGRAÇÃO UPLOAD XML
const fileInput = document.getElementById("fileInput");
if (fileInput) {
  fileInput.addEventListener("change", function () {
    let file = this.files[0];
    if (file) {
      document.getElementById("dropZone").classList.add("success");
      document.getElementById("uploadText").innerText = file.name;
      document.getElementById("uploadIcon").className = "fa-solid fa-file-circle-check fa-3x";
      document.getElementById("uploadIcon").style.color = "#34d399";

      addLogLine("info", `Carregando arquivo: ${file.name}`);

      let formData = new FormData();
      formData.append("file", file);

      fetch("/upload", { method: "POST", body: formData })
        .then((r) => {
          if (!r.ok) throw new Error("Servidor não encontrado");
          return r.json();
        })
        .then((data) => {
          if (data.status === "ok") {
            addLogLine("ok", "Arquivo carregado. Pronto para auditoria.");
            document.getElementById("dot-fase1").className = "status-dot bg-yellow";
            document.getElementById("badge-fase1").className = "badge-fase badge-pendente";
            document.getElementById("txt-fase1").innerText = "Pronto para iniciar";
            document.getElementById("btn-fase1").disabled = false;
          }
        })
        .catch((err) => {
          addLogLine("error", `Erro no upload: ${err.message}`);
        });
    }
  });
}

// FASE 1
function rodarFase1() {
  document.getElementById("btn-fase1").disabled = true;
  document.getElementById("dot-fase1").className = "status-dot bg-yellow";

  const footerProc = document.getElementById("footerProc");
  if (footerProc) footerProc.textContent = "fase1_ncm.py";

  addLogLine("default", "─────────────────────────────────");
  addLogLine("info", "Iniciando Robô de Triagem — Fase 1...");

  const source = new EventSource("/run_fase1");

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();
      addLogLine("ok", "Fase 1 concluída! Itens na fila.");
      addLogLine("default", "─────────────────────────────────");
      if (footerProc) footerProc.textContent = "fase1 ok";
      document.getElementById("dot-fase1").className = "status-dot bg-green";
      document.getElementById("btn-fase2").disabled = false;

    } else if (event.data === "[FIM_SEM_ITENS]") {
      source.close();
      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();
      addLogLine("warn", "Nenhum item novo para cadastrar.");
      addLogLine("default", "─────────────────────────────────");
      if (footerProc) footerProc.textContent = "sem itens";
      document.getElementById("dot-fase1").className = "status-dot bg-green";
      document.getElementById("btn-fase2").disabled = true;

    } else {
      const msg = event.data;
      if (msg.includes("✅") || msg.toLowerCase().includes("válido")) {
        addLogLine("ok", msg);
      } else if (msg.includes("❌") || msg.toLowerCase().includes("erro")) {
        addLogLine("error", msg);
      } else if (msg.includes("⚠️") || msg.toLowerCase().includes("não encontrado")) {
        addLogLine("warn", msg);
      } else {
        addLogLine("default", msg);
      }
    }
  };

  source.onerror = function () {
    source.close();
    addLogLine("error", "Erro de conexão com o servidor na Fase 1.");
    if (footerProc) footerProc.textContent = "erro";
    document.getElementById("dot-fase1").className = "status-dot bg-red";
    document.getElementById("btn-fase1").disabled = false;
  };
}

// FASE 2
function rodarFase2() {
  document.getElementById("btn-fase2").disabled = true;
  document.getElementById("dot-fase2").className = "status-dot bg-yellow";
  document.getElementById("txt-fase2").innerText = "Rodando...";

  const footerProc = document.getElementById("footerProc");
  if (footerProc) footerProc.textContent = "fase2_item.py";

  addLogLine("default", "─────────────────────────────────");
  addLogLine("info", "Iniciando Robô de Cadastro — Fase 2...");

  const source = new EventSource("/run_fase2");

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      addLogLine("default", "─────────────────────────────────");
      addLogLine("ok", "Operação finalizada! Todos os itens estão no ERP.");
      if (footerProc) footerProc.textContent = "concluído";
      document.getElementById("dot-fase2").className = "status-dot bg-green";
      document.getElementById("txt-fase2").innerText = "Concluído!";
      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();
    } else {
      const msg = event.data;
      if (msg.includes("✅") || msg.toLowerCase().includes("cadastrado")) {
        addLogLine("ok", msg);
      } else if (msg.includes("❌") || msg.toLowerCase().includes("erro")) {
        addLogLine("error", msg);
      } else if (msg.includes("⚠️")) {
        addLogLine("warn", msg);
      } else {
        addLogLine("default", msg);
      }
    }
  };

  source.onerror = function () {
    source.close();
    addLogLine("error", "Conexão encerrada com o servidor.");
    if (footerProc) footerProc.textContent = "erro";
    document.getElementById("dot-fase2").className = "status-dot bg-red";
    document.getElementById("txt-fase2").innerText = "Erro";
    document.getElementById("btn-fase2").disabled = false;
  };
}
