// --- FUNÇÕES DE MÁSCARA ---

document.getElementById("cnpjInput").addEventListener("input", function (e) {
  let value = e.target.value.replace(/\D/g, "");
  if (value.length > 14) value = value.slice(0, 14);
  value = value.replace(/^(\d{2})(\d)/, "$1.$2");
  value = value.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
  value = value.replace(/\.(\d{3})(\d)/, ".$1/$2");
  value = value.replace(/(\d{4})(\d)/, "$1-$2");
  e.target.value = value;
});

function formatarCEP(cep) {
  let value = cep.replace(/\D/g, "");
  if (value.length > 8) value = value.slice(0, 8);
  return value.replace(/^(\d{5})(\d)/, "$1-$2");
}

function formatarData(dataISO) {
  if (!dataISO) return "";
  return dataISO.split("-").reverse().join("/");
}

function formatarCNPJ(cnpj) {
  if (!cnpj) return "";
  let value = cnpj.replace(/\D/g, "");
  return value.replace(
    /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2}).*/,
    "$1.$2.$3/$4-$5",
  );
}

// --- CONSOLE MODERNO ---

function addLogLine(tipo, texto) {
  const body = document.getElementById("terminal-fornecedor");
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
  const linhas = document.querySelectorAll("#terminal-fornecedor .log-text");
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

// --- LÓGICA DE BUSCA NA BRASILAPI ---

document.getElementById("btnConsultar").addEventListener("click", function () {
  const cnpj = document.getElementById("cnpjInput").value.replace(/\D/g, "");
  const btn = this;
  const dotStatus = document.getElementById("dot-fornecedor");
  const txtStatus = document.getElementById("txt-fornecedor");

  if (cnpj.length !== 14) {
    txtStatus.innerText = "CNPJ Inválido. Digite 14 números.";
    dotStatus.className = "status-dot bg-danger";
    return;
  }

  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
  btn.disabled = true;
  txtStatus.innerText = "Consultando Receita Federal...";
  dotStatus.className = "status-dot bg-warning";

  addLogLine(
    "info",
    `Consultando CNPJ ${document.getElementById("cnpjInput").value}...`,
  );

  fetch(`/consulta_cnpj/${cnpj}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.erro || data.message === "CNPJ não encontrado na base.") {
        throw new Error(data.message || "Erro na consulta.");
      }

      document.getElementById("razaoSocial").value = data.razao_social;
      document.getElementById("mei").value = data.mei;
      document.getElementById("cnpjCapturado").value = formatarCNPJ(data.cnpj);
      document.getElementById("nomeFantasia").value = data.nome_fantasia || "";
      document.getElementById("inscricaoEstadual").value =
        data.inscricao_estadual || "";
      document.getElementById("matrizFilial").value =
        data.descricao_identificador_matriz_filial;
      document.getElementById("dataAbertura").value = formatarData(
        data.data_inicio_atividade,
      );
      document.getElementById("naturezaJuridica").value =
        `${data.codigo_natureza_juridica} - ${data.natureza_juridica}`;
      document.getElementById("logradouro").value = data.logradouro;
      document.getElementById("numero").value = data.numero;
      document.getElementById("complemento").value = data.complemento;
      document.getElementById("cep").value = formatarCEP(data.cep);
      document.getElementById("bairro").value = data.bairro || "";
      document.getElementById("cidade").value =
        `${data.municipio} - ${data.uf}`;
      document.getElementById("cnaePrincipal").value =
        `${data.cnae_fiscal} - ${data.cnae_fiscal_descricao}`;

      txtStatus.innerText = "Dados carregados com sucesso! Revise e inicie.";
      dotStatus.className = "status-dot bg-success";

      // === INÍCIO DA CORREÇÃO: RESETANDO O BOTÃO VERDE ===
      const btnIniciar = document.getElementById("btnIniciarRobo");
      btnIniciar.style.display = "flex"; // Garante que ele apareça
      btnIniciar.disabled = false; // Destrava o botão (tira o bloqueio do robô anterior)
      btnIniciar.innerHTML =
        '<i class="fa-solid fa-play me-2"></i> Iniciar Cadastro no ERP'; // Volta o texto original
      btnIniciar.classList.remove("btn-secondary"); // Tira a cor cinza de "concluído"
      btnIniciar.classList.add("btn-success"); // Volta a cor verde
      // === FIM DA CORREÇÃO ===

      addLogLine("ok", `Empresa encontrada: ${data.razao_social}`);
      addLogLine("info", `Município: ${data.municipio} - ${data.uf}`);
      addLogLine("info", "--------------------------------------------------"); // Opcional: Linha para separar os logs visualmente
    })
    .catch((err) => {
      txtStatus.innerText = err.message;
      dotStatus.className = "status-dot bg-danger";
      document.getElementById("formFornecedor").reset();
      document.getElementById("btnIniciarRobo").style.display = "none";
      addLogLine("error", `Erro na consulta: ${err.message}`);
    })
    .finally(() => {
      btn.innerHTML = '<i class="fa-solid fa-search me-1"></i> Buscar';
      btn.disabled = false;
    });
});

// --- LÓGICA DO ROBÔ ---

async function iniciarCadastroERP() {
  const btn = document.getElementById("btnIniciarRobo");
  btn.disabled = true;
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Aguardando fila...';

  const cidadeUF = document.getElementById("cidade").value.split(" - ");
  const uf = cidadeUF.length > 1 ? cidadeUF[1] : "";
  const dados = {
    cnpj: document.getElementById("cnpjInput").value,
    razao_social: document.getElementById("razaoSocial").value,
    nome_fantasia: document.getElementById("nomeFantasia").value,
    inscricao_estadual: document.getElementById("inscricaoEstadual").value,
    cep: document.getElementById("cep").value,
    logradouro: document.getElementById("logradouro").value,
    numero: document.getElementById("numero").value,
    complemento: document.getElementById("complemento").value,
    bairro: document.getElementById("bairro").value,
    uf: uf,
  };

  const footerProc = document.getElementById("footerProc");
  if (footerProc) footerProc.textContent = "robo_fornecedor.py";

  const resp = await fetch("/fila/entrar", { method: "POST" });
  const { id: filaId, posicao } = await resp.json();

  addLogLine("default", "─────────────────────────────────");
  if (posicao > 1) {
    addLogLine(
      "warn",
      `Sistema ocupado. Você é o ${posicao}º na fila. Aguardando automaticamente...`,
    );
  } else {
    addLogLine("info", `Iniciando robô para CNPJ: ${dados.cnpj}`);
  }

  const jsonString = encodeURIComponent(JSON.stringify(dados));
  const source = new EventSource(
    `/run_fornecedor?fila_id=${filaId}&dados=${jsonString}`,
  );

  source.onmessage = function (event) {
    if (event.data.startsWith("[FILA]")) {
      const pos = event.data.match(/posição (\d+)/);
      if (pos) {
        const terminal = document.getElementById("terminal-fornecedor");
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
      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();
      addLogLine("ok", "Processo finalizado com sucesso!");
      addLogLine("default", "─────────────────────────────────");
      if (footerProc) footerProc.textContent = "concluído";
      btn.innerHTML =
        '<i class="fa-solid fa-check-double me-2"></i> Cadastro Concluído';
      return;
    }
    const msg = event.data;
    if (msg.includes("✅") || msg.toLowerCase().includes("cadastrado"))
      addLogLine("ok", msg);
    else if (msg.includes("❌") || msg.toLowerCase().includes("erro"))
      addLogLine("error", msg);
    else if (msg.includes("⚠️")) addLogLine("warn", msg);
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
