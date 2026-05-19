/* global React, ReactDOM, NotaCard, RegisterModal, AvulsaModal, DetailDrawer,
   CategoryIcon, UnitBadge, statusOf, daysLate, formatBRL, dayLabel */
// Main app — Controle de Notas Ciamed

const { useState, useEffect, useMemo, useRef, useCallback } = React;

const MES_NOMES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];

const App = () => {
  const {
    TODAY: TODAY_BASE,
    MONTH: BASE_MONTH,
    YEAR: BASE_YEAR,
    UNIDADES,
    CATEGORIAS,
    NOTAS_INICIAIS,
    EXPECTATIVAS_INICIAIS,
  } = window.CIAMED;

  // ---- view state
  const [view, setView] = useState("kanban"); // 'kanban' | 'fornecedores' | 'panorama'

  // ---- expectativas (recurring supplier registry) — vem do backend Flask
  const [expectativas, setExpectativas] = useState([]);
  const [loadingExpectativas, setLoadingExpectativas] = useState(true);

  // Recarrega a lista de fornecedores recorrentes do backend.
  // Exposto pra FornecedoresView chamar depois de criar/editar/remover.
  const reloadExpectativas = useCallback(() => {
    setLoadingExpectativas(true);
    return fetch("/notas/api/fornecedores?ativo=todos")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setExpectativas(data);
        setLoadingExpectativas(false);
      })
      .catch((err) => {
        console.error("Erro ao carregar fornecedores:", err);
        setLoadingExpectativas(false);
      });
  }, []);

  useEffect(() => {
    reloadExpectativas();
  }, [reloadExpectativas]);

  // ---- view month state (drives header + data slicing)
  const [viewMonth, setViewMonth] = useState({
    year: BASE_YEAR,
    month: BASE_MONTH,
  });
  const isCurrentMonth =
    viewMonth.year === BASE_YEAR && viewMonth.month === BASE_MONTH;
  const isPastMonth =
    viewMonth.year < BASE_YEAR ||
    (viewMonth.year === BASE_YEAR && viewMonth.month < BASE_MONTH);
  const TODAY = useMemo(() => {
    if (isCurrentMonth) return TODAY_BASE;
    if (isPastMonth) return new Date(viewMonth.year, viewMonth.month + 1, 0);
    return new Date(viewMonth.year, viewMonth.month, 1);
  }, [isCurrentMonth, isPastMonth, viewMonth, TODAY_BASE]);
  const recurringTemplates = useMemo(
    () => NOTAS_INICIAIS.filter((n) => !n.avulsa),
    [NOTAS_INICIAIS],
  );

  const goPrevMonth = () =>
    setViewMonth((v) => ({
      year: v.month === 0 ? v.year - 1 : v.year,
      month: v.month === 0 ? 11 : v.month - 1,
    }));
  const goNextMonth = () =>
    setViewMonth((v) => ({
      year: v.month === 11 ? v.year + 1 : v.year,
      month: v.month === 11 ? 0 : v.month + 1,
    }));
  const goCurrentMonth = () =>
    setViewMonth({ year: BASE_YEAR, month: BASE_MONTH });

  // ---- jump from Panorama / Fornecedores to Kanban at a specific month
  const jumpToMonth = ({ year, month }) => {
    setViewMonth({ year, month });
    setView("kanban");
  };

  // ---- state
  // Notas vêm do backend (Flask + PostgreSQL). localStorage NÃO é mais usado pra dados.
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [filtroUnidade, setFiltroUnidade] = useState("todas");
  const [filtroCategoria, setFiltroCategoria] = useState("todas");
  const [filtroEspecial, setFiltroEspecial] = useState(null); // 'atrasadas-2plus' | 'hoje' | 'retencao'
  const [busca, setBusca] = useState("");
  const [recebidasExpanded, setRecebidasExpanded] = useState(false);
  const [registerNota, setRegisterNota] = useState(null);
  const [showAvulsa, setShowAvulsa] = useState(false);
  const [detail, setDetail] = useState(null);
  const [draggingId, setDraggingId] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const [recentlyChanged, setRecentlyChanged] = useState(null);
  const [hoveredCardId, setHoveredCardId] = useState(null);
  const [toast, setToast] = useState(null);

  const buscaRef = useRef(null);

  // ---- carrega notas do backend sempre que o mês mudar
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);

    const mes = viewMonth.month + 1; // JS: 0-11 → API: 1-12
    const ano = viewMonth.year;

    fetch(`/notas/api/notas?mes=${mes}&ano=${ano}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        const parsed = data.map((n) => ({
          ...n,
          recebidaEm: n.recebidaEm
            ? new Date(n.recebidaEm + "T12:00:00")
            : null,
        }));
        setNotas(parsed);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Erro ao carregar notas:", err);
        setLoadError(err.message);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [viewMonth]);

  // toast
  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  }, []);

  // ---- displayed notas: tudo vem do backend (API auto-gera meses sem registro)
  const displayedNotas = notas;

  // ---- filtering
  const filteredNotas = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return displayedNotas.filter((n) => {
      if (filtroUnidade !== "todas" && n.unidade !== filtroUnidade)
        return false;
      if (filtroCategoria !== "todas" && n.categoria !== filtroCategoria)
        return false;
      if (q) {
        const hay =
          `${n.fornecedor} ${n.nfNumero || ""} ${n.valor != null ? n.valor : ""} ${n.cnpj || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (filtroEspecial === "retencao" && !n.retencao) return false;
      if (filtroEspecial === "atrasadas-2plus") {
        if (statusOf(n, TODAY) !== "atrasada") return false;
        if (daysLate(n, TODAY) < 2) return false;
      }
      if (filtroEspecial === "vencem-hoje") {
        if (statusOf(n, TODAY) !== "aguardando") return false;
        if (n.diaEsperado !== TODAY.getDate()) return false;
      }
      return true;
    });
  }, [
    displayedNotas,
    filtroUnidade,
    filtroCategoria,
    busca,
    filtroEspecial,
    TODAY,
  ]);

  // bucket
  const buckets = useMemo(() => {
    const atrasadas = [],
      aguardando = [],
      recebidas = [],
      avulsas = [];
    for (const n of filteredNotas) {
      const s = statusOf(n, TODAY);
      if (s === "atrasada") atrasadas.push(n);
      else if (s === "aguardando") aguardando.push(n);
      else if (s === "recebida") recebidas.push(n);
      else if (s === "avulsa") avulsas.push(n);
    }
    // sort
    atrasadas.sort((a, b) => daysLate(b, TODAY) - daysLate(a, TODAY));
    aguardando.sort((a, b) => a.diaEsperado - b.diaEsperado);
    recebidas.sort((a, b) => b.recebidaEm - a.recebidaEm);
    avulsas.sort((a, b) => b.recebidaEm - a.recebidaEm);
    return { atrasadas, aguardando, recebidas, avulsas };
  }, [filteredNotas, TODAY]);

  // aguardando subgroups
  const agSubgroups = useMemo(() => {
    const todayDay = TODAY.getDate();
    // current week: today through Sunday (week starts Monday)
    // dayOfWeek: 0=Sun .. 6=Sat. Want days remaining in current week.
    const dow = TODAY.getDay(); // 5 (Friday) for May 8
    const remainingThisWeek = dow === 0 ? 0 : 7 - dow; // Friday: 2 (Sat, Sun)
    const endThisWeek = todayDay + remainingThisWeek;
    const endNextWeek = endThisWeek + 7;

    const hoje = [],
      esta = [],
      proxima = [],
      depois = [];
    for (const n of buckets.aguardando) {
      if (n.diaEsperado === todayDay) hoje.push(n);
      else if (n.diaEsperado > todayDay && n.diaEsperado <= endThisWeek)
        esta.push(n);
      else if (n.diaEsperado > endThisWeek && n.diaEsperado <= endNextWeek)
        proxima.push(n);
      else depois.push(n);
    }
    return { hoje, esta, proxima, depois };
  }, [buckets.aguardando, TODAY]);

  // ---- editing guard for non-current months
  const guardEdit = () => {
    if (!isCurrentMonth) {
      showToast("Modo leitura — volta pro mês atual pra editar");
      return false;
    }
    return true;
  };

  const handleOpenRegister = (nota) => {
    if (!guardEdit()) return;
    setRegisterNota(nota);
  };
  const handleOpenAvulsa = () => {
    if (!guardEdit()) return;
    setShowAvulsa(true);
  };

  // ---- mark received (API: PATCH /notas/api/notas/<id>/receber)
  const markReceived = async (nota, payload) => {
    try {
      const recebidaIso =
        payload.recebidaEm instanceof Date
          ? payload.recebidaEm.toISOString().slice(0, 10)
          : payload.recebidaEm;

      const r = await fetch(`/notas/api/notas/${nota.id}/receber`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, recebidaEm: recebidaIso }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const updated = await r.json();
      const parsed = {
        ...updated,
        recebidaEm: updated.recebidaEm
          ? new Date(updated.recebidaEm + "T12:00:00")
          : null,
      };
      setNotas((prev) => prev.map((n) => (n.id === nota.id ? parsed : n)));
      setRegisterNota(null);
      setRecentlyChanged(nota.id);
      setTimeout(
        () => setRecentlyChanged((curr) => (curr === nota.id ? null : curr)),
        1800,
      );
      showToast(`✓ ${nota.fornecedor} registrada`);
    } catch (err) {
      console.error(err);
      showToast(`Erro ao registrar: ${err.message}`);
    }
  };

  const unreceive = async (nota) => {
    try {
      const r = await fetch(`/notas/api/notas/${nota.id}/desfazer`, {
        method: "PATCH",
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const updated = await r.json();
      const parsed = { ...updated, recebidaEm: null };
      setNotas((prev) => prev.map((n) => (n.id === nota.id ? parsed : n)));
      setDetail(null);
      showToast(`Recebimento desfeito · ${nota.fornecedor}`);
    } catch (err) {
      console.error(err);
      showToast(`Erro: ${err.message}`);
    }
  };

  const addAvulsa = async (data) => {
    try {
      const recebidaIso =
        data.recebidaEm instanceof Date
          ? data.recebidaEm.toISOString().slice(0, 10)
          : data.recebidaEm;

      const body = {
        ...data,
        mes: viewMonth.month + 1,
        ano: viewMonth.year,
        recebidaEm: recebidaIso,
      };
      const r = await fetch(`/notas/api/notas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const created = await r.json();
      const parsed = {
        ...created,
        recebidaEm: created.recebidaEm
          ? new Date(created.recebidaEm + "T12:00:00")
          : null,
      };
      setNotas((prev) => [...prev, parsed]);
      setShowAvulsa(false);
      setRecentlyChanged(parsed.id);
      setTimeout(() => setRecentlyChanged(null), 1800);
      showToast(`+ ${parsed.fornecedor} adicionada`);
    } catch (err) {
      console.error(err);
      showToast(`Erro: ${err.message}`);
    }
  };

  // ---- drag-drop
  const onDragStart = (e, nota) => {
    if (!isCurrentMonth) {
      e.preventDefault();
      return;
    }
    setDraggingId(nota.id);
    e.dataTransfer.effectAllowed = "move";
    try {
      e.dataTransfer.setData("text/plain", nota.id);
    } catch (err) {}
  };
  const onDragEnd = () => {
    setDraggingId(null);
    setDropTarget(null);
  };
  const onDragOverCol = (e, col) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (col === "recebidas") setDropTarget("recebidas");
    else setDropTarget(col);
  };
  const onDropCol = (e, col) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain") || draggingId;
    const nota = notas.find((n) => n.id === id);
    setDraggingId(null);
    setDropTarget(null);
    if (!nota) return;
    if (col === "recebidas" && isCurrentMonth) {
      setRegisterNota(nota);
    } else if (col === "recebidas" && !isCurrentMonth) {
      showToast("Modo leitura — volta pro mês atual pra editar");
    }
    // dropping on other columns: no-op for now
  };

  // ---- keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      // ignore in input
      const tag = (e.target.tagName || "").toLowerCase();
      const isInput =
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        e.target.isContentEditable;
      // view switches (work everywhere)
      if (!isInput && (e.key === "k" || e.key === "K")) {
        setView("kanban");
        return;
      }
      if (!isInput && (e.key === "f" || e.key === "F")) {
        setView("fornecedores");
        return;
      }
      if (!isInput && (e.key === "p" || e.key === "P")) {
        setView("panorama");
        return;
      }
      // kanban-only shortcuts below
      if (view !== "kanban") return;
      if (e.key === "/" && !isInput) {
        e.preventDefault();
        buscaRef.current && buscaRef.current.focus();
        return;
      }
      if (e.key === "Escape") {
        if (filtroEspecial) setFiltroEspecial(null);
        if (busca) setBusca("");
        return;
      }
      if (isInput) return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrevMonth();
        return;
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        goNextMonth();
        return;
      }
      if (e.key >= "1" && e.key <= "4") {
        const map = { 1: "matriz", 2: "f2", 3: "f3", 4: "f4" };
        setFiltroUnidade((prev) =>
          prev === map[e.key] ? "todas" : map[e.key],
        );
        return;
      }
      if (e.key === "0") {
        setFiltroUnidade("todas");
        return;
      }
      if (e.key === "r" || e.key === "R") {
        if (hoveredCardId) {
          const n = notas.find((x) => x.id === hoveredCardId);
          if (n && !n.recebidaEm) {
            setRegisterNota(n);
          }
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hoveredCardId, notas, filtroEspecial, busca, view]);

  // ---- stats
  const stats = useMemo(() => {
    let atrasadas = 0,
      aguardando = 0,
      recebidas = 0,
      avulsas = 0;
    let atrasadas2plus = 0,
      vencemHoje = 0,
      retMes = 0;
    for (const n of displayedNotas) {
      const s = statusOf(n, TODAY);
      if (s === "atrasada") {
        atrasadas++;
        if (daysLate(n, TODAY) >= 2) atrasadas2plus++;
      } else if (s === "aguardando") {
        aguardando++;
        if (n.diaEsperado === TODAY.getDate()) vencemHoje++;
      } else if (s === "recebida") recebidas++;
      else if (s === "avulsa") avulsas++;
      if (n.retencao) retMes++;
    }
    const esperadas = displayedNotas.filter((n) => !n.avulsa).length;
    return {
      atrasadas,
      aguardando,
      recebidas,
      avulsas,
      atrasadas2plus,
      vencemHoje,
      retMes,
      esperadas,
    };
  }, [displayedNotas, TODAY]);

  // ---- visible cards count for empty states
  const totalVisible = filteredNotas.length;

  // ---- render
  const todayStr = `${dayLabel(TODAY.getDate())}/${dayLabel(TODAY.getMonth() + 1)}`;

  return (
    <div className="app">
      <TopBar view={view} setView={setView} stats={stats} />
      <div className="app-inner">
        {view === "fornecedores" && (
          <FornecedoresView
            expectativas={expectativas}
            reloadExpectativas={reloadExpectativas}
            today={TODAY_BASE}
            onJumpToKanban={() => setView("kanban")}
          />
        )}

        {view === "panorama" && (
          <PanoramaView
            expectativas={expectativas}
            notas={notas}
            today={TODAY_BASE}
            viewMonth={viewMonth}
            onJumpToMonth={jumpToMonth}
          />
        )}

        {view === "kanban" && (
          <>
            {/* ============= HEADER ============= */}
            <header className="hdr">
              <div className="hdr-row hdr-top">
                <div className="hdr-title">
                  <div className="hdr-month">
                    {MES_NOMES[viewMonth.month][0].toUpperCase() +
                      MES_NOMES[viewMonth.month].slice(1)}{" "}
                    {viewMonth.year}
                  </div>
                  {isCurrentMonth ? (
                    <div className="hdr-today">
                      hoje · <span className="mono">{todayStr}</span>
                    </div>
                  ) : (
                    <div className="hdr-today hdr-readonly">
                      {isPastMonth ? "histórico" : "previsão"} · somente leitura
                    </div>
                  )}
                </div>
                <nav className="hdr-nav">
                  <button
                    className="nav-btn"
                    title="Mês anterior (←)"
                    onClick={goPrevMonth}
                  >
                    ‹
                  </button>
                  <button
                    className={`nav-btn nav-now ${isCurrentMonth ? "is-current" : ""}`}
                    onClick={goCurrentMonth}
                    title="Voltar pra mês atual"
                  >
                    HOJE
                  </button>
                  <button
                    className="nav-btn"
                    title="Próximo mês (→)"
                    onClick={goNextMonth}
                  >
                    ›
                  </button>
                </nav>
              </div>

              <div className="hdr-row hdr-stats">
                <div className="stat-counter">
                  <span className="stat-num mono">
                    {stats.esperadas + stats.avulsas}
                  </span>
                  <span className="stat-lbl">notas no mês</span>
                </div>
                <div className="stat-divider"></div>

                <button
                  className={`actstat actstat-late ${filtroEspecial === "atrasadas-2plus" ? "on" : ""} ${stats.atrasadas2plus === 0 ? "is-empty" : ""}`}
                  onClick={() =>
                    setFiltroEspecial((prev) =>
                      prev === "atrasadas-2plus" ? null : "atrasadas-2plus",
                    )
                  }
                  title="Filtrar atrasadas há +2 dias"
                >
                  <span className="actstat-bullet" aria-hidden="true">
                    !
                  </span>
                  <span>
                    <b>{stats.atrasadas2plus}</b> atrasadas há +2 dias
                  </span>
                </button>

                <button
                  className={`actstat actstat-today ${filtroEspecial === "vencem-hoje" ? "on" : ""} ${stats.vencemHoje === 0 ? "is-empty" : ""}`}
                  onClick={() =>
                    setFiltroEspecial((prev) =>
                      prev === "vencem-hoje" ? null : "vencem-hoje",
                    )
                  }
                  title="Filtrar notas que vencem hoje"
                >
                  <span className="actstat-bullet" aria-hidden="true">
                    ●
                  </span>
                  <span>
                    <b>{stats.vencemHoje}</b> vencem hoje
                  </span>
                </button>

                <button
                  className={`actstat actstat-ret ${filtroEspecial === "retencao" ? "on" : ""} ${stats.retMes === 0 ? "is-empty" : ""}`}
                  onClick={() =>
                    setFiltroEspecial((prev) =>
                      prev === "retencao" ? null : "retencao",
                    )
                  }
                  title="Filtrar notas com retenção"
                >
                  <span className="actstat-bullet" aria-hidden="true">
                    ⊖
                  </span>
                  <span>
                    <b>{stats.retMes}</b> com retenção
                  </span>
                </button>

                <div style={{ flex: 1 }}></div>

                <div className="hdr-progress">
                  <div className="hdr-progress-bar">
                    <span
                      className="seg seg-rec"
                      style={{ flex: stats.recebidas + stats.avulsas }}
                    ></span>
                    <span
                      className="seg seg-aw"
                      style={{ flex: stats.aguardando }}
                    ></span>
                    <span
                      className="seg seg-late"
                      style={{ flex: stats.atrasadas }}
                    ></span>
                  </div>
                  <div className="hdr-progress-lbl mono">
                    <span>
                      <i className="dot dot-rec"></i>
                      {stats.recebidas + stats.avulsas} rec.
                    </span>
                    <span>
                      <i className="dot dot-aw"></i>
                      {stats.aguardando} aguard.
                    </span>
                    <span>
                      <i className="dot dot-late"></i>
                      {stats.atrasadas} atras.
                    </span>
                  </div>
                </div>
              </div>

              <div className="hdr-row hdr-filters">
                <div className="filter-group">
                  <span className="filter-lbl">Unidade</span>
                  <div className="chips">
                    {[{ id: "todas", nome: "Todas" }, ...UNIDADES].map((u) => (
                      <button
                        key={u.id}
                        className={`chip ${filtroUnidade === u.id ? "on" : ""}`}
                        onClick={() => setFiltroUnidade(u.id)}
                      >
                        {u.id !== "todas" && (
                          <UnitBadge unidade={u.id} size="xs" />
                        )}
                        {u.id === "todas" ? "Todas" : u.nome}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="filter-group">
                  <span className="filter-lbl">Categoria</span>
                  <select
                    className="cat-select"
                    value={filtroCategoria}
                    onChange={(e) => setFiltroCategoria(e.target.value)}
                  >
                    <option value="todas">Todas as categorias</option>
                    {CATEGORIAS.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome}
                      </option>
                    ))}
                  </select>
                </div>

                {(filtroEspecial ||
                  filtroUnidade !== "todas" ||
                  filtroCategoria !== "todas" ||
                  busca) && (
                  <button
                    className="clear-all"
                    onClick={() => {
                      setFiltroEspecial(null);
                      setFiltroUnidade("todas");
                      setFiltroCategoria("todas");
                      setBusca("");
                    }}
                  >
                    Limpar filtros
                  </button>
                )}
              </div>
            </header>

            {/* ============= SEARCH BAR (above the board) ============= */}
            <div className="searchbar-row">
              <div className={`searchbar-big ${busca ? "is-active" : ""}`}>
                <svg
                  className="search-icon"
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  aria-hidden="true"
                >
                  <circle
                    cx="7"
                    cy="7"
                    r="4.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                  <line
                    x1="10.5"
                    y1="10.5"
                    x2="14"
                    y2="14"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                </svg>
                <input
                  ref={buscaRef}
                  type="text"
                  placeholder="Buscar por fornecedor, Nº NF ou valor…"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                />
                {!busca && (
                  <span className="searchbar-hint">
                    <kbd>/</kbd>
                  </span>
                )}
                {busca && (
                  <button
                    className="search-clear"
                    onClick={() => setBusca("")}
                    title="Limpar (Esc)"
                  >
                    ×
                  </button>
                )}
              </div>
              {busca && (
                <span className="searchbar-result mono">
                  {filteredNotas.length} resultado
                  {filteredNotas.length !== 1 ? "s" : ""}
                </span>
              )}
              {!isCurrentMonth && (
                <button
                  className="month-readonly-pill"
                  onClick={goCurrentMonth}
                >
                  <span className="month-pill-dot" aria-hidden="true"></span>
                  Visão {isPastMonth ? "histórica" : "futura"} · clique pra
                  voltar pra hoje
                </button>
              )}
            </div>

            {/* ============= BOARD ============= */}
            <main className="board">
              {/* ATRASADAS */}
              <Column
                id="atrasadas"
                title="Atrasadas"
                count={buckets.atrasadas.length}
                tone="late"
                isDropTarget={dropTarget === "atrasadas"}
                onDragOver={(e) => onDragOverCol(e, "atrasadas")}
                onDrop={(e) => onDropCol(e, "atrasadas")}
                onDragLeave={() => setDropTarget(null)}
              >
                {buckets.atrasadas.length === 0 ? (
                  <EmptyState tone="late" />
                ) : (
                  buckets.atrasadas.map((n) => (
                    <CardWrap
                      key={n.id}
                      id={n.id}
                      setHovered={setHoveredCardId}
                    >
                      <NotaCard
                        nota={n}
                        today={TODAY}
                        status="atrasada"
                        onMarkReceived={handleOpenRegister}
                        onOpenDetail={setDetail}
                        isDragging={draggingId === n.id}
                        onDragStart={onDragStart}
                        onDragEnd={onDragEnd}
                      />
                    </CardWrap>
                  ))
                )}
              </Column>

              {/* AGUARDANDO */}
              <Column
                id="aguardando"
                title="Aguardando"
                count={buckets.aguardando.length}
                tone="aw"
                isDropTarget={dropTarget === "aguardando"}
                onDragOver={(e) => onDragOverCol(e, "aguardando")}
                onDrop={(e) => onDropCol(e, "aguardando")}
                onDragLeave={() => setDropTarget(null)}
              >
                {buckets.aguardando.length === 0 ? (
                  <EmptyState tone="aw" />
                ) : (
                  <>
                    {agSubgroups.hoje.length > 0 && (
                      <Subgroup
                        label="Hoje"
                        count={agSubgroups.hoje.length}
                        accent
                      >
                        {agSubgroups.hoje.map((n) => (
                          <CardWrap
                            key={n.id}
                            id={n.id}
                            setHovered={setHoveredCardId}
                          >
                            <NotaCard
                              nota={n}
                              today={TODAY}
                              status="aguardando"
                              onMarkReceived={handleOpenRegister}
                              onOpenDetail={setDetail}
                              isDragging={draggingId === n.id}
                              onDragStart={onDragStart}
                              onDragEnd={onDragEnd}
                            />
                          </CardWrap>
                        ))}
                      </Subgroup>
                    )}
                    {agSubgroups.esta.length > 0 && (
                      <Subgroup
                        label="Esta semana"
                        count={agSubgroups.esta.length}
                      >
                        {agSubgroups.esta.map((n) => (
                          <CardWrap
                            key={n.id}
                            id={n.id}
                            setHovered={setHoveredCardId}
                          >
                            <NotaCard
                              nota={n}
                              today={TODAY}
                              status="aguardando"
                              onMarkReceived={handleOpenRegister}
                              onOpenDetail={setDetail}
                              isDragging={draggingId === n.id}
                              onDragStart={onDragStart}
                              onDragEnd={onDragEnd}
                            />
                          </CardWrap>
                        ))}
                      </Subgroup>
                    )}
                    {agSubgroups.proxima.length > 0 && (
                      <Subgroup
                        label="Próxima semana"
                        count={agSubgroups.proxima.length}
                      >
                        {agSubgroups.proxima.map((n) => (
                          <CardWrap
                            key={n.id}
                            id={n.id}
                            setHovered={setHoveredCardId}
                          >
                            <NotaCard
                              nota={n}
                              today={TODAY}
                              status="aguardando"
                              onMarkReceived={handleOpenRegister}
                              onOpenDetail={setDetail}
                              isDragging={draggingId === n.id}
                              onDragStart={onDragStart}
                              onDragEnd={onDragEnd}
                            />
                          </CardWrap>
                        ))}
                      </Subgroup>
                    )}
                    {agSubgroups.depois.length > 0 && (
                      <Subgroup
                        label="Mais tarde no mês"
                        count={agSubgroups.depois.length}
                      >
                        {agSubgroups.depois.map((n) => (
                          <CardWrap
                            key={n.id}
                            id={n.id}
                            setHovered={setHoveredCardId}
                          >
                            <NotaCard
                              nota={n}
                              today={TODAY}
                              status="aguardando"
                              onMarkReceived={handleOpenRegister}
                              onOpenDetail={setDetail}
                              isDragging={draggingId === n.id}
                              onDragStart={onDragStart}
                              onDragEnd={onDragEnd}
                            />
                          </CardWrap>
                        ))}
                      </Subgroup>
                    )}
                  </>
                )}
              </Column>

              {/* RECEBIDAS */}
              <Column
                id="recebidas"
                title="Recebidas"
                count={buckets.recebidas.length}
                tone="rec"
                isDropTarget={dropTarget === "recebidas"}
                onDragOver={(e) => onDragOverCol(e, "recebidas")}
                onDrop={(e) => onDropCol(e, "recebidas")}
                onDragLeave={() => setDropTarget(null)}
                droppable
              >
                {(() => {
                  if (buckets.recebidas.length === 0)
                    return <EmptyState tone="rec" />;
                  const last7 = [];
                  const older = [];
                  for (const n of buckets.recebidas) {
                    const days = (TODAY - n.recebidaEm) / 86400000;
                    if (days <= 7) last7.push(n);
                    else older.push(n);
                  }
                  return (
                    <>
                      {last7.length > 0 && (
                        <Subgroup label="Últimos 7 dias" count={last7.length}>
                          {last7.map((n) => (
                            <CardWrap
                              key={n.id}
                              id={n.id}
                              setHovered={setHoveredCardId}
                            >
                              <NotaCard
                                nota={n}
                                today={TODAY}
                                status="recebida"
                                onMarkReceived={() => {}}
                                onOpenDetail={setDetail}
                                isDragging={false}
                                onDragStart={() => {}}
                                onDragEnd={() => {}}
                              />
                            </CardWrap>
                          ))}
                        </Subgroup>
                      )}
                      {older.length > 0 && (
                        <>
                          {recebidasExpanded && (
                            <Subgroup label="Anteriores" count={older.length}>
                              {older.map((n) => (
                                <CardWrap
                                  key={n.id}
                                  id={n.id}
                                  setHovered={setHoveredCardId}
                                >
                                  <NotaCard
                                    nota={n}
                                    today={TODAY}
                                    status="recebida"
                                    onMarkReceived={() => {}}
                                    onOpenDetail={setDetail}
                                    isDragging={false}
                                    onDragStart={() => {}}
                                    onDragEnd={() => {}}
                                  />
                                </CardWrap>
                              ))}
                            </Subgroup>
                          )}
                          <button
                            className="expand-btn"
                            onClick={() => setRecebidasExpanded((v) => !v)}
                          >
                            {recebidasExpanded
                              ? "▴ Ocultar anteriores"
                              : `▾ Ver mais ${older.length} recebida${older.length > 1 ? "s" : ""}`}
                          </button>
                        </>
                      )}
                    </>
                  );
                })()}
              </Column>

              {/* AVULSAS */}
              <Column
                id="avulsas"
                title="Avulsas"
                count={buckets.avulsas.length}
                tone="avu"
                isDropTarget={false}
              >
                <button
                  className="add-avulsa"
                  onClick={handleOpenAvulsa}
                  disabled={!isCurrentMonth}
                >
                  <span className="plus" aria-hidden="true">
                    +
                  </span>
                  <span>Adicionar nota avulsa</span>
                </button>
                {buckets.avulsas.length === 0 ? (
                  <p className="empty-soft">Sem notas avulsas no mês.</p>
                ) : (
                  buckets.avulsas.map((n) => (
                    <CardWrap
                      key={n.id}
                      id={n.id}
                      setHovered={setHoveredCardId}
                    >
                      <NotaCard
                        nota={n}
                        today={TODAY}
                        status="avulsa"
                        onMarkReceived={() => {}}
                        onOpenDetail={setDetail}
                        isDragging={false}
                        onDragStart={() => {}}
                        onDragEnd={() => {}}
                      />
                    </CardWrap>
                  ))
                )}
              </Column>
            </main>

            <footer className="app-foot">
              <span className="kbd-bar">
                <kbd>/</kbd> buscar
                <kbd>1</kbd>–<kbd>4</kbd> filtrar unidade
                <kbd>0</kbd> limpar
                <kbd>R</kbd> registrar nota sob o cursor
                <kbd>K</kbd> kanban · <kbd>F</kbd> fornecedores · <kbd>P</kbd>{" "}
                panorama
                <kbd>Esc</kbd> sair / cancelar
              </span>
              <span className="brand mono">
                Ciamed · Controle de Notas Fiscais
              </span>
            </footer>
          </>
        )}
      </div>

      {/* ============= MODALS ============= */}
      {registerNota && (
        <RegisterModal
          nota={registerNota}
          today={TODAY}
          onConfirm={(updated) => markReceived(registerNota, updated)}
          onCancel={() => setRegisterNota(null)}
        />
      )}
      {showAvulsa && (
        <AvulsaModal
          today={TODAY}
          onConfirm={addAvulsa}
          onCancel={() => setShowAvulsa(false)}
        />
      )}
      {detail && (
        <DetailDrawer
          nota={detail}
          today={TODAY}
          onClose={() => setDetail(null)}
          onUpdate={() => {}}
          onUnreceive={unreceive}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
};

// ============================================================
// TopBar — global tab bar (always visible)
// ============================================================
const TopBar = ({ view, setView, stats }) => {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-brand">
          <div className="topbar-logo" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 22 22">
              <rect
                x="1.5"
                y="3"
                width="14"
                height="17"
                rx="1.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.4"
              />
              <rect
                x="5"
                y="1"
                width="14"
                height="17"
                rx="1.5"
                fill="var(--paper)"
                stroke="currentColor"
                strokeWidth="1.4"
              />
              <line
                x1="8"
                y1="6"
                x2="16"
                y2="6"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <line
                x1="8"
                y1="9"
                x2="16"
                y2="9"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <line
                x1="8"
                y1="12"
                x2="13"
                y2="12"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div className="topbar-brand-text">
            <div className="topbar-brand-name">Ciamed</div>
            <div className="topbar-brand-sub">Controle de notas fiscais</div>
          </div>
        </div>

        <nav className="topbar-tabs" role="tablist">
          <button
            role="tab"
            className={`topbar-tab ${view === "kanban" ? "on" : ""}`}
            onClick={() => setView("kanban")}
            aria-selected={view === "kanban"}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
              <rect
                x="1"
                y="2"
                width="3.5"
                height="10"
                rx="0.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.2"
              />
              <rect
                x="5.25"
                y="2"
                width="3.5"
                height="6"
                rx="0.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.2"
              />
              <rect
                x="9.5"
                y="2"
                width="3.5"
                height="8"
                rx="0.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.2"
              />
            </svg>
            <span>Kanban do mês</span>
            {stats && stats.atrasadas > 0 && (
              <span className="topbar-tab-badge">{stats.atrasadas}</span>
            )}
            <span className="topbar-tab-kbd">
              <kbd>K</kbd>
            </span>
          </button>

          <button
            role="tab"
            className={`topbar-tab ${view === "fornecedores" ? "on" : ""}`}
            onClick={() => setView("fornecedores")}
            aria-selected={view === "fornecedores"}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
              <rect
                x="1.5"
                y="2"
                width="11"
                height="10"
                rx="1"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.2"
              />
              <line
                x1="4"
                y1="5"
                x2="10"
                y2="5"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <line
                x1="4"
                y1="7.5"
                x2="10"
                y2="7.5"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <line
                x1="4"
                y1="10"
                x2="7.5"
                y2="10"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </svg>
            <span>Fornecedores</span>
            <span className="topbar-tab-kbd">
              <kbd>F</kbd>
            </span>
          </button>

          <button
            role="tab"
            className={`topbar-tab ${view === "panorama" ? "on" : ""}`}
            onClick={() => setView("panorama")}
            aria-selected={view === "panorama"}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
              <rect x="1.5" y="1.5" width="3" height="3" fill="currentColor" />
              <rect
                x="5.5"
                y="1.5"
                width="3"
                height="3"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.1"
              />
              <rect x="9.5" y="1.5" width="3" height="3" fill="currentColor" />
              <rect
                x="1.5"
                y="5.5"
                width="3"
                height="3"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.1"
              />
              <rect x="5.5" y="5.5" width="3" height="3" fill="currentColor" />
              <rect
                x="9.5"
                y="5.5"
                width="3"
                height="3"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.1"
              />
              <rect x="1.5" y="9.5" width="3" height="3" fill="currentColor" />
              <rect
                x="5.5"
                y="9.5"
                width="3"
                height="3"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.1"
              />
              <rect
                x="9.5"
                y="9.5"
                width="3"
                height="3"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.1"
              />
            </svg>
            <span>Panorama</span>
            <span className="topbar-tab-kbd">
              <kbd>P</kbd>
            </span>
          </button>
        </nav>

        <div className="topbar-meta mono">
          {new Date().toLocaleDateString("pt-BR", {
            day: "2-digit",
            month: "short",
            year: "numeric",
          })}
        </div>
      </div>
    </header>
  );
};

// ============================================================
// Column shell
// ============================================================
const Column = ({
  id,
  title,
  count,
  tone,
  droppable,
  isDropTarget,
  onDragOver,
  onDrop,
  onDragLeave,
  children,
}) => (
  <section
    className={`col col-${tone} ${isDropTarget ? "is-drop" : ""}`}
    onDragOver={onDragOver}
    onDrop={onDrop}
    onDragLeave={onDragLeave}
    data-screen-label={`${id}`}
  >
    <header className="col-header">
      <div className="col-title-row">
        <span className={`col-marker col-marker-${tone}`}></span>
        <h3 className="col-title">{title}</h3>
        <span className="col-count mono">{count}</span>
        {droppable && (
          <span className="col-drop-hint">arraste aqui pra registrar</span>
        )}
      </div>
    </header>
    <div className="col-body">{children}</div>
  </section>
);

const Subgroup = ({ label, count, accent, children }) => (
  <div className={`subgrp ${accent ? "subgrp-accent" : ""}`}>
    <div className="subgrp-head">
      <span className="subgrp-label">{label}</span>
      <span className="subgrp-count mono">{count}</span>
    </div>
    <div className="subgrp-body">{children}</div>
  </div>
);

const CardWrap = ({ id, setHovered, children }) => (
  <div
    onMouseEnter={() => setHovered(id)}
    onMouseLeave={() => setHovered((prev) => (prev === id ? null : prev))}
  >
    {children}
  </div>
);

const EmptyState = ({ tone }) => {
  const map = {
    late: { ico: "✓", t: "Nenhuma nota atrasada", s: "Tudo em dia por aqui." },
    aw: {
      ico: "·",
      t: "Sem notas aguardando",
      s: "Filtros ativos podem estar escondendo.",
    },
    rec: {
      ico: "·",
      t: "Nada recebido ainda",
      s: "Marque a primeira nota com o atalho R.",
    },
  };
  const e = map[tone] || map.aw;
  return (
    <div className={`empty empty-${tone}`}>
      <div className="empty-ico" aria-hidden="true">
        {e.ico}
      </div>
      <div className="empty-t">{e.t}</div>
      <div className="empty-s">{e.s}</div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
