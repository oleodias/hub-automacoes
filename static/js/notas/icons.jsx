/* global React */
// Icons + small atoms — Controle de Notas Ciamed

const { useState, useRef, useEffect, useCallback, useMemo } = React;

// ============================================================
// Category icons — monochromatic, line, 16x16 viewbox
// ============================================================
const ICONS = {
  energia: (
    <path d="M9 1.5L3 9.2h4.2L7 14.5l5.8-7.7H8.6L9 1.5z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" />
  ),
  agua: (
    <path d="M8 1.5C5 5.5 3 8 3 10.5a5 5 0 0 0 10 0C13 8 11 5.5 8 1.5z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
  ),
  internet: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
      <path d="M2 6.5a9 9 0 0 1 12 0" />
      <path d="M4 9a6 6 0 0 1 8 0" />
      <path d="M6 11.5a3 3 0 0 1 4 0" />
      <circle cx="8" cy="13.5" r="0.7" fill="currentColor" stroke="none" />
    </g>
  ),
  movel: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <rect x="4.5" y="1.5" width="7" height="13" rx="1.2" />
      <line x1="7" y1="12" x2="9" y2="12" />
    </g>
  ),
  assinatura: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <path d="M2 12.5c2-0.5 3-3 4.5-5.5S9 3 10.5 3.5s0 3-1 4.5-2 2.5-1 3 3-1 5-1" />
      <path d="M11.5 2L14 4.5" />
    </g>
  ),
  juridica: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <line x1="8" y1="2" x2="8" y2="14" />
      <line x1="3" y1="14" x2="13" y2="14" />
      <path d="M3 6L8 4L13 6" />
      <path d="M2 9L4 6L6 9" />
      <path d="M10 9L12 6L14 9" />
    </g>
  ),
  contabil: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <rect x="3" y="2" width="10" height="12" rx="1" />
      <rect x="5" y="4" width="6" height="2.5" />
      <circle cx="5.7" cy="9" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="8" cy="9" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="10.3" cy="9" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="5.7" cy="11.5" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="8" cy="11.5" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="10.3" cy="11.5" r="0.5" fill="currentColor" stroke="none" />
    </g>
  ),
  aluguel: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <path d="M2.5 14V6.5L8 2.5L13.5 6.5V14" />
      <line x1="2.5" y1="14" x2="13.5" y2="14" />
      <rect x="6.5" y="9" width="3" height="5" />
      <line x1="5" y1="7.5" x2="5" y2="8.5" />
      <line x1="11" y1="7.5" x2="11" y2="8.5" />
    </g>
  ),
  manutencao: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <path d="M10.5 2a3 3 0 0 0-2.4 4.7L2 12.8l1.2 1.2 6.1-6.1A3 3 0 1 0 10.5 2z" />
      <circle cx="10.5" cy="5" r="0.6" fill="currentColor" stroke="none" />
    </g>
  ),
  escritorio: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round">
      <rect x="3" y="3" width="10" height="11" rx="1" />
      <line x1="5.5" y1="6" x2="10.5" y2="6" />
      <line x1="5.5" y1="8.5" x2="10.5" y2="8.5" />
      <line x1="5.5" y1="11" x2="9" y2="11" />
    </g>
  ),
  outros: (
    <g fill="none" stroke="currentColor" strokeWidth="1.3">
      <circle cx="8" cy="8" r="5" />
    </g>
  ),
};

const CategoryIcon = ({ id, size = 16, className = "" }) => (
  <svg className={`cat-icon ${className}`} width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
    {ICONS[id] || ICONS.outros}
  </svg>
);

// ============================================================
// UI atoms
// ============================================================
const UnitBadge = ({ unidade, size = "sm" }) => {
  const map = { matriz: "MTZ", f2: "F2", f3: "F3 SC", f4: "F4" };
  return <span className={`unit-badge unit-${unidade} unit-${size}`}>{map[unidade]}</span>;
};

const RetentionMark = ({ tip = "Nota com retenção" }) => (
  <span className="ret-mark" title={tip} aria-label={tip}>
    <svg width="11" height="11" viewBox="0 0 11 11" aria-hidden="true">
      <circle cx="5.5" cy="5.5" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <line x1="3" y1="5.5" x2="8" y2="5.5" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  </span>
);

// Helpers
const formatBRL = (v) =>
  v == null ? "—" : v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dayLabel = (n) => String(n).padStart(2, "0");
const sameDay = (a, b) => a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

// Compute status: "atrasada" | "aguardando" | "recebida" | "avulsa"
const statusOf = (nota, today) => {
  if (nota.recebidaEm) return nota.avulsa ? "avulsa" : "recebida";
  return nota.diaEsperado < today.getDate() ? "atrasada" : "aguardando";
};
const daysLate = (nota, today) => Math.max(0, today.getDate() - nota.diaEsperado);

// Urgency tier for atrasadas
const urgencyTier = (days) => {
  if (days <= 0) return "now";   // virou hoje (0/1 day mark)
  if (days <= 2) return "low";
  if (days <= 6) return "med";
  return "high";
};

Object.assign(window, { CategoryIcon, UnitBadge, RetentionMark, ICONS,
  formatBRL, dayLabel, sameDay, statusOf, daysLate, urgencyTier });
