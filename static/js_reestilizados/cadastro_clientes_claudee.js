// ==========================================
// MÓDULO: CADASTRO E REATIVAÇÃO DE CLIENTES
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  // 1. Configurar Drag & Drop e Clique na Área de Upload
  const dropZone = document.getElementById("dropZoneCliente");
  const fileInput = document.getElementById("fileFichaCliente");

  dropZone.addEventListener("click", (e) => {
    // Bloqueia o "efeito bolha": só aciona se o clique não tiver vindo do próprio input!
    if (e.target !== fileInput) {
      fileInput.click();
    }
  });
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--teal)";
    dropZone.style.background = "var(--teal-dim)";
  });

  dropZone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--border-hover)";
    dropZone.style.background = "rgba(0,0,0,0.15)";
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.style.borderColor = "var(--border-hover)";
    dropZone.style.background = "rgba(0,0,0,0.15)";

    if (e.dataTransfer.files.length > 0) {
      enviarFicha(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      enviarFicha(e.target.files[0]);
    }
  });
});

// 2. Enviar a Ficha para o Backend (Python)
async function enviarFicha(file) {
  // === NOVO: Muda o visual da caixa de upload na hora! ===
  const uploadText = document.getElementById("uploadText");
  const uploadIcon = document.getElementById("uploadIcon");

  uploadText.innerHTML = `Arquivo <span style="color: var(--teal); font-weight: bold;">${file.name}</span> carregado!`;
  uploadIcon.className = "fa-solid fa-file-circle-check upload-icon";
  uploadIcon.style.color = "var(--teal)";
  // ========================================================

  logConsole(`Lendo arquivo: ${file.name}...`, "info");
  document.getElementById("txt-cliente").innerText =
    "Lendo ficha e cruzando dados com a Receita Federal...";
  document.getElementById("dot-cliente").className = "status-dot bg-yellow";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/upload_ficha_cliente", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (data.erro) {
      logConsole(`Erro: ${data.mensagem}`, "error");
      document.getElementById("txt-cliente").innerText =
        "Erro ao processar a ficha.";
      document.getElementById("dot-cliente").className = "status-dot bg-red";
      return;
    }

    preencherTela(data);
  } catch (error) {
    logConsole(`Erro fatal de comunicação: ${error}`, "error");
    document.getElementById("dot-cliente").className = "status-dot bg-red";
  }
}

