function trocarAba(aba, btn) {
  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.remove("ativo"));
  document
    .querySelectorAll(".tab-conteudo")
    .forEach((c) => c.classList.remove("ativo"));
  btn.classList.add("ativo");
  document.getElementById("aba-" + aba).classList.add("ativo");
}


let chamados = [], filtroChamados = 'todos', chamadosStats = {};

function carregarChamados() {
    var url = '/api/suporte/admin/chamados';
    if (filtroChamados !== 'todos') url += '?status=' + filtroChamados;

    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            chamados = data.chamados || [];
            chamadosStats = data.stats || {};
            var st = chamadosStats;
            var el;
            el = document.getElementById('ch-stat-total'); if (el) el.textContent = st.total || 0;
            el = document.getElementById('ch-stat-pendente'); if (el) el.textContent = st.pendente || 0;
            el = document.getElementById('ch-stat-analise'); if (el) el.textContent = st.em_analise || 0;
            el = document.getElementById('ch-stat-resolvido'); if (el) el.textContent = st.resolvido || 0;
            document.getElementById('tab-count-chamados').textContent = chamadosStats.total || 0;
            renderizarChamados();
        });
}

function filtrarChamados(s, btn) {
    filtroChamados = s;
    document.querySelectorAll('.filtro-btn').forEach(function(b) { b.classList.remove('ativo'); });
    btn.classList.add('ativo');
    carregarChamados();
}

function calcularSLA(createdAt, prioridade, status) {
    if (status === 'resolvido' || status === 'cancelado') return '';

    var partes = createdAt.split(' ');
    if (partes.length < 2) return '';
    var d = partes[0].split('/');
    var h = partes[1].split(':');
    var criado = new Date(d[2], d[1] - 1, d[0], h[0], h[1]);
    var agora = new Date();
    var horasDecorridas = (agora - criado) / (1000 * 60 * 60);

    var slaHoras = { 'critica': 0.5, 'alta': 2, 'media': 8, 'baixa': 24 };
    var limite = slaHoras[prioridade] || 8;
    var percentual = (horasDecorridas / limite) * 100;

    var cor, icone, texto;
    if (percentual >= 100) {
        cor = '#ef4444'; icone = '🔴'; texto = 'SLA ESTOURADO';
    } else if (percentual >= 75) {
        cor = '#f97316'; icone = '🟠'; texto = 'SLA em risco';
    } else if (percentual >= 50) {
        cor = '#f59e0b'; icone = '🟡'; texto = 'Atenção';
    } else {
        cor = '#16a34a'; icone = '🟢'; texto = 'No prazo';
    }

    var tempoStr;
    if (horasDecorridas < 1) {
        tempoStr = Math.floor(horasDecorridas * 60) + 'min';
    } else if (horasDecorridas < 24) {
        tempoStr = Math.floor(horasDecorridas) + 'h';
    } else {
        tempoStr = Math.floor(horasDecorridas / 24) + 'd';
    }

    return '<span style="font-size:11px;color:' + cor + ';font-weight:600;margin-left:8px" title="' +
        texto + ' — ' + tempoStr + ' de ' + limite + 'h">' +
        icone + ' ' + tempoStr + '</span>';
}

