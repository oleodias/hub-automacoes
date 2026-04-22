// ════════════════════════════════════════════════════════════════════
// MÓDULO: CADASTRO E REATIVAÇÃO DE CLIENTES — Geração de Link
// ════════════════════════════════════════════════════════════════════
// Este módulo cuida APENAS da parte de "Rastreio e Geração de Link".
// Não faz mais upload de Excel, não chama robô direto, não tem terminal.
// O fluxo agora é 100% via link → ficha digital → n8n → robô.
// ════════════════════════════════════════════════════════════════════

// ────────────────────────────────────────────────────────────────────
// LÓGICA CONDICIONAL DO CAMPO "CÓDIGO NL"
// Quando o vendedor seleciona "Reativação" no select de tipo,
// o container do código NL aparece e o campo vira obrigatório.
// Quando desmarca (volta pra "Novo" ou limpa), o container some
// e o campo é limpo — pra não ficar lixo antigo no payload.
// ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const selectTipo = document.getElementById("linkTipoCadastro");
  const containerCodigoNl = document.getElementById("container-codigo-nl");
  const inputCodigoNl = document.getElementById("linkCodigoNl");

  if (!selectTipo || !containerCodigoNl || !inputCodigoNl) {
    console.warn("Elementos do formulário de link não encontrados.");
    return;
  }

  // Handler único que reage a mudanças no select de tipo
  selectTipo.addEventListener("change", () => {
    if (selectTipo.value === "REATIVACAO") {
      // Aparece com animação suave (pra não dar "soco visual")
      containerCodigoNl.style.display = "block";
      containerCodigoNl.style.opacity = "0";
      containerCodigoNl.style.transform = "translateY(-4px)";
      requestAnimationFrame(() => {
        containerCodigoNl.style.transition =
          "opacity 0.25s ease, transform 0.25s ease";
        containerCodigoNl.style.opacity = "1";
        containerCodigoNl.style.transform = "translateY(0)";
      });
      // Foca pra agilizar o preenchimento
      setTimeout(() => inputCodigoNl.focus(), 280);
    } else {
      // Some e limpa o valor — importante pra não propagar lixo
      containerCodigoNl.style.display = "none";
      inputCodigoNl.value = "";
    }
  });
});

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

  // ── Validação básica (campos sempre obrigatórios) ──
  if (!vendedor || !representante || !captacao || !tipo) {
    alert("⚠️ Preencha todos os campos antes de gerar o link!");
    return;
  }

  // ── Validação condicional do código NL ──
  // Só exige quando o tipo é REATIVACAO. O campo pode nem existir
  // visualmente (está escondido) se o tipo for NOVO, então não dá
  // pra usar `required` nativo do HTML — validação manual mesmo.
  if (tipo === "REATIVACAO" && !codigoNl) {
    alert(
      "⚠️ Para reativações, é obrigatório informar o Código NL do cliente!",
    );
    document.getElementById("linkCodigoNl").focus();
    return;
  }

  // ── Validação extra: código NL deve ser numérico ──
  // Se o vendedor digitar letra ou símbolo, avisa antes de gerar o link
  // (o ERP só aceita códigos numéricos no campo lovPsPessoas_txtCod)
  if (tipo === "REATIVACAO" && !/^\d+$/.test(codigoNl)) {
    alert("⚠️ O Código NL deve conter apenas números.");
    document.getElementById("linkCodigoNl").focus();
    return;
  }

  // ── Monta a URL ──
  // Usa a mesma rota /ficha_cliente que já existe, só adicionando
  // o parâmetro codigo_nl quando for reativação. Pra cadastro novo,
  // o parâmetro não vai pra URL — fica mais limpo.
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

  // Scroll suave pra mostrar o link gerado (especialmente útil em telas pequenas)
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
  navigator.clipboard.writeText(inputLink.value).then(() => {
    alert("✅ Link copiado com sucesso! Pode colar no WhatsApp.");
  });
}