// 3. Preencher os Inputs da Tela (Human in the Loop)
function preencherTela(data) {
  logConsole("Sucesso! Dados extraídos e validados pela API.", "ok");

  if (data.aviso_api) {
    logConsole(data.aviso_api, "warn");
  }

  // --- Dados Fiscais ---
  document.getElementById("cliCnpj").value = data.cnpj_limpo || "";
  document.getElementById("cliIe").value = data.inscricao_estadual || "";
  document.getElementById("cliCodigo").value = data.codigo_cliente || "";
  document.getElementById("cliRazao").value = data.razao_social || "";
  document.getElementById("cliFantasia").value = data.nome_fantasia || "";
  document.getElementById("cliCep").value = data.cep || "";
  document.getElementById("cliLogradouro").value = data.logradouro || "";
  document.getElementById("cliNumero").value = data.numero || "";
  document.getElementById("cliCnae").value = data.cnae_principal || "";

  // --- Contatos ---
  document.getElementById("cliEmailXml").value = data.email_xml || "";

  document.getElementById("ctoComprasNome").value = data.compras_nome || "";
  document.getElementById("ctoComprasTel").value = data.compras_tel || "";
  document.getElementById("ctoComprasEmail").value = data.compras_email || "";

  document.getElementById("ctoRecNome").value = data.rec_nome || "";
  document.getElementById("ctoRecTel").value = data.rec_tel || "";
  document.getElementById("ctoRecEmail").value = data.rec_email || "";

  document.getElementById("ctoFinNome").value = data.fin_nome || "";
  document.getElementById("ctoFinTel").value = data.fin_tel || "";
  document.getElementById("ctoFinEmail").value = data.fin_email || "";

  document.getElementById("ctoFarmaNome").value = data.farma_nome || "";
  document.getElementById("ctoFarmaTel").value = data.farma_tel || "";
  document.getElementById("ctoFarmaEmail").value = data.farma_email || "";

  // --- Comercial ---
  document.getElementById("cliRegraFat").value = data.regra_faturamento || "";
  document.getElementById("cliCaptacao").value = data.captacao || "";
  document.getElementById("cliVendedor").value = data.vendedor || "";
  document.getElementById("cliRepresentante").value = data.representante || "";

  // --- Status Visual ---
  document.getElementById("txt-cliente").innerText =
    "Ficha processada! Revise os dados abaixo.";
  document.getElementById("dot-cliente").className = "status-dot bg-green";

  const dropZone = document.getElementById("dropZoneCliente");
  dropZone.classList.add("success");

  // Tocar áudio de sucesso
  const audio = document.getElementById("audioSucesso");
  if (audio) audio.play();

  // --- Lógica de Botões (Novo vs Reativação) ---
  const badge = document.getElementById("badgeTipoCadastro");
  const btnNovo = document.getElementById("btnAprovarNovo");
  const btnReativacao = document.getElementById("btnAprovarReativacao");

  btnNovo.disabled = true;
  btnReativacao.disabled = true;

  if (data.tipo_cadastro === "NOVO") {
    badge.innerText = "CADASTRO NOVO";
    badge.className = "badge-tipo novo";
    btnNovo.disabled = false;
    logConsole("> Ficha identificada como: CADASTRO NOVO.", "info");
  } else if (data.tipo_cadastro === "REATIVACAO") {
    badge.innerText = "REATIVAÇÃO";
    badge.className = "badge-tipo reativacao";
    btnReativacao.disabled = false;
    logConsole(
      `> Ficha identificada como: REATIVAÇÃO (Código ERP: ${data.codigo_cliente})`,
      "info",
    );
  } else {
    badge.innerText = "NÃO IDENTIFICADO";
    badge.className = "badge-tipo";
    logConsole(
      "> AVISO: O tipo de cadastro (E237 ou X237) não estava preenchido na ficha!",
      "warn",
    );
  }
}

// ==========================================
// FUNÇÕES DOS BOTÕES (FUTURAS)
// ==========================================
function iniciarCadastroNovo() {
  logConsole("Iniciando Robô de Cadastro de Cliente Novo no ERP...", "info");
  // Aqui chamaremos a rota do segundo robô python (cadastro_novo.py)
}

function iniciarReativacao() {
  logConsole("Iniciando Robô de Reativação de Cliente no ERP...", "info");
  // Aqui chamaremos a rota do terceiro robô python (cadastro_reativacao.py)
}

// ==========================================
// TERMINAL LOGS
// ==========================================
function logConsole(text, type = "default") {
  const term = document.getElementById("terminal-cliente");
  if (!term) return;

  const time = new Date().toLocaleTimeString("pt-BR");
  const div = document.createElement("div");
  div.className = `log-line log-${type}`;
  div.innerHTML = `
      <span class="log-time">${time}</span>
      <span class="log-prefix">·</span>
      <span class="log-text">${text}</span>
    `;

  term.appendChild(div);
  term.scrollTop = term.scrollHeight;

  const linesCount = term.querySelectorAll(".log-line").length;
  document.getElementById("footerLines").innerText = linesCount;
}

function copiarLog() {
  const term = document.getElementById("terminal-cliente");
  if (!term) return;
  const lines = Array.from(term.querySelectorAll(".log-line"))
    .map((line) => line.innerText)
    .join("\n");
  navigator.clipboard.writeText(lines).then(() => {
    const btn = document.getElementById("btnCopiarLog");
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
    btn.classList.add("copied");
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.classList.remove("copied");
    }, 2000);
  });
}