function renderizarChamados() {
    var c = document.getElementById('lista-chamados');
    var l = chamados;
    var prioPeso = { 'critica': 4, 'alta': 3, 'media': 2, 'baixa': 1 };
    l.sort(function(a, b) {
        var statusPeso = { 'pendente': 2, 'em_analise': 2, 'resolvido': 0, 'cancelado': 0 };
        var diffStatus = (statusPeso[b.status] || 0) - (statusPeso[a.status] || 0);
        if (diffStatus !== 0) return diffStatus;
        var diffPrio = (prioPeso[b.prioridade] || 0) - (prioPeso[a.prioridade] || 0);
        if (diffPrio !== 0) return diffPrio;
        return b.id - a.id;
    });

    if (!l.length) {
        c.innerHTML = '<div class="vazio">Nenhum chamado encontrado.</div>';
        return;
    }

    var statusLabels = {
        'pendente': 'Pendente',
        'em_analise': 'Em Análise',
        'resolvido': 'Resolvido',
        'cancelado': 'Cancelado'
    };

    var statusBadgeClass = {
        'pendente': 'badge-pendente',
        'em_analise': 'badge-analise',
        'resolvido': 'badge-ativo',
        'cancelado': 'badge-inativo'
    };

    var prioridadeLabels = {
        'baixa': 'Baixa',
        'media': 'Média',
        'alta': 'Alta',
        'critica': 'Crítica'
    };

    var prioridadeColors = {
        'baixa': '#3b82f6',
        'media': '#f59e0b',
        'alta': '#f97316',
        'critica': '#ef4444'
    };

    c.innerHTML = l.map(function(x) {
        var statusLabel = statusLabels[x.status] || x.status;
        var badgeClass = statusBadgeClass[x.status] || 'badge-pendente';
        var prioLabel = prioridadeLabels[x.prioridade] || 'Média';
        var prioColor = prioridadeColors[x.prioridade] || '#f59e0b';
        var anexosCount = (x.anexos && x.anexos.length) ? ' · <i class="fa-solid fa-paperclip"></i> ' + x.anexos.length + ' anexo(s)' : '';

        return '<div class="chamado-card">' +
            '<div class="chamado-topo">' +
                '<span class="chamado-nome">' +
                    '<i class="fa-solid fa-user" style="margin-right:6px;color:var(--teal)"></i>' +
                    escHtmlAdmin(x.usuario) +
                '</span>' +
                '<span class="chamado-data">' +
                    '<span style="font-weight:600;color:var(--teal);margin-right:8px">#' +
                      escHtmlAdmin(x.protocolo) + '</span>' +
                      calcularSLA(x.created_at, x.prioridade, x.status) +
                      escHtmlAdmin(x.created_at) +
                '</span>' +
            '</div>' +
            '<div class="chamado-assunto">' + escHtmlAdmin(x.assunto) + '</div>' +
            '<div class="chamado-msg">' + escHtmlAdmin(x.mensagem) + '</div>' +
            '<div class="chamado-footer">' +
                '<span class="chamado-setor">' +
                    '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + prioColor + ';margin-right:4px"></span>' +
                    prioLabel + ' · ' +
                    '<i class="fa-solid fa-cube" style="margin-right:4px"></i>' +
                    escHtmlAdmin(x.modulo_nome) +
                    anexosCount +
                '</span>' +
                '<div class="chamado-acoes">' +
                    '<span class="badge ' + badgeClass + '">' + statusLabel + '</span>' +
                    '<select onchange="mudarStatusChamado(' + x.id + ', this.value)">' +
                        '<option value="pendente"' + (x.status === 'pendente' ? ' selected' : '') + '>Pendente</option>' +
                        '<option value="em_analise"' + (x.status === 'em_analise' ? ' selected' : '') + '>Em Análise</option>' +
                        '<option value="resolvido"' + (x.status === 'resolvido' ? ' selected' : '') + '>Resolvido</option>' +
                        '<option value="cancelado"' + (x.status === 'cancelado' ? ' selected' : '') + '>Cancelado</option>' +
                    '</select>' +
                    '<button class="btn-acao" onclick="abrirModalResponder(' + x.id + ')" title="Responder" style="color:var(--teal)">' +
                        '<i class="fa-solid fa-reply"></i>' +
                    '</button>' +
                    '<button class="btn-acao danger" onclick="deletarChamado(' + x.id + ')" title="Excluir">' +
                        '<i class="fa-solid fa-trash"></i>' +
                    '</button>' +
                '</div>' +
            '</div>' +
        '</div>';
    }).join('');
}

function mudarStatusChamado(id, s) {
    fetch('/api/suporte/admin/chamados/' + id + '/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: s })
    }).then(function() { carregarChamados(); });
}

function deletarChamado(id) {
    if (!confirm('Excluir este chamado definitivamente?')) return;
    fetch('/api/suporte/admin/chamados/' + id, { method: 'DELETE' })
        .then(function() { carregarChamados(); });
}

// ── Modal de Resposta ─────────────────────────────────────

