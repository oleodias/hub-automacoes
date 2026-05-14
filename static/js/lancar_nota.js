// ══════════════════════════════════════════════════════════════
// lancar_nota.js — lógica da página de Lançamento de Nota
// ══════════════════════════════════════════════════════════════
// Fluxo: 4 abas (steps) em sequência.
//   1. Upload do XML → /notas/upload_xml
//   2. Preencher CC por item
//   3. Revisar/editar parcelas
//   4. Datas + operação → /notas/lancar
//
// Estado é mantido em memória JS (não usa localStorage). Recarregar
// a página descarta tudo — é proposital, pra evitar dados antigos.
// ══════════════════════════════════════════════════════════════

(function() {
'use strict';

// ══════════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ══════════════════════════════════════════════════════════════

const estado = {
    abaAtual: 1,
    xmlPath: null,
    dadosXml: null,
    dropdowns: { centros_custo: {}, operacoes: [] },
    centrosPorItem: {},       // { item_numero: codigo_cc }
    parcelas: [],             // [{ numero, data_vencimento, valor }]
    modoManualParcelas: false,
    dataRecebimento: '',
    dataBase: '',
    operacaoCodigo: '',
};

// ══════════════════════════════════════════════════════════════
// INICIALIZAÇÃO
// ══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    bindUpload();
    bindNavegacao();
    bindAplicarTodos();
    bindParcelas();
    bindFormFinal();
    await carregarDropdowns();
});

async function carregarDropdowns() {
    try {
        const resp = await fetch('/notas/dropdowns');
        const data = await resp.json();
        estado.dropdowns = data;
        popularCcAplicarTodos();
    } catch (e) {
        console.error('Falha ao carregar dropdowns:', e);
        alert('Erro ao carregar centros de custo e operações. Recarregue a página.');
    }
}

function popularCcAplicarTodos() {
    const sel = document.getElementById('cc-aplicar-todos');
    sel.innerHTML = '<option value="">— selecione —</option>';
    for (const [empresa, ccs] of Object.entries(estado.dropdowns.centros_custo)) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = empresa;
        ccs.forEach(cc => {
            const opt = document.createElement('option');
            opt.value = cc.codigo;
            opt.textContent = `${cc.codigo} — ${cc.descricao}`;
            optgroup.appendChild(opt);
        });
        sel.appendChild(optgroup);
    }
}

// ══════════════════════════════════════════════════════════════
// ABA 1 — UPLOAD DO XML
// ══════════════════════════════════════════════════════════════

function bindUpload() {
    const zona  = document.getElementById('upload-zona');
    const input = document.getElementById('input-xml');

    zona.addEventListener('click', () => input.click());

    zona.addEventListener('dragover', (e) => {
        e.preventDefault();
        zona.classList.add('arrastando');
    });
    zona.addEventListener('dragleave', () => zona.classList.remove('arrastando'));
    zona.addEventListener('drop', (e) => {
        e.preventDefault();
        zona.classList.remove('arrastando');
        if (e.dataTransfer.files.length > 0) {
            enviarXml(e.dataTransfer.files[0]);
        }
    });

    input.addEventListener('change', () => {
        if (input.files.length > 0) {
            enviarXml(input.files[0]);
        }
    });
}

async function enviarXml(arquivo) {
    if (!arquivo.name.toLowerCase().endsWith('.xml')) {
        mostrarStatusUpload('O arquivo precisa ter extensão .xml', 'erro');
        return;
    }

    mostrarLoading('Lendo o XML...');

    const fd = new FormData();
    fd.append('xml', arquivo);

    try {
        const resp = await fetch('/notas/upload_xml', { method: 'POST', body: fd });
        const data = await resp.json();
        esconderLoading();

        if (data.status === 'ok') {
            estado.xmlPath = data.xml_path;
            estado.dadosXml = data.dados;
            estado.parcelas = JSON.parse(JSON.stringify(data.dados.duplicatas || []));
            renderizarResumo(data.dados);
            renderizarItens(data.dados.itens);
            renderizarParcelas();
            atualizarTotalizadores();
            mostrarStatusUpload(`XML lido com sucesso: ${arquivo.name}`, 'ok');
            atualizarBotoes();
            atualizarStepCompleta(1);
        } else {
            mostrarStatusUpload(data.msg || 'Erro ao processar o XML.', 'erro');
        }
    } catch (e) {
        esconderLoading();
        console.error(e);
        mostrarStatusUpload('Erro de rede ao enviar o XML.', 'erro');
    }
}

