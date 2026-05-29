/* global React, CategoryIcon, UnitBadge, statusOf, daysLate, formatBRL, dayLabel */
// Panorama view — annual heatmap, fornecedor × mês

const { useState: puseState, useMemo: puseMemo, useRef: puseRef, useEffect: puseEffect } = React;

const MES_ABRV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const MES_NOMES_P = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];

// ============================================================
// Cell color mapping:
//   ok      → green checkmark
//   late    → orange dot
//   miss    → red bang
//   aguar   → yellow dot (current month, pending)
//   atras   → red bang (current month, late)
//   future  → empty
//   na      → empty
// ============================================================
const cellStatusForCurrentMonth = (notas, exp, today) => {
  // Find the nota for this expectativa in the current month
  const match = notas.find(n => !n.avulsa &&
    n.fornecedor === exp.fornecedor &&
    n.unidade === exp.unidade &&
    n.diaEsperado === exp.diaEsperado);
  if (!match) return exp.ativo ? "future" : "na";
  const s = statusOf(match, today);
  if (s === "recebida") return "ok";
  if (s === "aguardando") return "aguar";
  if (s === "atrasada") return "atras";
  return "future";
};

const PanoramaView = ({ expectativas, notas, today, viewMonth, onJumpToMonth }) => {
  const { UNIDADES, CATEGORIAS, MONTH: BASE_M, YEAR: BASE_Y } = window.CIAMED;

  const [year, setYear] = puseState(BASE_Y);
  const [filtroUnidade, setFiltroUnidade] = puseState("todas");
  const [filtroCategoria, setFiltroCategoria] = puseState("todas");
  const [highlight, setHighlight] = puseState({ row: null, col: null });
  const [hoveredCell, setHoveredCell] = puseState(null); // {expId, m, status}

  // histórico vindo da API: { fornecedor_id: { mes: status } }
  const [historico, setHistorico] = puseState({});
  puseEffect(() => {
    let cancelled = false;
    fetch(`/notas/api/panorama?ano=${year}`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data) => {
        if (cancelled) return;
        const map = {};
        data.forEach((row) => { map[row.fornecedor_id] = row.mensal; });
        setHistorico(map);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Erro ao carregar panorama:", err);
        setHistorico({});
      });
    return () => { cancelled = true; };
  }, [year]);

  // historicalStatus agora lê do estado (dados reais do PostgreSQL)
  const historicalStatus = (expId, _year, monthIdx0) => {
    const mensal = historico[expId];
    if (!mensal) return "na";
    return mensal[monthIdx0 + 1] || "na"; // backend usa mês 1-12
  };

  const currentMonthIdx = year === BASE_Y ? BASE_M : -1;
  const isFutureYear = year > BASE_Y;

  const filteredExp = puseMemo(() => {
    return expectativas.filter(e => {
      if (filtroUnidade !== "todas" && e.unidade !== filtroUnidade) return false;
      if (filtroCategoria !== "todas" && e.categoria !== filtroCategoria) return false;
      return true;
    }).sort((a, b) => a.fornecedor.localeCompare(b.fornecedor) || a.diaEsperado - b.diaEsperado);
  }, [expectativas, filtroUnidade, filtroCategoria]);

  // For each cell compute status
  const matrix = puseMemo(() => {
    const out = filteredExp.map(exp => {
      const cells = [];
      for (let m = 0; m < 12; m++) {
        let status;
        if (year > BASE_Y || (year === BASE_Y && m > BASE_M)) {
          status = exp.ativo ? "future" : "na";
        } else if (year === BASE_Y && m === BASE_M) {
          status = cellStatusForCurrentMonth(notas, exp, today);
        } else {
          status = exp.ativo ? historicalStatus(exp.id, year, m) : "na";
        }
        cells.push({ status, m, expId: exp.id });
      }
      return { exp, cells };
    });
    return out;
  }, [filteredExp, year, notas, today, BASE_M, BASE_Y, historico]);

  // Row pontualidade (across the visible year up to current/end)
  const rowPont = (row) => {
    const lastIdx = year === BASE_Y ? BASE_M : (year < BASE_Y ? 11 : -1);
    if (lastIdx < 0) return null;
    let ok = 0, total = 0;
    for (let m = 0; m <= lastIdx; m++) {
      const s = row.cells[m].status;
      if (s === "ok" || s === "atras" || s === "miss" || s === "late") {
        total++;
        if (s === "ok") ok++;
      }
    }
    return total > 0 ? ok / total : null;
  };

  // Month totals (column footer)
  const monthTotals = puseMemo(() => {
    const totals = [];
    for (let m = 0; m < 12; m++) {
      let ok = 0, late = 0, miss = 0, aguar = 0, atras = 0, total = 0;
      for (const row of matrix) {
        const s = row.cells[m].status;
        if (s === "future" || s === "na") continue;
        total++;
        if (s === "ok") ok++;
        else if (s === "late") late++;
        else if (s === "miss") miss++;
        else if (s === "aguar") aguar++;
        else if (s === "atras") atras++;
      }
      totals.push({ m, ok, late, miss, aguar, atras, total });
    }
    return totals;
  }, [matrix]);

  // overall stats
  const stats = puseMemo(() => {
    let ok = 0, miss = 0, late = 0, total = 0;
    for (const row of matrix) {
      for (const c of row.cells) {
        const s = c.status;
        if (s === "future" || s === "na") continue;
        total++;
        if (s === "ok") ok++;
        else if (s === "miss" || s === "atras") miss++;
        else if (s === "late") late++;
      }
    }
    return { ok, miss, late, total, okPct: total > 0 ? Math.round((ok / total) * 100) : 0 };
  }, [matrix]);

  const onCellClick = (row, c) => {
    if (c.status === "future" || c.status === "na") return;
    if (onJumpToMonth) onJumpToMonth({ year, month: c.m });
  };

  return (
    <div className="pano-view">
      <header className="pano-header">
        <div className="pano-title-row">
          <div>
            <div className="page-eyebrow">Visão histórica · auditoria</div>
            <h2 className="page-title">Panorama</h2>
            <p className="page-lede">
              Cada quadradinho é uma nota esperada em um mês. <span className="mono">✓</span> chegou,
              <span className="cell-mini cell-mini-late">!</span> atrasou,
              <span className="cell-mini cell-mini-miss">·</span> furou.
              Clique em qualquer célula passada pra abrir aquele mês no Kanban.
            </p>
          </div>

          <div className="pano-year-nav">
            <button className="nav-btn" onClick={() => setYear(y => y - 1)} title="Ano anterior">‹</button>
            <span className="pano-year mono">{year}</span>
            <button className="nav-btn" onClick={() => setYear(y => y + 1)} title="Próximo ano">›</button>
          </div>
        </div>

        <div className="pano-stats">
          <div className="pano-bigstat">
            <span className="pano-bigstat-n mono">{stats.okPct}%</span>
            <span className="pano-bigstat-l">de notas em dia em {year}</span>
          </div>
          <span className="stat-divider"></span>
          <FStat2 n={stats.ok} l="recebidas em dia" tone="ok" />
          <FStat2 n={stats.late} l="recebidas com atraso" tone="warn" />
          <FStat2 n={stats.miss} l={`${isFutureYear ? "não esperado" : "furos / atrasos abertos"}`} tone="late" />
          <FStat2 n={stats.total} l="expectativas no ano" />
        </div>

        <div className="pano-filters">
          <div className="chips">
            {[{ id: "todas", nome: "Todas" }, ...UNIDADES].map(u => (
              <button key={u.id} className={`chip ${filtroUnidade === u.id ? "on" : ""}`} onClick={() => setFiltroUnidade(u.id)}>
                {u.id !== "todas" && <UnitBadge unidade={u.id} size="xs" />}
                {u.id === "todas" ? "Todas" : u.nome}
              </button>
            ))}
          </div>
          <select className="cat-select" value={filtroCategoria} onChange={(e) => setFiltroCategoria(e.target.value)}>
            <option value="todas">Todas categorias</option>
            {CATEGORIAS.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>

          <div className="pano-legend">
            <span className="leg-item"><span className="leg-sq sq-ok">✓</span> em dia</span>
            <span className="leg-item"><span className="leg-sq sq-late">!</span> atrasou</span>
            <span className="leg-item"><span className="leg-sq sq-miss">·</span> furou</span>
            <span className="leg-item"><span className="leg-sq sq-aguar">○</span> aguardando</span>
            <span className="leg-item"><span className="leg-sq sq-atras">!</span> atrasada (aberta)</span>
          </div>
        </div>
      </header>

      <div className="pano-grid-wrap">
        <div className="pano-grid" role="grid" onMouseLeave={() => setHighlight({ row: null, col: null })}>

          {/* corner */}
          <div className="pano-corner"></div>

          {/* month headers */}
          {MES_ABRV.map((m, i) => (
            <div
              key={m}
              className={`pano-mh ${highlight.col === i ? "on" : ""} ${i === currentMonthIdx ? "is-current" : ""}`}
              onMouseEnter={() => setHighlight(h => ({ ...h, col: i }))}
            >
              <span className="pano-mh-abrv">{m}</span>
              {i === currentMonthIdx && <span className="pano-mh-tag">atual</span>}
            </div>
          ))}

          {/* pontualidade header */}
          <div className="pano-pont-h">% em dia</div>

          {/* rows */}
          {matrix.map((row, rIdx) => {
            const exp = row.exp;
            const pont = rowPont(row);
            const pontPct = pont != null ? Math.round(pont * 100) : null;
            return (
              <React.Fragment key={exp.id}>
                <div
                  className={`pano-rh ${highlight.row === rIdx ? "on" : ""} ${!exp.ativo ? "is-paused" : ""}`}
                  onMouseEnter={() => setHighlight(h => ({ ...h, row: rIdx }))}
                >
                  <CategoryIcon id={exp.categoria} size={12} className="pano-rh-ico" />
                  <span className="pano-rh-name" title={exp.fornecedor}>{exp.fornecedor}</span>
                  <UnitBadge unidade={exp.unidade} size="xs" />
                  <span className="pano-rh-day mono">·d{dayLabel(exp.diaEsperado)}</span>
                </div>

                {row.cells.map((c) => (
                  <button
                    key={c.m}
                    className={`pano-cell pano-cell-${c.status} ${highlight.row === rIdx ? "row-hi" : ""} ${highlight.col === c.m ? "col-hi" : ""} ${c.m === currentMonthIdx ? "is-current" : ""}`}
                    onMouseEnter={() => {
                      setHighlight({ row: rIdx, col: c.m });
                      setHoveredCell({ exp, m: c.m, status: c.status });
                    }}
                    onMouseLeave={() => setHoveredCell(null)}
                    onClick={() => onCellClick(row, c)}
                    disabled={c.status === "future" || c.status === "na"}
                    aria-label={`${exp.fornecedor} ${MES_ABRV[c.m]} ${year}: ${c.status}`}
                  >
                    <span className="cell-glyph">
                      {c.status === "ok" ? "✓"
                        : c.status === "late" ? "!"
                        : c.status === "miss" ? "·"
                        : c.status === "atras" ? "!"
                        : c.status === "aguar" ? "○"
                        : ""}
                    </span>
                    {exp.retencaoPadrao && (c.status === "ok" || c.status === "atras" || c.status === "aguar") && (
                      <span className="cell-ret-strip" aria-hidden="true"></span>
                    )}
                  </button>
                ))}

                <div className={`pano-pont ${highlight.row === rIdx ? "on" : ""}`}>
                  {pontPct != null ? (
                    <span className={`pont-bar pont-${pontPct >= 95 ? "ok" : pontPct >= 80 ? "med" : "low"}`}>
                      <span className="pont-bar-fill" style={{ width: pontPct + "%" }}></span>
                      <span className="pont-bar-num mono">{pontPct}%</span>
                    </span>
                  ) : <span className="muted mono">—</span>}
                </div>
              </React.Fragment>
            );
          })}

          {/* footer: totals */}
          <div className="pano-foot-h">Total no mês</div>
          {monthTotals.map(t => (
            <div key={t.m} className={`pano-foot ${highlight.col === t.m ? "on" : ""} ${t.m === currentMonthIdx ? "is-current" : ""}`}>
              {t.total > 0 ? (
                <>
                  <span className="pano-foot-n mono">{t.ok + t.late + (t.aguar)}/{t.total}</span>
                  {(t.miss > 0 || t.atras > 0) && (
                    <span className="pano-foot-miss mono">!{t.miss + t.atras}</span>
                  )}
                </>
              ) : (
                <span className="muted">—</span>
              )}
            </div>
          ))}
          <div className="pano-foot pano-foot-tot">
            <span className="pano-foot-n mono">{stats.okPct}%</span>
          </div>
        </div>

        {hoveredCell && (
          <PanoramaTooltip cell={hoveredCell} year={year} currentMonthIdx={currentMonthIdx} />
        )}
      </div>

      {matrix.length === 0 && (
        <div className="empty empty-big" style={{ padding: "60px 12px" }}>
          <div className="empty-ico" aria-hidden="true">·</div>
          <div className="empty-t">Sem expectativas pra mostrar</div>
          <div className="empty-s">Ajuste os filtros, ou cadastre fornecedores recorrentes primeiro.</div>
        </div>
      )}
    </div>
  );
};

