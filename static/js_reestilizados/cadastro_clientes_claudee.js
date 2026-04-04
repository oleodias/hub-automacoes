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
  document.getElementById("cliComplemento").value = data.complemento || "";
  document.getElementById("cliBairro").value = data.bairro || "";
  document.getElementById("cliUf").value = data.estado || ""; // O leitor_ficha usa "estado"
  document.getElementById("cliNumero").value = data.numero || "";
  document.getElementById("cliCnae").value = data.cnae_principal || "";

  // --- Contatos ---
  document.getElementById("cliEmailXml").value = data.email_xml || "";
  document.getElementById("cliTelefone").value = data.telefone_empresa || "";

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

  // 👇 ADICIONE ESTA LÓGICA DO CEBAS AQUI 👇
  const cnaeDesc = (data.cnae_principal || "").toLowerCase();
  const containerCebas = document.getElementById("container-cebas");
  document.getElementById("cliCebas").value = ""; // Limpa testes antigos

  if (cnaeDesc.includes("varejista") || cnaeDesc.includes("atacadista")) {
    containerCebas.style.display = "none";
  } else {
    containerCebas.style.display = "block";
  }
  // 👆 FIM DA LÓGICA DO CEBAS 👆

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

async function iniciarCadastroNovo() {
  // 👇 1. ADICIONE A TRAVA DE SEGURANÇA AQUI NO TOPO 👇
  const containerCebas = document.getElementById("container-cebas");
  const cebasValor = document.getElementById("cliCebas").value;

  if (containerCebas.style.display === "block" && cebasValor === "") {
    logConsole(
      "❌ ERRO: Você precisa informar se o cliente possui CEBAS antes de iniciar!",
      "error",
    );
    alert("Por favor, responda se o CNPJ possui CEBAS.");
    return; // Impede o robô de rodar!
  }
  // 👆 FIM DA TRAVA 👆

  // 👇 NOVA TRAVA DA CAPTAÇÃO 👇
  const captacaoValor = document.getElementById("cliNovaCaptacao").value;
  if (captacaoValor === "") {
    logConsole(
      "❌ ERRO: Você precisa informar a Forma de Captação antes de iniciar!",
      "error",
    );
    alert("Por favor, selecione a Forma de Captação do cliente.");
    return;
  }
  // 👆 FIM DA NOVA TRAVA 👆

  const btn = document.getElementById("btnAprovarNovo");
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Ligando Robô...';
  btn.disabled = true;

  // 1. LENDO OS CONTATOS DA TELA
  const contatos_da_tela = [
    {
      codigo: "30", // Compras
      nome: document.getElementById("ctoComprasNome")?.value || "",
      tel: document.getElementById("ctoComprasTel")?.value || "",
      email: document.getElementById("ctoComprasEmail")?.value || "",
    },
    {
      codigo: "35", // Recebimento
      nome: document.getElementById("ctoRecNome")?.value || "",
      tel: document.getElementById("ctoRecTel")?.value || "",
      email: document.getElementById("ctoRecEmail")?.value || "",
    },
    {
      codigo: "50", // Financeiro
      nome: document.getElementById("ctoFinNome")?.value || "",
      tel: document.getElementById("ctoFinTel")?.value || "",
      email: document.getElementById("ctoFinEmail")?.value || "",
    },
    {
      codigo: "20", // Farmacêutico
      nome: document.getElementById("ctoFarmaNome")?.value || "",
      tel: document.getElementById("ctoFarmaTel")?.value || "",
      email: document.getElementById("ctoFarmaEmail")?.value || "",
    },
  ];

  // 2. EMPACOTANDO TUDO PARA O PYTHON
  const pacoteDeDados = {
    cnpj_limpo: document.getElementById("cliCnpj")?.value || "",
    razao_social: document.getElementById("cliRazao")?.value || "",
    nome_fantasia: document.getElementById("cliFantasia")?.value || "",
    inscricao_estadual: document.getElementById("cliIe")?.value || "",
    cep: document.getElementById("cliCep")?.value || "",
    regra_faturamento: document.getElementById("cliRegraFat")?.value || "",
    logradouro: document.getElementById("cliLogradouro")?.value || "",
    numero: document.getElementById("cliNumero")?.value || "",
    complemento: document.getElementById("cliComplemento")?.value || "",
    bairro: document.getElementById("cliBairro")?.value || "",
    uf: document.getElementById("cliUf")?.value || "RS",
    cnae_principal_descricao:
      document.getElementById("cliCnae")?.value || "Varejista",
    telefone_empresa: document.getElementById("cliTelefone")?.value || "",

    // 👇 ADICIONE ESTA LINHA 👇
    tem_cebas: cebasValor,
    representante: document.getElementById("cliRepresentante")?.value || "",
    forma_captacao: captacaoValor,
    vendedor: document.getElementById("cliVendedor")?.value || "",

    // AQUI VÃO OS CONTATOS!
    email_xml: document.getElementById("cliEmailXml")?.value || "",
    contatos_da_tela: contatos_da_tela,
  };

  // 3. ENVIANDO PARA O SERVIDOR
  try {
    const resposta = await fetch("/iniciar_cadastro_novo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pacoteDeDados),
    });

    const resultado = await resposta.json();

    if (resultado.status === "Sucesso") {
      logConsole("✅ " + resultado.msg, "ok");
    } else {
      logConsole("❌ Erro no robô: " + resultado.msg, "error");
    }
  } catch (error) {
    logConsole("❌ Erro de conexão com o servidor.", "error");
  } finally {
    btn.innerHTML =
      '<i class="fa-solid fa-play me-2"></i> Iniciar Cadastro NOVO';
    btn.disabled = false;
  }
}

