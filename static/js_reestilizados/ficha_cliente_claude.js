// ══════════════════════════════════════════════════════════════════════════════
// VARIÁVEIS GLOBAIS DE CONTROLE (modo correção)
// ══════════════════════════════════════════════════════════════════════════════

// Guarda o UUID da submissão original quando estamos em modo correção
window._correcaoUuid = null;

// Guarda a lista de documentos que estavam na submissão original
// Usada para calcular: já existentes, substituídos e adicionados
window._docsEnviadosOriginais = [];

document.addEventListener("DOMContentLoaded", async () => {
  // ──────────────────────────────────────────────────────────────────────────
  // 1. LER PARÂMETROS DA URL
  // ──────────────────────────────────────────────────────────────────────────
  const params = new URLSearchParams(window.location.search);
  const vendedor = params.get("vendedor");
  const representante = params.get("rep");
  const captacao = params.get("cap");
  const tipo = params.get("tipo");
  const codigoNl = params.get("codigo_nl"); // presente só quando tipo=REATIVACAO
  const correcaoUuid = params.get("correcao"); // presente só em modo correção

  // ──────────────────────────────────────────────────────────────────────────
  // 2. PREENCHER CAMPOS OCULTOS (rastreadores do vendedor)
  // ──────────────────────────────────────────────────────────────────────────
  if (tipo) document.getElementById("hdnTipoCadastro").value = tipo;
  if (vendedor) document.getElementById("hdnVendedor").value = vendedor;
  if (representante)
    document.getElementById("hdnRepresentante").value = representante;
  if (captacao) document.getElementById("hdnCaptacao").value = captacao;
  if (codigoNl) document.getElementById("hdnCodigoNl").value = codigoNl;

  // ──────────────────────────────────────────────────────────────────────────
  // 3. MÁSCARA DO CNPJ
  // ──────────────────────────────────────────────────────────────────────────
  const inputCnpj = document.getElementById("cliCnpj");

  inputCnpj.addEventListener("input", (e) => {
    let v = e.target.value.replace(/\D/g, "");
    v = v.replace(/^(\d{2})(\d)/, "$1.$2");
    v = v.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
    v = v.replace(/\.(\d{3})(\d)/, ".$1/$2");
    v = v.replace(/(\d{4})(\d)/, "$1-$2");
    e.target.value = v.substring(0, 18);
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 4. MÁSCARA DE TELEFONES
  // ──────────────────────────────────────────────────────────────────────────
  const idsTelefone = [
    "cliTelefone",
    "cliWhatsapp",
    "ctoComprasTel",
    "ctoRecTel",
    "ctoFinTel",
    "ctoFarmaTel",
  ];

  idsTelefone.forEach((id) => {
    const campo = document.getElementById(id);
    if (!campo) return;
    campo.addEventListener("input", (e) => {
      let v = e.target.value.replace(/\D/g, "").substring(0, 11);
      if (v.length > 2) {
        v = v.replace(/^(\d{2})(\d)/g, "($1) $2");
        v = v.replace(/(\d)(\d{4})$/, "$1-$2");
      }
      e.target.value = v;
    });
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 5. BUSCA AUTOMÁTICA DE CNPJ NA RECEITA FEDERAL
  //    A flag window._prefilling suprime esta busca durante o pré-preenchimento
  // ──────────────────────────────────────────────────────────────────────────
  inputCnpj.addEventListener("blur", async () => {
    if (window._prefilling) return;

    const cnpjLimpo = inputCnpj.value.replace(/\D/g, "");
    if (cnpjLimpo.length !== 14) return;

    document.getElementById("cliRazao").value =
      "Buscando na Receita Federal...";
    document.getElementById("cliEndereco").value = "Aguarde...";

    try {
      const res = await fetch(`/api/cnpj_completo/${cnpjLimpo}`);
      const dados = await res.json();

      if (!dados.erro) {
        const estab = dados.estabelecimento || {};
        const tipoLog = estab.tipo_logradouro || "";
        const log = estab.logradouro || "";
        const num = estab.numero || "S/N";
        const comp = estab.complemento ? ` - ${estab.complemento}` : "";
        const bairro = estab.bairro ? ` - ${estab.bairro}` : "";
        const cid = estab.cidade?.nome || "";
        const uf = estab.estado?.sigla || "";

        document.getElementById("cliEndereco").value =
          `${tipoLog} ${log}, ${num}${comp}${bairro} - ${cid} / ${uf}`;
        document.getElementById("cliRazao").value =
          dados.razao_social || "Razão não encontrada";

        if (document.getElementById("cliFantasia"))
          document.getElementById("cliFantasia").value =
            estab.nome_fantasia || dados.razao_social || "Não possui";

        let dataFormatada = estab.data_inicio_atividade || "";
        if (dataFormatada.includes("-")) {
          const p = dataFormatada.split("-");
          dataFormatada = `${p[2]}/${p[1]}/${p[0]}`;
        }
        if (document.getElementById("cliAbertura"))
          document.getElementById("cliAbertura").value = dataFormatada || "N/A";

        const sit = estab.situacao_cadastral || "Desconhecida";
        const inputSit = document.getElementById("cliSituacao");
        if (inputSit) {
          inputSit.value = sit;
          if (sit.toUpperCase() !== "ATIVA") {
            inputSit.style.color = "#e74c3c";
            inputSit.style.borderColor = "rgba(231, 76, 60, 0.3)";
          }
        }

        const cnaeId = estab.atividade_principal?.id || "";
        const cnaeDesc = estab.atividade_principal?.descricao || "";
        if (document.getElementById("cliCnae"))
          document.getElementById("cliCnae").value = cnaeId
            ? `${cnaeId} - ${cnaeDesc}`
            : "Não informado";
      } else {
        alert("CNPJ não encontrado! Verifique os números.");
        document.getElementById("cliRazao").value = "";
        document.getElementById("cliEndereco").value = "";
      }
    } catch {
      alert("Erro ao buscar CNPJ. A Receita Federal pode estar instável.");
    }
  });

  // ──────────────────────────────────────────────────────────────────────────
  // 6. LÓGICA CONDICIONAL: ICMS E REGIME ESPECIAL
  // ──────────────────────────────────────────────────────────────────────────
  const wrapperPerguntaRegime = document.getElementById(
    "wrapperRegimeEspecial",
  );
  const wrapperUploadRegime = document.getElementById("wrapperUploadRegime");
  const inputUploadRegime = document.getElementById("docRegimeEspecial");
  const radiosIcms = document.querySelectorAll('input[name="cliIcms"]');
  const radiosRegime = document.querySelectorAll(
    'input[name="cliRegimeEspecial"]',
  );

  function gerenciarPerguntaRegime(e) {
    if (e.target.value === "Sim") {
      wrapperPerguntaRegime.style.display = "flex";
    } else {
      wrapperPerguntaRegime.style.display = "none";
      wrapperUploadRegime.style.display = "none";
      inputUploadRegime.required = false;
      inputUploadRegime.value = "";
      radiosRegime.forEach((r) => (r.checked = false));
    }
  }

  function gerenciarUploadRegime(e) {
    if (e.target.value === "Sim") {
      wrapperUploadRegime.style.display = "block";
      inputUploadRegime.required = true;
    } else {
      wrapperUploadRegime.style.display = "none";
      inputUploadRegime.required = false;
      inputUploadRegime.value = "";
    }
  }

  radiosIcms.forEach((r) =>
    r.addEventListener("change", gerenciarPerguntaRegime),
  );
  radiosRegime.forEach((r) =>
    r.addEventListener("change", gerenciarUploadRegime),
  );

  // ──────────────────────────────────────────────────────────────────────────
  // 7. PRÉ-PREENCHIMENTO (MODO CORREÇÃO)
  //    Só executa se a URL tiver ?correcao=UUID
  // ──────────────────────────────────────────────────────────────────────────
  if (correcaoUuid) {
    await preencherModoCorrecao(correcaoUuid);
  }
});

// ══════════════════════════════════════════════════════════════════════════════
// FUNÇÃO: PRÉ-PREENCHIMENTO DO MODO CORREÇÃO
// Busca os dados salvos no SQLite via Flask e preenche toda a ficha
// ══════════════════════════════════════════════════════════════════════════════

async function preencherModoCorrecao(uuid) {
  try {
    const res = await fetch(`/api/ficha/${uuid}`);
    if (!res.ok) {
      console.error("UUID não encontrado:", uuid);
      return;
    }

    const sub = await res.json();
    const d = sub.dados;

    // Salva nas globais para uso no momento do envio
    window._correcaoUuid = uuid;
    window._docsEnviadosOriginais = sub.docs_enviados || [];

    // Ativa flag para suprimir a busca automática de CNPJ durante o preenchimento
    window._prefilling = true;

    // ── Campos de texto ────────────────────────────────────────────────────
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el && val !== undefined && val !== null) el.value = val;
    };

    // Em correção, o codigo_nl vem do SQLite e precisa voltar pro hidden
    // (senão o fluxo de reativação perde a referência do cliente).
    if (d.codigo_nl) document.getElementById("hdnCodigoNl").value = d.codigo_nl;

    set("cliCnpj", d.cnpj);
    set("cliRazao", d.razao_social);
    set("cliEndereco", d.endereco);
    set("cliTelefone", d.telefone_empresa);
    set("cliWhatsapp", d.whatsapp);
    set("cliEmailXml", d.email_xml_1);
    set("cliEmailXml2", d.email_xml_2);
    set("cliEmailXml3", d.email_xml_3);
    set("ctoComprasNome", d.compras_nome);
    set("ctoComprasTel", d.compras_tel);
    set("ctoComprasEmail", d.compras_email);
    set("ctoRecNome", d.rec_nome);
    set("ctoRecTel", d.rec_tel);
    set("ctoRecEmail", d.rec_email);
    set("ctoFinNome", d.fin_nome);
    set("ctoFinTel", d.fin_tel);
    set("ctoFinEmail", d.fin_email);
    set("ctoFarmaNome", d.farma_nome);
    set("ctoFarmaTel", d.farma_tel);
    set("ctoFarmaEmail", d.farma_email);

    // ── Radio buttons ──────────────────────────────────────────────────────
    // Disparamos o evento 'change' para acionar a lógica condicional (ICMS, Regime)
    const selecionarRadio = (name, valor) => {
      const radio = document.querySelector(
        `input[name="${name}"][value="${valor}"]`,
      );
      if (radio) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change", { bubbles: true }));
      }
    };

    selecionarRadio("cliIcms", d.contribuinte_icms);
    selecionarRadio("cliRegimeEspecial", d.possui_regime_especial);
    selecionarRadio("cliRegraFat", d.regra_faturamento);

    // Desativa flag de pré-preenchimento
    window._prefilling = false;

    // ── Badges visuais nos documentos já enviados ──────────────────────────
    // Para cada doc que existia na tentativa anterior, mostra um aviso verde
    const mapaDocWrap = {
      doc_regime_especial: "wrapDocRegime",
      doc_alvara: "wrapAlvara",
      doc_crt: "wrapCRT",
      doc_afe: "wrapAFE",
      doc_balanco: "wrapBalanco",
      doc_balancete: "wrapBalancete",
      doc_contrato: "wrapContrato",
    };

    window._docsEnviadosOriginais.forEach((docNome) => {
      const wrapId = mapaDocWrap[docNome];
      if (!wrapId) return;
      const wrapper = document.getElementById(wrapId);
      if (!wrapper) return;

      const badge = document.createElement("div");
      badge.style.cssText = `
        font-size: 12px;
        color: #34d399;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
      `;
      badge.innerHTML = `
        <i class="fa-solid fa-circle-check"></i>
        Enviado anteriormente — envie um novo arquivo para substituir
      `;
      wrapper.parentElement.appendChild(badge);
    });

    // ── Banner de aviso de correção no topo da ficha ───────────────────────
    const proximaTentativa = sub.tentativa + 1;
    const motivosAntigos = sub.motivos_reprovacao || [];

    const motivosHtml =
      motivosAntigos.length > 0
        ? motivosAntigos
            .map(
              (m) => `
          <div style="margin-top:8px; padding:10px 14px;
               background:rgba(248,113,113,0.08); border-radius:8px;
               border-left:3px solid #f87171;">
            <span style="font-size:11px; color:#7a8ba3;">
              ${m.data} — ${m.tentativa}ª tentativa
            </span><br>
            <span style="font-size:13px; color:#f87171;">❌ ${m.motivo}</span>
          </div>`,
            )
            .join("")
        : "";

    const banner = document.createElement("div");
    banner.style.cssText = `
      background: rgba(248,113,113,0.08);
      border: 1px solid rgba(248,113,113,0.25);
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 20px;
      display: flex;
      align-items: flex-start;
      gap: 14px;
    `;
    banner.innerHTML = `
      <i class="fa-solid fa-triangle-exclamation"
         style="color:#f87171; font-size:18px; margin-top:2px; flex-shrink:0;"></i>
      <div style="flex:1;">
        <div style="font-family:'Syne',sans-serif; font-size:15px;
                    font-weight:700; color:#f87171; margin-bottom:4px;">
          Ficha em Correção — ${proximaTentativa}ª tentativa
        </div>
        <div style="font-size:13px; color:#7a8ba3; line-height:1.5;">
          Esta ficha foi reprovada. Corrija o que for necessário e reenvie para análise.
        </div>
        ${motivosHtml}
      </div>
    `;

    const primeiroCard = document.querySelector(".card-dark");
    if (primeiroCard)
      primeiroCard.parentNode.insertBefore(banner, primeiroCard);
  } catch (err) {
    console.error("Erro ao pré-preencher modo correção:", err);
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// FEEDBACK VISUAL DOS UPLOADS
// ══════════════════════════════════════════════════════════════════════════════

function marcarDoc(input, wrapId) {
  const wrapper = document.getElementById(wrapId);
  const labelSpan = wrapper.querySelector("span");
  const icon = wrapper.querySelector("i");

  if (input.files && input.files.length > 0) {
    const nome = input.files[0].name;
    wrapper.classList.add("has-file");
    labelSpan.textContent =
      nome.length > 25 ? nome.substring(0, 22) + "..." : nome;
    icon.classList.remove("fa-cloud-arrow-up");
    icon.classList.add("fa-circle-check");
  } else {
    wrapper.classList.remove("has-file");
    labelSpan.textContent = "Clique ou arraste";
    icon.classList.remove("fa-circle-check");
    icon.classList.add("fa-cloud-arrow-up");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// DISPENSA DE DOCUMENTO ("Não possuo no momento")
// ══════════════════════════════════════════════════════════════════════════════

function dispensarDoc(inputId, wrapId, checkbox) {
  const input = document.getElementById(inputId);
  const wrapper = document.getElementById(wrapId);
  const labelSpan = wrapper.querySelector("span");
  const icon = wrapper.querySelector("i");
  const reqStar = wrapper.parentElement.querySelector(".doc-label span");

  if (checkbox.checked) {
    input.required = false;
    input.value = "";
    wrapper.classList.add("disabled");
    wrapper.classList.remove("has-file");
    labelSpan.textContent = "Envio dispensado";
    icon.className = "fa-solid fa-ban";
    if (reqStar) reqStar.style.display = "none";
  } else {
    input.required = true;
    wrapper.classList.remove("disabled");
    labelSpan.textContent = "Clique ou arraste";
    icon.className = "fa-solid fa-cloud-arrow-up";
    if (reqStar) reqStar.style.display = "inline";
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// ENVIO DA FICHA → Flask /receber_ficha
//
// MUDANÇA PRINCIPAL em relação à versão anterior:
//   O JS não envia mais direto pro N8N!
//   Agora envia para o Flask, que:
//     1. Salva os dados e arquivos localmente
//     2. Compara documentos (novo x original) se for correção
//     3. Repassa tudo pro N8N via JSON com os metadados da comparação
// ══════════════════════════════════════════════════════════════════════════════

async function enviarParaN8N() {
  const form = document.getElementById("formClienteFinal");

  // Validação nativa do HTML5
  if (!form.reportValidity()) return;

  const btn = document.querySelector(".btn-submit");
  const textoOriginal = btn.innerHTML;

  // Garante que veio de link com vendedor
  const vendedor = document.getElementById("hdnVendedor").value;
  if (!vendedor) {
    alert(
      "❌ Erro: este link não possui Vendedor associado. Solicite um novo link.",
    );
    return;
  }

  // Valida lógica do Regime Especial de ICMS
  const icmsSelecionado = document.querySelector(
    'input[name="cliIcms"]:checked',
  );
  if (icmsSelecionado.value === "Sim") {
    const regimeSelecionado = document.querySelector(
      'input[name="cliRegimeEspecial"]:checked',
    );
    if (!regimeSelecionado) {
      alert("⚠️ Informe se possui Regime Especial de ICMS (Sim ou Não).");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
  }

  // ── Monta o FormData ─────────────────────────────────────────────────────
  const formData = new FormData();
  // Rastreadores
  formData.append("vendedor", vendedor);
  formData.append(
    "representante",
    document.getElementById("hdnRepresentante").value,
  );
  formData.append("captacao", document.getElementById("hdnCaptacao").value);
  formData.append(
    "tipo_cadastro",
    document.getElementById("hdnTipoCadastro").value,
  );
  formData.append("codigo_nl", document.getElementById("hdnCodigoNl").value);

  // Regras comerciais
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

  // Dados fiscais
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

  // ── Documentos ───────────────────────────────────────────────────────────
  // Lógica dos três estados:
  //   → Novo arquivo selecionado: envia o arquivo no FormData
  //   → Sem arquivo novo + existia antes: adiciona em docs_manter
  //   → Sem arquivo + nunca existiu: ignorado
  const listaDocumentos = [
    { id: "docRegimeEspecial", nome: "doc_regime_especial" },
    { id: "docAlvara", nome: "doc_alvara" },
    { id: "docCRT", nome: "doc_crt" },
    { id: "docAFE", nome: "doc_afe" },
    { id: "docBalanco", nome: "doc_balanco" },
    { id: "docBalancete", nome: "doc_balancete" },
    { id: "docContrato", nome: "doc_contrato" },
  ];

  const docs_manter = [];

  listaDocumentos.forEach((doc) => {
    const inputEl = document.getElementById(doc.id);
    if (inputEl && inputEl.files && inputEl.files.length > 0) {
      formData.append(doc.nome, inputEl.files[0]);
    } else if (window._docsEnviadosOriginais.includes(doc.nome)) {
      docs_manter.push(doc.nome);
    }
  });

  formData.append("docs_manter", JSON.stringify(docs_manter));

  // UUID da correção — vazio na 1ª submissão, preenchido nas correções
  if (window._correcaoUuid) {
    formData.append("uuid", window._correcaoUuid);
  }

  // ── Disparo para o Flask ──────────────────────────────────────────────────
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Enviando...';
  btn.disabled = true;

  try {
    const resposta = await fetch("/receber_ficha", {
      method: "POST",
      body: formData,
    });

    if (resposta.ok) {
      const dados = await resposta.json();
      if (dados.status === "ok") {
        alert(
          "✅ Ficha enviada com sucesso! Nossa equipe já recebeu e irá analisar.",
        );
        window.location.reload();
      } else {
        alert("❌ Erro: " + (dados.mensagem || "Tente novamente."));
      }
    } else {
      alert("❌ Erro no servidor. Tente novamente ou contate seu vendedor.");
    }
  } catch (error) {
    alert("❌ Erro de conexão. Verifique sua internet.");
    console.error(error);
  } finally {
    btn.innerHTML = textoOriginal;
    btn.disabled = false;
  }
}
