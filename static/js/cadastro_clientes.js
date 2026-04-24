// ════════════════════════════════════════════════════════════════════
// MÓDULO: CADASTRO E REATIVAÇÃO DE CLIENTES — Geração de Link
// ════════════════════════════════════════════════════════════════════
// Funcionalidades:
//   1. Modal de seleção de Vendedor e Representante (com busca)
//   2. Campo condicional "Código NL" pra reativação
//   3. Geração do link mágico
// ════════════════════════════════════════════════════════════════════

// ────────────────────────────────────────────────────────────────────
// CACHE DAS LISTAS (carregadas uma vez do servidor)
// ────────────────────────────────────────────────────────────────────
let listaVendedores = [];
let listaRepresentantes = [];
let modalCampoAlvo = null; // qual input preencher quando o usuário selecionar

// ────────────────────────────────────────────────────────────────────
// INICIALIZAÇÃO
// ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // ── 1. Carregar listas de vendedores e representantes ──
  try {
    const [resV, resR] = await Promise.all([
      fetch("/static/data/vendedores.json"),
      fetch("/static/data/representantes.json"),
    ]);
    listaVendedores = await resV.json();
    listaRepresentantes = await resR.json();
    console.log(
      `✅ Listas carregadas: ${listaVendedores.length} vendedores, ${listaRepresentantes.length} representantes`,
    );
  } catch (e) {
    console.error("❌ Erro ao carregar listas:", e);
    alert(
      "Erro ao carregar listas de vendedores/representantes. Recarregue a página.",
    );
  }

  // ── 2. Configurar clique nos campos pra abrir o modal ──
  const campoVendedor = document.getElementById("linkVendedor");
  const campoRepresentante = document.getElementById("linkRepresentante");

  if (campoVendedor) {
    campoVendedor.addEventListener("click", () => {
      abrirModalSelecao("Selecionar Vendedor", listaVendedores, campoVendedor);
    });
  }

  if (campoRepresentante) {
    campoRepresentante.addEventListener("click", () => {
      abrirModalSelecao(
        "Selecionar Representante",
        listaRepresentantes,
        campoRepresentante,
      );
    });
  }

  // ── 3. Fechar modal ao clicar fora ──
  const overlay = document.getElementById("modalSelecao");
  if (overlay) {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) fecharModalSelecao();
    });
  }

  // ── 4. Fechar modal com ESC ──
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") fecharModalSelecao();
  });

  // ── 5. Busca em tempo real no modal ──
  const inputBusca = document.getElementById("modalSelecaoBusca");
  if (inputBusca) {
    inputBusca.addEventListener("input", () => {
      const filtro = inputBusca.value.trim().toLowerCase();
      filtrarListaModal(filtro);
    });
  }

  // ── 6. Lógica condicional do campo "Código NL" ──
  const selectTipo = document.getElementById("linkTipoCadastro");
  const containerCodigoNl = document.getElementById("container-codigo-nl");
  const inputCodigoNl = document.getElementById("linkCodigoNl");

  if (selectTipo && containerCodigoNl && inputCodigoNl) {
    selectTipo.addEventListener("change", () => {
      if (selectTipo.value === "REATIVACAO") {
        containerCodigoNl.style.display = "block";
        containerCodigoNl.style.opacity = "0";
        containerCodigoNl.style.transform = "translateY(-4px)";
        requestAnimationFrame(() => {
          containerCodigoNl.style.transition =
            "opacity 0.25s ease, transform 0.25s ease";
          containerCodigoNl.style.opacity = "1";
          containerCodigoNl.style.transform = "translateY(0)";
        });
        setTimeout(() => inputCodigoNl.focus(), 280);
      } else {
        containerCodigoNl.style.display = "none";
        inputCodigoNl.value = "";
      }
    });
  }
});

// ════════════════════════════════════════════════════════════════════
// MODAL DE SELEÇÃO
// ════════════════════════════════════════════════════════════════════

// Lista completa atualmente exibida no modal (sem filtro)
let listaAtualModal = [];

function abrirModalSelecao(titulo, lista, campoAlvo) {
  modalCampoAlvo = campoAlvo;
  listaAtualModal = lista;

  // Atualiza título
  document.getElementById("modalSelecaoTitulo").textContent = titulo;

  // Limpa busca
  const inputBusca = document.getElementById("modalSelecaoBusca");
  inputBusca.value = "";

  // Renderiza lista completa
  renderizarListaModal(lista);

  // Mostra overlay
  document.getElementById("modalSelecao").classList.add("ativo");

  // Foca na busca automaticamente
  setTimeout(() => inputBusca.focus(), 100);
}

function fecharModalSelecao() {
  document.getElementById("modalSelecao").classList.remove("ativo");
  modalCampoAlvo = null;
}

