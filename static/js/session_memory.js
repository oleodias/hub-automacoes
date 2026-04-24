// ════════════════════════════════════════════════════════════════════
// session_memory.js — Memória de Sessão do Hub de Automações
// ════════════════════════════════════════════════════════════════════
// Incluído no base.html, funciona em TODAS as páginas automaticamente.
//
// O que faz:
//   - Salva o estado de TODOS os campos de formulário (inputs, selects,
//     textareas) no sessionStorage toda vez que o usuário muda algo
//   - Quando o usuário volta pra aba (ex: foi consultar CNPJ), os
//     campos são restaurados automaticamente
//   - Quando o formulário é submetido ou o link é gerado, a memória
//     daquela página é limpa
//   - Cada página tem seu próprio "espaço" no sessionStorage (namespaced
//     pelo pathname), então não tem conflito entre abas
//
// Exclusões automáticas:
//   - Campos de senha (type="password")
//   - Campos de arquivo (type="file")
//   - Campos com atributo data-no-memory
//   - Campos sem ID
//
// Exclusão manual:
//   Adicione data-no-memory em qualquer campo pra pular:
//   <input id="campo" data-no-memory />
//
// Limpar memória via JS (pra usar nos botões de submit):
//   window.sessionMemory.limpar()
// ════════════════════════════════════════════════════════════════════

(function () {
  "use strict";

  // ── Namespace baseado no pathname da página ──
  // Garante que /cadastro_clientes não interfere com /consulta_cnpj
  const PREFIXO = "hub_mem_" + window.location.pathname + "_";

  // ── Tipos de campo que NÃO devem ser salvos ──
  const TIPOS_IGNORADOS = new Set(["password", "file", "hidden"]);

  // ── Busca todos os campos elegíveis na página ──
  function getCamposElegiveis() {
    const todos = document.querySelectorAll("input, select, textarea");
    const elegiveis = [];

    todos.forEach((campo) => {
      // Precisa ter ID (senão não tem como identificar)
      if (!campo.id) return;

      // Pula tipos ignorados
      if (TIPOS_IGNORADOS.has(campo.type)) return;

      // Pula campos marcados com data-no-memory
      if (campo.hasAttribute("data-no-memory")) return;

      // Pula campos dentro de modais (geralmente são temporários)
      if (campo.closest(".modal-selecao-overlay")) return;

      elegiveis.push(campo);
    });

    return elegiveis;
  }

  // ── Salva o valor de um campo no sessionStorage ──
  function salvarCampo(campo) {
    const chave = PREFIXO + campo.id;

    if (campo.type === "checkbox") {
      sessionStorage.setItem(chave, campo.checked ? "1" : "0");
    } else if (campo.type === "radio") {
      if (campo.checked) {
        sessionStorage.setItem(chave, campo.value);
      }
    } else {
      sessionStorage.setItem(chave, campo.value);
    }
  }

  // ── Restaura o valor de um campo do sessionStorage ──
  function restaurarCampo(campo) {
    const chave = PREFIXO + campo.id;
    const salvo = sessionStorage.getItem(chave);

    if (salvo === null) return false; // Nada salvo pra esse campo

    if (campo.type === "checkbox") {
      campo.checked = salvo === "1";
    } else if (campo.type === "radio") {
      campo.checked = campo.value === salvo;
    } else {
      campo.value = salvo;
    }

    return true; // Restaurou com sucesso
  }

  // ── Limpa toda a memória desta página ──
  function limparMemoria() {
    const chavesParaRemover = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const chave = sessionStorage.key(i);
      if (chave && chave.startsWith(PREFIXO)) {
        chavesParaRemover.push(chave);
      }
    }
    chavesParaRemover.forEach((chave) => sessionStorage.removeItem(chave));
  }

  // ── Inicialização ──
  document.addEventListener("DOMContentLoaded", () => {
    const campos = getCamposElegiveis();

    if (campos.length === 0) return; // Página sem formulários

    // 1. RESTAURAR valores salvos
    let restaurados = 0;
    campos.forEach((campo) => {
      if (restaurarCampo(campo)) restaurados++;
    });

    if (restaurados > 0) {
      console.log(
        `🧠 [SessionMemory] ${restaurados} campo(s) restaurado(s) em ${window.location.pathname}`
      );

      // Dispara "change" nos selects restaurados pra reativar lógicas
      // condicionais (ex: campo codigo_nl que aparece quando tipo=REATIVACAO)
      campos.forEach((campo) => {
        if (campo.tagName === "SELECT" && sessionStorage.getItem(PREFIXO + campo.id) !== null) {
          campo.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
    }

    // 2. ESCUTAR mudanças pra salvar automaticamente
    campos.forEach((campo) => {
      const eventos =
        campo.tagName === "SELECT"
          ? ["change"]
          : campo.type === "checkbox" || campo.type === "radio"
            ? ["change"]
            : ["input", "change"]; // input pra digitação, change pra autofill

      eventos.forEach((evento) => {
        campo.addEventListener(evento, () => salvarCampo(campo));
      });
    });

    // 3. OBSERVAR novos campos que aparecem dinamicamente
    // (ex: campos que aparecem via JS depois do DOM carregar)
    const observer = new MutationObserver(() => {
      const camposAtuais = getCamposElegiveis();
      camposAtuais.forEach((campo) => {
        // Se o campo não tem listener ainda, adiciona
        if (!campo._sessionMemoryAtivo) {
          campo._sessionMemoryAtivo = true;

          // Restaura se tiver valor salvo
          restaurarCampo(campo);

          // Escuta mudanças
          const eventos =
            campo.tagName === "SELECT"
              ? ["change"]
              : campo.type === "checkbox" || campo.type === "radio"
                ? ["change"]
                : ["input", "change"];

          eventos.forEach((evento) => {
            campo.addEventListener(evento, () => salvarCampo(campo));
          });
        }
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  });

  // ── API pública (pra outros scripts usarem) ──
  window.sessionMemory = {
    limpar: limparMemoria,
    salvar: salvarCampo,
    restaurar: restaurarCampo,
  };
})();
