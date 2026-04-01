document.addEventListener("DOMContentLoaded", () => {
  // 1. LER A URL MÁGICA
  const parametrosDaUrl = new URLSearchParams(window.location.search);

  // 2. SALVAR OS DADOS NOS CAMPOS OCULTOS
  const vendedor = parametrosDaUrl.get("vendedor");
  const representante = parametrosDaUrl.get("rep");
  const captacao = parametrosDaUrl.get("cap");

  if (vendedor) document.getElementById("hdnVendedor").value = vendedor;
  if (representante)
    document.getElementById("hdnRepresentante").value = representante;
  if (captacao) document.getElementById("hdnCaptacao").value = captacao;

  // 3. BUSCAR O CNPJ AUTOMATICAMENTE NA SUA API
  const inputCnpj = document.getElementById("cliCnpj");

  // 👇 MÁSCARA AUTOMÁTICA: Formata o CNPJ enquanto o usuário digita 👇
  inputCnpj.addEventListener("input", (e) => {
    let valor = e.target.value.replace(/\D/g, ""); // Remove tudo o que não for número

    // Aplica a formatação: 00.000.000/0000-00
    valor = valor.replace(/^(\d{2})(\d)/, "$1.$2");
    valor = valor.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
    valor = valor.replace(/\.(\d{3})(\d)/, ".$1/$2");
    valor = valor.replace(/(\d{4})(\d)/, "$1-$2");

    // Limita a quantidade máxima de caracteres (14 números + 4 pontuações = 18)
    e.target.value = valor.substring(0, 18);
  });
  // 👆 FIM DA MÁSCARA 👆

  // 👇 MÁSCARA AUTOMÁTICA PARA TODOS OS TELEFONES 👇
  const inputsTelefone = [
    "cliTelefone",
    "cliWhatsapp",
    "ctoComprasTel",
    "ctoRecTel",
    "ctoFinTel",
    "ctoFarmaTel",
  ];

  inputsTelefone.forEach((id) => {
    const campo = document.getElementById(id);
    if (campo) {
      campo.addEventListener("input", (e) => {
        let v = e.target.value.replace(/\D/g, ""); // Remove tudo que não for número
        v = v.substring(0, 11); // Limita a 11 números (DDD + 9 dígitos)

        // Aplica a formatação: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
        if (v.length > 2) {
          v = v.replace(/^(\d{2})(\d)/g, "($1) $2");
          v = v.replace(/(\d)(\d{4})$/, "$1-$2");
        }
        e.target.value = v;
      });
    }
  });
  // 👆 FIM DA MÁSCARA DE TELEFONES 👆

  inputCnpj.addEventListener("blur", async () => {
    const cnpjLimpo = inputCnpj.value.replace(/\D/g, "");

    if (cnpjLimpo.length === 14) {
      document.getElementById("cliRazao").value =
        "Buscando na Receita Federal...";
      document.getElementById("cliEndereco").value = "Aguarde...";

      try {
        const resposta = await fetch(`/api/cnpj_completo/${cnpjLimpo}`);
        const dados = await resposta.json();

        if (!dados.erro) {
          const estab = dados.estabelecimento || {};

          // ==========================================
          // 1. MONTAR O ENDEREÇO COMPLETÍSSIMO
          // ==========================================
          const tipoLog = estab.tipo_logradouro || "";
          const log = estab.logradouro || "";
          const num = estab.numero || "S/N";
          const comp = estab.complemento ? ` - ${estab.complemento}` : "";
          const bairro = estab.bairro ? ` - ${estab.bairro}` : "";
          const cid = estab.cidade?.nome || "";
          const uf = estab.estado?.sigla || "";

          // Junta tudo: Rua X, 123 - Sala 2 - Bairro - Cidade/UF
          const enderecoCompleto = `${tipoLog} ${log}, ${num}${comp}${bairro} - ${cid} / ${uf}`;
          document.getElementById("cliEndereco").value = enderecoCompleto;

          // ==========================================
          // 2. PREENCHER OS DEMAIS CAMPOS DA API
          // ==========================================
          document.getElementById("cliRazao").value =
            dados.razao_social || "Razão não encontrada";

          if (document.getElementById("cliFantasia")) {
            document.getElementById("cliFantasia").value =
              estab.nome_fantasia || dados.razao_social || "Não possui";
          }

          // Formatar Data de Abertura (Muda de YYYY-MM-DD para DD/MM/YYYY)
          let dataFormatada = estab.data_inicio_atividade || "";
          if (dataFormatada.includes("-")) {
            const partes = dataFormatada.split("-");
            dataFormatada = `${partes[2]}/${partes[1]}/${partes[0]}`;
          }
          if (document.getElementById("cliAbertura")) {
            document.getElementById("cliAbertura").value =
              dataFormatada || "N/A";
          }

          // Situação Cadastral (Com Alerta de Cor)
          const sit = estab.situacao_cadastral || "Desconhecida";
          const inputSit = document.getElementById("cliSituacao");
          if (inputSit) {
            inputSit.value = sit;
            if (sit.toUpperCase() === "ATIVA") {
            } else {
              inputSit.style.color = "#e74c3c"; // Vermelho perigo
              inputSit.style.borderColor = "rgba(231, 76, 60, 0.3)";
            }
          }

          // CNAE Principal
          const cnaeId = estab.atividade_principal?.id || "";
          const cnaeDesc = estab.atividade_principal?.descricao || "";
          if (document.getElementById("cliCnae")) {
            document.getElementById("cliCnae").value = cnaeId
              ? `${cnaeId} - ${cnaeDesc}`
              : "Não informado";
          }
        } else {
          alert("CNPJ não encontrado! Verifique os números.");
          document.getElementById("cliRazao").value = "";
          document.getElementById("cliEndereco").value = "";
        }
      } catch (e) {
        alert("Erro ao buscar CNPJ. A Receita Federal pode estar instável.");
      }
    }
  });

  // ==========================================
  // 👇 LÓGICA CONDICIONAL: ICMS E REGIME ESPECIAL 👇
  // ==========================================

  const wrapperPerguntaRegime = document.getElementById(
    "wrapperRegimeEspecial",
  );
  const wrapperUploadRegime = document.getElementById("wrapperUploadRegime");
  const inputUploadRegime = document.getElementById("docRegimeEspecial");

  const radiosIcms = document.querySelectorAll('input[name="cliIcms"]');
  const radiosRegime = document.querySelectorAll(
    'input[name="cliRegimeEspecial"]',
  );

  // 1. O que acontece quando clica em "Contribuinte do ICMS?"
  function gerenciarPerguntaRegime(e) {
    if (e.target.value === "Sim") {
      wrapperPerguntaRegime.style.display = "flex"; // Mostra a 2ª pergunta
    } else {
      wrapperPerguntaRegime.style.display = "none"; // Esconde a 2ª pergunta

      // Se não é contribuinte, também temos que esconder/limpar o anexo lá embaixo
      wrapperUploadRegime.style.display = "none";
      inputUploadRegime.required = false;
      inputUploadRegime.value = "";

      // Desmarca os botões de "Regime Especial" (já que a pergunta sumiu)
      radiosRegime.forEach((radio) => (radio.checked = false));
    }
  }

  // 2. O que acontece quando clica em "Regime Especial de ICMS?"
  function gerenciarUploadRegime(e) {
    if (e.target.value === "Sim") {
      wrapperUploadRegime.style.display = "block"; // Mostra a caixa de upload
      inputUploadRegime.required = true; // Torna o upload obrigatório
    } else {
      wrapperUploadRegime.style.display = "none"; // Esconde a caixa de upload
      inputUploadRegime.required = false; // Tira a obrigatoriedade
      inputUploadRegime.value = ""; // Limpa o arquivo se já tinha selecionado
    }
  }

  // Adiciona os "ouvintes" de clique aos botões
  radiosIcms.forEach((radio) =>
    radio.addEventListener("change", gerenciarPerguntaRegime),
  );

  radiosRegime.forEach((radio) =>
    radio.addEventListener("change", gerenciarUploadRegime),
  );
});

