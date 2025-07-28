// Configurações globais
let processos = [];
let paginaAtual = 1;
let itensPorPagina = 25;
let ordenacaoColuna = 'numero';
let ordenacaoReversa = false;

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    // Configura links para abrir em nova aba
    document.querySelectorAll('a').forEach(link => {
        if (link.href.includes('/busca')) {
            link.target = '_blank';
        }
    });
    
    // Carrega dados iniciais
    carregarClientes();
    executarBusca();
    
    // Configura eventos
    document.getElementById('itensPorPagina').addEventListener('change', atualizarItensPorPagina);
});

// Nova função para carregar clientes
function carregarClientes() {
    fetch('/busca/api/clientes')
        .then(response => response.json())
        .then(clientes => {
            const select = document.getElementById('cliente');
            select.innerHTML = '<option value="">Todos</option>';
            clientes.forEach(cliente => {
                const option = document.createElement('option');
                option.value = cliente;
                option.textContent = cliente;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Erro ao carregar clientes:', error);
        });
}

// Função principal de busca
function executarBusca() {
    const numeroInicio = document.getElementById('numero_inicio').value;
    const numeroFim = document.getElementById('numero_fim').value;
    
    // Validação básica do intervalo
    if (numeroInicio && numeroFim && parseInt(numeroInicio) > parseInt(numeroFim)) {
        alert("O número inicial deve ser menor ou igual ao número final");
        return;
    }

    const filtros = {
        cliente: document.getElementById('cliente').value,
        numero_inicio: numeroInicio,
        numero_fim: numeroFim,
        ano: document.getElementById('ano').value,
        area: document.getElementById('area').value,
        servico: document.getElementById('servico').value,
        referencia: document.getElementById('referencia').value
    };
    
    // Mostra loading
    const corpoTabela = document.getElementById('corpoTabela');
    corpoTabela.innerHTML = '<tr><td colspan="7" style="text-align: center;">Carregando...</td></tr>';
    
    // Faz a requisição AJAX
    fetch('/busca/api/buscar_processos?' + new URLSearchParams(filtros))
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            processos = Array.isArray(data) ? data : [];
            paginaAtual = 1;
            atualizarTabela();
        })
        .catch(error => {
            console.error('Erro:', error);
            corpoTabela.innerHTML = `<tr><td colspan="7" style="text-align: center; color: red;">
                Erro ao carregar dados: ${error.message || error}
            </td></tr>`;
        });
}

// Limpa os filtros
function limparFiltros() {
    document.getElementById('cliente').value = '';
    document.getElementById('numero_inicio').value = '';
    document.getElementById('numero_fim').value = '';
    document.getElementById('ano').value = '';
    document.getElementById('area').value = '';
    document.getElementById('servico').value = '';
    document.getElementById('referencia').value = '';
    executarBusca();
}

// Ordenação por coluna
function ordenarPor(coluna) {
    if (ordenacaoColuna === coluna) {
        ordenacaoReversa = !ordenacaoReversa;
    } else {
        ordenacaoColuna = coluna;
        ordenacaoReversa = false;
    }
    
    // Atualiza indicadores visuais
    document.querySelectorAll('th').forEach(th => {
        th.innerHTML = th.innerHTML.replace(' ▲', '').replace(' ▼', '');
    });
    
    const thAtual = document.querySelector(`th[onclick="ordenarPor('${coluna}')"]`);
    if (thAtual) {
        thAtual.innerHTML += ordenacaoReversa ? ' ▼' : ' ▲';
    }
    
    // Aplica ordenação
    processos.sort((a, b) => {
        let valorA = a[coluna];
        let valorB = b[coluna];
        
        if (coluna === 'numero') {
            valorA = parseInt(valorA);
            valorB = parseInt(valorB);
        }
        
        if (valorA < valorB) return ordenacaoReversa ? 1 : -1;
        if (valorA > valorB) return ordenacaoReversa ? -1 : 1;
        return 0;
    });
    
    atualizarTabela();
}

