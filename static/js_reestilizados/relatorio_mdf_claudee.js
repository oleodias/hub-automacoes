// --- LÓGICA DO MÓDULO: RELATÓRIO MDF-E ---

document.addEventListener("DOMContentLoaded", () => {
  preencherDatasMDF();
});

// --- CONSOLE MODERNO ---

function addLogLine(tipo, texto) {
  const body = document.getElementById("terminal-mdf");
  if (!body) return;
  const prefixos = {
    ok: "✓",
    error: "✗",
    warn: "!",
    info: "i",
    muted: "·",
    default: "›",
  };
  const agora = new Date().toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const linha = document.createElement("div");
  linha.className = "log-line log-" + tipo;
  linha.innerHTML = `<span class="log-time">${agora}</span><span class="log-prefix">${prefixos[tipo] || "›"}</span><span class="log-text">${texto}</span>`;
  body.appendChild(linha);
  body.scrollTop = body.scrollHeight;
  const counter = document.getElementById("footerLines");
  if (counter) counter.textContent = body.querySelectorAll(".log-line").length;
}

function copiarLog() {
  const linhas = document.querySelectorAll("#terminal-mdf .log-text");
  const texto = Array.from(linhas)
    .map((l) => l.textContent)
    .join("\n");
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

// --- DATAS ---

function preencherDatasMDF() {
  const dataHoje = new Date();
  const ultimoDiaMesPassado = new Date(
    dataHoje.getFullYear(),
    dataHoje.getMonth(),
    0,
  );
  const primeiroDiaMesPassado = new Date(
    ultimoDiaMesPassado.getFullYear(),
    ultimoDiaMesPassado.getMonth(),
    1,
  );

  const formatarDataInput = (data) => {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, "0");
    const dia = String(data.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  };

  const inputInicio = document.getElementById("mdf-inicio");
  const inputFim = document.getElementById("mdf-fim");

  if (inputInicio && inputFim && !inputInicio.value && !inputFim.value) {
    inputInicio.value = formatarDataInput(primeiroDiaMesPassado);
    inputFim.value = formatarDataInput(ultimoDiaMesPassado);
  }
}

function limparDatas() {
  document.getElementById("mdf-inicio").value = "";
  document.getElementById("mdf-fim").value = "";
  addLogLine("muted", "Datas limpas. Insira o novo período.");
}

// --- ROBÔ MDF ---

function rodarMDF() {
  const inicioRaw = document.getElementById("mdf-inicio").value;
  const fimRaw = document.getElementById("mdf-fim").value;

  if (!inicioRaw || !fimRaw) {
    addLogLine("warn", "Selecione as datas de início e fim antes de começar!");
    return;
  }

  const formatar = (d) => d.split("-").reverse().join("/");
  const inicio = formatar(inicioRaw);
  const fim = formatar(fimRaw);

  const footerProc = document.getElementById("footerProc");
  if (footerProc) footerProc.textContent = "robo_mdf.py";

  document.getElementById("btn-mdf").disabled = true;
  document.getElementById("btn-download-mdf").style.display = "none";
  document.getElementById("dot-mdf").className = "status-dot bg-yellow";
  document.getElementById("txt-mdf").innerText = "Robô operando...";

  addLogLine("default", "─────────────────────────────────");
  addLogLine("info", `Iniciando extração: ${inicio} até ${fim}...`);

  const source = new EventSource(`/run_mdf?inicio=${inicio}&fim=${fim}`);

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      const audio = document.getElementById("audioSucesso");
      if (audio) {
        audio.volume = 0.5;
        audio.play();
      }
      addLogLine("ok", "Processo finalizado com sucesso! Planilha gerada.");
      addLogLine("default", "─────────────────────────────────");
      if (footerProc) footerProc.textContent = "concluído";
      document.getElementById("dot-mdf").className = "status-dot bg-green";
      document.getElementById("txt-mdf").innerText = "Concluído!";
      document.getElementById("btn-mdf").disabled = false;
      document.getElementById("btn-download-mdf").style.display = "flex";
    } else {
      const msg = event.data;
      if (msg.includes("✅") || msg.toLowerCase().includes("sucesso")) {
        addLogLine("ok", msg);
      } else if (msg.includes("❌") || msg.toLowerCase().includes("erro")) {
        addLogLine("error", msg);
      } else if (msg.includes("⚠️") || msg.toLowerCase().includes("aviso")) {
        addLogLine("warn", msg);
      } else {
        addLogLine("default", msg);
      }
    }
  };

  source.onerror = function () {
    source.close();
    addLogLine(
      "error",
      "Erro de conexão. O processo pode ter sido interrompido.",
    );
    if (footerProc) footerProc.textContent = "erro";
    document.getElementById("dot-mdf").className = "status-dot bg-red";
    document.getElementById("txt-mdf").innerText = "Erro de Conexão";
    document.getElementById("btn-mdf").disabled = false;
  };
}

// --- DOWNLOAD ---

let navegarLivremente = false;

/* window.addEventListener("beforeunload", (event) => {
  if (navegarLivremente) return;
  event.preventDefault();
  event.returnValue = "";
}); */

function baixarRelatorio() {
  navegarLivremente = true;
  addLogLine("info", "Iniciando download do relatório...");
  window.location.href = "/download_mdf";
  setTimeout(() => {
    navegarLivremente = false;
  }, 1000);
}
