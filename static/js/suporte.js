// --- VARIÁVEIS GLOBAIS ---
let navegarLivremente = false;

// Alerta de saída da página (Se tentar fechar a aba sem querer)
window.addEventListener("beforeunload", (event) => {
  if (navegarLivremente) return;
  event.preventDefault();
  event.returnValue = "";
});

// --- INICIALIZAÇÃO DA TELA (UM ÚNICO DOMContentLoaded) ---
document.addEventListener("DOMContentLoaded", function () {
  // 1. Inicia os Tooltips (Somente para PC)
  if (window.innerWidth > 768) {
    var tooltipTriggerList = [].slice.call(
      document.querySelectorAll('[data-bs-toggle="tooltip"]'),
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl, {
        animation: true,
        delay: { show: 100, hide: 100 },
      });
    });
  }

  // 2. Inicia os Popovers (Agora no lugar certo!)
  document
    .querySelectorAll('[data-bs-toggle="popover"]')
    .forEach((el) => new bootstrap.Popover(el));

  // 3. Lógica do Menu Lateral (Sidebar) com Animação Fade
  const linksMenu = document.querySelectorAll(".sidebar a");
  linksMenu.forEach((link) => {
    link.addEventListener("click", function (e) {
      const destino = this.getAttribute("href");
      const alvo = this.getAttribute("target");
      const modal = this.getAttribute("data-bs-toggle");

      // Libera o alerta de fechamento de página ao clicar no menu
      navegarLivremente = true;

      // Se for um link interno real, faz a transição de tela suave
      if (
        destino &&
        destino !== "#" &&
        destino !== "javascript:void(0)" &&
        alvo !== "_blank" &&
        modal !== "modal"
      ) {
        e.preventDefault();
        document.body.classList.add("page-fade-out");

        setTimeout(() => {
          window.location.href = destino;
        }, 350);
      }
    });
  });
});

// --- FUNÇÕES DE AÇÃO (Ficam soltas para serem chamadas pelo HTML) ---

// Função para abrir o Modal Sobre
function abrirSobre() {
  new bootstrap.Modal(document.getElementById("sobreModal")).show();
}

// Função de envio do Chamado ao Python
function enviarChamado(event) {
  event.preventDefault(); // Impede a página de recarregar

  let btn = document.getElementById("btnEnviarChamado");
  let msgBox = document.getElementById("msgRetorno");

  // Dados preenchidos
  let dados = {
    nome: document.getElementById("nomeUser").value,
    setor: document.getElementById("setorUser").value,
    assunto: document.getElementById("assuntoChamado").value,
    mensagem: document.getElementById("mensagemChamado").value,
  };

  // Efeito visual de carregamento no botão
  btn.disabled = true;
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Enviando...';

  // ENVIO PARA O SERVIDOR PYTHON
  fetch("/enviar_chamado", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  })
    .then((r) => r.json())
    .then((data) => {
      btn.disabled = false;
      btn.innerHTML =
        '<i class="fa-solid fa-paper-plane me-2"></i> Enviar Novo Chamado';

      msgBox.classList.remove("d-none", "text-danger", "text-success");

      if (data.status === "ok") {
        msgBox.classList.add("text-success");
        msgBox.innerHTML =
          '<i class="fa-solid fa-check"></i> Chamado enviado com sucesso para a Controladoria!';
        document.getElementById("formSuporte").reset(); // Limpa o formulário
      } else {
        msgBox.classList.add("text-danger");
        msgBox.innerHTML =
          '<i class="fa-solid fa-xmark"></i> Erro: ' + data.msg;
      }
    })
    .catch((e) => {
      btn.disabled = false;
      btn.innerHTML =
        '<i class="fa-solid fa-paper-plane me-2"></i> Enviar Chamado';
      msgBox.classList.remove("d-none", "text-success");
      msgBox.classList.add("text-danger");
      msgBox.innerHTML =
        '<i class="fa-solid fa-triangle-exclamation"></i> Ocorreu um erro de conexão com o servidor.';
    });
}