function mostrarStatusUpload(msg, tipo) {
    const el = document.getElementById('upload-status');
    el.textContent = msg;
    el.className = `upload-status ${tipo}`;
}

function renderizarResumo(dados) {
    const r = document.getElementById('resumo-nota');
    document.getElementById('r-numero').textContent     = `${dados.numero_nota} / ${dados.serie}`;
    document.getElementById('r-emissao').textContent    = formatarData(dados.data_emissao);
    document.getElementById('r-fornecedor').textContent = dados.emitente.razao_social || '—';
    document.getElementById('r-cnpj').textContent       = dados.emitente.cnpj_formatado || '—';
    document.getElementById('r-itens').textContent      = `${dados.itens.length} ${dados.itens.length === 1 ? 'item' : 'itens'}`;
    document.getElementById('r-parcelas').textContent   = `${dados.duplicatas.length}x`;
    document.getElementById('r-total').textContent      = formatarMoeda(dados.totais.valor_total_nota);
    r.classList.remove('oculto');
}

// ══════════════════════════════════════════════════════════════
// ABA 2 — ITENS E CENTROS DE CUSTO
// ══════════════════════════════════════════════════════════════

function renderizarItens(itens) {
    const tbody = document.getElementById('tbody-itens');
    tbody.innerHTML = '';

    itens.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="numero">${item.numero}</td>
            <td>${escapeHtml(item.codigo)}</td>
            <td>${escapeHtml(item.descricao)}</td>
            <td class="valor">${item.quantidade.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            <td class="valor">${formatarMoeda(item.valor_unitario)}</td>
            <td class="valor">${formatarMoeda(item.valor_total)}</td>
            <td>${gerarSelectCc(item.numero)}</td>
        `;
        tbody.appendChild(tr);
    });

    // Bind dos selects gerados
    tbody.querySelectorAll('.select-cc').forEach(sel => {
        sel.addEventListener('change', (e) => {
            const itemNumero = parseInt(e.target.dataset.itemNumero, 10);
            estado.centrosPorItem[itemNumero] = e.target.value || null;
            if (!e.target.value) delete estado.centrosPorItem[itemNumero];
            atualizarContadorCC();
            atualizarBotoes();
        });
    });

    atualizarContadorCC();
}

function gerarSelectCc(itemNumero) {
    let html = `<select class="select-cc" data-item-numero="${itemNumero}">`;
    html += '<option value="">— selecione —</option>';
    for (const [empresa, ccs] of Object.entries(estado.dropdowns.centros_custo)) {
        html += `<optgroup label="${escapeHtml(empresa)}">`;
        ccs.forEach(cc => {
            html += `<option value="${cc.codigo}">${cc.codigo} — ${escapeHtml(cc.descricao)}</option>`;
        });
        html += '</optgroup>';
    }
    html += '</select>';
    return html;
}

function atualizarContadorCC() {
    const total       = estado.dadosXml ? estado.dadosXml.itens.length : 0;
    const preenchidos = Object.keys(estado.centrosPorItem).length;
    const cont = document.getElementById('contador-cc');
    cont.textContent = `${preenchidos} de ${total} itens preenchidos`;
    cont.classList.toggle('completo', preenchidos === total && total > 0);
}

function bindAplicarTodos() {
    document.getElementById('btn-aplicar-todos').addEventListener('click', () => {
        const codigo = document.getElementById('cc-aplicar-todos').value;
        if (!codigo) {
            alert('Selecione um centro de custo para aplicar.');
            return;
        }
        document.querySelectorAll('.select-cc[data-item-numero]').forEach(sel => {
            sel.value = codigo;
            const itemNumero = parseInt(sel.dataset.itemNumero, 10);
            estado.centrosPorItem[itemNumero] = codigo;
        });
        atualizarContadorCC();
        atualizarBotoes();
    });
}

// ══════════════════════════════════════════════════════════════
// ABA 3 — PARCELAMENTO
// ══════════════════════════════════════════════════════════════

function bindParcelas() {
    document.getElementById('btn-editar-parcelas').addEventListener('click', () => {
        estado.modoManualParcelas = !estado.modoManualParcelas;
        document.getElementById('distribuir-area').classList.toggle('oculto', !estado.modoManualParcelas);
        document.getElementById('info-auto').classList.toggle('oculto', estado.modoManualParcelas);
        document.getElementById('info-manual').classList.toggle('oculto', !estado.modoManualParcelas);
        renderizarParcelas();
    });

    document.getElementById('btn-distribuir').addEventListener('click', () => {
        const qtd       = parseInt(document.getElementById('qtd-parcelas').value, 10);
        const primeiro  = document.getElementById('primeiro-vencimento').value;
        const intervalo = parseInt(document.getElementById('intervalo-dias').value, 10);

        if (!primeiro) {
            alert('Informe a data do primeiro vencimento.');
            return;
        }

        const valorTotal = estado.dadosXml.totais.valor_total_nota;
        // Distribui o valor: as primeiras parcelas pegam a parte inteira, a última
        // recebe a diferença pra somar exatamente o total (sem erro de centavo)
        const valorBase = Math.floor((valorTotal / qtd) * 100) / 100;
        const ultimaSoma = (valorTotal - valorBase * (qtd - 1)).toFixed(2);

        const novas = [];
        const dataIni = new Date(primeiro + 'T00:00:00');
        for (let i = 0; i < qtd; i++) {
            const d = new Date(dataIni);
            d.setDate(d.getDate() + intervalo * i);
            novas.push({
                numero: String(i + 1).padStart(3, '0'),
                data_vencimento: d.toISOString().slice(0, 10),
                valor: i === qtd - 1 ? parseFloat(ultimaSoma) : valorBase,
            });
        }
        estado.parcelas = novas;
        renderizarParcelas();
        atualizarTotalizadores();
    });
}

function renderizarParcelas() {
    const tbody = document.getElementById('tbody-parcelas');
    tbody.innerHTML = '';

    estado.parcelas.forEach((p, idx) => {
        const tr = document.createElement('tr');
        const editavel = estado.modoManualParcelas;

        tr.innerHTML = `
            <td class="numero">${escapeHtml(p.numero)}</td>
            <td>
                <input type="date" data-idx="${idx}" data-campo="data_vencimento"
                       value="${p.data_vencimento}" ${editavel ? '' : 'readonly'}>
            </td>
            <td>
                <input type="number" step="0.01" min="0.01" data-idx="${idx}" data-campo="valor"
                       value="${parseFloat(p.valor).toFixed(2)}" ${editavel ? '' : 'readonly'}>
            </td>
            <td>
                ${editavel ? `<button class="btn-remover-parcela" data-idx="${idx}" title="Remover">
                    <i class="fas fa-trash"></i>
                </button>` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Bind dos inputs editáveis
    tbody.querySelectorAll('input').forEach(inp => {
        inp.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.idx, 10);
            const campo = e.target.dataset.campo;
            const val = campo === 'valor' ? parseFloat(e.target.value) || 0 : e.target.value;
            estado.parcelas[idx][campo] = val;
            atualizarTotalizadores();
            atualizarBotoes();
        });
    });

    tbody.querySelectorAll('.btn-remover-parcela').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.currentTarget.dataset.idx, 10);
            estado.parcelas.splice(idx, 1);
            // Renumera
            estado.parcelas.forEach((p, i) => p.numero = String(i + 1).padStart(3, '0'));
            renderizarParcelas();
            atualizarTotalizadores();
            atualizarBotoes();
        });
    });
}

