document.addEventListener("DOMContentLoaded", () => {
  const dataHoje = new Date();
  const ultimoDiaMesPassado = new Date(
    dataHoje.getFullYear(),
    dataHoje.getMonth(),
    0,
  );
  const primeiroDiaMesPassado = new Date(
    ultimoDiaMesPassado.getFullYear(),
    ultimoDiaMesPassado.getMonth(),
    1,
  );

  const formatarDataInput = (data) => {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, "0");
    const dia = String(data.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  };

  const inputInicio = document.getElementById("mdf-inicio");
  const inputFim = document.getElementById("mdf-fim");

  if (inputInicio && inputFim) {
    inputInicio.value = formatarDataInput(primeiroDiaMesPassado);
    inputFim.value = formatarDataInput(ultimoDiaMesPassado);
  }

  const splash = document.getElementById("splashScreen");
  const video = document.getElementById("splashVideo");

  if (window.innerWidth > 768) {
    video.src = "/static/videos/videopcciamednovo.mp4";
  } else {
    video.src = "/static/videos/videopcciamednovo.mp4";
  }

  video.load();
  if (video) {
    video.playbackRate = 2;
    video.play().catch((e) => console.log("Play bloqueado:", e));
  }

  setTimeout(() => {
    if (splash) {
      splash.style.opacity = "0";
      splash.style.visibility = "hidden";
      setTimeout(() => splash.remove(), 800);
    }
  }, 1450);

  if (window.innerWidth > 768) {
    document
      .querySelectorAll('[data-bs-toggle="tooltip"]')
      .forEach((el) => new bootstrap.Tooltip(el));
  }
  document
    .querySelectorAll('[data-bs-toggle="popover"]')
    .forEach((el) => new bootstrap.Popover(el));

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
        navegarLivremente = true;
        document.body.classList.add("page-fade-out");
        setTimeout(() => {
          window.location.href = dest;
        }, 350);
      }
    });
  });
});

function toggleExpandirLog(elementoIcone) {
  const wrapper = elementoIcone.closest(".card-log-wrapper");
  wrapper.classList.toggle("log-expandido");
  if (wrapper.classList.contains("log-expandido")) {
    elementoIcone.classList.replace("fa-expand", "fa-compress");
  } else {
    elementoIcone.classList.replace("fa-compress", "fa-expand");
  }
}

function logMDF(mensagem) {
  const logElement = document.getElementById("terminal-mdf");
  const data = new Date().toLocaleTimeString();
  logElement.innerHTML += `<div><span class="log-tempo">[${data}]</span> ${mensagem}</div>`;
  logElement.scrollTop = logElement.scrollHeight;
}

function log(mensagem) {
  const logElement = document.getElementById("terminal");
  if (!logElement) return;
  const data = new Date().toLocaleTimeString();
  logElement.innerHTML += `<div><span class="log-tempo">[${data}]</span> ${mensagem}</div>`;
  logElement.scrollTop = logElement.scrollHeight;
}

function abrirSobre() {
  new bootstrap.Modal(document.getElementById("sobreModal")).show();
}

function alternarTelaCheia() {
  const container = document.getElementById("container-do-log");
  container.classList.toggle("log-expandido");
}

function abrirFerramenta(nome) {
  document.getElementById("tela-dashboard").style.display = "none";
  document.getElementById("tela-fiscal").style.display = "none";
  document.getElementById("tela-mdf").style.display = "none";

  if (nome === "fiscal") {
    document.getElementById("tela-fiscal").style.display = "block";
    document.getElementById("tela-fiscal").style.animation = "fadeIn 0.4s ease";
  } else if (nome === "mdf") {
    document.getElementById("tela-mdf").style.display = "block";
    document.getElementById("tela-mdf").style.animation = "fadeIn 0.4s ease";
    preencherDatasMDF();
  }
}

function voltarDashboard() {
  document.getElementById("tela-fiscal").style.display = "none";
  document.getElementById("tela-mdf").style.display = "none";
  document.getElementById("tela-dashboard").style.display = "block";
  document.getElementById("tela-dashboard").style.animation =
    "fadeIn 0.4s ease";
}

// --- INTEGRAÇÃO UPLOAD XML ---
document.getElementById("fileInput").addEventListener("change", function () {
  let file = this.files[0];
  if (file) {
    document.getElementById("dropZone").classList.add("success");
    document.getElementById("uploadText").innerText = file.name;
    document.getElementById("uploadIcon").className =
      "fa-solid fa-file-circle-check fa-3x text-success";

    console.log(`Carregando XML: ${file.name}...`);
    let formData = new FormData();
    formData.append("file", file);

    fetch("/upload", { method: "POST", body: formData })
      .then((r) => {
        if (!r.ok) throw new Error("Servidor não encontrado");
        return r.json();
      })
      .then((data) => {
        if (data.status === "ok") {
          console.log("✅ Arquivo pronto para auditoria.");
          document.getElementById("dot-fase1").className =
            "status-dot bg-yellow";
          document.getElementById("badge-fase1").className =
            "badge bg-warning text-dark";
          document.getElementById("txt-fase1").innerText =
            "Pronto para iniciar";
          document.getElementById("btn-fase1").disabled = false;
        }
      })
      .catch((err) => {
        console.error("Erro no upload:", err);
        alert(
          "⚠️ Erro de conexão! O Servidor Python está rodando na porta correta?",
        );
      });
  }
});