function selecionarItem(nome) {
  if (modalCampoAlvo) {
    modalCampoAlvo.value = nome;
  }
  fecharModalSelecao();
}

function renderizarListaModal(lista) {
  const container = document.getElementById("modalSelecaoLista");
  const contador = document.getElementById("modalSelecaoContador");

  if (!lista.length) {
    container.innerHTML =
      '<div class="modal-selecao-vazio"><i class="fa-solid fa-magnifying-glass" style="margin-right:6px"></i>Nenhum resultado encontrado</div>';
    contador.textContent = "0 resultado(s)";
    return;
  }

  container.innerHTML = lista
    .map(
      (nome) =>
        `<div class="modal-selecao-item" onclick="selecionarItem('${nome.replace(/'/g, "\\'")}')">${nome}</div>`,
    )
    .join("");

  contador.textContent = `${lista.length} resultado(s)`;
}

function filtrarListaModal(filtro) {
  if (!filtro) {
    renderizarListaModal(listaAtualModal);
    return;
  }

  // Busca inteligente: divide o filtro em palavras e exige que TODAS
  // estejam presentes no nome (não necessariamente na ordem).
  // Exemplo: "ciamed pr" encontra "CIAMED PR" e "CIAMED PRIVADO PR"
  const palavras = filtro.split(/\s+/);
  const filtrada = listaAtualModal.filter((nome) => {
    const nomeLower = nome.toLowerCase();
    return palavras.every((p) => nomeLower.includes(p));
  });

  renderizarListaModal(filtrada);
}

// ════════════════════════════════════════════════════════════════════
// GERAÇÃO DO LINK MÁGICO
// ════════════════════════════════════════════════════════════════════
function gerarLinkCliente() {
  const vendedor = document.getElementById("linkVendedor").value.trim();
  const representante = document
    .getElementById("linkRepresentante")
    .value.trim();
  const captacao = document.getElementById("linkCaptacao").value;
  const tipo = document.getElementById("linkTipoCadastro").value;
  const codigoNl = document.getElementById("linkCodigoNl").value.trim();

  // ── Validação básica ──
  if (!vendedor || !representante || !captacao || !tipo) {
    alert("⚠️ Preencha todos os campos antes de gerar o link!");
    return;
  }

  // ── Validação condicional do código NL ──
  if (tipo === "REATIVACAO" && !codigoNl) {
    alert(
      "⚠️ Para reativações, é obrigatório informar o Código NL do cliente!",
    );
    document.getElementById("linkCodigoNl").focus();
    return;
  }

  if (tipo === "REATIVACAO" && !/^\d+$/.test(codigoNl)) {
    alert("⚠️ O Código NL deve conter apenas números.");
    document.getElementById("linkCodigoNl").focus();
    return;
  }

  // ── Monta a URL ──
  const baseUrl = window.location.origin + "/ficha_cliente";
  let urlCompleta =
    `${baseUrl}?vendedor=${encodeURIComponent(vendedor)}` +
    `&rep=${encodeURIComponent(representante)}` +
    `&cap=${encodeURIComponent(captacao)}` +
    `&tipo=${encodeURIComponent(tipo)}`;

  if (tipo === "REATIVACAO") {
    urlCompleta += `&codigo_nl=${encodeURIComponent(codigoNl)}`;
  }

  // Mostra o link na tela
  document.getElementById("urlMágica").value = urlCompleta;
  document.getElementById("areaLinkGerado").style.display = "block";

  // Limpa a memória de sessão (link gerado, não precisa mais)
  window.sessionMemory.limpar();

  document.getElementById("areaLinkGerado").scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

// ════════════════════════════════════════════════════════════════════
// COPIAR LINK MÁGICO
// ════════════════════════════════════════════════════════════════════
function copiarLinkMagico() {
  const inputLink = document.getElementById("urlMágica");
  const texto = inputLink.value;

  // navigator.clipboard só funciona em HTTPS/localhost.
  // Como o Hub roda em HTTP (192.168.x.x), usamos o fallback
  // clássico com textarea invisível + execCommand.
  try {
    const textarea = document.createElement("textarea");
    textarea.value = texto;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);

    // Feedback visual no botão (troca texto por 2 segundos)
    const btn = event.currentTarget;
    const textoOriginal = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
    btn.style.background = "#34d399";
    setTimeout(() => {
      btn.innerHTML = textoOriginal;
      btn.style.background = "#0ee6b8";
    }, 2000);
  } catch (e) {
    // Último recurso: seleciona o texto pra o usuário copiar manualmente
    inputLink.select();
    alert("Selecione o link acima e copie com Ctrl+C");
  }
}
