// --- FUNÇÕES GLOBAIS E DA PÁGINA INICIAL ---

document.addEventListener("DOMContentLoaded", () => {
  // Controle do Vídeo da Splash Screen
  const splash = document.getElementById("splashScreen");
  const video = document.getElementById("splashVideo");

  if (splash && video) {
    if (sessionStorage.getItem("jaViuLogo")) {
      splash.style.display = "none";
    } else {
      sessionStorage.setItem("jaViuLogo", "true");
      video.src = "/static/videos/videopcciamednovo.mp4";
      video.load();
      video.playbackRate = 2;
      video.play().catch((e) => console.log("Play bloqueado:", e));

      setTimeout(() => {
        splash.style.opacity = "0";
        splash.style.visibility = "hidden";
        setTimeout(() => splash.remove(), 800);
      }, 1450);
    }
  }

  // Ativadores do Bootstrap (Tooltips e Popovers)
  if (window.innerWidth > 768) {
    document
      .querySelectorAll('[data-bs-toggle="tooltip"]')
      .forEach((el) => new bootstrap.Tooltip(el));
  }
  document
    .querySelectorAll('[data-bs-toggle="popover"]')
    .forEach((el) => new bootstrap.Popover(el));

  // Efeito de transição suave ao clicar no menu lateral
  document.querySelectorAll(".sidebar a").forEach((link) => {
    link.addEventListener("click", function (e) {
      const dest = this.getAttribute("href");
      if (dest === "/") return;
      if (
        dest &&
        dest !== "#" &&
        dest !== "javascript:void(0)" &&
        !this.getAttribute("target")
      ) {
        e.preventDefault();
        document.body.classList.add("page-fade-out");
        setTimeout(() => {
          window.location.href = dest;
        }, 350);
      }
    });
  });
});

// Funções Globais (Usadas em várias páginas)
function abrirSobre() {
  new bootstrap.Modal(document.getElementById("sobreModal")).show();
}

function toggleExpandirLog(elementoIcone) {
  const wrapper = elementoIcone.closest(".card-log-wrapper");
  wrapper.classList.toggle("log-expandido");
  if (wrapper.classList.contains("log-expandido")) {
    elementoIcone.classList.replace("fa-expand", "fa-compress");
  } else {
    elementoIcone.classList.replace("fa-compress", "fa-expand");
  }
}