// --- FASE 1 ---
function rodarFase1() {
  document.getElementById("btn-fase1").disabled = true;
  log("🚀 <b>Iniciando Robô de Triagem (Fase 1)...</b>");
  document.getElementById("dot-fase1").className = "status-dot bg-yellow";

  const source = new EventSource("/run_fase1");

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      document.getElementById("audioSucesso").play();
      log("🎉 <b>Fase 1 Concluída! Itens na fila.</b>");
      document.getElementById("dot-fase1").className = "status-dot bg-green";
      document.getElementById("btn-fase2").disabled = false;
    } else if (event.data === "[FIM_SEM_ITENS]") {
      source.close();
      document.getElementById("audioSucesso").play();
      log("⚠️ <b>Processo finalizado: Nenhum item novo para cadastrar.</b>");
      document.getElementById("dot-fase1").className = "status-dot bg-green";
      document.getElementById("btn-fase2").disabled = true;
    } else {
      log(event.data);
    }
  };

  source.onerror = function (err) {
    source.close();
    log("❌ <b>Erro de conexão com o servidor na Fase 1.</b>");
    document.getElementById("dot-fase1").className = "status-dot bg-red";
    document.getElementById("btn-fase1").disabled = false;
  };
}

// --- FASE 2 ---
function rodarFase2() {
  document.getElementById("btn-fase2").disabled = true;
  document.getElementById("dot-fase2").className = "status-dot bg-yellow";
  document.getElementById("txt-fase2").innerHTML = `<b>Rodando...</b>`;

  log("🚀 <b>Iniciando Robô de Cadastro (Fase 2)...</b>");
  log("--------------------------------------------------");

  const source = new EventSource("/run_fase2");

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      log("--------------------------------------------------");
      log("🎉 <b>Operação Finalizada! Todos os itens estão no ERP.</b><br>");
      document.getElementById("dot-fase2").className = "status-dot bg-green";
      document.getElementById("txt-fase2").innerHTML = `<b>Concluído!</b>`;
      document.getElementById("audioSucesso").play();
    } else {
      log(`💻 <i>${event.data}</i>`);
    }
  };

  source.onerror = function (err) {
    source.close();
    log("❌ <b>Conexão encerrada com o servidor.</b>");
    document.getElementById("dot-fase2").className = "status-dot bg-red";
    document.getElementById("txt-fase2").innerHTML = `<b>Erro</b>`;
    document.getElementById("btn-fase2").disabled = false;
  };
}

// --- MDF ---
function rodarMDF() {
  const inicioRaw = document.getElementById("mdf-inicio").value;
  const fimRaw = document.getElementById("mdf-fim").value;

  if (!inicioRaw || !fimRaw) {
    logMDF(
      "⚠️ <b>Erro: Selecione as datas de início e fim antes de começar!</b>",
    );
    return;
  }

  const formatar = (d) => d.split("-").reverse().join("/");
  const inicio = formatar(inicioRaw);
  const fim = formatar(fimRaw);

  document.getElementById("btn-mdf").disabled = true;
  document.getElementById("btn-download-mdf").style.display = "none";
  document.getElementById("dot-mdf").className = "status-dot bg-yellow";
  document.getElementById("txt-mdf").innerText = "Robô operando...";

  logMDF(`🚀 <b>Iniciando Extração do período ${inicio} até ${fim}...</b>`);

  const source = new EventSource(`/run_mdf?inicio=${inicio}&fim=${fim}`);

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      document.getElementById("audioSucesso").volume = 0.5;
      document.getElementById("audioSucesso").play();
      logMDF("🎉 <b>Processo Finalizado com sucesso! Planilha gerada.</b>");
      document.getElementById("dot-mdf").className = "status-dot bg-green";
      document.getElementById("txt-mdf").innerText = "Concluído!";
      document.getElementById("btn-mdf").disabled = false;
      document.getElementById("btn-download-mdf").style.display = "block";
    } else {
      logMDF(event.data);
    }
  };

  source.onerror = function (err) {
    source.close();
    logMDF("❌ <b>Erro de conexão. O processo pode ter sido interrompido.</b>");
    document.getElementById("dot-mdf").className = "status-dot bg-red";
    document.getElementById("txt-mdf").innerText = "Erro de Conexão";
    document.getElementById("btn-mdf").disabled = false;
  };
}

let navegarLivremente = false;
window.addEventListener("beforeunload", (event) => {
  if (navegarLivremente) return;
  event.preventDefault();
  event.returnValue = "";
});

function baixarRelatorio() {
  navegarLivremente = true;
  window.location.href = "/download_mdf";
  setTimeout(() => {
    navegarLivremente = false;
  }, 1000);
}

function limparDatas() {
  document.getElementById("mdf-inicio").value = "";
  document.getElementById("mdf-fim").value = "";
  logMDF("🧹 <b>Datas limpas.</b> Insira o novo período.");
}

function preencherDatasMDF() {
  const dataHoje = new Date();
  const ultimoDiaMesPassado = new Date(
    dataHoje.getFullYear(),
    dataHoje.getMonth(),
    0,
  );
  const primeiroDiaMesPassado = new Date(
    ultimoDiaMesPassado.getFullYear(),
    ultimoDiaMesPassado.getMonth(),
    1,
  );

  const formatarDataInput = (data) => {
    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, "0");
    const dia = String(data.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  };

  const inputInicio = document.getElementById("mdf-inicio");
  const inputFim = document.getElementById("mdf-fim");

  if (inputInicio && inputFim && !inputInicio.value && !inputFim.value) {
    inputInicio.value = formatarDataInput(primeiroDiaMesPassado);
    inputFim.value = formatarDataInput(ultimoDiaMesPassado);
  }
}
