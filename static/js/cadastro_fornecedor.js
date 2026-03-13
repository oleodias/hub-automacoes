// --- FUNÇÕES DE MÁSCARA ---

// Formata o CNPJ enquanto o usuário digita (00.000.000/0000-00)
document.getElementById("cnpjInput").addEventListener("input", function (e) {
  let value = e.target.value.replace(/\D/g, ""); // Remove tudo que não é número

  // Aplica a formatação
  if (value.length > 14) value = value.slice(0, 14);

  value = value.replace(/^(\d{2})(\d)/, "$1.$2");
  value = value.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
  value = value.replace(/\.(\d{3})(\d)/, ".$1/$2");
  value = value.replace(/(\d{4})(\d)/, "$1-$2");

  e.target.value = value;
});

// Função para formatar o CEP (00000-000)
function formatarCEP(cep) {
  let value = cep.replace(/\D/g, "");
  if (value.length > 8) value = value.slice(0, 8);
  return value.replace(/^(\d{5})(\d)/, "$1-$2");
}

// Função para formatar a data (De AAAA-MM-DD para DD/MM/AAAA)
function formatarData(dataISO) {
  if (!dataISO) return "";
  return dataISO.split("-").reverse().join("/");
}

// --- LÓGICA DE BUSCA NA BRASILAPI ---

document.getElementById("btnConsultar").addEventListener("click", function () {
  // Pega o valor e tira os pontos para enviar para a API
  const cnpj = document.getElementById("cnpjInput").value.replace(/\D/g, "");
  const btn = this;
  const dotStatus = document.getElementById("dot-fornecedor");
  const txtStatus = document.getElementById("txt-fornecedor");

  if (cnpj.length !== 14) {
    txtStatus.innerText = "CNPJ Inválido. Digite 14 números.";
    dotStatus.className = "status-dot bg-danger";
    return;
  }

  // Estado de Carregamento
  btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
  btn.disabled = true;
  txtStatus.innerText = "Consultando Receita Federal...";
  dotStatus.className = "status-dot bg-warning";

  fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.message) throw new Error("CNPJ não encontrado na base.");

      // Preenche os campos
      document.getElementById("razaoSocial").value = data.razao_social;
      document.getElementById("nomeFantasia").value = data.nome_fantasia || "";

      // Novos Campos Inseridos
      document.getElementById("matrizFilial").value =
        data.descricao_identificador_matriz_filial;
      document.getElementById("dataAbertura").value = formatarData(
        data.data_inicio_atividade,
      );

      // Natureza Jurídica agora tem Código + Descrição
      document.getElementById("naturezaJuridica").value =
        `${data.codigo_natureza_juridica} - ${data.natureza_juridica}`;

      // Endereço Completo
      document.getElementById("logradouro").value = data.logradouro;
      document.getElementById("numero").value = data.numero;
      document.getElementById("complemento").value = data.complemento;
      document.getElementById("cep").value = formatarCEP(data.cep);

      // Cidade agora mostra a UF junto (Ex: VIDEIRA - SC)
      document.getElementById("cidade").value =
        `${data.municipio} - ${data.uf}`;

      // CNAE
      document.getElementById("cnaePrincipal").value =
        `${data.cnae_fiscal} - ${data.cnae_fiscal_descricao}`;

      // Atualiza Interface (Sucesso)
      txtStatus.innerText = "Dados carregados com sucesso! Revise e inicie.";
      dotStatus.className = "status-dot bg-success";

      // Mostra o botão de Iniciar o Robô (tira a classe 'd-none')
      document.getElementById("btnIniciarRobo").classList.remove("d-none");
    })
    .catch((err) => {
      // Atualiza Interface (Erro)
      txtStatus.innerText = err.message;
      dotStatus.className = "status-dot bg-danger";

      // Limpa os campos se der erro
      document.getElementById("formFornecedor").reset();
      document.getElementById("btnIniciarRobo").classList.add("d-none");
    })
    .finally(() => {
      // Volta o botão ao normal
      btn.innerHTML = "Buscar";
      btn.disabled = false;
    });
});
