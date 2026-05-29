/* global React, CategoryIcon, UnitBadge, RetTags, formatBRL, dayLabel, retNome, retLabel, retSort, statusOf */
// Fechamento de Retenções — Controle de Notas Ciamed
// 4ª aba: a contabilidade usa no fim do mês pra separar as notas recebidas
// por tipo de retenção (cada tipo tem um processo de recolhimento diferente).

const { useState: xuseState, useMemo: xuseMemo } = React;

const MES_NOMES_F = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

const FechamentoView = ({
  notas, today, viewMonth, mesNome, isCurrentMonth, isPastMonth,
  onPrevMonth, onNextMonth, onCurrentMonth, onOpenDetail,
}) => {
  const { UNIDADES, CATEGORIAS, RETENCAO_TIPOS } = window.CIAMED;
  const [foco, setFoco] = xuseState(null); // id de tipo em foco (ou null = todos)

  // Notas recebidas do mês (recebidaEm != null) — inclui avulsas.
  const recebidas = xuseMemo(
    () => notas.filter((n) => n.recebidaEm),
    [notas],
  );

  // Recebidas que têm pelo menos um tipo de retenção.
  const recebidasComRet = xuseMemo(
    () => recebidas.filter((n) => n.retencao && Array.isArray(n.retencoes) && n.retencoes.length > 0),
    [recebidas],
  );

  // Agrupamento por tipo — uma nota com vários tipos aparece em cada seção.
  const grupos = xuseMemo(() => {
    return RETENCAO_TIPOS.map((t) => {
      const lote = recebidasComRet
        .filter((n) => n.retencoes.includes(t.id))
        .sort((a, b) => a.fornecedor.localeCompare(b.fornecedor));
      let soma = 0;
      let temValor = false;
      for (const n of lote) {
        if (n.valor != null) { soma += n.valor; temValor = true; }
      }
      return { tipo: t, lote, soma: temValor ? soma : null };
    });
  }, [recebidasComRet, RETENCAO_TIPOS]);

  const tiposComMovimento = grupos.filter((g) => g.lote.length > 0).length;
  const mesCap = (mesNome || MES_NOMES_F[viewMonth.month] || "")
    .replace(/^./, (c) => c.toUpperCase());

  const gruposVisiveis = foco ? grupos.filter((g) => g.tipo.id === foco) : grupos;

  return (
    <div className="fech-view">
      {/* ============= HEADER ============= */}
      <header className="fech-header">
        <div className="fech-title-row">
          <div className="fech-title-text">
            <div className="page-eyebrow">Contabilidade · fim do mês</div>
            <h2 className="page-title">Fechamento de Retenções</h2>
            <p className="page-lede">
              Cada tipo de retenção tem um <em>processo de recolhimento diferente</em> —
              use esta tela pra separar e conferir os lotes antes do fechamento.
              Só entram as notas <em>recebidas</em> do mês.
            </p>
          </div>

          <div className="fech-month-nav">
            <button className="nav-btn" onClick={onPrevMonth} title="Mês anterior (←)">‹</button>
            <div className="fech-month-label">
              <span className="fech-month-name">{mesCap}</span>
              <span className="fech-month-year mono">{viewMonth.year}</span>
            </div>
            <button className="nav-btn" onClick={onNextMonth} title="Próximo mês (→)">›</button>
            <button
              className={`nav-btn nav-now ${isCurrentMonth ? "is-current" : ""}`}
              onClick={onCurrentMonth}
              title="Voltar pro mês atual"
            >
              Hoje
            </button>
          </div>
        </div>

        {/* ===== RESUMO ===== */}
        <div className="fech-summary">
          <div className="fech-summary-lead">
            <div className="fech-bignum">
              <span className="fech-bignum-n mono">{recebidasComRet.length}</span>
              <span className="fech-bignum-l">
                nota{recebidasComRet.length !== 1 ? "s" : ""} recebida{recebidasComRet.length !== 1 ? "s" : ""} com retenção
              </span>
            </div>
            <span className="fech-summary-sub">
              {tiposComMovimento} de {RETENCAO_TIPOS.length} tipos com movimento ·
              {" "}{recebidas.length} recebidas no mês
            </span>
          </div>

          <div className="fech-type-strip" role="group" aria-label="Resumo por tipo de retenção">
            {grupos.map((g) => {
              const n = g.lote.length;
              const on = foco === g.tipo.id;
              return (
                <button
                  key={g.tipo.id}
                  className={`fech-type-pill ${n === 0 ? "is-empty" : ""} ${on ? "on" : ""}`}
                  onClick={() => setFoco((p) => (p === g.tipo.id ? null : g.tipo.id))}
                  title={n === 0 ? `Nenhuma nota com ${g.tipo.nome}` : `${n} nota${n > 1 ? "s" : ""} · ${g.tipo.nome} — clique pra focar`}
                  aria-pressed={on}
                >
                  <span className="fech-type-pill-num mono">{n}</span>
                  <span className="fech-type-pill-lbl">{g.tipo.label}</span>
                </button>
              );
            })}
          </div>
        </div>
        {foco && (
          <button className="fech-foco-clear" onClick={() => setFoco(null)}>
            ← Ver todos os tipos
          </button>
        )}
      </header>

      {/* ============= SEÇÕES POR TIPO ============= */}
      <div className="fech-sections">
        {gruposVisiveis.map((g) => (
          <FechSection
            key={g.tipo.id}
            tipo={g.tipo}
            lote={g.lote}
            soma={g.soma}
            onOpenDetail={onOpenDetail}
          />
        ))}
      </div>
    </div>
  );
};

