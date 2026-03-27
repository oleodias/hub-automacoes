document.addEventListener("DOMContentLoaded", () => {
  const chaveInput = document.getElementById("chaveInput");
  const btnConsultar = document.getElementById("btnConsultar");

  // Máscara para a Chave de Acesso (agrupa de 4 em 4 números)
  chaveInput.addEventListener("input", function (e) {
    let value = e.target.value.replace(/\D/g, "");
    let formatted = "";
    for (let i = 0; i < value.length; i++) {
      if (i > 0 && i % 4 === 0) formatted += " ";
      formatted += value[i];
    }
    e.target.value = formatted;
  });

  // Evento de clique
  btnConsultar.addEventListener("click", async () => {
    const chaveCrua = chaveInput.value.replace(/\D/g, "");

    if (chaveCrua.length !== 44) {
      atualizarStatus("A chave deve conter 44 números.", "red");
      return;
    }

    iniciarCarregamento();

    try {
      const response = await fetch(`/api/consulta_cte/${chaveCrua}`);
      const data = await response.json();

      if (data.erro) {
        atualizarStatus(data.message, "red");
        document.getElementById("resultado-wrap").style.display = "none";
        return;
      }

      preencherDados(data);
    } catch (error) {
      atualizarStatus("Erro de conexão com o servidor interno.", "red");
    }
  });
});

function iniciarCarregamento() {
  const btn = document.getElementById("btnConsultar");
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-1"></i> Buscando...';
  btn.disabled = true;
  document.getElementById("resultado-wrap").style.display = "none";
  atualizarStatus("Consultando portal da SEFAZ...", "yellow");
}

function atualizarStatus(texto, cor) {
  const btn = document.getElementById("btnConsultar");
  btn.innerHTML = '<i class="fa-solid fa-search me-1"></i> Consultar';
  btn.disabled = false;

  document.getElementById("txtStatus").innerText = texto;
  const dot = document.getElementById("dotStatus");
  dot.className = `status-dot bg-${cor}`;
}

function preencherDados(data) {
  // Preenche a tela com os dados raspados pelo Python
  document.getElementById("cteChave").innerText = formatarChave(data.chave);
  document.getElementById("cteStatus").innerText = data.status_sefaz;
  document.getElementById("cteEmitente").innerText = data.emitente;
  document.getElementById("cteCnpjEmitente").innerText = data.cnpj_emitente;
  document.getElementById("cteDestinatario").innerText = data.destinatario;
  document.getElementById("cteValor").innerText = `R$ ${data.valor_total}`;
  document.getElementById("cteData").innerText = data.data_emissao;

  document.getElementById("resultado-wrap").style.display = "block";
  atualizarStatus("CT-e consultado com sucesso!", "green");
}

function formatarChave(chave) {
  return chave.replace(/(\d{4})/g, "$1 ").trim();
}