// ==========================================
// FUNÇÃO DE FEEDBACK VISUAL DOS UPLOADS
// ==========================================
function marcarDoc(input, wrapId) {
  const wrapper = document.getElementById(wrapId);
  const labelSpan = wrapper.querySelector("span");
  const icon = wrapper.querySelector("i");

  if (input.files && input.files.length > 0) {
    // Arquivo selecionado com sucesso!
    const nomeArquivo = input.files[0].name;

    // Adiciona a classe que deixa a borda verde
    wrapper.classList.add("has-file");

    // Troca o texto para o nome do arquivo (cortando se for muito grande)
    labelSpan.textContent =
      nomeArquivo.length > 25
        ? nomeArquivo.substring(0, 22) + "..."
        : nomeArquivo;

    // Troca o ícone da nuvem por um ícone de "check"
    icon.classList.remove("fa-cloud-arrow-up");
    icon.classList.add("fa-circle-check");
  } else {
    // O usuário abriu a janela mas cancelou sem escolher nada
    wrapper.classList.remove("has-file");
    labelSpan.textContent = "Clique ou arraste";

    icon.classList.remove("fa-circle-check");
    icon.classList.add("fa-cloud-arrow-up");
  }
}

// ==========================================
// FUNÇÃO DE DISPENSA DE DOCUMENTO (BYPASS)
// ==========================================
function dispensarDoc(inputId, wrapId, checkbox) {
  const input = document.getElementById(inputId);
  const wrapper = document.getElementById(wrapId);
  const labelSpan = wrapper.querySelector("span");
  const icon = wrapper.querySelector("i");

  // Pega a estrelinha vermelha do título (para esconder)
  const reqStar = wrapper.parentElement.querySelector(".doc-label span");

  if (checkbox.checked) {
    // 1. Tira a obrigatoriedade
    input.required = false;
    input.value = ""; // Limpa se o cara já tinha subido um arquivo

    // 2. Muda o visual da caixa
    wrapper.classList.add("disabled");
    wrapper.classList.remove("has-file");
    labelSpan.textContent = "Envio dispensado";
    icon.className = "fa-solid fa-ban";

    // 3. Esconde o asterisco vermelho
    if (reqStar) reqStar.style.display = "none";
  } else {
    // 1. Volta a ser obrigatório
    input.required = true;

    // 2. Volta o visual ao normal
    wrapper.classList.remove("disabled");
    labelSpan.textContent = "Clique ou arraste";
    icon.className = "fa-solid fa-cloud-arrow-up";

    // 3. Mostra o asterisco vermelho de volta
    if (reqStar) reqStar.style.display = "inline";
  }
}