var chamadoResponderId = null;

function abrirModalResponder(id) {
    chamadoResponderId = id;
    fetch('/api/suporte/chamados/' + id)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status !== 'ok') return;
            var ch = data.chamado;
            document.getElementById('resp-protocolo').textContent = '#' + ch.protocolo;
            document.getElementById('resp-assunto').textContent = ch.assunto;
            document.getElementById('resp-usuario').textContent = ch.usuario;
            document.getElementById('resp-mensagem').textContent = ch.mensagem;
            document.getElementById('resp-status-select').value = ch.status;
            document.getElementById('resp-texto').value = '';

            var timelineEl = document.getElementById('resp-timeline');
            if (ch.historico && ch.historico.length) {
                timelineEl.innerHTML = ch.historico.map(function(h) {
                    var icon = '📝';
                    if (h.tipo === 'criacao') icon = '🟢';
                    else if (h.tipo === 'mudanca_status') icon = '🔄';
                    else if (h.tipo === 'resposta_admin') icon = '💬';
                    var msg = h.mensagem || (h.status_anterior ? h.status_anterior + ' → ' + h.status_novo : h.tipo);
                    return '<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px solid #f1f5f9">' +
                        '<span style="font-size:14px">' + icon + '</span>' +
                        '<div style="flex:1">' +
                            '<div style="font-size:12px;color:#475569">' + escHtmlAdmin(h.usuario) + ' · ' + escHtmlAdmin(h.created_at) + '</div>' +
                            '<div style="font-size:13px;color:#0f172a">' + escHtmlAdmin(msg) + '</div>' +
                        '</div>' +
                    '</div>';
                }).join('');
            } else {
                timelineEl.innerHTML = '<div style="color:#94a3b8;font-size:13px">Sem histórico</div>';
            }

            document.getElementById('modalResponder').style.display = 'flex';
        });
}

function fecharModalResponder() {
    document.getElementById('modalResponder').style.display = 'none';
    chamadoResponderId = null;
}

function enviarResposta() {
    var texto = document.getElementById('resp-texto').value.trim();
    var novoStatus = document.getElementById('resp-status-select').value;

    if (!texto) {
        alert('Escreva uma resposta antes de enviar.');
        return;
    }

    fetch('/api/suporte/admin/chamados/' + chamadoResponderId + '/responder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resposta: texto, status: novoStatus })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.status === 'ok') {
            fecharModalResponder();
            carregarChamados();
        } else {
            alert(data.msg || 'Erro ao enviar resposta.');
        }
    });
}

function escHtmlAdmin(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}


let usuarios = [];
function carregarUsuarios() {
  fetch("/api/usuarios")
    .then((r) => r.json())
    .then((data) => {
      usuarios = data;
      document.getElementById("tab-count-usuarios").textContent =
        data.length;
      document.getElementById("stat-total").textContent = data.length;
      document.getElementById("stat-ativos").textContent = data.filter(
        (u) => u.ativo,
      ).length;
      document.getElementById("stat-admins").textContent = data.filter(
        (u) => u.cargo === "admin",
      ).length;
      document.getElementById("stat-operadores").textContent = data.filter(
        (u) => u.cargo === "operador",
      ).length;
      renderizarUsuarios();
    });
}

function renderizarUsuarios() {
  const t = document.getElementById("tabela-usuarios");
  if (!usuarios.length) {
    t.innerHTML =
      '<tr><td colspan="6" class="vazio">Nenhum usuário.</td></tr>';
    return;
  }
  t.innerHTML = usuarios
    .map(
      (u) =>
        `<tr><td style="font-weight:600;color:var(--text-primary)">${u.nome}</td><td>${u.email}</td><td><span class="badge ${u.cargo === "admin" ? "badge-admin" : "badge-operador"}">${u.cargo}</span></td><td><span class="badge ${u.ativo ? "badge-ativo" : "badge-inativo"}">${u.ativo ? "Ativo" : "Inativo"}</span></td><td style="color:var(--text-secondary);font-size:0.8rem">${u.created_at}</td><td><div class="acoes"><button class="btn-acao" onclick="abrirModalEditar(${u.id})" title="Editar"><i class="fa-solid fa-pen-to-square"></i></button><button class="btn-acao" onclick="abrirModalResetSenha(${u.id})" title="Resetar Senha"><i class="fa-solid fa-key"></i></button><button class="btn-acao" onclick="toggleUsuario(${u.id})" title="${u.ativo ? "Desativar" : "Ativar"}"><i class="fa-solid fa-toggle-${u.ativo ? "on" : "off"}"></i></button><button class="btn-acao danger" onclick="deletarUsuario(${u.id},'${u.nome}')" title="Deletar"><i class="fa-solid fa-trash"></i></button></div></td></tr>`,
    )
    .join("");
}

