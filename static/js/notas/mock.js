// Mock data + helpers — Controle de Notas Ciamed
// Today fixed at 2026-05-08 (sexta-feira)

(() => {
  // PRODUÇÃO: usa a data real do navegador (não mais data fixa de mock).
  const TODAY = new Date();
  const MONTH = TODAY.getMonth(); // 0-indexed
  const YEAR = TODAY.getFullYear();

  const UNIDADES = [
    { id: "matriz", nome: "Matriz (RS)", short: "MTZ RS" },
    { id: "f2", nome: "Filial 2 (SP)", short: "F2 SP" },
    { id: "f3", nome: "Filial 3 (SC)", short: "F3 SC" },
    { id: "f4", nome: "Filial 4 (ES)", short: "F4 ES" },
  ];

  const CATEGORIAS = [
    { id: "energia", nome: "Energia elétrica" },
    { id: "agua", nome: "Água e esgoto" },
    { id: "internet", nome: "Internet/Telefonia" },
    { id: "movel", nome: "Telefonia móvel" },
    { id: "assinatura", nome: "Assinatura digital" },
    { id: "juridica", nome: "Assessoria jurídica" },
    { id: "contabil", nome: "Assessoria contábil" },
    { id: "aluguel", nome: "Aluguel" },
    { id: "manutencao", nome: "Manutenção" },
    { id: "escritorio", nome: "Material de escritório" },
    { id: "outros", nome: "Outros" },
  ];

  // Each note: id, fornecedor, cnpj, categoria, unidade, diaEsperado,
  //            recebida (Date | null), nfNumero, valor, retencao (bool), avulsa (bool), obs
  let nextId = 1;
  const N = (props) => ({
    id: `n${nextId++}`,
    fornecedor: "",
    cnpj: "",
    categoria: "outros",
    unidade: "matriz",
    diaEsperado: 1,
    recebidaEm: null,
    nfNumero: "",
    valor: null,
    retencao: false,
    avulsa: false,
    obs: "",
    historico: [],
    ...props,
  });

  const d = (day) => new Date(YEAR, MONTH, day);

  const NOTAS = [
    // ============ RECEBIDAS (12) ============
    N({
      fornecedor: "Microsoft 365",
      cnpj: "60.701.190/0001-04",
      categoria: "assinatura",
      unidade: "matriz",
      diaEsperado: 2,
      recebidaEm: d(2),
      nfNumero: "000.012.448",
      valor: 1284.9,
    }),
    N({
      fornecedor: "Microsoft 365",
      cnpj: "60.701.190/0001-04",
      categoria: "assinatura",
      unidade: "f3",
      diaEsperado: 2,
      recebidaEm: d(2),
      nfNumero: "000.012.449",
      valor: 421.3,
    }),
    N({
      fornecedor: "Microsoft 365",
      cnpj: "60.701.190/0001-04",
      categoria: "assinatura",
      unidade: "f2",
      diaEsperado: 2,
      recebidaEm: d(2),
      nfNumero: "000.012.450",
      valor: 219.8,
    }),
    N({
      fornecedor: "Adobe Creative Cloud",
      cnpj: "01.900.789/0001-77",
      categoria: "assinatura",
      unidade: "f3",
      diaEsperado: 3,
      recebidaEm: d(3),
      nfNumero: "ADO-998211",
      valor: 380.0,
    }),
    N({
      fornecedor: "CELESC Distribuição",
      cnpj: "08.336.783/0001-90",
      categoria: "energia",
      unidade: "f4",
      diaEsperado: 4,
      recebidaEm: d(4),
      nfNumero: "55.778.401",
      valor: 2910.12,
    }),
    N({
      fornecedor: "Sabesp",
      cnpj: "43.776.517/0001-80",
      categoria: "agua",
      unidade: "f4",
      diaEsperado: 5,
      recebidaEm: d(5),
      nfNumero: "778-2204",
      valor: 280.4,
    }),
    N({
      fornecedor: "CASAN",
      cnpj: "82.508.433/0001-17",
      categoria: "agua",
      unidade: "f3",
      diaEsperado: 5,
      recebidaEm: d(5),
      nfNumero: "CSN-441902",
      valor: 480.0,
      retencao: true,
    }),
    N({
      fornecedor: "Vivo Empresas",
      cnpj: "02.558.157/0001-62",
      categoria: "internet",
      unidade: "f3",
      diaEsperado: 6,
      recebidaEm: d(6),
      nfNumero: "VV-220411",
      valor: 540.2,
    }),
    N({
      fornecedor: "Claro Empresas",
      cnpj: "40.432.544/0001-47",
      categoria: "movel",
      unidade: "matriz",
      diaEsperado: 6,
      recebidaEm: d(6),
      nfNumero: "CL-118842",
      valor: 650.3,
      retencao: true,
    }),
    N({
      fornecedor: "Sabesp",
      cnpj: "43.776.517/0001-80",
      categoria: "agua",
      unidade: "f2",
      diaEsperado: 6,
      recebidaEm: d(6),
      nfNumero: "778-2205",
      valor: 320.0,
    }),
    N({
      fornecedor: "Escr. Adv. Mendes",
      cnpj: "12.448.998/0001-03",
      categoria: "juridica",
      unidade: "f2",
      diaEsperado: 7,
      recebidaEm: d(7),
      nfNumero: "ME-2026-501",
      valor: 1200.0,
      retencao: true,
    }),
    N({
      fornecedor: "Vivo Empresas",
      cnpj: "02.558.157/0001-62",
      categoria: "internet",
      unidade: "matriz",
      diaEsperado: 7,
      recebidaEm: d(7),
      nfNumero: "VV-220412",
      valor: 1180.0,
    }),

    // ============ ATRASADAS (3) ============
    N({
      fornecedor: "CELESC Distribuição",
      cnpj: "08.336.783/0001-90",
      categoria: "energia",
      unidade: "f3",
      diaEsperado: 5,
    }),
    N({
      fornecedor: "Sabesp",
      cnpj: "43.776.517/0001-80",
      categoria: "agua",
      unidade: "matriz",
      diaEsperado: 6,
    }),
    N({
      fornecedor: "DocuSign",
      cnpj: "23.554.901/0001-58",
      categoria: "assinatura",
      unidade: "matriz",
      diaEsperado: 7,
    }),

    // ============ AGUARDANDO (12) ============
    N({
      fornecedor: "JS Imóveis",
      cnpj: "11.225.443/0001-78",
      categoria: "aluguel",
      unidade: "f2",
      diaEsperado: 8,
    }),
    N({
      fornecedor: "Escr. Adv. Mendes",
      cnpj: "12.448.998/0001-03",
      categoria: "juridica",
      unidade: "matriz",
      diaEsperado: 10,
      retencao: true,
    }),
    N({
      fornecedor: "Vivo Empresas",
      cnpj: "02.558.157/0001-62",
      categoria: "internet",
      unidade: "f4",
      diaEsperado: 12,
    }),
    N({
      fornecedor: "Vivo Empresas",
      cnpj: "02.558.157/0001-62",
      categoria: "internet",
      unidade: "f2",
      diaEsperado: 12,
    }),
    N({
      fornecedor: "Claro Empresas",
      cnpj: "40.432.544/0001-47",
      categoria: "movel",
      unidade: "f3",
      diaEsperado: 14,
    }),
    N({
      fornecedor: "Contadora Silva & Cia.",
      cnpj: "33.117.221/0001-09",
      categoria: "contabil",
      unidade: "matriz",
      diaEsperado: 15,
      retencao: true,
    }),
    N({
      fornecedor: "JS Imóveis",
      cnpj: "11.225.443/0001-78",
      categoria: "aluguel",
      unidade: "matriz",
      diaEsperado: 18,
    }),
    N({
      fornecedor: "Adobe Creative Cloud",
      cnpj: "01.900.789/0001-77",
      categoria: "assinatura",
      unidade: "matriz",
      diaEsperado: 20,
    }),
    N({
      fornecedor: "RefriNorte Manutenção",
      cnpj: "55.881.220/0001-44",
      categoria: "manutencao",
      unidade: "f2",
      diaEsperado: 25,
      retencao: true,
    }),
    N({
      fornecedor: "Papelaria Central",
      cnpj: "67.443.210/0001-22",
      categoria: "escritorio",
      unidade: "matriz",
      diaEsperado: 22,
    }),
    N({
      fornecedor: "CELESC Distribuição",
      cnpj: "08.336.783/0001-90",
      categoria: "energia",
      unidade: "matriz",
      diaEsperado: 28,
    }),
    N({
      fornecedor: "CELESC Distribuição",
      cnpj: "08.336.783/0001-90",
      categoria: "energia",
      unidade: "f2",
      diaEsperado: 28,
    }),

    // ============ AVULSAS (2 — already received) ============
    N({
      fornecedor: "Climatec Refrigeração",
      cnpj: "78.991.220/0001-15",
      categoria: "manutencao",
      unidade: "f2",
      diaEsperado: 0,
      recebidaEm: d(3),
      nfNumero: "CT-9982",
      valor: 1450.0,
      avulsa: true,
      obs: "Conserto emergencial unidade externa do ar-condicionado.",
    }),
    N({
      fornecedor: "Escr. Adv. Mendes",
      cnpj: "12.448.998/0001-03",
      categoria: "juridica",
      unidade: "matriz",
      diaEsperado: 0,
      recebidaEm: d(5),
      nfNumero: "ME-2026-512",
      valor: 800.0,
      retencao: true,
      avulsa: true,
      obs: "Honorário pontual — assessoria contrato fornecedor X.",
    }),
  ];

  window.CIAMED = {
    TODAY,
    MONTH,
    YEAR,
    UNIDADES,
    CATEGORIAS,
    NOTAS_INICIAIS: NOTAS,
  };

  // ============================================================
  // EXPECTATIVAS — derived recurring registrations
  // (one row per fornecedor + unidade + dia)
  // ============================================================
  const seen = new Map();
  for (const n of NOTAS) {
    if (n.avulsa) continue;
    const key = `${n.fornecedor}|${n.unidade}|${n.diaEsperado}`;
    if (!seen.has(key)) {
      seen.set(key, {
        id:
          "exp-" +
          key
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, ""),
        fornecedor: n.fornecedor,
        cnpj: n.cnpj,
        categoria: n.categoria,
        unidade: n.unidade,
        diaEsperado: n.diaEsperado,
        retencaoPadrao: !!n.retencao,
        valorMedio: null, // computed below
        valorAcumulado: 0,
        valorCount: 0,
        ativo: true,
        iniciadoEm: "2024-01",
        observacoes: "",
      });
    }
    const e = seen.get(key);
    if (n.valor) {
      e.valorAcumulado += n.valor;
      e.valorCount += 1;
    }
  }
  const EXPECTATIVAS = [...seen.values()]
    .map((e) => ({
      ...e,
      valorMedio: e.valorCount > 0 ? e.valorAcumulado / e.valorCount : null,
    }))
    .sort(
      (a, b) =>
        a.fornecedor.localeCompare(b.fornecedor) ||
        a.diaEsperado - b.diaEsperado,
    );

  // ============================================================
  // Deterministic historical status synthesis for Panorama
  // Returns one of: 'ok' | 'late' | 'miss' | 'na'
  // For current month, the caller should override with real data.
  // ============================================================
  const hash32 = (str) => {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h;
  };
  const rand01 = (seed) => (hash32(seed) % 10000) / 10000;

  const historicalStatus = (expId, year, month /* 0-indexed */) => {
    const ymKey = `${year}-${String(month).padStart(2, "0")}`;
    const r = rand01(`${expId}::${ymKey}`);
    // Most recurring suppliers: ~85% on-time, ~10% late, ~5% miss
    if (r < 0.86) return "ok";
    if (r < 0.96) return "late";
    return "miss";
  };

  // pontualidade over last N months (excluding current month)
  const pontualidade = (expId, today, monthsBack = 12) => {
    let ok = 0,
      total = 0;
    for (let i = 1; i <= monthsBack; i++) {
      const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
      const s = historicalStatus(expId, d.getFullYear(), d.getMonth());
      if (s === "na") continue;
      total++;
      if (s === "ok") ok++;
    }
    return total > 0 ? ok / total : 1;
  };

  window.CIAMED.EXPECTATIVAS_INICIAIS = EXPECTATIVAS;
  window.CIAMED.historicalStatus = historicalStatus;
  window.CIAMED.pontualidade = pontualidade;
})();
