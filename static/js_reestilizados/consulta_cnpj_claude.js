const dtEl = document.getElementById("printDateTime");
if (dtEl) dtEl.textContent = new Date().toLocaleString("pt-BR");

document
  .querySelectorAll('[data-bs-toggle="tooltip"]')
  .forEach((el) => new bootstrap.Tooltip(el));

// MÁSCARA CNPJ
document.getElementById("cnpjInput").addEventListener("input", function (e) {
  let v = e.target.value.replace(/\D/g, "");
  if (v.length > 14) v = v.slice(0, 14);
  v = v.replace(/^(\d{2})(\d)/, "$1.$2");
  v = v.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
  v = v.replace(/\.(\d{3})(\d)/, ".$1/$2");
  v = v.replace(/(\d{4})(\d)/, "$1-$2");
  e.target.value = v;
});
document.getElementById("cnpjInput").addEventListener("keydown", function (e) {
  if (e.key === "Enter") document.getElementById("btnConsultar").click();
});

// HELPERS
const fmt = (v) => v || "—";
const fmtCNPJ = (v) => {
  if (!v) return "—";
  v = v.replace(/\D/g, "");
  return v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
};
const fmtData = (d) => {
  if (!d) return "—";
  return d.includes("-") ? d.split("-").reverse().join("/") : d;
};
const fmtCEP = (c) => {
  if (!c) return "—";
  c = c.replace(/\D/g, "");
  return c.replace(/^(\d{5})(\d{3})/, "$1-$2");
};
const fmtTel = (ddd, num) => {
  if (!ddd && !num) return "—";
  return `(${ddd || ""}) ${num || ""}`;
};
const fmtCap = (v) => {
  if (!v) return "—";
  return (
    "R$ " + parseFloat(v).toLocaleString("pt-BR", { minimumFractionDigits: 2 })
  );
};
const fmtDT = (s) => {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("pt-BR");
  } catch (e) {
    return s;
  }
};
const initials = (n) => {
  if (!n) return "--";
  return n
    .trim()
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
};
const setEl = (id, v) => {
  const el = document.getElementById(id);
  if (el) el.textContent = v || "—";
};

// BUSCA
document.getElementById("btnConsultar").addEventListener("click", function () {
  const cnpj = document.getElementById("cnpjInput").value.replace(/\D/g, "");
  const btn = this;
  const dot = document.getElementById("dotStatus");
  const txt = document.getElementById("txtStatus");

  if (cnpj.length !== 14) {
    dot.className = "status-dot bg-red";
    txt.textContent = "CNPJ inválido. Digite 14 números.";
    return;
  }

  btn.innerHTML =
    '<span class="spinner-border spinner-border-sm me-1"></span> Consultando...';
  btn.disabled = true;
  dot.className = "status-dot bg-yellow";
  txt.textContent = "Consultando Receita Federal...";
  document.getElementById("resultado-wrap").classList.remove("visivel");

  fetch(`/api/cnpj_completo/${cnpj}`)
    .then((r) => r.json())
    .then((data) => {
      if (data.erro) throw new Error(data.message || "CNPJ não encontrado.");
      renderizar(data);
      dot.className = "status-dot bg-green";
      txt.textContent = "Dados carregados com sucesso!";
      document.getElementById("resultado-wrap").classList.add("visivel");
      window.scrollTo({
        top: document.getElementById("resultado-wrap").offsetTop - 80,
        behavior: "smooth",
      });
    })
    .catch((err) => {
      dot.className = "status-dot bg-red";
      txt.textContent = err.message;
    })
    .finally(() => {
      btn.innerHTML = '<i class="fa-solid fa-search me-1"></i> Consultar';
      btn.disabled = false;
    });
});

