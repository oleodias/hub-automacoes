/* global React, CategoryIcon, UnitBadge, RetentionMark, formatBRL, dayLabel, statusOf, daysLate, urgencyTier */
// Card + Modals — Controle de Notas Ciamed

const { useState: cuseState, useRef: cuseRef, useEffect: cuseEffect } = React;

// ============================================================
// CARD — fornecedor card on the kanban
// ============================================================
const NotaCard = ({
  nota, today, status, onMarkReceived, onOpenDetail, isDragging,
  onDragStart, onDragEnd,
}) => {
  const days = daysLate(nota, today);
  const tier = urgencyTier(days);
  const justTurned = status === "atrasada" && days === 1; // virou hoje (yesterday's expected)
  const showCheck = status !== "recebida" && status !== "avulsa";

  const lateLabel = (() => {
    if (status !== "atrasada") return null;
    if (days === 1) return "virou hoje";
    return `+${days}d`;
  })();

  const dayHint = (() => {
    if (status === "recebida" || status === "avulsa") {
      return nota.recebidaEm ? `d${dayLabel(nota.recebidaEm.getDate())}` : "avulsa";
    }
    if (status === "atrasada") return `d${dayLabel(nota.diaEsperado)}`;
    return `d${dayLabel(nota.diaEsperado)}`;
  })();

  return (
    <div
      className={`card status-${status} ${status === "atrasada" ? `tier-${tier}` : ""} ${nota.retencao ? "has-ret" : ""} ${isDragging ? "is-dragging" : ""}`}
      draggable={status !== "recebida" && status !== "avulsa"}
      onDragStart={(e) => onDragStart && onDragStart(e, nota)}
      onDragEnd={onDragEnd}
      onClick={() => onOpenDetail && onOpenDetail(nota)}
      tabIndex={0}
      role="button"
      aria-label={`Nota ${nota.fornecedor} ${nota.unidade}`}
    >
      {nota.retencao && <span className="card-ret-stripe" aria-hidden="true" />}

      <div className="card-row card-top">
        <CategoryIcon id={nota.categoria} size={14} className="card-cat" />
        <span className="card-fornecedor" title={nota.fornecedor}>{nota.fornecedor}</span>
        {lateLabel && (
          <span className={`card-late-tag ${justTurned ? "just-turned" : ""}`}>{lateLabel}</span>
        )}
        {!lateLabel && <span className="card-day">{dayHint}</span>}
      </div>

      <div className="card-row card-bottom">
        <UnitBadge unidade={nota.unidade} />
        {nota.retencao && (
          <span className="card-ret-pill" title="Retenção (INSS/ISSQN/IRRF/PIS/COFINS/CSLL)">
            <RetentionMark tip="" /> retenção
          </span>
        )}
        {status === "recebida" && nota.valor != null && (
          <span className="card-valor">R$ {formatBRL(nota.valor)}</span>
        )}
        {status === "avulsa" && (
          <span className="card-avulsa-tag">avulsa</span>
        )}

        {showCheck && (
          <button
            className="card-check"
            type="button"
            onClick={(e) => { e.stopPropagation(); onMarkReceived(nota); }}
            title="Registrar recebimento (R)"
            aria-label="Registrar recebimento"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path d="M2 6.4 L4.8 9 L10 3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

// ============================================================
// REGISTER MODAL — opens when a card is moved to "Recebidas"
// ============================================================
const RegisterModal = ({ nota, today, onConfirm, onCancel }) => {
  const dataDefault = today.toISOString().slice(0, 10);
  const [dataRecebida, setDataRecebida] = cuseState(dataDefault);
  const [nfNumero, setNfNumero] = cuseState(nota.nfNumero || "");
  const [valor, setValor] = cuseState(nota.valor != null ? String(nota.valor).replace(".", ",") : "");
  const [retencao, setRetencao] = cuseState(!!nota.retencao);
  const nfRef = cuseRef(null);

  cuseEffect(() => {
    setTimeout(() => nfRef.current && nfRef.current.focus(), 60);
    const onKey = (e) => {
      if (e.key === "Escape") { e.preventDefault(); onCancel(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const submit = (e) => {
    e.preventDefault();
    const [y, m, d] = dataRecebida.split("-").map(Number);
    const v = valor ? Number(valor.replace(/\./g, "").replace(",", ".")) : null;
    onConfirm({
      ...nota,
      recebidaEm: new Date(y, m - 1, d),
      nfNumero: nfNumero.trim(),
      valor: isFinite(v) ? v : null,
      retencao,
    });
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <form className="modal modal-register" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <header className="modal-header">
          <div className="modal-eyebrow">Registrar nota recebida</div>
          <div className="modal-title">
            <CategoryIcon id={nota.categoria} size={16} />
            <span>{nota.fornecedor}</span>
            <UnitBadge unidade={nota.unidade} />
            <span className="modal-cat">· {nota.categoria === "outros" ? "Outros" : window.CIAMED.CATEGORIAS.find(c => c.id === nota.categoria)?.nome}</span>
          </div>
        </header>

        <div className="modal-grid">
          <label className="field">
            <span className="lbl">Data recebida</span>
            <input type="date" value={dataRecebida} onChange={(e) => setDataRecebida(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Nº NF <em>(foco)</em></span>
            <input ref={nfRef} type="text" placeholder="ex: 000.012.448" value={nfNumero} onChange={(e) => setNfNumero(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Valor líquido</span>
            <div className="input-prefix">
              <span className="prefix">R$</span>
              <input type="text" inputMode="decimal" placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} />
            </div>
          </label>
          <label className="field">
            <span className="lbl">Retenção?</span>
            <div className="seg">
              <button type="button" className={!retencao ? "on" : ""} onClick={() => setRetencao(false)}>Não</button>
              <button type="button" className={retencao ? "on ret" : ""} onClick={() => setRetencao(true)}>Sim — sinalizar</button>
            </div>
          </label>
        </div>

        <footer className="modal-footer">
          <span className="kbd-hint"><kbd>Tab</kbd> navegar · <kbd>Enter</kbd> salvar · <kbd>Esc</kbd> cancelar</span>
          <div className="actions">
            <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
            <button type="submit" className="btn btn-primary">Registrar recebimento</button>
          </div>
        </footer>
      </form>
    </div>
  );
};

// ============================================================
// AVULSA MODAL — add a non-recurring invoice
// ============================================================
const AvulsaModal = ({ today, onConfirm, onCancel }) => {
  const [fornecedor, setFornecedor] = cuseState("");
  const [categoria, setCategoria] = cuseState("outros");
  const [unidade, setUnidade] = cuseState("matriz");
  const [dataRecebida, setDataRecebida] = cuseState(today.toISOString().slice(0, 10));
  const [nfNumero, setNfNumero] = cuseState("");
  const [valor, setValor] = cuseState("");
  const [retencao, setRetencao] = cuseState(false);
  const [obs, setObs] = cuseState("");
  const fornRef = cuseRef(null);

  cuseEffect(() => {
    setTimeout(() => fornRef.current && fornRef.current.focus(), 60);
    const onKey = (e) => { if (e.key === "Escape") { e.preventDefault(); onCancel(); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const submit = (e) => {
    e.preventDefault();
    if (!fornecedor.trim()) return;
    const [y, m, d] = dataRecebida.split("-").map(Number);
    const v = valor ? Number(valor.replace(/\./g, "").replace(",", ".")) : null;
    onConfirm({
      fornecedor: fornecedor.trim(),
      categoria, unidade,
      recebidaEm: new Date(y, m - 1, d),
      diaEsperado: 0,
      nfNumero: nfNumero.trim(),
      valor: isFinite(v) ? v : null,
      retencao, obs,
      avulsa: true,
    });
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <form className="modal modal-avulsa" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <header className="modal-header">
          <div className="modal-eyebrow">Adicionar nota avulsa</div>
          <div className="modal-title-plain">Nota não prevista no recorrente</div>
        </header>

        <div className="modal-grid grid-2">
          <label className="field span-2">
            <span className="lbl">Fornecedor</span>
            <input ref={fornRef} type="text" placeholder="Nome do fornecedor" value={fornecedor} onChange={(e) => setFornecedor(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Categoria</span>
            <select value={categoria} onChange={(e) => setCategoria(e.target.value)}>
              {window.CIAMED.CATEGORIAS.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="lbl">Unidade</span>
            <select value={unidade} onChange={(e) => setUnidade(e.target.value)}>
              {window.CIAMED.UNIDADES.map(u => <option key={u.id} value={u.id}>{u.nome}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="lbl">Data recebida</span>
            <input type="date" value={dataRecebida} onChange={(e) => setDataRecebida(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Nº NF</span>
            <input type="text" value={nfNumero} onChange={(e) => setNfNumero(e.target.value)} />
          </label>
          <label className="field">
            <span className="lbl">Valor líquido</span>
            <div className="input-prefix">
              <span className="prefix">R$</span>
              <input type="text" inputMode="decimal" placeholder="0,00" value={valor} onChange={(e) => setValor(e.target.value)} />
            </div>
          </label>
          <label className="field">
            <span className="lbl">Retenção?</span>
            <div className="seg">
              <button type="button" className={!retencao ? "on" : ""} onClick={() => setRetencao(false)}>Não</button>
              <button type="button" className={retencao ? "on ret" : ""} onClick={() => setRetencao(true)}>Sim</button>
            </div>
          </label>
          <label className="field span-2">
            <span className="lbl">Observações</span>
            <textarea rows="2" value={obs} onChange={(e) => setObs(e.target.value)} placeholder="Contexto da nota — opcional"></textarea>
          </label>
        </div>

        <footer className="modal-footer">
          <span className="kbd-hint"><kbd>Esc</kbd> cancelar</span>
          <div className="actions">
            <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={!fornecedor.trim()}>Adicionar avulsa</button>
          </div>
        </footer>
      </form>
    </div>
  );
};

// ============================================================
// DETAIL DRAWER — slide-out detail / edit / history
// ============================================================
const DetailDrawer = ({ nota, today, onClose, onUpdate, onUnreceive }) => {
  if (!nota) return null;
  const status = statusOf(nota, today);
  const cat = window.CIAMED.CATEGORIAS.find(c => c.id === nota.categoria);
  const unit = window.CIAMED.UNIDADES.find(u => u.id === nota.unidade);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <header className="drawer-header">
          <div>
            <div className="modal-eyebrow">Detalhes da nota</div>
            <h3 className="drawer-title">
              <CategoryIcon id={nota.categoria} size={16} />
              {nota.fornecedor}
            </h3>
          </div>
          <button className="icon-btn" onClick={onClose} title="Fechar (Esc)">
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M2 2L12 12 M12 2L2 12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
        </header>

        <dl className="kv">
          <dt>Status</dt>
          <dd><span className={`status-pill st-${status}`}>{status === "recebida" ? "Recebida" : status === "atrasada" ? "Atrasada" : status === "avulsa" ? "Avulsa" : "Aguardando"}</span></dd>
          <dt>Unidade</dt><dd>{unit?.nome}</dd>
          <dt>Categoria</dt><dd>{cat?.nome}</dd>
          <dt>CNPJ</dt><dd className="mono">{nota.cnpj || "—"}</dd>
          <dt>Dia esperado</dt><dd className="mono">{nota.avulsa ? "—" : dayLabel(nota.diaEsperado)}</dd>
          <dt>Recebida em</dt><dd className="mono">{nota.recebidaEm ? nota.recebidaEm.toLocaleDateString("pt-BR") : "—"}</dd>
          <dt>Nº NF</dt><dd className="mono">{nota.nfNumero || "—"}</dd>
          <dt>Valor líquido</dt><dd className="mono">{nota.valor != null ? `R$ ${formatBRL(nota.valor)}` : "—"}</dd>
          <dt>Retenção</dt><dd>{nota.retencao ? <span className="ret-inline"><RetentionMark tip="" /> Sim — atenção contabilidade</span> : "Não"}</dd>
          {nota.obs && (<><dt>Observações</dt><dd>{nota.obs}</dd></>)}
        </dl>

        {(status === "recebida" || status === "avulsa") && (
          <div className="drawer-actions">
            <button className="btn btn-ghost" onClick={() => onUnreceive(nota)}>Desfazer recebimento</button>
          </div>
        )}
      </aside>
    </div>
  );
};

Object.assign(window, { NotaCard, RegisterModal, AvulsaModal, DetailDrawer });