function atualizarTotalizadores() {
    if (!estado.dadosXml) return;

    const total = estado.dadosXml.totais.valor_total_nota;
    const soma  = estado.parcelas.reduce((acc, p) => acc + (parseFloat(p.valor) || 0), 0);
    const diff  = soma - total;

    document.getElementById('tot-soma').textContent     = formatarMoeda(soma);
    document.getElementById('tot-nota').textContent     = formatarMoeda(total);
    document.getElementById('tot-diferenca').textContent = formatarMoeda(Math.abs(diff));

    const bloco = document.getElementById('tot-validacao');
    bloco.classList.remove('ok', 'erro');
    if (Math.abs(diff) < 0.01) {
        bloco.classList.add('ok');
        document.getElementById('tot-diferenca').textContent = 'R$ 0,00 ✓';
    } else {
        bloco.classList.add('erro');
    }
}

// ══════════════════════════════════════════════════════════════
// ABA 4 — DATAS E OPERAÇÃO
// ══════════════════════════════════════════════════════════════

function bindFormFinal() {
    document.getElementById('data-recebimento').addEventListener('change', (e) => {
        estado.dataRecebimento = e.target.value;
        atualizarBotoes();
    });
    document.getElementById('data-base').addEventListener('change', (e) => {
        estado.dataBase = e.target.value;
        atualizarBotoes();
    });

    // Autocomplete de operação
    const busca = document.getElementById('busca-operacao');
    const resultados = document.getElementById('op-resultados');

    busca.addEventListener('input', () => filtrarOperacoes(busca.value));
    busca.addEventListener('focus', () => filtrarOperacoes(busca.value));
    busca.addEventListener('blur', () => {
        // Pequeno delay pra permitir o clique no item
        setTimeout(() => resultados.classList.add('oculto'), 200);
    });

    document.querySelector('.btn-limpar-op').addEventListener('click', () => {
        estado.operacaoCodigo = '';
        document.getElementById('operacao-codigo').value = '';
        document.getElementById('op-selecionada').classList.add('oculto');
        document.getElementById('busca-operacao').value = '';
        document.getElementById('busca-operacao').classList.remove('oculto');
        atualizarBotoes();
    });

    document.getElementById('btn-lancar').addEventListener('click', enviarLancamento);
}

