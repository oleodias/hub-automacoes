// --- LÓGICA DO MÓDULO: RELATÓRIO MDF-E ---

document.addEventListener("DOMContentLoaded", () => {
  preencherDatasMDF();
});

function logMDF(mensagem) {
  const logElement = document.getElementById("terminal-mdf");
  if (!logElement) return;
  const data = new Date().toLocaleTimeString();
  logElement.innerHTML += `<div><span class="log-tempo">[${data}]</span> ${mensagem}</div>`;
  logElement.scrollTop = logElement.scrollHeight;
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

function limparDatas() {
  document.getElementById("mdf-inicio").value = "";
  document.getElementById("mdf-fim").value = "";
  logMDF("🧹 <b>Datas limpas.</b> Insira o novo período.");
}

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
      const audio = document.getElementById("audioSucesso");
      if (audio) {
        audio.volume = 0.5;
        audio.play();
      }
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
