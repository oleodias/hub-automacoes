/* global React, ReactDOM, CategoryIcon, UnitBadge, RetentionMark, formatBRL, dayLabel, NkOverlay */
// Fornecedores view — Controle de Notas Ciamed

const { useState: fuseState, useMemo: fuseMemo, useRef: fuseRef, useEffect: fuseEffect } = React;

// Fallback caso components.jsx ainda não tenha carregado.
const FOverlay = (typeof window !== "undefined" && window.NkOverlay)
  ? window.NkOverlay
  : ({ children }) => (ReactDOM && ReactDOM.createPortal)
      ? ReactDOM.createPortal(children, document.body)
      : children;

// ============================================================
// FornecedoresView
// ============================================================
const FornecedoresView = ({ expectativas, reloadExpectativas, today, onJumpToKanban }) => {
  const { UNIDADES, CATEGORIAS, pontualidade } = window.CIAMED;

  const [busca, setBusca] = fuseState("");
  const [filtroUnidade, setFiltroUnidade] = fuseState("todas");
  const [filtroCategoria, setFiltroCategoria] = fuseState("todas");
  const [filtroStatus, setFiltroStatus] = fuseState("todos"); // 'todos' | 'ativo' | 'pausado'
  const [agrupado, setAgrupado] = fuseState(true);
  const [editing, setEditing] = fuseState(null); // expectativa object or 'new'
  const [confirmDelete, setConfirmDelete] = fuseState(null);
  const [savingId, setSavingId] = fuseState(null); // feedback visual durante chamadas à API
  const buscaRef = fuseRef(null);

  const filtered = fuseMemo(() => {
    const q = busca.trim().toLowerCase();
    return expectativas.filter(e => {
      if (filtroUnidade !== "todas" && e.unidade !== filtroUnidade) return false;
      if (filtroCategoria !== "todas" && e.categoria !== filtroCategoria) return false;
      if (filtroStatus === "ativo" && !e.ativo) return false;
      if (filtroStatus === "pausado" && e.ativo) return false;
      if (q) {
        const hay = `${e.fornecedor} ${e.cnpj || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [expectativas, busca, filtroUnidade, filtroCategoria, filtroStatus]);

  const grouped = fuseMemo(() => {
    if (!agrupado) return null;
    const m = new Map();
    for (const e of filtered) {
      if (!m.has(e.fornecedor)) m.set(e.fornecedor, []);
      m.get(e.fornecedor).push(e);
    }
    return [...m.entries()].map(([nome, items]) => ({ nome, items })).sort((a, b) => a.nome.localeCompare(b.nome));
  }, [filtered, agrupado]);

  // stats
  const stats = fuseMemo(() => {
    const ativos = expectativas.filter(e => e.ativo).length;
    const pausados = expectativas.filter(e => !e.ativo).length;
    const semCnpj = expectativas.filter(e => !e.cnpj).length;
    const comRet = expectativas.filter(e => e.retencaoPadrao).length;
    const fornecedoresUnicos = new Set(expectativas.map(e => e.fornecedor)).size;
    return { ativos, pausados, semCnpj, comRet, fornecedoresUnicos, total: expectativas.length };
  }, [expectativas]);

  const togglePause = async (exp) => {
    setSavingId(exp.id);
    try {
      const r = await fetch(`/notas/api/fornecedores/${exp.id}/toggle`, { method: "PATCH" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      await reloadExpectativas();
    } catch (err) {
      console.error(err);
      alert("Erro ao pausar/reativar: " + err.message);
    } finally {
      setSavingId(null);
    }
  };

  // mapToApi: converte o shape do nk-modal (camelCase) pro shape que o backend espera
  const mapToApi = (data) => ({
    fornecedor: data.fornecedor,
    cnpj: data.cnpj,
    categoria_id: data.categoria,
    unidade_id: data.unidade,
    dia_esperado: data.diaEsperado,
    valor_medio: data.valorMedio,
    retencao_padrao: data.retencaoPadrao,
    observacoes: data.observacoes,
  });

  const saveExpectativa = async (data) => {
    try {
      const isNew = (editing === "new");
      const url = isNew
        ? "/notas/api/fornecedores"
        : `/notas/api/fornecedores/${editing.id}`;
      const method = isNew ? "POST" : "PUT";

      const r = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mapToApi(data)),
      });
      const resp = await r.json();
      if (!r.ok) throw new Error(resp.erro || `HTTP ${r.status}`);

      setEditing(null);
      await reloadExpectativas();
    } catch (err) {
      console.error(err);
      alert("Erro ao salvar: " + err.message);
    }
  };

  const removeExpectativa = async (exp) => {
    try {
      const r = await fetch(`/notas/api/fornecedores/${exp.id}`, { method: "DELETE" });
      if (!r.ok) {
        const resp = await r.json().catch(() => ({}));
        throw new Error(resp.erro || `HTTP ${r.status}`);
      }
      setConfirmDelete(null);
      await reloadExpectativas();
    } catch (err) {
      console.error(err);
      alert("Erro ao remover: " + err.message);
    }
  };

  // Empty state
  const hasFilters = busca || filtroUnidade !== "todas" || filtroCategoria !== "todas" || filtroStatus !== "todos";

  return (
    <div className="forn-view">
      {/* ============= HEADER ============= */}
      <header className="forn-header">
        <div className="forn-title-row">
          <div>
            <div className="page-eyebrow">Cadastro · expectativas recorrentes</div>
            <h2 className="page-title">Fornecedores</h2>
            <p className="page-lede">
              Cada linha define <em>uma nota esperada por mês</em>. Mesmo fornecedor que emite pra Matriz e
              pra Filial 3 vira duas entradas — porque são duas notas a receber.
            </p>
          </div>
          <button className="btn btn-primary btn-tall" onClick={() => setEditing("new")}>
            <span style={{ fontFamily: "ui-monospace", fontWeight: 700, marginRight: 6 }}>+</span>
            Novo fornecedor
          </button>
        </div>

        <div className="forn-stats">
          <FStat n={stats.fornecedoresUnicos} l="fornecedores únicos" />
          <FStat n={stats.ativos} l="expectativas ativas" tone="ok" />
          {stats.pausados > 0 && <FStat n={stats.pausados} l="pausadas" tone="muted" />}
          <FStat n={stats.comRet} l="com retenção" tone="ret" />
          {stats.semCnpj > 0 && <FStat n={stats.semCnpj} l="sem CNPJ cadastrado" tone="warn" />}
        </div>

        {/* filters */}
        <div className="forn-filters">
          <div className="search-wrap searchbar-mid">
            <svg className="search-icon" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
              <circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" strokeWidth="1.4" />
              <line x1="9" y1="9" x2="12.5" y2="12.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
            <input ref={buscaRef} type="text" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar fornecedor ou CNPJ…" />
            {busca && <button className="search-clear" onClick={() => setBusca("")}>×</button>}
          </div>

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

          <div className="seg seg-sm">
            <button className={filtroStatus === "todos" ? "on" : ""} onClick={() => setFiltroStatus("todos")}>Todos</button>
            <button className={filtroStatus === "ativo" ? "on" : ""} onClick={() => setFiltroStatus("ativo")}>Ativos</button>
            <button className={filtroStatus === "pausado" ? "on" : ""} onClick={() => setFiltroStatus("pausado")}>Pausados</button>
          </div>

          <label className="toggle-group" title="Agrupar várias unidades do mesmo fornecedor">
            <input type="checkbox" checked={agrupado} onChange={(e) => setAgrupado(e.target.checked)} />
            <span>Agrupar por fornecedor</span>
          </label>
        </div>
      </header>

      {/* ============= TABLE ============= */}
      <div className="forn-table-wrap">
        {filtered.length === 0 ? (
          <div className="empty empty-big">
            <div className="empty-ico" aria-hidden="true">·</div>
            <div className="empty-t">Nenhum fornecedor encontrado</div>
            <div className="empty-s">
              {hasFilters
                ? "Tente limpar os filtros ou ajustar a busca."
                : "Adicione o primeiro fornecedor recorrente pra começar."}
            </div>
          </div>
        ) : (
          <div className="forn-table" role="table">
            <div className="forn-row forn-row-head" role="row">
              <span className="c c-name">Fornecedor</span>
              <span className="c c-cat">Categoria</span>
              <span className="c c-unit">Unidade</span>
              <span className="c c-dia">Dia</span>
              <span className="c c-valor">Valor médio</span>
              <span className="c c-ret">Retenção</span>
              <span className="c c-pont">Pontualidade 12m</span>
              <span className="c c-status">Status</span>
              <span className="c c-actions"></span>
            </div>

            {agrupado ? (
              grouped.map(g => (
                <React.Fragment key={g.nome}>
                  <div className="forn-grp-head">
                    <span className="forn-grp-name">{g.nome}</span>
                    <span className="forn-grp-count mono">{g.items.length} {g.items.length === 1 ? "expectativa" : "expectativas"}</span>
                  </div>
                  {g.items.map(e => (
                    <FRow key={e.id} exp={e} today={today} grouped
                      onEdit={() => setEditing(e)} onTogglePause={() => togglePause(e)}
                      onDelete={() => setConfirmDelete(e)} onJumpToKanban={onJumpToKanban} />
                  ))}
                </React.Fragment>
              ))
            ) : (
              filtered.map(e => (
                <FRow key={e.id} exp={e} today={today}
                  onEdit={() => setEditing(e)} onTogglePause={() => togglePause(e)}
                  onDelete={() => setConfirmDelete(e)} onJumpToKanban={onJumpToKanban} />
              ))
            )}
          </div>
        )}
      </div>

      {/* ============= MODALS ============= */}
      {editing && (
        <ExpectativaModal
          initial={editing === "new" ? null : editing}
          onConfirm={saveExpectativa}
          onCancel={() => setEditing(null)}
        />
      )}
      {confirmDelete && (
        <ConfirmModal
          title="Remover expectativa?"
          body={
            <>
              Você está prestes a remover a expectativa recorrente de{" "}
              <b>{confirmDelete.fornecedor}</b> ({UNIDADES.find(u => u.id === confirmDelete.unidade)?.nome}, dia {dayLabel(confirmDelete.diaEsperado)}).
              <br /><br />
              Notas já registradas <em>não são apagadas</em> — apenas paramos de esperar essa nota nos próximos meses.
            </>
          }
          confirmLabel="Remover"
          danger
          onConfirm={() => removeExpectativa(confirmDelete)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
};

const FStat = ({ n, l, tone }) => (
  <div className={`fstat fstat-${tone || "default"}`}>
    <span className="fstat-n mono">{n}</span>
    <span className="fstat-l">{l}</span>
  </div>
);

// ============================================================
// FRow — single fornecedor row
// ============================================================
const FRow = ({ exp, today, grouped, onEdit, onTogglePause, onDelete, onJumpToKanban }) => {
  const { UNIDADES, CATEGORIAS } = window.CIAMED;
  const cat = CATEGORIAS.find(c => c.id === exp.categoria);
  const unit = UNIDADES.find(u => u.id === exp.unidade);
  // pontualidade vem do backend (campo no objeto). null = ainda sem histórico.
  const pont = (exp.pontualidade != null) ? exp.pontualidade : 1;
  const pontPct = Math.round(pont * 100);
  const pontClass = pontPct >= 95 ? "ok" : pontPct >= 80 ? "med" : "low";

  return (
    <div className={`forn-row ${grouped ? "forn-row-grp" : ""} ${!exp.ativo ? "is-paused" : ""}`} role="row">
      <span className="c c-name">
        <CategoryIcon id={exp.categoria} size={14} className="forn-cat-ico" />
        <span className="forn-name">
          {grouped ? <span className="forn-name-grp">↳ </span> : null}
          {!grouped && exp.fornecedor}
          {grouped && cat?.nome}
        </span>
        {!grouped && <span className="forn-cnpj mono">{exp.cnpj || "—"}</span>}
      </span>
      <span className="c c-cat">{cat?.nome}</span>
      <span className="c c-unit"><UnitBadge unidade={exp.unidade} /></span>
      <span className="c c-dia">
        <span className="forn-dia-pill mono">dia {dayLabel(exp.diaEsperado)}</span>
      </span>
      <span className="c c-valor mono">
        {exp.valorMedio != null ? <>R$&nbsp;{formatBRL(exp.valorMedio)}</> : <span className="muted">—</span>}
      </span>
      <span className="c c-ret">
        {exp.retencaoPadrao
          ? <span className="card-ret-pill"><RetentionMark tip="" /> sim</span>
          : <span className="muted">—</span>}
      </span>
      <span className="c c-pont">
        <span className={`pont-bar pont-${pontClass}`}>
          <span className="pont-bar-fill" style={{ width: pontPct + "%" }}></span>
          <span className="pont-bar-num mono">{pontPct}%</span>
        </span>
      </span>
      <span className="c c-status">
        <span className={`status-pill ${exp.ativo ? "st-ativo" : "st-pausado"}`}>
          {exp.ativo ? "Ativo" : "Pausado"}
        </span>
      </span>
      <span className="c c-actions">
        <button className="icon-btn-sm" onClick={onEdit} title="Editar">
          <svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true">
            <path d="M9.5 1.5L12.5 4.5L4 13L1 13L1 10L9.5 1.5Z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
          </svg>
        </button>
        <button className="icon-btn-sm" onClick={onTogglePause} title={exp.ativo ? "Pausar" : "Reativar"}>
          {exp.ativo ? (
            <svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true">
              <rect x="3" y="2" width="2.5" height="10" fill="currentColor" />
              <rect x="8.5" y="2" width="2.5" height="10" fill="currentColor" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true">
              <path d="M3 2L11.5 7L3 12Z" fill="currentColor" />
            </svg>
          )}
        </button>
        <button className="icon-btn-sm danger" onClick={onDelete} title="Remover">
          <svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true">
            <path d="M3 4H11M5 4V2.5C5 2 5.5 1.5 6 1.5H8C8.5 1.5 9 2 9 2.5V4M4 4L4.5 12C4.5 12.5 5 13 5.5 13H8.5C9 13 9.5 12.5 9.5 12L10 4" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" />
          </svg>
        </button>
      </span>
    </div>
  );
};

// ============================================================
// ExpectativaModal — add / edit
// ============================================================
const ExpectativaModal = ({ initial, onConfirm, onCancel }) => {
  const { UNIDADES, CATEGORIAS } = window.CIAMED;
  const isNew = !initial;
  const [fornecedor, setFornecedor] = fuseState(initial?.fornecedor || "");
  const [cnpj, setCnpj] = fuseState(initial?.cnpj || "");
  const [categoria, setCategoria] = fuseState(initial?.categoria || "outros");
  const [unidade, setUnidade] = fuseState(initial?.unidade || "matriz");
  const [diaEsperado, setDiaEsperado] = fuseState(initial?.diaEsperado || 1);
  const [valorMedio, setValorMedio] = fuseState(initial?.valorMedio != null ? String(initial.valorMedio).replace(".", ",") : "");
  const [retencaoPadrao, setRetencaoPadrao] = fuseState(!!initial?.retencaoPadrao);
  const [observacoes, setObservacoes] = fuseState(initial?.observacoes || "");
  const fornRef = fuseRef(null);

  fuseEffect(() => {
    setTimeout(() => fornRef.current && fornRef.current.focus(), 60);
    const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); onCancel(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const submit = (e) => {
    e.preventDefault();
    if (!fornecedor.trim()) return;
    const v = valorMedio ? Number(valorMedio.replace(/\./g, "").replace(",", ".")) : null;
    onConfirm({
      fornecedor: fornecedor.trim(),
      cnpj: cnpj.trim(),
      categoria, unidade,
      diaEsperado: Math.max(1, Math.min(31, Number(diaEsperado) || 1)),
      valorMedio: isFinite(v) ? v : null,
      retencaoPadrao,
      observacoes,
    });
  };

  return (
    <FOverlay>
    <div className="nk-modal-backdrop" onClick={onCancel}>
      <form className="nk-modal nk-modal-avulsa" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <header className="nk-modal-header">
          <div className="nk-modal-eyebrow">{isNew ? "Novo fornecedor recorrente" : "Editar fornecedor"}</div>
          <div className="nk-modal-title-plain">
            {isNew ? "Nova expectativa de nota mensal" : initial.fornecedor}
          </div>
        </header>

        <div className="nk-modal-grid grid-2">
          <label className="field span-2">
            <span className="lbl">Fornecedor</span>
            <input ref={fornRef} type="text" placeholder="Nome do fornecedor" value={fornecedor} onChange={(e) => setFornecedor(e.target.value)} />
          </label>
          <label className="field span-2">
            <span className="lbl">CNPJ</span>
            <input type="text" placeholder="00.000.000/0000-00" value={cnpj} onChange={(e) => setCnpj(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Categoria</span>
            <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
              {CATEGORIAS.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="lbl">Unidade</span>
            <select value={unidade} onChange={(e) => setUnidade(e.target.value)}>
              {UNIDADES.map(u => <option key={u.id} value={u.id}>{u.nome}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="lbl">Dia esperado do mês</span>
            <input type="number" min="1" max="31" value={diaEsperado} onChange={(e) => setDiaEsperado(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Valor médio <em>(opcional)</em></span>
            <div className="input-prefix">
              <span className="prefix">R$</span>
              <input type="text" inputMode="decimal" placeholder="0,00" value={valorMedio} onChange={(e) => setValorMedio(e.target.value)} />
            </div>
          </label>
          <label className="field span-2">
            <span className="lbl">Retenção padrão</span>
            <div className="seg">
              <button type="button" className={!retencaoPadrao ? "on" : ""} onClick={() => setRetencaoPadrao(false)}>Não</button>
              <button type="button" className={retencaoPadrao ? "on ret" : ""} onClick={() => setRetencaoPadrao(true)}>Sim — toda nota desse fornecedor tem retenção</button>
            </div>
          </label>
          <label className="field span-2">
            <span className="lbl">Observações</span>
            <textarea rows="2" value={observacoes} onChange={(e) => setObservacoes(e.target.value)} placeholder="Contexto, contatos, particularidades…"></textarea>
          </label>
        </div>

        <footer className="nk-modal-footer">
          <span className="kbd-hint"><kbd>Esc</kbd> cancelar</span>
          <div className="actions">
            <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={!fornecedor.trim()}>
              {isNew ? "Adicionar" : "Salvar alterações"}
            </button>
          </div>
        </footer>
      </form>
    </div>
    </FOverlay>
  );
};

// ============================================================
// ConfirmModal — small confirm dialog
// ============================================================
const ConfirmModal = ({ title, body, confirmLabel = "Confirmar", danger, onConfirm, onCancel }) => {
  fuseEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); onCancel(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <FOverlay>
    <div className="nk-modal-backdrop" onClick={onCancel}>
      <div className="nk-modal nk-modal-confirm" onClick={(e) => e.stopPropagation()}>
        <header className="nk-modal-header">
          <div className="nk-modal-title-plain">{title}</div>
        </header>
        <div className="nk-modal-body">{body}</div>
        <footer className="nk-modal-footer">
          <span></span>
          <div className="actions">
            <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
            <button type="button" className={`btn ${danger ? "btn-danger" : "btn-primary"}`} onClick={onConfirm}>{confirmLabel}</button>
          </div>
        </footer>
      </div>
    </div>
    </FOverlay>
  );
};

Object.assign(window, { FornecedoresView, ConfirmModal });