const FStat2 = ({ n, l, tone }) => (
  <div className={`fstat fstat-${tone || "default"}`}>
    <span className="fstat-n mono">{n}</span>
    <span className="fstat-l">{l}</span>
  </div>
);

// ============================================================
// Tooltip — appears next to hovered cell
// ============================================================
const PanoramaTooltip = ({ cell, year, currentMonthIdx }) => {
  const labels = {
    ok: { title: "Em dia", body: "Nota recebida no mês esperado." },
    late: { title: "Recebida com atraso", body: "Chegou, mas depois do dia previsto." },
    miss: { title: "Furo", body: "Nota não recebida nesse mês — verificar." },
    atras: { title: "Atrasada (aberta)", body: "Era pra ter chegado e ainda não chegou." },
    aguar: { title: "Aguardando", body: "Ainda dentro do prazo do mês corrente." },
    future: { title: "Mês futuro", body: "Ainda não chegou a data esperada." },
    na: { title: "Não esperada", body: "Expectativa pausada ou não ativa nesse período." },
  };
  const info = labels[cell.status] || labels.na;
  return (
    <div className="pano-tip">
      <div className="pano-tip-head">
        <CategoryIcon id={cell.exp.categoria} size={13} />
        <span>{cell.exp.fornecedor}</span>
        <UnitBadge unidade={cell.exp.unidade} size="xs" />
      </div>
      <div className="pano-tip-month mono">{MES_NOMES_P[cell.m]} · {year}</div>
      <div className={`pano-tip-status status-${cell.status}`}>
        <span className="pano-tip-bullet" aria-hidden="true"></span>
        <strong>{info.title}</strong>
      </div>
      <div className="pano-tip-body">{info.body}</div>
      {cell.status !== "future" && cell.status !== "na" && (
        <div className="pano-tip-hint">Clique pra abrir esse mês no Kanban</div>
      )}
    </div>
  );
};

Object.assign(window, { PanoramaView });