function abrirModalCriar() {
  document.getElementById("modal-titulo").textContent = "Novo Usuário";
  document.getElementById("edit-id").value = "";
  document.getElementById("edit-nome").value = "";
  document.getElementById("edit-email").value = "";
  document.getElementById("edit-senha").value = "";
  document.getElementById("edit-cargo").value = "operador";
  document.getElementById("campo-senha").style.display = "block";
  esconderFeedback();
  document
    .querySelectorAll("#permissoes-grid input[type=checkbox]")
    .forEach((cb) => (cb.checked = true));
  document.getElementById("modal-usuario").classList.add("ativo");
}

function abrirModalEditar(id) {
  const u = usuarios.find((x) => x.id === id);
  if (!u) return;
  document.getElementById("modal-titulo").textContent = "Editar Usuário";
  document.getElementById("edit-id").value = u.id;
  document.getElementById("edit-nome").value = u.nome;
  document.getElementById("edit-email").value = u.email;
  document.getElementById("edit-cargo").value = u.cargo;
  document.getElementById("campo-senha").style.display = "none";
  esconderFeedback();
  document
    .querySelectorAll("#permissoes-grid input[type=checkbox]")
    .forEach((cb) => {
      cb.checked = u.permissoes[cb.getAttribute("data-modulo")] !== false;
    });
  document.getElementById("modal-usuario").classList.add("ativo");
}

function fecharModal() {
  document.getElementById("modal-usuario").classList.remove("ativo");
}

function salvarUsuario() {
  const id = document.getElementById("edit-id").value,
    nome = document.getElementById("edit-nome").value.trim(),
    email = document.getElementById("edit-email").value.trim(),
    senha = document.getElementById("edit-senha").value.trim(),
    cargo = document.getElementById("edit-cargo").value,
    permissoes = {};
  document
    .querySelectorAll("#permissoes-grid input[type=checkbox]")
    .forEach((cb) => {
      permissoes[cb.getAttribute("data-modulo")] = cb.checked;
    });
  if (!nome || !email) {
    mostrarErro("modal-erro", "Nome e email são obrigatórios.");
    return;
  }
  if (!id && !senha) {
    mostrarErro("modal-erro", "Senha é obrigatória.");
    return;
  }
  const body = { nome, email, cargo, permissoes };
  if (!id) body.senha = senha;
  fetch(id ? `/api/usuarios/${id}` : "/api/usuarios", {
    method: id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
    .then((r) => r.json())
    .then((d) => {
      if (d.erro) mostrarErro("modal-erro", d.erro);
      else {
        fecharModal();
        carregarUsuarios();
      }
    });
}

function toggleUsuario(id) {
  const u = usuarios.find((x) => x.id === id);
  if (!u || !confirm(`${u.ativo ? "Desativar" : "Ativar"} "${u.nome}"?`))
    return;
  fetch(`/api/usuarios/${id}/toggle`, { method: "POST" })
    .then((r) => r.json())
    .then((d) => {
      if (d.erro) alert(d.erro);
      else carregarUsuarios();
    });
}

function deletarUsuario(id, nome) {
  if (!confirm(`Deletar "${nome}"?`)) return;
  fetch(`/api/usuarios/${id}`, { method: "DELETE" })
    .then((r) => r.json())
    .then((d) => {
      if (d.erro) alert(d.erro);
      else carregarUsuarios();
    });
}

function abrirModalResetSenha(id) {
  const u = usuarios.find((x) => x.id === id);
  if (!u) return;
  document.getElementById("reset-id").value = u.id;
  document.getElementById("reset-nome").textContent = u.nome;
  document.getElementById("reset-nova-senha").value = "";
  esconderFeedback();
  document.getElementById("modal-senha").classList.add("ativo");
}

function fecharModalSenha() {
  document.getElementById("modal-senha").classList.remove("ativo");
}

function resetarSenha() {
  const id = document.getElementById("reset-id").value,
    senha = document.getElementById("reset-nova-senha").value.trim();
  if (senha.length < 4) {
    mostrarErro("senha-erro", "Mínimo 4 caracteres.");
    return;
  }
  fetch(`/api/usuarios/${id}/reset_senha`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ senha }),
  })
    .then((r) => r.json())
    .then((d) => {
      if (d.erro) mostrarErro("senha-erro", d.erro);
      else {
        fecharModalSenha();
        alert("Senha resetada!");
      }
    });
}