// ==========================================
// 4. FUNÇÃO DO BOTÃO ENVIAR (FASE 3 - N8N)
// ==========================================
async function enviarParaN8N() {
  const form = document.getElementById("formClienteFinal");

  // A MÁGICA DA VALIDAÇÃO NATIVA:
  // Se faltar algum campo "required" (texto, radio ou arquivo), ele avisa o usuário e para tudo!
  if (!form.reportValidity()) {
    return;
  }

  const btn = document.querySelector(".btn-submit");
  const textoOriginal = btn.innerHTML;

  // Verificação extra de segurança (Garante que veio do link do vendedor)
  const vendedor = document.getElementById("hdnVendedor").value;
  if (!vendedor) {
    alert(
      "❌ Erro de segurança: Este link não possui um Vendedor associado na URL. Solicite um novo link.",
    );
    return;
  }

  // Verificação da Lógica do Regime Especial
  const icmsSelecionado = document.querySelector(
    'input[name="cliIcms"]:checked',
  );
  if (icmsSelecionado.value === "Sim") {
    const regimeSelecionado = document.querySelector(
      'input[name="cliRegimeEspecial"]:checked',
    );
    if (!regimeSelecionado) {
      alert(
        "⚠️ Por favor, informe se possui Regime Especial de ICMS (Sim ou Não).",
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
  }

  // Empacotando tudo
  const formData = new FormData();

  // Rastreadores
  formData.append("vendedor", vendedor);
  formData.append(
    "representante",
    document.getElementById("hdnRepresentante").value,
  );
  formData.append("captacao", document.getElementById("hdnCaptacao").value);

  // Regras Comerciais
  formData.append("contribuinte_icms", icmsSelecionado.value);
  const regimeCheck = document.querySelector(
    'input[name="cliRegimeEspecial"]:checked',
  );
  formData.append(
    "possui_regime_especial",
    regimeCheck ? regimeCheck.value : "Não se aplica",
  );
  formData.append(
    "regra_faturamento",
    document.querySelector('input[name="cliRegraFat"]:checked').value,
  );

  // Fiscais
  formData.append("cnpj", document.getElementById("cliCnpj").value);
  formData.append("razao_social", document.getElementById("cliRazao").value);
  formData.append("endereco", document.getElementById("cliEndereco").value);
  formData.append(
    "telefone_empresa",
    document.getElementById("cliTelefone").value,
  );
  formData.append("whatsapp", document.getElementById("cliWhatsapp").value);

  // E-mails XML
  formData.append("email_xml_1", document.getElementById("cliEmailXml").value);
  formData.append("email_xml_2", document.getElementById("cliEmailXml2").value);
  formData.append("email_xml_3", document.getElementById("cliEmailXml3").value);

  // Contatos
  formData.append(
    "compras_nome",
    document.getElementById("ctoComprasNome").value,
  );
  formData.append(
    "compras_tel",
    document.getElementById("ctoComprasTel").value,
  );
  formData.append(
    "compras_email",
    document.getElementById("ctoComprasEmail").value,
  );

  formData.append("rec_nome", document.getElementById("ctoRecNome").value);
  formData.append("rec_tel", document.getElementById("ctoRecTel").value);
  formData.append("rec_email", document.getElementById("ctoRecEmail").value);

  formData.append("fin_nome", document.getElementById("ctoFinNome").value);
  formData.append("fin_tel", document.getElementById("ctoFinTel").value);
  formData.append("fin_email", document.getElementById("ctoFinEmail").value);

  formData.append("farma_nome", document.getElementById("ctoFarmaNome").value);
  formData.append("farma_tel", document.getElementById("ctoFarmaTel").value);
  formData.append(
    "farma_email",
    document.getElementById("ctoFarmaEmail").value,
  );

  // Arquivos (Só anexa se o usuário realmente selecionou um arquivo)
  const listaDocumentos = [
    { id: "docRegimeEspecial", nome: "doc_regime_especial" },
    { id: "docAlvara", nome: "doc_alvara" },
    { id: "docCRT", nome: "doc_crt" },
    { id: "docAFE", nome: "doc_afe" },
    { id: "docBalanco", nome: "doc_balanco" },
    { id: "docBalancete", nome: "doc_balancete" },
    { id: "docContrato", nome: "doc_contrato" },
  ];

  listaDocumentos.forEach((doc) => {
    const inputElement = document.getElementById(doc.id);
    if (inputElement && inputElement.files[0]) {
      formData.append(doc.nome, inputElement.files[0]);
    }
  });

  // Disparo para o servidor (n8n)
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Enviando...';
  btn.disabled = true;

  try {
    // ⚠️ ATENÇÃO: COLOQUE AQUI A URL DE TESTE DO SEU WEBHOOK DO N8N ⚠️
    const urlWebhookN8N =
      "https://ciamedrs.app.n8n.cloud/webhook-test/receber-cadastro-leo";

    const resposta = await fetch(urlWebhookN8N, {
      method: "POST",
      body: formData,
    });

    if (resposta.ok) {
      alert(
        "✅ Cadastro enviado com sucesso! Nossa equipe já recebeu seus dados.",
      );
      window.location.reload();
    } else {
      alert(
        "❌ Ocorreu um erro no servidor. Tente novamente ou contate seu vendedor.",
      );
    }
  } catch (error) {
    alert("❌ Erro de conexão. Verifique sua internet.");
    console.error(error);
  } finally {
    btn.innerHTML = textoOriginal;
    btn.disabled = false;
  }
}
