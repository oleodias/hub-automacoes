// Mock data + helpers — Controle de Notas Ciamed
// Today fixed at 2026-05-08 (sexta-feira)

(() => {
  const TODAY = new Date(2026, 4, 8); // 8 de maio de 2026
  const MONTH = 4; // 0-indexed
  const YEAR = 2026;

  const UNIDADES = [
    { id: "matriz", nome: "Matriz (1)",     short: "MTZ" },
    { id: "f2",     nome: "Filial 2",       short: "F2"  },
    { id: "f3",     nome: "Filial 3 (SC)",  short: "F3 SC" },
    { id: "f4",     nome: "Filial 4",       short: "F4"  },
  ];

  const CATEGORIAS = [
    { id: "energia",    nome: "Energia elétrica" },
    { id: "agua",       nome: "Água e esgoto" },
    { id: "internet",   nome: "Internet/Telefonia" },
    { id: "movel",      nome: "Telefonia móvel" },
    { id: "assinatura", nome: "Assinatura digital" },
    { id: "juridica",   nome: "Assessoria jurídica" },
    { id: "contabil",   nome: "Assessoria contábil" },
    { id: "aluguel",    nome: "Aluguel" },
    { id: "manutencao", nome: "Manutenção" },
    { id: "escritorio", nome: "Material de escritório" },
    { id: "outros",     nome: "Outros" },
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
    N({ fornecedor: "Microsoft 365",      cnpj: "60.701.190/0001-04", categoria: "assinatura", unidade: "matriz", diaEsperado: 2,
        recebidaEm: d(2),  nfNumero: "000.012.448", valor: 1284.90 }),
    N({ fornecedor: "Microsoft 365",      cnpj: "60.701.190/0001-04", categoria: "assinatura", unidade: "f3",     diaEsperado: 2,
        recebidaEm: d(2),  nfNumero: "000.012.449", valor: 421.30 }),
    N({ fornecedor: "Microsoft 365",      cnpj: "60.701.190/0001-04", categoria: "assinatura", unidade: "f2",     diaEsperado: 2,
        recebidaEm: d(2),  nfNumero: "000.012.450", valor: 219.80 }),
    N({ fornecedor: "Adobe Creative Cloud", cnpj: "01.900.789/0001-77", categoria: "assinatura", unidade: "f3",   diaEsperado: 3,
        recebidaEm: d(3),  nfNumero: "ADO-998211",  valor: 380.00 }),
    N({ fornecedor: "CELESC Distribuição", cnpj: "08.336.783/0001-90", categoria: "energia",    unidade: "f4",    diaEsperado: 4,
        recebidaEm: d(4),  nfNumero: "55.778.401",  valor: 2910.12 }),
    N({ fornecedor: "Sabesp",              cnpj: "43.776.517/0001-80", categoria: "agua",       unidade: "f4",    diaEsperado: 5,
        recebidaEm: d(5),  nfNumero: "778-2204",    valor: 280.40 }),
    N({ fornecedor: "CASAN",               cnpj: "82.508.433/0001-17", categoria: "agua",       unidade: "f3",    diaEsperado: 5,
        recebidaEm: d(5),  nfNumero: "CSN-441902",  valor: 480.00,  retencao: true }),
    N({ fornecedor: "Vivo Empresas",       cnpj: "02.558.157/0001-62", categoria: "internet",   unidade: "f3",    diaEsperado: 6,
        recebidaEm: d(6),  nfNumero: "VV-220411",   valor: 540.20 }),
    N({ fornecedor: "Claro Empresas",      cnpj: "40.432.544/0001-47", categoria: "movel",      unidade: "matriz", diaEsperado: 6,
        recebidaEm: d(6),  nfNumero: "CL-118842",   valor: 650.30,  retencao: true }),
    N({ fornecedor: "Sabesp",              cnpj: "43.776.517/0001-80", categoria: "agua",       unidade: "f2",    diaEsperado: 6,
        recebidaEm: d(6),  nfNumero: "778-2205",    valor: 320.00 }),
    N({ fornecedor: "Escr. Adv. Mendes",   cnpj: "12.448.998/0001-03", categoria: "juridica",   unidade: "f2",    diaEsperado: 7,
        recebidaEm: d(7),  nfNumero: "ME-2026-501", valor: 1200.00, retencao: true }),
    N({ fornecedor: "Vivo Empresas",       cnpj: "02.558.157/0001-62", categoria: "internet",   unidade: "matriz", diaEsperado: 7,
        recebidaEm: d(7),  nfNumero: "VV-220412",   valor: 1180.00 }),

    // ============ ATRASADAS (3) ============
    N({ fornecedor: "CELESC Distribuição", cnpj: "08.336.783/0001-90", categoria: "energia",    unidade: "f3",    diaEsperado: 5 }),
    N({ fornecedor: "Sabesp",              cnpj: "43.776.517/0001-80", categoria: "agua",       unidade: "matriz", diaEsperado: 6 }),
    N({ fornecedor: "DocuSign",            cnpj: "23.554.901/0001-58", categoria: "assinatura", unidade: "matriz", diaEsperado: 7 }),

    // ============ AGUARDANDO (12) ============
    N({ fornecedor: "JS Imóveis",          cnpj: "11.225.443/0001-78", categoria: "aluguel",    unidade: "f2",    diaEsperado: 8 }),
    N({ fornecedor: "Escr. Adv. Mendes",   cnpj: "12.448.998/0001-03", categoria: "juridica",   unidade: "matriz", diaEsperado: 10, retencao: true }),
    N({ fornecedor: "Vivo Empresas",       cnpj: "02.558.157/0001-62", categoria: "internet",   unidade: "f4",    diaEsperado: 12 }),
    N({ fornecedor: "Vivo Empresas",       cnpj: "02.558.157/0001-62", categoria: "internet",   unidade: "f2",    diaEsperado: 12 }),
    N({ fornecedor: "Claro Empresas",      cnpj: "40.432.544/0001-47", categoria: "movel",      unidade: "f3",    diaEsperado: 14 }),
    N({ fornecedor: "Contadora Silva & Cia.", cnpj: "33.117.221/0001-09", categoria: "contabil", unidade: "matriz", diaEsperado: 15, retencao: true }),
    N({ fornecedor: "JS Imóveis",          cnpj: "11.225.443/0001-78", categoria: "aluguel",    unidade: "matriz", diaEsperado: 18 }),
    N({ fornecedor: "Adobe Creative Cloud", cnpj: "01.900.789/0001-77", categoria: "assinatura", unidade: "matriz", diaEsperado: 20 }),
    N({ fornecedor: "RefriNorte Manutenção", cnpj: "55.881.220/0001-44", categoria: "manutencao", unidade: "f2",   diaEsperado: 25, retencao: true }),
    N({ fornecedor: "Papelaria Central",   cnpj: "67.443.210/0001-22", categoria: "escritorio", unidade: "matriz", diaEsperado: 22 }),
    N({ fornecedor: "CELESC Distribuição", cnpj: "08.336.783/0001-90", categoria: "energia",    unidade: "matriz", diaEsperado: 28 }),
    N({ fornecedor: "CELESC Distribuição", cnpj: "08.336.783/0001-90", categoria: "energia",    unidade: "f2",    diaEsperado: 28 }),

    // ============ AVULSAS (2 — already received) ============
    N({ fornecedor: "Climatec Refrigeração", cnpj: "78.991.220/0001-15", categoria: "manutencao", unidade: "f2", diaEsperado: 0,
        recebidaEm: d(3), nfNumero: "CT-9982",  valor: 1450.00, avulsa: true,
        obs: "Conserto emergencial unidade externa do ar-condicionado." }),
    N({ fornecedor: "Escr. Adv. Mendes",   cnpj: "12.448.998/0001-03", categoria: "juridica",   unidade: "matriz", diaEsperado: 0,
        recebidaEm: d(5), nfNumero: "ME-2026-512", valor: 800.00, retencao: true, avulsa: true,
        obs: "Honorário pontual — assessoria contrato fornecedor X." }),
  ];

  window.CIAMED = {
    TODAY,
    MONTH,
    YEAR,
    UNIDADES,
    CATEGORIAS,
    NOTAS_INICIAIS: NOTAS,
  };
})();
