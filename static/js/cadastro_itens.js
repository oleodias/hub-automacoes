// --- LÓGICA DO MÓDULO: CADASTRO DE ITENS (FISCAL) ---

function log(mensagem) {
  const logElement = document.getElementById("terminal");
  if (!logElement) return;
  const data = new Date().toLocaleTimeString();
  logElement.innerHTML += `<div><span class="log-tempo">[${data}]</span> ${mensagem}</div>`;
  logElement.scrollTop = logElement.scrollHeight;
}

function alternarTelaCheia() {
  const container = document.getElementById("container-do-log");
  container.classList.toggle("log-expandido");
}

// INTEGRAÇÃO UPLOAD XML
const fileInput = document.getElementById("fileInput");
if (fileInput) {
  fileInput.addEventListener("change", function () {
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
            log("✅ Arquivo carregado. Pronto para auditoria.");
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
          alert("⚠️ Erro de conexão! O Servidor Python está rodando?");
        });
    }
  });
}

// FASE 1
function rodarFase1() {
  document.getElementById("btn-fase1").disabled = true;
  log("🚀 <b>Iniciando Robô de Triagem (Fase 1)...</b>");
  document.getElementById("dot-fase1").className = "status-dot bg-yellow";

  const source = new EventSource("/run_fase1");

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();

      // Trava de segurança do áudio
      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();

      log("🎉 <b>Fase 1 Concluída! Itens na fila.</b>");
      document.getElementById("dot-fase1").className = "status-dot bg-green";

      // AGORA SIM ELE DESTRAVA O BOTÃO!
      document.getElementById("btn-fase2").disabled = false;
    } else if (event.data === "[FIM_SEM_ITENS]") {
      source.close();

      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();

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

// FASE 2
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
      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();
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