// ============================================================
// Seção de um tipo de retenção
// ============================================================
const FechSection = ({ tipo, lote, soma, onOpenDetail }) => {
  const { CATEGORIAS, UNIDADES } = window.CIAMED;
  const vazio = lote.length === 0;

  return (
    <section className={`fech-section fech-section-${tipo.id} ${vazio ? "is-empty" : ""}`} data-screen-label={`fechamento-${tipo.id}`}>
      <header className="fech-sec-head">
        <span className="fech-sec-tag">{tipo.label}</span>
        <div className="fech-sec-titles">
          <h3 className="fech-sec-title">{tipo.nome}</h3>
          <span className="fech-sec-sub">
            {vazio
              ? "Nenhuma nota com retenção neste mês"
              : `${lote.length} nota${lote.length > 1 ? "s" : ""} no lote`}
          </span>
        </div>
        {!vazio && (
          <div className="fech-sec-meta">
            <span className="fech-sec-count mono">{lote.length}</span>
            {soma != null && (
              <span className="fech-sec-soma mono">R$ {formatBRL(soma)}</span>
            )}
          </div>
        )}
      </header>

      {vazio ? (
        <p className="fech-empty">Nenhuma nota com retenção de {tipo.label} neste mês.</p>
      ) : (
        <div className="fech-list" role="table">
          <div className="fech-list-head" role="row">
            <span className="fl-c fl-forn">Fornecedor</span>
            <span className="fl-c fl-unit">Unidade</span>
            <span className="fl-c fl-nf">Nº NF</span>
            <span className="fl-c fl-tipos">Retenções</span>
            <span className="fl-c fl-valor">Valor</span>
          </div>
          {lote.map((n) => {
            const cat = CATEGORIAS.find((c) => c.id === n.categoria);
            const unit = UNIDADES.find((u) => u.id === n.unidade);
            return (
              <button
                key={n.id}
                className="fech-row"
                role="row"
                onClick={() => onOpenDetail && onOpenDetail(n)}
                title={`Abrir detalhe · ${n.fornecedor}`}
              >
                <span className="fl-c fl-forn">
                  <CategoryIcon id={n.categoria} size={14} className="fech-row-ico" />
                  <span className="fech-row-forn" title={n.fornecedor}>{n.fornecedor}</span>
                  {n.avulsa && <span className="fech-row-avulsa">avulsa</span>}
                </span>
                <span className="fl-c fl-unit"><UnitBadge unidade={n.unidade} /></span>
                <span className="fl-c fl-nf mono">{n.nfNumero || "—"}</span>
                <span className="fl-c fl-tipos">
                  <RetTags tipos={n.retencoes} max={4} />
                </span>
                <span className="fl-c fl-valor mono">
                  {n.valor != null ? <>R$&nbsp;{formatBRL(n.valor)}</> : <span className="muted">—</span>}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
};

Object.assign(window, { FechamentoView });