// Atualiza a tabela com os dados paginados
function atualizarTabela() {
    const inicio = (paginaAtual - 1) * itensPorPagina;
    const fim = inicio + itensPorPagina;
    const processosPaginados = processos.slice(inicio, fim);
    
    const corpoTabela = document.getElementById('corpoTabela');
    corpoTabela.innerHTML = '';
    
    if (processosPaginados.length === 0) {
        corpoTabela.innerHTML = '<tr><td colspan="7" style="text-align: center;">Nenhum resultado encontrado</td></tr>';
        return;
    }
    
    processosPaginados.forEach(processo => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${processo.numero}</td>
            <td>${processo.cliente}</td>
            <td>${processo.area}</td>
            <td>${processo.servico}</td>
            <td>${processo.ano}</td>
            <td>${processo.referencia}</td>
            <td><button class="btn-abrir" onclick="abrirPasta('${encodeURIComponent(processo.caminho)}')">Abrir Pasta</button></td>
        `;
        
        corpoTabela.appendChild(row);
    });
    
    // Atualiza contador e paginação
    document.getElementById('contador').textContent = `Total: ${processos.length} processos encontrados`;
    
    const totalPaginas = Math.max(1, Math.ceil(processos.length / itensPorPagina));
    document.getElementById('infoPaginacao').textContent = `Página ${paginaAtual} de ${totalPaginas}`;
    
    // Habilita/desabilita botões de paginação
    document.querySelector('button[onclick="paginaAnterior()"]').disabled = paginaAtual <= 1;
    document.querySelector('button[onclick="proximaPagina()"]').disabled = paginaAtual >= totalPaginas;
}

// Função para abrir pasta
function abrirPasta(caminho) {
    caminho = decodeURIComponent(caminho);
    
    // Mostra loading
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Abrindo...';
    
    fetch('/busca/api/abrir_pasta', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            caminho: caminho.replace(/\\/g, '\\\\')
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { 
                throw new Error(err.message || 'Erro no servidor'); 
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.status !== "success") {
            showErrorModal(`Erro ao abrir pasta: ${data.message || 'Contate o administrador'}`);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        showErrorModal(`Falha: ${error.message || 'Verifique:\n1. Se o servidor está acessível\n2. Se a pasta ainda existe'}`);
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-folder-open"></i> Abrir Pasta';
    });
}

function showErrorModal(message) {
    // Implemente um modal de erro mais amigável
    const modal = document.createElement('div');
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.right = '0';
    modal.style.backgroundColor = '#ffebee';
    modal.style.padding = '15px';
    modal.style.zIndex = '1000';
    modal.style.textAlign = 'center';
    modal.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
    
    modal.innerHTML = `
        <p style="margin: 0; color: #c62828; font-weight: bold;">${message}</p>
        <button onclick="this.parentNode.remove()" 
                style="margin-top: 10px; padding: 5px 10px; background: #c62828; color: white; border: none; border-radius: 4px;">
            Fechar
        </button>
    `;
    
    document.body.appendChild(modal);
}

// Controles de paginação
function atualizarItensPorPagina() {
    itensPorPagina = parseInt(document.getElementById('itensPorPagina').value);
    paginaAtual = 1;
    atualizarTabela();
}

function primeiraPagina() {
    paginaAtual = 1;
    atualizarTabela();
}

function paginaAnterior() {
    if (paginaAtual > 1) {
        paginaAtual--;
        atualizarTabela();
    }
}

function proximaPagina() {
    const totalPaginas = Math.ceil(processos.length / itensPorPagina);
    if (paginaAtual < totalPaginas) {
        paginaAtual++;
        atualizarTabela();
    }
}

function ultimaPagina() {
    paginaAtual = Math.ceil(processos.length / itensPorPagina);
    atualizarTabela();
}

// Torna as funções disponíveis globalmente para os eventos HTML
window.executarBusca = executarBusca;
window.limparFiltros = limparFiltros;
window.ordenarPor = ordenarPor;
window.abrirPasta = abrirPasta;
window.atualizarItensPorPagina = atualizarItensPorPagina;
window.primeiraPagina = primeiraPagina;
window.paginaAnterior = paginaAnterior;
window.proximaPagina = proximaPagina;
window.ultimaPagina = ultimaPagina;