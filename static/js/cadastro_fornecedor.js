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

// Função para formatar o CNPJ que vem da API
function formatarCNPJ(cnpj) {
  if (!cnpj) return "";
  let value = cnpj.replace(/\D/g, "");
  return value.replace(
    /^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2}).*/,
    "$1.$2.$3/$4-$5",
  );
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

  // Em vez de ir na BrasilAPI, o JS pede pro seu próprio servidor Python buscar!
  fetch(`/consulta_cnpj/${cnpj}`)
    .then((response) => response.json())
    .then((data) => {
      // Se o Python avisar que deu erro, a gente para por aqui
      if (data.erro || data.message === "CNPJ não encontrado na base.") {
        throw new Error(data.message || "Erro na consulta.");
      }

      // Preenche os campos normais
      document.getElementById("razaoSocial").value = data.razao_social;
      // PREENCHE O NOVO CAMPO DE CNPJ FORMATADO
      document.getElementById("cnpjCapturado").value = formatarCNPJ(data.cnpj);
      document.getElementById("nomeFantasia").value = data.nome_fantasia || "";

      // Preenche a Inscrição Estadual na tela
      document.getElementById("inscricaoEstadual").value =
        data.inscricao_estadual || "";

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

      // PREENCHE O BAIRRO
      document.getElementById("bairro").value = data.bairro || "";

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
      // Atualiza Interface (Erro amigável)
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

// --- LÓGICA DO ROBÔ (INTEGRAÇÃO COM PYTHON) ---

function logFornecedor(mensagem) {
  const terminal = document.getElementById("terminal-fornecedor");
  if (!terminal) return;
  const hora = new Date().toLocaleTimeString();
  terminal.innerHTML += `<div><span class="log-tempo">[${hora}]</span> ${mensagem}</div>`;
  terminal.scrollTop = terminal.scrollHeight;
}

function iniciarCadastroERP() {
  const btn = document.getElementById("btnIniciarRobo");
  btn.disabled = true;
  btn.innerHTML =
    '<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Operando ERP...';

  // Pega a UF separando do campo cidade (Ex: "VIDEIRA - SC" -> Pega só o "SC")
  const cidadeUF = document.getElementById("cidade").value.split(" - ");
  const uf = cidadeUF.length > 1 ? cidadeUF[1] : "";

  // Monta o pacote de dados para enviar ao Python
  const dados = {
    cnpj: document.getElementById("cnpjInput").value,
    razao_social: document.getElementById("razaoSocial").value,
    nome_fantasia: document.getElementById("nomeFantasia").value,
    inscricao_estadual: document.getElementById("inscricaoEstadual").value,
    cep: document.getElementById("cep").value,
    logradouro: document.getElementById("logradouro").value,
    numero: document.getElementById("numero").value,
    complemento: document.getElementById("complemento").value,
    bairro: document.getElementById("bairro").value,
    uf: uf,
  };

  logFornecedor(`🚀 <b>Iniciando Robô para o CNPJ: ${dados.cnpj}</b>`);

  // Converte os dados e chama a rota do Python
  const jsonString = encodeURIComponent(JSON.stringify(dados));
  const source = new EventSource(`/run_fornecedor?dados=${jsonString}`);

  source.onmessage = function (event) {
    if (event.data === "[FIM_DO_PROCESSO]") {
      source.close();
      logFornecedor("🎉 <b>Processo Finalizado!</b>");

      const audio = document.getElementById("audioSucesso");
      if (audio) audio.play();

      btn.innerHTML =
        '<i class="fa-solid fa-check-double me-2"></i> Cadastro Concluído';
      btn.classList.replace("btn-success", "btn-secondary"); // Fica cinza indicando que terminou
    } else {
      logFornecedor(event.data);
    }
  };

  source.onerror = function () {
    source.close();
    logFornecedor("❌ <b>Erro de conexão com o servidor.</b>");
    btn.disabled = false;
    btn.innerHTML =
      '<i class="fa-solid fa-rotate-right me-2"></i> Tentar Novamente';
  };
}
