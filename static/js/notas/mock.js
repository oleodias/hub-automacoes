// Constantes da UI + helpers — Controle de Notas Ciamed
// PRODUÇÃO: nada de dados fictícios aqui. Tudo vem da API Flask.
// Este arquivo só define UNIDADES, CATEGORIAS, RETENCAO_TIPOS e helpers
// que o React app consome de forma síncrona.

(() => {
  // Data real (produção) — vem do navegador
  const TODAY = new Date();
  const MONTH = TODAY.getMonth();
  const YEAR = TODAY.getFullYear();

  const UNIDADES = [
    { id: "matriz", nome: "Matriz (RS)", short: "MTZ RS" },
    { id: "f2", nome: "Filial 2 (SP)", short: "F2 SP" },
    { id: "f3", nome: "Filial 3 (SC)", short: "F3 SC" },
    { id: "f4", nome: "Filial 4 (ES)", short: "F4 ES" },
  ];

  // Tipos de retenção — cada um tem um processo de recolhimento diferente
  // no fim do mês. Uma nota pode ter vários ao mesmo tempo (só marcação).
  const RETENCAO_TIPOS = [
    { id: "inss",   label: "INSS",   nome: "INSS" },
    { id: "iss",    label: "ISS",    nome: "ISS (ISSQN)" },
    { id: "irrf",   label: "IRRF",   nome: "IRRF" },
    { id: "pis",    label: "PIS",    nome: "PIS" },
    { id: "cofins", label: "COFINS", nome: "COFINS" },
    { id: "csll",   label: "CSLL",   nome: "CSLL" },
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

  // Em produção, notas/expectativas vêm da API — arrays vazios aqui só
  // pra o app.jsx não crashar caso ainda referencie por nome.
  const NOTAS_INICIAIS = [];
  const EXPECTATIVAS_INICIAIS = [];

  // Fallback caso a chamada da API do Panorama falhe.
  const historicalStatus = () => "na";
  const pontualidade = () => null;

  window.CIAMED = {
    TODAY, MONTH, YEAR,
    UNIDADES, CATEGORIAS, RETENCAO_TIPOS,
    NOTAS_INICIAIS, EXPECTATIVAS_INICIAIS,
    historicalStatus, pontualidade,
  };
})();