function renderizar(d) {
  const estab = d.estabelecimento || d;
  const simples = d.simples || estab.simples || null;

  // ── HERO ──
  const nome = d.razao_social || estab.razao_social || "—";
  document.getElementById("eAvatar").textContent = initials(nome);
  document.getElementById("eNome").textContent = nome;
  const fantasia = estab.nome_fantasia || d.nome_fantasia;
  document.getElementById("eFantasia").textContent = fantasia
    ? `"${fantasia}"`
    : "Sem nome fantasia";
  document.getElementById("eCnpj").textContent = fmtCNPJ(estab.cnpj || d.cnpj);

  const atualizado = d.atualizado_em || estab.atualizado_em;
  document.getElementById("eAtualizado").innerHTML =
    `<i class="fa-solid fa-clock-rotate-left"></i> Atualizado: ${fmtDT(atualizado)}`;

  // BADGES HERO
  const badgesEl = document.getElementById("eBadges");
  badgesEl.innerHTML = "";
  const sit = (
    estab.situacao_cadastral ||
    d.situacao_cadastral ||
    ""
  ).toUpperCase();
  const ativa = sit === "ATIVA";
  badgesEl.innerHTML += `<span class="badge-pill ${ativa ? "badge-ativa" : "badge-inativa"}">${sit || "—"}</span>`;
  const tipo = estab.tipo || d.descricao_identificador_matriz_filial || "";
  if (tipo.toUpperCase().includes("MATRIZ"))
    badgesEl.innerHTML += `<span class="badge-pill badge-matriz">MATRIZ</span>`;
  else if (tipo.toUpperCase().includes("FILIAL"))
    badgesEl.innerHTML += `<span class="badge-pill badge-filial">FILIAL</span>`;
  if (simples && simples.simples === "Sim")
    badgesEl.innerHTML += `<span class="badge-pill badge-simples">SIMPLES</span>`;
  if (simples && simples.mei === "Sim")
    badgesEl.innerHTML += `<span class="badge-pill badge-mei">MEI</span>`;
  const sitEsp = estab.situacao_especial || d.situacao_especial;
  if (sitEsp)
    badgesEl.innerHTML += `<span class="badge-pill badge-especial">${sitEsp}</span>`;

  // ── SITUAÇÃO ──
  const sitIcon = document.getElementById("sitIcon");
  const sitValor = document.getElementById("sitValor");
  sitIcon.className = `situacao-icon ${ativa ? "ativa" : "inativa"}`;
  sitIcon.innerHTML = `<i class="fa-solid fa-${ativa ? "check" : "xmark"}"></i>`;
  sitValor.className = `situacao-valor ${ativa ? "ativa" : "inativa"}`;
  sitValor.textContent = sit || "—";
  setEl(
    "sitData",
    fmtData(estab.data_situacao_cadastral || d.data_situacao_cadastral)
      ? `Desde ${fmtData(estab.data_situacao_cadastral || d.data_situacao_cadastral)}`
      : "—",
  );
  const motivo = estab.motivo_situacao_cadastral || d.motivo_situacao_cadastral;
  setEl(
    "sitMotivo",
    motivo ? motivo.descricao || motivo : "Sem motivo registrado",
  );
  setEl("sitEspecial", sitEsp || "Nenhuma");
  setEl(
    "sitEspecialData",
    fmtData(estab.data_situacao_especial || d.data_situacao_especial),
  );

  // ── IDENTIFICAÇÃO ──
  setEl("iCnpj", fmtCNPJ(estab.cnpj || d.cnpj));
  setEl("iCnpjRaiz", estab.cnpj_raiz || d.cnpj_raiz);
  setEl(
    "iCnpjOrdem",
    `${estab.cnpj_ordem || "—"} / ${estab.cnpj_digito_verificador || "—"}`,
  );
  setEl("iTipo", estab.tipo || d.descricao_identificador_matriz_filial);
  setEl(
    "iAbertura",
    fmtData(estab.data_inicio_atividade || d.data_inicio_atividade),
  );
  setEl("iResponsavel", d.responsavel_federativo || "Não informado");

  // ── PORTE & NATUREZA ──
  const porte = d.porte || estab.porte;
  setEl("nPorte", porte ? porte.descricao || porte : "—");
  const nat = d.natureza_juridica || estab.natureza_juridica;
  setEl("nNatureza", nat ? `${nat.id || ""} - ${nat.descricao || nat}` : "—");
  const qualif =
    d.qualificacao_do_responsavel || estab.qualificacao_do_responsavel;
  setEl("nQualif", qualif ? qualif.descricao || qualif : "—");
  setEl("nCapital", fmtCap(d.capital_social || estab.capital_social));
  setEl("nAtualizado", fmtDT(d.atualizado_em || estab.atualizado_em));

  // ── CONTATO ──
  const ddd1 = estab.ddd1 || d.ddd_telefone_1;
  const tel1 = estab.telefone1 || d.telefone1;
  const ddd2 = estab.ddd2 || d.ddd_telefone_2;
  const tel2 = estab.telefone2 || d.telefone2;
  const dddF = estab.ddd_fax || d.ddd_fax;
  const fax = estab.fax || d.fax;
  setEl("cTel1", ddd1 || tel1 ? fmtTel(ddd1, tel1) : "—");
  setEl("cTel2", ddd2 || tel2 ? fmtTel(ddd2, tel2) : "—");
  setEl("cFax", dddF || fax ? fmtTel(dddF, fax) : "—");
  setEl("cEmail", estab.email || d.email);

  // ── ENDEREÇO ──
  setEl(
    "eTipoLog",
    estab.tipo_logradouro || d.tipo_logradouro || d.descricao_tipo_logradouro,
  );
  setEl("eLogradouro", estab.logradouro || d.logradouro);
  const num = estab.numero || d.numero;
  const comp = estab.complemento || d.complemento;
  setEl("eNumeroComp", [num, comp].filter(Boolean).join(" / ") || "—");
  setEl("eBairro", estab.bairro || d.bairro);
  setEl("eCep", fmtCEP(estab.cep || d.cep));
  const cidade = estab.cidade || d.cidade;
  const estado = estab.estado || d.estado || d.uf;
  setEl(
    "eCidade",
    [
      cidade ? cidade.nome || cidade : null,
      estado ? estado.sigla || estado : null,
    ]
      .filter(Boolean)
      .join(" / ") || "—",
  );
  const pais = estab.pais || d.pais;
  setEl("ePais", pais ? pais.nome || pais : "Brasil");
  setEl(
    "eCidadeExt",
    estab.nome_cidade_exterior || d.nome_cidade_exterior || "—",
  );

  // ── SIMPLES NACIONAL & MEI ──
  const sg = document.getElementById("simplesGrid");
  sg.innerHTML = "";
  if (simples) {
    const sim = simples.simples === "Sim";
    const mei = simples.mei === "Sim";
    sg.innerHTML = `
            <div class="simples-card">
              <div class="simples-icon ${sim ? "sim" : "nao"}"><i class="fa-solid fa-${sim ? "check" : "xmark"}"></i></div>
              <div>
                <div class="simples-label">Simples Nacional</div>
                <div class="simples-valor ${sim ? "sim" : "nao"}">${sim ? "Optante" : "Não Optante"}</div>
                <div class="simples-data">Opção: ${fmtData(simples.data_opcao_simples) || "—"}</div>
                <div class="simples-data">Exclusão: ${fmtData(simples.data_exclusao_simples) || "—"}</div>
              </div>
            </div>
            <div class="simples-card">
              <div class="simples-icon ${mei ? "sim" : "nao"}"><i class="fa-solid fa-${mei ? "check" : "xmark"}"></i></div>
              <div>
                <div class="simples-label">MEI</div>
                <div class="simples-valor ${mei ? "sim" : "nao"}">${mei ? "Enquadrado" : "Não Enquadrado"}</div>
                <div class="simples-data">Opção: ${fmtData(simples.data_opcao_mei) || "—"}</div>
                <div class="simples-data">Exclusão: ${fmtData(simples.data_exclusao_mei) || "—"}</div>
              </div>
            </div>`;
  } else {
    sg.innerHTML = `<div class="empty-state" style="grid-column:1/-1;"><i class="fa-solid fa-receipt"></i>Empresa não enquadrada no Simples/MEI ou dado não disponível</div>`;
  }

  // ── CNAE PRINCIPAL ──
  const cpWrap = document.getElementById("cnaePrincipalWrap");
  const atPrinc = estab.atividade_principal || d.atividade_principal;
  if (atPrinc) {
    const cod = atPrinc.id || atPrinc.codigo || atPrinc.cnae_fiscal || "";
    const desc = atPrinc.descricao || atPrinc.cnae_fiscal_descricao || "";
    cpWrap.innerHTML = `<div class="cnae-item"><span class="cnae-code">${cod}</span><span class="cnae-desc"><strong>Principal</strong> — ${desc}</span></div>`;
  } else {
    cpWrap.innerHTML = `<div class="empty-state"><i class="fa-solid fa-industry"></i>Não informado</div>`;
  }

  // ── CNAES SECUNDÁRIOS ──
  const csEl = document.getElementById("cnaeSecList");
  csEl.innerHTML = "";
  const atSec =
    estab.atividades_secundarias ||
    d.atividades_secundarias ||
    d.cnaes_secundarios ||
    [];
  if (atSec && atSec.length > 0) {
    atSec.forEach((c) => {
      const cod = c.id || c.codigo || "";
      const desc = c.descricao || "";
      csEl.innerHTML += `<div class="cnae-item"><span class="cnae-code sec">${cod}</span><span class="cnae-desc">${desc}</span></div>`;
    });
  } else {
    csEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-layer-group"></i>Nenhuma atividade secundária</div>`;
  }

  // ── INSCRIÇÕES ESTADUAIS ──
  const ieEl = document.getElementById("ieList");
  ieEl.innerHTML = "";
  const ies = estab.inscricoes_estaduais || d.inscricoes_estaduais || [];
  if (ies && ies.length > 0) {
    ies.forEach((ie) => {
      const ativo =
        ie.ativo === true || ie.ativo === "true" || ie.ativo === "Ativa";
      const estado_ie = ie.estado ? ie.estado.sigla || ie.estado : ie.uf || "";
      ieEl.innerHTML += `
              <div class="ie-item">
                <div>
                  <div class="ie-numero">${ie.inscricao_estadual || ie.numero || "—"}</div>
                  <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${ie.tipo || ""}</div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                  <span class="ie-uf">${estado_ie}</span>
                  <span class="${ativo ? "ie-status-ok" : "ie-status-no"}">
                    <i class="fa-solid fa-${ativo ? "circle-check" : "circle-xmark"}"></i>
                    ${ativo ? "Ativa" : "Inativa"}
                  </span>
                </div>
              </div>`;
    });
  } else {
    ieEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-file-invoice"></i>Nenhuma inscrição estadual retornada pela API</div>`;
  }

  // ── SÓCIOS (QSA) ──
  const qsaEl = document.getElementById("qsaList");
  qsaEl.innerHTML = "";
  const socios = d.socios || estab.socios || [];
  if (socios && socios.length > 0) {
    socios.forEach((s) => {
      const nome_s = s.nome || s.nome_socio || "—";
      const qualSocio = s.qualificacao_socio
        ? s.qualificacao_socio.descricao || s.qualificacao_socio
        : s.qualificacao_socio_descricao || "—";
      const qualRep = s.qualificacao_representante
        ? s.qualificacao_representante.descricao || s.qualificacao_representante
        : "";
      const pais_s = s.pais ? s.pais.nome || s.pais : "";
      qsaEl.innerHTML += `
              <div class="socio-item">
                <div class="socio-avatar">${initials(nome_s)}</div>
                <div style="flex:1;">
                  <div class="socio-nome">${nome_s}</div>
                  <div class="socio-info">
                    <span><i class="fa-solid fa-briefcase" style="font-size:10px;margin-right:4px;"></i>${qualSocio}</span>
                    <span><i class="fa-solid fa-calendar" style="font-size:10px;margin-right:4px;"></i>Entrada: ${fmtData(s.data_entrada || s.data_entrada_sociedade)}</span>
                    ${s.faixa_etaria ? `<span><i class="fa-solid fa-user" style="font-size:10px;margin-right:4px;"></i>${s.faixa_etaria}</span>` : ""}
                    ${s.tipo ? `<span><i class="fa-solid fa-tag" style="font-size:10px;margin-right:4px;"></i>${s.tipo}</span>` : ""}
                    ${pais_s && pais_s !== "Brasil" ? `<span><i class="fa-solid fa-globe" style="font-size:10px;margin-right:4px;"></i>${pais_s}</span>` : ""}
                  </div>
                  <div class="socio-cpf">${s.cpf_cnpj_socio || s.cnpj_cpf_socio || ""}</div>
                  ${s.nome_representante ? `<div class="socio-rep"><i class="fa-solid fa-user-tie me-1"></i>Rep. Legal: ${s.nome_representante} ${qualRep ? "— " + qualRep : ""}</div>` : ""}
                </div>
              </div>`;
    });
  } else {
    qsaEl.innerHTML = `<div class="empty-state"><i class="fa-solid fa-users"></i>Nenhum sócio encontrado</div>`;
  }
}
