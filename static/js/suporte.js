// ══════════════════════════════════════════════════════════════
// suporte.js — Central de Suporte (Hub Ciamed)
// ══════════════════════════════════════════════════════════════
// Vanilla JS — sem React, sem jQuery.
// Todas as interações: tabs, FAQ, formulário, chamados, modal, notificações.
// ══════════════════════════════════════════════════════════════

(function () {
  "use strict";

  // ── Config ────────────────────────────────────────────────
  const MODULO_ICONS = {
    itens: "fa-boxes-stacked",
    mdf: "fa-truck-fast",
    fornecedor: "fa-industry",
    clientes: "fa-user-plus",
    cnpj: "fa-magnifying-glass",
    monitor: "fa-chart-line",
    notas: "fa-file-lines",
    lancamento_notas: "fa-file-invoice",
    geral: "fa-circle-info",
  };

  const STATUS_META = {
    pendente: { label: "Pendente", cls: "st-pendente", icon: "fa-clock" },
    em_analise: {
      label: "Em Análise",
      cls: "st-em_analise",
      icon: "fa-magnifying-glass",
    },
    resolvido: {
      label: "Resolvido",
      cls: "st-resolvido",
      icon: "fa-circle-check",
    },
    cancelado: { label: "Cancelado", cls: "st-cancelado", icon: "fa-ban" },
  };

  const PRIO_META = {
    baixa: { label: "Baixa", cls: "prio-baixa" },
    media: { label: "Média", cls: "prio-media" },
    alta: { label: "Alta", cls: "prio-alta" },
    critica: { label: "Crítica", cls: "prio-critica" },
  };

  const TAB_META = {
    faq: {
      eyebrow: "Base de conhecimento",
      title: "Como podemos ajudar você?",
      desc: "Consulte respostas para as dúvidas mais comuns sobre os robôs do Hub, organizadas por módulo.",
    },
    novo: {
      eyebrow: "Abertura de chamado",
      title: "Abrir um novo chamado",
      desc: "Conte para o time de TI o que aconteceu. Quanto mais detalhes e anexos, mais rápida a resolução.",
    },
    chamados: {
      eyebrow: "Meus chamados",
      title: "Acompanhe suas solicitações",
      desc: "Veja o status de cada chamado, leia respostas do TI e acompanhe a linha do tempo até a resolução.",
    },
    guias: {
      eyebrow: "Guias & tutoriais",
      title: "Aprenda a usar cada robô",
      desc: "Tutoriais passo a passo de cada módulo do Hub. Em construção — sua área aparece aqui em breve.",
    },
  };

  // ── Estado local ──────────────────────────────────────────
  let currentTab = "faq";
  let currentFilter = "todos";
  let currentPriority = "media";
  let faqData = [];
  let chamadosData = [];
  let chamadosStats = {};
  let uploadedFiles = [];

  // ══════════════════════════════════════════════════════════
  // TABS
  // ══════════════════════════════════════════════════════════

  window.supSwitchTab = function (tabId) {
    currentTab = tabId;
    const meta = TAB_META[tabId];

    // Update header
    document.getElementById("supEyebrow").textContent = meta.eyebrow;
    document.getElementById("supTitle").textContent = meta.title;
    document.getElementById("supDesc").textContent = meta.desc;

    // Update tab buttons
    document.querySelectorAll(".sup-tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });

    // Show/hide sections
    document.querySelectorAll(".sup-section").forEach((sec) => {
      sec.classList.remove("active");
    });
    const sec = document.getElementById("sec-" + tabId);
    if (sec) {
      sec.classList.add("active");
      // Re-trigger animation
      sec.style.animation = "none";
      sec.offsetHeight; // force reflow
      sec.style.animation = "";
    }

    // Auto-scroll da tab ativa pra dentro do viewport (em monitores estreitos)
    const activeTab = document.querySelector(".sup-tab.active");
    const scroller = document.getElementById("supTabsScroller");
    if (activeTab && scroller) {
      const aRect = activeTab.getBoundingClientRect();
      const sRect = scroller.getBoundingClientRect();
      if (aRect.left < sRect.left || aRect.right > sRect.right) {
        const target =
          activeTab.offsetLeft -
          (scroller.clientWidth - activeTab.offsetWidth) / 2;
        scroller.scrollTo({ left: Math.max(0, target), behavior: "smooth" });
      }
    }
    updateTabsOverflowHint();

    // Load data on tab switch
    if (tabId === "chamados") loadChamados();
  };

  // Atualiza atributos data-overflow-left/right pra mostrar os gradients
  function updateTabsOverflowHint() {
    const scroller = document.getElementById("supTabsScroller");
    if (!scroller) return;
    const left = scroller.scrollLeft > 4;
    const right =
      scroller.scrollLeft + scroller.clientWidth < scroller.scrollWidth - 4;
    scroller.dataset.overflowLeft = left ? "1" : "0";
    scroller.dataset.overflowRight = right ? "1" : "0";
  }

  // ══════════════════════════════════════════════════════════
  // FAQ
  // ══════════════════════════════════════════════════════════

  function loadFaq() {
    fetch("/api/suporte/faq")
      .then((r) => r.json())
      .then((data) => {
        faqData = data.faq || [];
        renderFaq();
        const total = faqData.reduce((acc, g) => acc + g.perguntas.length, 0);
        document.getElementById("faqCount").textContent = total;
      })
      .catch((err) => console.error("Erro ao carregar FAQ:", err));
  }

  function renderFaq(searchTerm) {
    const grid = document.getElementById("faqGrid");
    const empty = document.getElementById("faqEmpty");
    const q = (searchTerm || "").toLowerCase().trim();

    let filtered = faqData;
    if (q) {
      filtered = faqData
        .map((g) => ({
          ...g,
          perguntas: g.perguntas.filter(
            (p) =>
              p.pergunta.toLowerCase().includes(q) ||
              p.resposta.toLowerCase().includes(q),
          ),
        }))
        .filter((g) => g.perguntas.length > 0);
    }

    if (filtered.length === 0) {
      grid.style.display = "none";
      empty.style.display = "block";
      return;
    }

    grid.style.display = "";
    empty.style.display = "none";
    grid.innerHTML = filtered
      .map((group, gi) => {
        const icon = MODULO_ICONS[group.modulo] || "fa-circle-info";
        const items = group.perguntas
          .map((p) => {
            const pText = q
              ? highlightText(p.pergunta, q)
              : escHtml(p.pergunta);
            const aText = q
              ? highlightText(p.resposta, q)
              : escHtml(p.resposta);
            return `
              <div class="faq-item" onclick="this.classList.toggle('open')">
                <button class="faq-question" type="button">
                  <span>${pText}</span>
                  <i class="fa-solid fa-chevron-down"></i>
                </button>
                <div class="faq-answer">
                  <div class="faq-answer-inner">${aText}</div>
                </div>
              </div>`;
          })
          .join("");

        return `
          <div class="sup-card" style="animation: supFadeUp 0.32s ease both; animation-delay:${0.05 + gi * 0.05}s;">
            <div class="faq-module-header">
              <div class="faq-module-icon"><i class="fa-solid ${icon}"></i></div>
              <div>
                <h3 class="faq-module-name">${escHtml(group.nome)}</h3>
                <div class="faq-module-count">${group.perguntas.length} ${group.perguntas.length === 1 ? "pergunta" : "perguntas"}</div>
              </div>
            </div>
            ${items}
          </div>`;
      })
      .join("");
  }

  window.supFilterFaq = function () {
    const q = document.getElementById("faqSearch").value.trim();
    const countEl = document.getElementById("faqResultCount");
    const clearEl = document.getElementById("faqClearBtn");

    renderFaq(q);

    if (q) {
      const total = faqData.reduce(
        (acc, g) =>
          acc +
          g.perguntas.filter(
            (p) =>
              p.pergunta.toLowerCase().includes(q.toLowerCase()) ||
              p.resposta.toLowerCase().includes(q.toLowerCase()),
          ).length,
        0,
      );
      countEl.textContent = `${total} ${total === 1 ? "resultado" : "resultados"}`;
      countEl.style.display = "";
      clearEl.style.display = "";
    } else {
      countEl.style.display = "none";
      clearEl.style.display = "none";
    }
  };

  window.supClearFaqSearch = function () {
    document.getElementById("faqSearch").value = "";
    supFilterFaq();
  };

  // ══════════════════════════════════════════════════════════
  // NOVO CHAMADO
  // ══════════════════════════════════════════════════════════

  window.supSetPriority = function (prio) {
    currentPriority = prio;
    document.querySelectorAll(".prio-pill").forEach((p) => {
      p.classList.toggle("active", p.dataset.prio === prio);
    });
  };

  // Character counter
  document.addEventListener("DOMContentLoaded", function () {
    const assuntoInput = document.getElementById("chamadoAssunto");
    if (assuntoInput) {
      assuntoInput.addEventListener("input", function () {
        document.getElementById("assuntoCount").textContent = this.value.length;
      });
    }
  });

  // File upload
  window.supHandleFiles = function (fileList) {
    const remaining = 5 - uploadedFiles.length;
    const newFiles = Array.from(fileList).slice(0, remaining);
    newFiles.forEach((f) => {
      if (f.size > 10 * 1024 * 1024) return; // skip >10MB
      const isImg = f.type.startsWith("image/");
      uploadedFiles.push({
        file: f,
        name: f.name,
        size: (f.size / 1024).toFixed(0) + " KB",
        type: isImg ? "image" : "file",
        preview: isImg ? URL.createObjectURL(f) : null,
      });
    });
    renderAttachments();
  };

  function renderAttachments() {
    const list = document.getElementById("attachmentsList");
    if (uploadedFiles.length === 0) {
      list.innerHTML = "";
      return;
    }

    list.innerHTML = uploadedFiles
      .map(
        (f, i) => `
          <div class="sup-attachment">
            ${
              f.preview
                ? `<img class="sup-attachment-preview" src="${f.preview}" alt="">`
                : `<div class="sup-attachment-icon"><i class="fa-solid fa-file"></i></div>`
            }
            <div class="sup-attachment-info">
              <div class="sup-attachment-name">${escHtml(f.name)}</div>
              <div class="sup-attachment-size">${f.size}</div>
            </div>
            <button class="sup-attachment-remove" onclick="supRemoveFile(${i})" title="Remover">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>`,
      )
      .join("");
  }

  window.supRemoveFile = function (idx) {
    if (uploadedFiles[idx]?.preview)
      URL.revokeObjectURL(uploadedFiles[idx].preview);
    uploadedFiles.splice(idx, 1);
    renderAttachments();
  };

  // Drag & drop
  window.supDragOver = function (e) {
    e.preventDefault();
    e.currentTarget.classList.add("drag-over");
  };
  window.supDragLeave = function (e) {
    e.currentTarget.classList.remove("drag-over");
  };
  window.supDrop = function (e) {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");
    supHandleFiles(e.dataTransfer.files);
  };

  // Ctrl+V paste
  document.addEventListener("paste", function (e) {
    if (currentTab !== "novo") return;
    const items = e.clipboardData?.items;
    if (!items) return;
    const images = [];
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) images.push(file);
      }
    }
    if (images.length > 0) {
      e.preventDefault();
      supHandleFiles(images);
      const dz = document.getElementById("dropzone");
      if (dz) {
        dz.classList.add("paste-flash");
        setTimeout(() => dz.classList.remove("paste-flash"), 1500);
      }
    }
  });

  // Submit
  window.supSubmitChamado = function () {
    const modulo = document.getElementById("chamadoModulo").value;
    const assunto = document.getElementById("chamadoAssunto").value.trim();
    const descricao = document.getElementById("chamadoDescricao").value.trim();

    if (!modulo || !assunto || !descricao) {
      alert("Preencha todos os campos obrigatórios.");
      return;
    }

    const fd = new FormData();
    fd.append("modulo", modulo);
    fd.append("prioridade", currentPriority);
    fd.append("assunto", assunto);
    fd.append("mensagem", descricao);
    uploadedFiles.forEach((f) => fd.append("anexos", f.file));

    fetch("/api/suporte/chamados", { method: "POST", body: fd })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === "ok") {
          document.getElementById("novoForm").style.display = "none";
          document.getElementById("novoSuccess").style.display = "block";
          document.getElementById("successProtocol").textContent =
            "#" + data.protocolo;
        } else {
          alert(data.msg || "Erro ao criar chamado.");
        }
      })
      .catch(() => alert("Erro de conexão ao enviar chamado."));
  };

  window.supResetForm = function () {
    document.getElementById("chamadoModulo").value = "";
    document.getElementById("chamadoAssunto").value = "";
    document.getElementById("chamadoDescricao").value = "";
    document.getElementById("assuntoCount").textContent = "0";
    uploadedFiles = [];
    renderAttachments();
    supSetPriority("media");
    document.getElementById("novoForm").style.display = "";
    document.getElementById("novoSuccess").style.display = "none";
  };

  // ══════════════════════════════════════════════════════════
  // MEUS CHAMADOS
  // ══════════════════════════════════════════════════════════

  function loadChamados() {
    fetch("/api/suporte/chamados")
      .then((r) => r.json())
      .then((data) => {
        chamadosData = data.chamados || [];
        chamadosStats = data.stats || {};
        renderStats();
        renderChamados();
        document.getElementById("chamadosCount").textContent =
          chamadosData.length;
      })
      .catch((err) => console.error("Erro ao carregar chamados:", err));
  }

  function renderStats() {
    const s = chamadosStats;
    const grid = document.getElementById("statsGrid");
    const items = [
      {
        key: "todos",
        label: "Total de chamados",
        value: s.total || 0,
        color: "#475569",
        icon: "fa-folder",
      },
      {
        key: "pendente",
        label: "Pendentes",
        value: s.pendente || 0,
        color: "#f59e0b",
        icon: "fa-clock",
      },
      {
        key: "em_analise",
        label: "Em análise",
        value: s.em_analise || 0,
        color: "#3b82f6",
        icon: "fa-magnifying-glass",
      },
      {
        key: "resolvido",
        label: "Resolvidos",
        value: s.resolvido || 0,
        color: "#16a34a",
        icon: "fa-circle-check",
      },
    ];
    grid.innerHTML = items
      .map(
        (it) => `
          <button class="sup-stat ${currentFilter === it.key ? "active" : ""}"
                  style="${currentFilter === it.key ? `border-color:${it.color}; background:${it.color}0d;` : ""}"
                  onclick="supSetFilter('${it.key}')">
            <div class="sup-stat-icon" style="background:${it.color}1a; color:${it.color};">
              <i class="fa-solid ${it.icon}"></i>
            </div>
            <div>
              <div class="sup-stat-value">${it.value}</div>
              <div class="sup-stat-label">${it.label}</div>
            </div>
          </button>`,
      )
      .join("");
  }

  window.supSetFilter = function (filter) {
    currentFilter = filter;
    document.querySelectorAll(".sup-filter-pill").forEach((p) => {
      p.classList.toggle("active", p.dataset.filter === filter);
    });
    renderStats();
    renderChamados();
  };

  window.supFilterChamados = function () {
    renderChamados();
  };

  function renderChamados() {
    const search = (document.getElementById("chamadosSearch")?.value || "")
      .toLowerCase()
      .trim();
    let list = chamadosData;

    if (currentFilter !== "todos") {
      list = list.filter((c) => c.status === currentFilter);
    }
    if (search) {
      list = list.filter(
        (c) =>
          c.protocolo.toLowerCase().includes(search) ||
          c.assunto.toLowerCase().includes(search) ||
          (c.mensagem || "").toLowerCase().includes(search),
      );
    }

    const container = document.getElementById("chamadosList");
    const empty = document.getElementById("chamadosEmpty");

    if (list.length === 0) {
      container.innerHTML = "";
      empty.style.display = "block";
      document.getElementById("chamadosEmptyTitle").textContent = search
        ? "Nenhum chamado encontrado"
        : "Nenhum chamado nesta categoria";
      document.getElementById("chamadosEmptyText").textContent = search
        ? "Tente outros termos de busca."
        : currentFilter === "todos"
          ? "Você não abriu nenhum chamado — tudo funcionando! 🎉"
          : `Nenhum chamado com status "${STATUS_META[currentFilter]?.label || currentFilter}".`;
      return;
    }

    empty.style.display = "none";
    container.innerHTML = list
      .map((c, i) => {
        const st = STATUS_META[c.status] || STATUS_META.pendente;
        const pr = PRIO_META[c.prioridade] || PRIO_META.media;
        const modIcon = MODULO_ICONS[c.modulo] || "fa-circle-info";
        return `
          <div class="sup-card hoverable sup-ticket" style="animation: supFadeUp 0.32s ease both; animation-delay:${0.04 + i * 0.04}s;"
               onclick="supOpenModal(${c.id})">
            <span class="sup-ticket-proto">#${escHtml(c.protocolo)}</span>
            <div style="min-width:0;">
              <div class="sup-ticket-subject">${escHtml(c.assunto)}</div>
              <div class="sup-ticket-module">
                <i class="fa-solid ${modIcon}"></i> ${escHtml(c.modulo_nome)}
              </div>
            </div>
            <span class="sup-badge dot ${pr.cls}">${pr.label}</span>
            <span class="sup-badge ${st.cls}">
              <i class="fa-solid ${st.icon}" style="font-size:10px;"></i> ${st.label}
            </span>
            <span class="sup-ticket-date">
              <i class="fa-regular fa-clock" style="margin-right:6px; color:var(--sup-muted);"></i>${escHtml(c.created_at)}
            </span>
            <i class="fa-solid fa-chevron-right sup-ticket-chevron"></i>
          </div>`;
      })
      .join("");
  }

  // ══════════════════════════════════════════════════════════
  // MODAL DE DETALHE
  // ══════════════════════════════════════════════════════════

  window.supOpenModal = function (chamadoId) {
    fetch(`/api/suporte/chamados/${chamadoId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.status !== "ok") return;
        const c = data.chamado;
        renderModal(c);
        document.getElementById("chamadoOverlay").classList.add("open");
        document.body.style.overflow = "hidden";
      })
      .catch((err) => console.error("Erro ao carregar detalhe:", err));
  };

  window.supCloseModal = function () {
    document.getElementById("chamadoOverlay").classList.remove("open");
    document.body.style.overflow = "";
  };

  // ESC to close
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") supCloseModal();
  });

  function renderModal(c) {
    const st = STATUS_META[c.status] || STATUS_META.pendente;
    const pr = PRIO_META[c.prioridade] || PRIO_META.media;

    document.getElementById("modalHeader").innerHTML = `
      <div style="display:flex; justify-content:space-between; gap:12px; margin-bottom:12px;">
        <span style="font-family:'Syne',sans-serif; font-weight:600; font-size:18px; color:var(--sup-teal-dark);">#${escHtml(c.protocolo)}</span>
        <button class="sup-modal-close" onclick="supCloseModal()"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <h2 style="font-family:'Syne',sans-serif; font-size:20px; font-weight:600; margin:0 0 12px; line-height:1.3;">${escHtml(c.assunto)}</h2>
      <div style="display:flex; gap:8px; flex-wrap:wrap;">
        <span class="sup-badge ${st.cls}"><i class="fa-solid ${st.icon}" style="font-size:10px;"></i> ${st.label}</span>
        <span class="sup-badge dot ${pr.cls}">${pr.label}</span>
      </div>`;

    let body = `
      <div class="sup-detail-grid">
        <div>
          <div class="sup-detail-label">Módulo</div>
          <div style="font-size:14px; font-weight:500;">${escHtml(c.modulo_nome)}</div>
        </div>
        <div>
          <div class="sup-detail-label">Solicitante</div>
          <div style="font-size:14px; font-weight:500;">${escHtml(c.usuario)}</div>
        </div>
        <div>
          <div class="sup-detail-label">Criado em</div>
          <div style="font-size:14px;">${escHtml(c.created_at)}</div>
        </div>
        <div>
          <div class="sup-detail-label">Atualizado em</div>
          <div style="font-size:14px;">${escHtml(c.updated_at)}</div>
        </div>
      </div>
      <div style="margin-bottom:28px;">
        <div class="sup-detail-section-title">Descrição</div>
        <div style="font-size:14px; color:var(--sup-text-2); line-height:1.6; white-space:pre-wrap;">${escHtml(c.mensagem)}</div>
      </div>`;

    if (c.anexos && c.anexos.length > 0) {
      body += `
        <div style="margin-bottom:28px;">
          <div class="sup-detail-section-title">Anexos · ${c.anexos.length}</div>
          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(190px,1fr)); gap:10px;">
            ${c.anexos
              .map((a) => {
                const isImg = (a.tipo_mime || "").startsWith("image/");
                return `
                <div class="sup-attachment">
                  <div class="sup-attachment-icon" style="${isImg ? "background:linear-gradient(135deg,#fef3c7,#fde68a); color:#b45309;" : ""}">
                    <i class="fa-solid ${isImg ? "fa-image" : "fa-file"}"></i>
                  </div>
                  <div class="sup-attachment-info">
                    <div class="sup-attachment-name">${escHtml(a.nome_arquivo)}</div>
                    <div class="sup-attachment-size">${a.tamanho_fmt || ""}</div>
                  </div>
                  <a href="/api/suporte/anexos/${a.id}/download" style="width:28px; height:28px; border-radius:8px; display:grid; place-items:center; color:var(--sup-text-2); text-decoration:none;" title="Download">
                    <i class="fa-solid fa-download" style="font-size:12px;"></i>
                  </a>
                </div>`;
              })
              .join("")}
          </div>
        </div>`;
    }

    if (c.historico && c.historico.length > 0) {
      body += `
        <div>
          <div class="sup-detail-section-title">Histórico</div>
          <div class="sup-timeline">
            ${c.historico.map((h) => renderTimelineItem(h)).join("")}
          </div>
        </div>`;
    }

    if (c.status === "pendente") {
      body += `
        <div style="margin-top:32px; padding-top:20px; border-top:1px solid var(--sup-border); display:flex; justify-content:flex-end; gap:10px;">
          <button class="sup-btn danger" onclick="supCancelChamado(${c.id})">
            <i class="fa-solid fa-ban"></i> Cancelar chamado
          </button>
        </div>`;
    }

    document.getElementById("modalBody").innerHTML = body;
  }

  function renderTimelineItem(h) {
    const dotClass =
      h.tipo === "criacao"
        ? "criacao"
        : h.tipo === "resposta_admin"
          ? "resposta"
          : h.status_novo === "resolvido"
            ? "resolvido"
            : "status";
    const dotIcon =
      h.tipo === "criacao"
        ? "fa-circle-plus"
        : h.tipo === "resposta_admin"
          ? "fa-comment-dots"
          : h.status_novo === "resolvido"
            ? "fa-check"
            : "fa-arrow-right";

    if (h.tipo === "resposta_admin") {
      return `
        <div class="sup-timeline-item">
          <div class="sup-timeline-line"></div>
          <div class="sup-timeline-dot ${dotClass}"><i class="fa-solid ${dotIcon}"></i></div>
          <div class="sup-timeline-comment">
            <div class="sup-timeline-comment-header">
              <i class="fa-solid fa-headset" style="color:var(--sup-purple); font-size:12px;"></i>
              <span class="sup-timeline-comment-who">${escHtml(h.usuario)}</span>
              <span class="sup-timeline-comment-when">· ${escHtml(h.created_at)}</span>
            </div>
            <div class="sup-timeline-comment-text">${escHtml(h.mensagem || "")}</div>
          </div>
        </div>`;
    }

    let text = h.mensagem || "";
    if (h.tipo === "mudanca_status" && h.status_novo) {
      const label = STATUS_META[h.status_novo]?.label || h.status_novo;
      text = text || `Status alterado para ${label}`;
    }
    if (h.tipo === "criacao") text = text || "Chamado criado";

    return `
      <div class="sup-timeline-item">
        <div class="sup-timeline-line"></div>
        <div class="sup-timeline-dot ${dotClass}"><i class="fa-solid ${dotIcon}"></i></div>
        <div>
          <div class="sup-timeline-text">${escHtml(text)}</div>
          <div class="sup-timeline-meta">${escHtml(h.usuario)} · ${escHtml(h.created_at)}</div>
        </div>
      </div>`;
  }

  window.supCancelChamado = function (chamadoId) {
    if (!confirm("Tem certeza que deseja cancelar este chamado?")) return;
    fetch(`/api/suporte/chamados/${chamadoId}/cancelar`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === "ok") {
          supCloseModal();
          loadChamados();
        } else {
          alert(data.msg || "Erro ao cancelar.");
        }
      });
  };

  // ══════════════════════════════════════════════════════════
  // GUIAS
  // ══════════════════════════════════════════════════════════

  function renderGuias() {
    const grid = document.getElementById("guiasGrid");
    if (!grid) return;
    const modulos = [];
    document.querySelectorAll("#chamadoModulo option").forEach((opt) => {
      if (opt.value && opt.value !== "geral") {
        modulos.push({ id: opt.value, name: opt.textContent });
      }
    });
    modulos.push({ id: "geral", name: "Geral" });

    grid.innerHTML = modulos
      .map((m, i) => {
        const icon = MODULO_ICONS[m.id] || "fa-circle-info";
        return `
          <div class="sup-card guia-card" style="animation: supFadeUp 0.32s ease both; animation-delay:${0.05 + i * 0.05}s;">
            <div class="guia-card-stripe"></div>
            <div class="guia-card-icon"><i class="fa-solid ${icon}"></i></div>
            <h3 style="font-size:16px; font-family:'Syne',sans-serif; margin:0 0 6px;">${escHtml(m.name)}</h3>
            <p style="font-size:13px; color:var(--sup-text-2); line-height:1.5; margin:0 0 18px;">
              Aprenda a usar o robô de ${escHtml(m.name)}.
            </p>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span class="sup-badge outline" style="color:var(--sup-muted); border-color:var(--sup-border-hover); font-size:11px; padding:4px 10px;">
                <i class="fa-regular fa-clock" style="font-size:10px;"></i> Em breve
              </span>
              <span style="font-size:11px; color:var(--sup-muted);">Previsão: Q3 2026</span>
            </div>
          </div>`;
      })
      .join("");
  }

  // ══════════════════════════════════════════════════════════
  // UTILS
  // ══════════════════════════════════════════════════════════

  function escHtml(str) {
    if (str === null || str === undefined) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
  }

  function highlightText(text, q) {
    const escaped = escHtml(text);
    const qEsc = escHtml(q);
    const regex = new RegExp(
      `(${qEsc.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );
    return escaped.replace(regex, '<span class="faq-highlight">$1</span>');
  }

  // ══════════════════════════════════════════════════════════
  // INIT
  // ══════════════════════════════════════════════════════════

  document.addEventListener("DOMContentLoaded", function () {
    loadFaq();
    renderGuias();

    // Inicia os indicadores de overflow das tabs
    updateTabsOverflowHint();
    const scroller = document.getElementById("supTabsScroller");
    if (scroller) {
      scroller.addEventListener("scroll", updateTabsOverflowHint, {
        passive: true,
      });
      window.addEventListener("resize", updateTabsOverflowHint);
    }
  });
})();
