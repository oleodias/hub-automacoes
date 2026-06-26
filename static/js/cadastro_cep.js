// --- MÁSCARA DE CEP ---

document.getElementById("cepInput").addEventListener("input", function (e) {
  let value = e.target.value.replace(/\D/g, "");
  if (value.length > 8) value = value.slice(0, 8);
  e.target.value = value.replace(/^(\d{5})(\d)/, "$1-$2");
});

function formatarCEP(cep) {
  let value = (cep || "").replace(/\D/g, "");
  if (value.length > 8) value = value.slice(0, 8);
  return value.replace(/^(\d{5})(\d)/, "$1-$2");
}

// --- CONSOLE MODERNO ---

function addLogLine(tipo, texto) {
  const body = document.getElementById("terminal-cep");
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
  const linhas = document.querySelectorAll("#terminal-cep .log-text");
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

// --- BUSCA DO CEP (preview) ---

document.getElementById("btnConsultar").addEventListener("click", function () {
  const cep = document.getElementById("cepInput").value.replace(/\D/g, "");
  const btn = this;
  const dotStatus = document.getElementById("dot-cep");
  const txtStatus = document.getElementById("txt-cep");

  if (cep.length !== 8) {
    txtStatus.innerText = "CEP inválido. Digite 8 números.";
    dotStatus.className = "status-dot bg-danger";
    return;
  }

  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
  btn.disabled = true;
  txtStatus.innerText = "Consultando endereço...";
  dotStatus.className = "status-dot bg-warning";

  addLogLine("info", `Consultando CEP ${formatarCEP(cep)}...`);

  fetch(`/api/consulta_cep/${cep}`)
    .then((response) => response.json())
    .then((data) => {
      const status = data._cep_api_status || "desconhecido";
      if (status !== "ok" && !data.cidade) {
        throw new Error(`CEP não encontrado (${status}).`);
      }

      document.getElementById("cep").value = formatarCEP(data.cep || cep);
      document.getElementById("logradouro").value = data.logradouro || "";
      document.getElementById("uf").value = data.uf || "";
      document.getElementById("cidade").value = data.cidade || "";
      document.getElementById("bairro").value = data.bairro || "";
      document.getElementById("ibge").value = data.ibge || "";
      document.getElementById("complemento").value = data.complemento || "";

      // Avisos de fallback (CEP "seco")
      if (!data.bairro)
        addLogLine("warn", "CEP sem bairro — será usado 'INFORMAR BAIRRO'.");
      if (!data.logradouro)
        addLogLine(
          "warn",
          "CEP sem logradouro — será usado 'INFORME LOGRADOURO'.",
        );

      txtStatus.innerText = "Endereço carregado! Revise e inicie.";
      dotStatus.className = "status-dot bg-success";

      const btnIniciar = document.getElementById("btnIniciarRobo");
      btnIniciar.style.display = "flex";
      btnIniciar.disabled = false;
      btnIniciar.innerHTML =
        '<i class="fa-solid fa-play me-2"></i> Iniciar Cadastro no ERP';

      addLogLine("ok", `Endereço: ${data.cidade} - ${data.uf}`);
      addLogLine("info", "--------------------------------------------------");
    })
    .catch((err) => {
      txtStatus.innerText = err.message;
      dotStatus.className = "status-dot bg-danger";
      document.getElementById("formCep").reset();
      document.getElementById("btnIniciarRobo").style.display = "none";
      addLogLine("error", `Erro na consulta: ${err.message}`);
    })
    .finally(() => {
      btn.innerHTML = '<i class="fa-solid fa-search me-1"></i> Buscar';
      btn.disabled = false;
    });
});

// --- LÓGICA DO ROBÔ ---

async function iniciarCadastroCep() {
  const btn = document.getElementById("btnIniciarRobo");
  btn.disabled = true;
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Aguardando fila...';

  const dados = {
    cep: document.getElementById("cep").value,
    logradouro: document.getElementById("logradouro").value,
    complemento: document.getElementById("complemento").value,
    bairro: document.getElementById("bairro").value,
    cidade: document.getElementById("cidade").value,
    uf: document.getElementById("uf").value,
    codigo_novo_bairro: document.getElementById("codigoNovoBairro").value,
    codigo_tipo_logradouro: document.getElementById("codigoTipoLogradouro").value,
  };

  const footerProc = document.getElementById("footerProc");
  if (footerProc) footerProc.textContent = "cadastro_cep.py";

  const resp = await fetch("/fila/entrar", { method: "POST" });
  const { id: filaId, posicao } = await resp.json();

  addLogLine("default", "─────────────────────────────────");
  if (posicao > 1) {
    addLogLine(
      "warn",
      `Sistema ocupado. Você é o ${posicao}º na fila. Aguardando automaticamente...`,
    );
  } else {
    addLogLine("info", `Iniciando robô para CEP: ${dados.cep}`);
  }

  const jsonString = encodeURIComponent(JSON.stringify(dados));
  const source = new EventSource(`/run_cep?fila_id=${filaId}&dados=${jsonString}`);

  source.onmessage = function (event) {
    if (event.data.startsWith("[FILA]")) {
      const pos = event.data.match(/posição (\d+)/);
      if (pos) {
        const terminal = document.getElementById("terminal-cep");
        const ultimaLinha = terminal
          ? terminal.querySelector(".log-line:last-child .log-text")
          : null;
        if (
          ultimaLinha &&
          ultimaLinha.textContent.startsWith("Aguardando na fila")
        ) {
          ultimaLinha.textContent = `Aguardando na fila... posição ${pos[1]}`;
        } else {
          addLogLine("muted", `Aguardando na fila... posição ${pos[1]}`);
        }
      }
      return;
    }
    if (event.data === "[FILA_LIBERADA]") {
      addLogLine("info", "Fila liberada! Iniciando agora...");
      btn.innerHTML =
        '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Operando ERP...';
      return;
    }
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      addLogLine("ok", "Processo finalizado!");
      addLogLine("default", "─────────────────────────────────");
      if (footerProc) footerProc.textContent = "concluído";
      btn.innerHTML =
        '<i class="fa-solid fa-check-double me-2"></i> Cadastro Concluído';
      return;
    }
    const msg = event.data;
    if (msg.includes("✅") || msg.includes("🏆") || msg.includes("🏁"))
      addLogLine("ok", msg);
    else if (msg.includes("❌")) addLogLine("error", msg);
    else if (msg.includes("⚠️") || msg.includes("🟡")) addLogLine("warn", msg);
    else addLogLine("default", msg);
  };

  source.onerror = function () {
    source.close();
    addLogLine("error", "Erro de conexão com o servidor.");
    if (footerProc) footerProc.textContent = "erro";
    btn.disabled = false;
    btn.innerHTML =
      '<i class="fa-solid fa-rotate-right me-2"></i> Tentar Novamente';
    fetch(`/fila/sair/${filaId}`, { method: "POST" });
  };
}