function filtrarOperacoes(termo) {
    const resultados = document.getElementById('op-resultados');
    const termoLower = (termo || '').trim().toLowerCase();

    if (!termoLower) {
        resultados.classList.add('oculto');
        return;
    }

    const filtradas = estado.dropdowns.operacoes.filter(op => {
        return op.codigo.toLowerCase().includes(termoLower)
            || op.descricao.toLowerCase().includes(termoLower);
    }).slice(0, 30);

    resultados.innerHTML = '';
    if (filtradas.length === 0) {
        resultados.innerHTML = '<div class="op-item-vazio">Nenhuma operação encontrada</div>';
    } else {
        filtradas.forEach(op => {
            const item = document.createElement('div');
            item.className = 'op-item';
            item.innerHTML = `<span class="codigo">${escapeHtml(op.codigo)}</span><span class="descricao">${escapeHtml(op.descricao)}</span>`;
            item.addEventListener('mousedown', (e) => {
                // mousedown roda antes do blur, garantindo que o click chega
                e.preventDefault();
                selecionarOperacao(op);
            });
            resultados.appendChild(item);
        });
    }
    resultados.classList.remove('oculto');
}

function selecionarOperacao(op) {
    estado.operacaoCodigo = op.codigo;
    document.getElementById('operacao-codigo').value = op.codigo;
    document.getElementById('op-selecionada-texto').textContent = `${op.codigo} — ${op.descricao}`;
    document.getElementById('op-selecionada').classList.remove('oculto');
    document.getElementById('busca-operacao').classList.add('oculto');
    document.getElementById('op-resultados').classList.add('oculto');
    atualizarBotoes();
}

// ══════════════════════════════════════════════════════════════
// NAVEGAÇÃO ENTRE ABAS
// ══════════════════════════════════════════════════════════════

function bindNavegacao() {
    document.getElementById('btn-anterior').addEventListener('click', () => irParaAba(estado.abaAtual - 1));
    document.getElementById('btn-proximo').addEventListener('click', () => {
        if (estado.abaAtual < 4) {
            atualizarStepCompleta(estado.abaAtual);
            irParaAba(estado.abaAtual + 1);
        }
    });
}

function irParaAba(num) {
    if (num < 1 || num > 4) return;

    document.querySelectorAll('.ln-aba').forEach(s => s.classList.remove('ativa'));
    document.getElementById(`aba-${num}`).classList.add('ativa');

    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    document.querySelector(`.step[data-step="${num}"]`).classList.add('active');

    estado.abaAtual = num;

    if (num === 4) renderizarResumoFinal();

    atualizarBotoes();
}

