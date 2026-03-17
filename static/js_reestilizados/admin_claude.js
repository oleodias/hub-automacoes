// --- VARIÁVEIS GLOBAIS ---
let filtroAtual = "todos";
let ordemAtual = "desc";
let navegarLivremente = false;

// Alerta de saída da página
window.addEventListener("beforeunload", (event) => {
  if (navegarLivremente) return;
  event.preventDefault();
  event.returnValue = "";
});

// --- INICIALIZAÇÃO DA TELA E MENU ---
document.addEventListener("DOMContentLoaded", () => {
  // 1. Tooltips do Menu
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

  // 2. Lógica do Menu Lateral (Sidebar) com Animação Fade
  const linksMenu = document.querySelectorAll(".sidebar a");
  linksMenu.forEach((link) => {
    link.addEventListener("click", function (e) {
      const destino = this.getAttribute("href");
      const alvo = this.getAttribute("target");
      const modal = this.getAttribute("data-bs-toggle");

      navegarLivremente = true;

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

// --- LÓGICA DE LOGIN ---
function tentarLogin() {
  const senha = document.getElementById("senhaAdmin").value;
  if (senha === "admin") {
    document.getElementById("erroLogin").classList.add("d-none");
    document.body.classList.add("dashboard-active");
    carregarChamados(); // Carrega pela primeira vez
  } else {
    document.getElementById("erroLogin").classList.remove("d-none");
  }
}

function verificarEnter(event) {
  if (event.key === "Enter") tentarLogin();
}

function sairPainel() {
  document.body.classList.remove("dashboard-active");
  document.getElementById("senhaAdmin").value = "";
}

// --- NOVAS FUNÇÕES DE FILTRO E ORDENAÇÃO ---
function aplicarFiltro(status, botaoElement) {
  filtroAtual = status;
  // Pinta o botão clicado
  document
    .querySelectorAll(".btn-filter")
    .forEach((btn) => btn.classList.remove("active"));
  botaoElement.classList.add("active");
  carregarChamados(); // Recarrega a lista aplicando o filtro
}

function mudarOrdem(ordem) {
  ordemAtual = ordem;
  carregarChamados(); // Recarrega a lista aplicando a ordem
}

// --- FUNÇÃO MESTRA (CARREGA, FILTRA E DESENHA) ---
function carregarChamados() {
  fetch("/api/chamados")
    .then((r) => r.json())
    .then((chamadosTotais) => {
      // 1. APLICAR O FILTRO DE STATUS
      let chamados = chamadosTotais;
      if (filtroAtual !== "todos") {
        chamados = chamadosTotais.filter((c) => c.status === filtroAtual);
      }

      // 2. APLICAR A ORDENAÇÃO POR DATA (Usando o ID, que é um timestamp)
      chamados.sort((a, b) => {
        if (ordemAtual === "desc") {
          return b.id - a.id; // Maior pro menor (Mais Novo Primeiro)
        } else {
          return a.id - b.id; // Menor pro maior (Mais Antigo Primeiro)
        }
      });

      // 3. ATUALIZAR O CONTADOR DE TELA
      document.getElementById("contadorTickets").innerText =
        `${chamados.length} Chamados (${filtroAtual})`;

      const container = document.getElementById("ticketsContainer");

      // 4. VERIFICAR SE TÁ VAZIO
      if (chamados.length === 0) {
        container.innerHTML = `<div class="text-center text-muted mt-5"><i class="fa-solid fa-inbox fa-3x mb-3"></i><p>Nenhum chamado encontrado para este filtro.</p></div>`;
        return;
      }

      // 5. DESENHAR OS CARDS
      let html = "";
      chamados.forEach((c) => {
        let badgeClass =
          c.status === "pendente"
            ? "bg-warning text-dark"
            : c.status === "analise"
              ? "bg-info text-dark"
              : "bg-success";

        let cardClass =
          c.status === "resolvido"
            ? "resolvido"
            : c.status === "analise"
              ? "analise"
              : "";

        html += `
            <div class="card ticket-card ${cardClass} p-3">
                <div class="ticket-header">
                    <div>
                        <span class="badge ${badgeClass} mb-1" id="badge-${c.id}">${c.status.toUpperCase()}</span>
                        <h6 class="mb-0 fw-bold text-dark ${c.status === "resolvido" ? "text-decoration-line-through" : ""}">${c.assunto}</h6>
                    </div>
                    <div class="text-end text-muted small">
                        <i class="fa-regular fa-clock"></i> ${c.data}<br>
                        <strong>Setor: ${c.setor}</strong>
                    </div>
                </div>
                <p class="text-muted small mb-3">
                    <strong>De: ${c.nome}</strong><br>
                    ${c.mensagem}
                </p>
                <div class="ticket-actions text-end">
                    ${
                      c.status !== "resolvido"
                        ? `
                        <button class="btn-analise" onclick="mudarStatus(${c.id}, 'analise')"><i class="fa-solid fa-magnifying-glass"></i> Em Análise</button>
                        <button class="btn-resolvido" id="btn-${c.id}" onclick="marcarResolvido(${c.id})"><i class="fa-solid fa-check"></i> Resolvido</button>
                        `
                        : ""
                    }
                    <button class="btn-excluir" onclick="deletarChamado(${c.id})"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>`;
      });
      container.innerHTML = html;
    });
}

// --- AÇÕES DOS BOTÕES ---
function mudarStatus(id, novoStatus) {
  fetch(`/api/chamados/${id}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: novoStatus }),
  }).then(() => carregarChamados()); // Recarrega a lista faz o item sumir se o filtro não for 'todos'!
}

function marcarResolvido(idChamado) {
  if (!confirm("Tem certeza que deseja marcar este chamado como resolvido?"))
    return;

  fetch(`/api/chamados/${idChamado}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "resolvido" }),
  })
    .then(() => carregarChamados())
    .catch((err) => console.error("Erro ao resolver chamado:", err));
}

function deletarChamado(id) {
  if (confirm("Tem certeza que deseja apagar este chamado definitivamente?")) {
    fetch(`/api/chamados/${id}`, { method: "DELETE" }).then(() =>
      carregarChamados(),
    );
  }
}