// ==========================================
// NOVAS FUNÇÕES: GERAÇÃO DE LINK MÁGICO
// ==========================================

function gerarLinkCliente() {
  const vendedor = document.getElementById("linkVendedor").value;
  const representante = document.getElementById("linkRepresentante").value;
  const captacao = document.getElementById("linkCaptacao").value;
  const tipo = document.getElementById("linkTipoCadastro").value;

  // Validação simples
  if (!vendedor || !representante || !captacao || !tipo) {
    alert("Preencha todos os campos antes de gerar o link!");
    return;
  }

  // Monta a URL (Vamos usar uma rota /ficha_cliente que criaremos depois no Flask)
  // O encodeURIComponent garante que espaços virem %20 (seguro para links)
  const baseUrl = window.location.origin + "/ficha_cliente";
  const urlCompleta = `${baseUrl}?vendedor=${encodeURIComponent(vendedor)}&rep=${encodeURIComponent(representante)}&cap=${encodeURIComponent(captacao)}&tipo=${encodeURIComponent(tipo)}`;

  // Mostra o link na tela
  document.getElementById("urlMágica").value = urlCompleta;
  document.getElementById("areaLinkGerado").style.display = "block";

  logConsole(`Link de captação gerado para o Vendedor: ${vendedor}`, "ok");
}

function copiarLinkMagico() {
  const inputLink = document.getElementById("urlMágica");
  navigator.clipboard.writeText(inputLink.value).then(() => {
    alert("Link copiado com sucesso! Pode colar no WhatsApp.");
  });
}

function abrirFormularioInterno() {
  const vendedor = document.getElementById("linkVendedor").value;
  const representante = document.getElementById("linkRepresentante").value;
  const captacao = document.getElementById("linkCaptacao").value;
  const tipo = document.getElementById("linkTipoCadastro").value;

  if (!vendedor || !representante || !captacao || !tipo) {
    alert("Preencha todos os campos antes de gerar o link!");
    return;
  }

  alert(
    "Aqui nós vamos expandir o formulário de Cadastro Web (Em construção na Fase 2!)",
  );
  // O que faremos aqui nas próximas etapas: Ocultar este card e mostrar o card do formulário limpo.
}