function atualizarStepCompleta(num) {
    document.querySelector(`.step[data-step="${num}"]`).classList.add('completa');
}

function atualizarBotoes() {
    const btnAnt    = document.getElementById('btn-anterior');
    const btnProx   = document.getElementById('btn-proximo');
    const btnLancar = document.getElementById('btn-lancar');

    btnAnt.disabled = estado.abaAtual === 1;

    if (estado.abaAtual < 4) {
        btnProx.classList.remove('oculto');
        btnLancar.classList.add('oculto');
        btnProx.disabled = !abaCompleta(estado.abaAtual);
    } else {
        btnProx.classList.add('oculto');
        btnLancar.classList.remove('oculto');
        btnLancar.disabled = !abaCompleta(4);
    }
}

function abaCompleta(num) {
    if (num === 1) return !!estado.dadosXml;
    if (num === 2) {
        const total = estado.dadosXml ? estado.dadosXml.itens.length : 0;
        return total > 0 && Object.keys(estado.centrosPorItem).length === total;
    }
    if (num === 3) {
        if (estado.parcelas.length === 0) return false;
        const total = estado.dadosXml.totais.valor_total_nota;
        const soma  = estado.parcelas.reduce((acc, p) => acc + (parseFloat(p.valor) || 0), 0);
        return Math.abs(soma - total) < 0.01
            && estado.parcelas.every(p => p.data_vencimento && parseFloat(p.valor) > 0);
    }
    if (num === 4) {
        return !!estado.dataRecebimento && !!estado.dataBase && !!estado.operacaoCodigo;
    }
    return false;
}

function renderizarResumoFinal() {
    if (!estado.dadosXml) return;
    document.getElementById('rf-fornecedor').textContent = estado.dadosXml.emitente.razao_social;
    document.getElementById('rf-nota').textContent       = `${estado.dadosXml.numero_nota} / ${estado.dadosXml.serie}`;
    document.getElementById('rf-valor').textContent      = formatarMoeda(estado.dadosXml.totais.valor_total_nota);
    document.getElementById('rf-itens').textContent      = `${estado.dadosXml.itens.length}`;
    document.getElementById('rf-parcelas').textContent   = `${estado.parcelas.length}x`;
}

// ══════════════════════════════════════════════════════════════
// ENVIO FINAL
// ══════════════════════════════════════════════════════════════

async function enviarLancamento() {
    const payload = {
        xml_path: estado.xmlPath,
        dados_xml: estado.dadosXml,
        dados_complementares: {
            centros_custo: Object.entries(estado.centrosPorItem).map(([item_numero, codigo_cc]) => ({
                item_numero: parseInt(item_numero, 10),
                codigo_cc,
            })),
            parcelas: estado.parcelas.map(p => ({
                numero: p.numero,
                data_vencimento: p.data_vencimento,
                valor: parseFloat(p.valor),
            })),
            data_recebimento: estado.dataRecebimento,
            data_base: estado.dataBase,
            operacao_codigo: estado.operacaoCodigo,
        },
    };

    mostrarLoading('Enviando para a fila...');

    try {
        const resp = await fetch('/notas/lancar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        esconderLoading();

        if (data.status === 'ok') {
            alert(`✓ ${data.msg}\nID do lançamento: ${data.id}`);
            // Reset pra próxima nota
            window.location.reload();
        } else {
            const erros = (data.erros || [data.msg]).join('\n  • ');
            alert(`Não foi possível lançar:\n  • ${erros}`);
        }
    } catch (e) {
        esconderLoading();
        console.error(e);
        alert('Erro de rede ao enviar o lançamento.');
    }
}

// ══════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════

function mostrarLoading(msg) {
    document.getElementById('ln-loading-msg').textContent = msg || 'Processando...';
    document.getElementById('ln-loading').classList.remove('oculto');
}

function esconderLoading() {
    document.getElementById('ln-loading').classList.add('oculto');
}

function formatarMoeda(v) {
    const n = parseFloat(v) || 0;
    return n.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
}

function formatarData(iso) {
    if (!iso) return '—';
    const [a, m, d] = iso.split('-');
    return `${d}/${m}/${a}`;
}

function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

})();