function mostrarErro(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.style.display = "block";
}

function esconderFeedback() {
  document
    .querySelectorAll(".msg-feedback")
    .forEach((el) => (el.style.display = "none"));
}

// ── Histórico de Execuções ────────────────────────────────────────────────────
function carregarHistorico() {
  const robo = document.getElementById("filtro-robo").value;
  const status = document.getElementById("filtro-status-hist").value;
  const dataDe = document.getElementById("filtro-data-de").value;
  const dataAte = document.getElementById("filtro-data-ate").value;

  let url = "/api/execucoes?limite=200";
  if (robo) url += `&robo=${robo}`;
  if (status) url += `&status=${status}`;
  if (dataDe) url += `&data_de=${dataDe}`;
  if (dataAte) url += `&data_ate=${dataAte}`;

  fetch(url)
    .then((r) => r.json())
    .then((data) => {
      document.getElementById("tab-count-historico").textContent =
        data.stats.total;
      document.getElementById("hist-total").textContent = data.stats.total;
      document.getElementById("hist-sucesso").textContent =
        data.stats.sucesso;
      document.getElementById("hist-erro").textContent = data.stats.erro;
      document.getElementById("hist-taxa").textContent =
        data.stats.taxa_sucesso + "%";
      renderizarHistorico(data.execucoes);
    });
}

function renderizarHistorico(execucoes) {
  const tbody = document.getElementById("tabela-historico");
  if (!execucoes.length) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="vazio">Nenhuma execução encontrada.</td></tr>';
    return;
  }

  const statusBadge = {
    sucesso: "badge-ativo",
    erro: "badge-inativo",
    executando: "badge-pendente",
    aviso: "badge-analise",
  };

  const statusLabel = {
    sucesso: "Sucesso",
    erro: "Erro",
    executando: "Executando",
    aviso: "Aviso",
  };

  tbody.innerHTML = execucoes
    .map((e) => {
      let detStr = "—";
      const d = e.detalhes || {};
      const partes = [];
      if (d.periodo_inicio)
        partes.push("Período: " + d.periodo_inicio + " a " + d.periodo_fim);
      if (d.cnpj) partes.push("CNPJ: " + d.cnpj);
      if (d.razao_social) partes.push(d.razao_social);
      if (d.arquivo_xml) partes.push("XML: " + d.arquivo_xml);
      if (d.erro) partes.push("Erro: " + d.erro);
      if (partes.length) detStr = partes.join(" | ");

      return `<tr>
        <td style="font-weight:600;color:var(--text-primary)">${e.robo_nome}</td>
        <td>${e.usuario_nome}</td>
        <td style="font-size:0.8rem;color:var(--text-secondary)">${e.inicio}</td>
        <td style="font-weight:600">${e.duracao_fmt}</td>
        <td><span class="badge ${statusBadge[e.status] || ""}">${statusLabel[e.status] || e.status}</span></td>
        <td style="font-size:0.78rem;color:var(--text-secondary);max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${detStr}">${detStr}</td>
      </tr>`;
    })
    .join("");
}

document.addEventListener("DOMContentLoaded", () => {
  carregarChamados();
  carregarUsuarios();
  carregarHistorico();
});
