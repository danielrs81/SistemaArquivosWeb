// Configurações globais
let processos = [];
let paginaAtual = 1;
let itensPorPagina = 25;
let ordenacaoColuna = 'numero';
let ordenacaoReversa = false;
let processosSelecionados = [];
let arquivosLote = [];

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
        corpoTabela.innerHTML = '<tr><td colspan="8" style="text-align: center;">Nenhum resultado encontrado</td></tr>';
        return;
    }
    
    processosPaginados.forEach(processo => {
        const isSelected = processosSelecionados.includes(processo.numero);
        const row = document.createElement('tr');
        
        if (isSelected) {
            row.style.backgroundColor = '#e3f2fd';
        }
        
        row.innerHTML = `
            <td><input type="checkbox" class="processo-checkbox" 
                 ${isSelected ? 'checked' : ''}
                 onchange="toggleSelecaoProcesso('${processo.numero}')"></td>
            <td>${processo.numero}</td>
            <td>${processo.cliente}</td>
            <td>${processo.area}</td>
            <td>${processo.servico}</td>
            <td>${processo.ano}</td>
            <td>${processo.referencia}</td>
            <td><button class="btn-open" onclick="abrirPasta('${encodeURIComponent(processo.caminho)}')">
                <i class="fas fa-folder-open"></i> Abrir
            </button></td>
        `;
        
        corpoTabela.appendChild(row);
    });
    
    // Atualiza contador e paginação
    document.getElementById('contador').textContent = processos.length;
    
    const totalPaginas = Math.max(1, Math.ceil(processos.length / itensPorPagina));
    document.getElementById('infoPaginacao').textContent = `Página ${paginaAtual} de ${totalPaginas}`;
    
    // Habilita/desabilita botões de paginação
    document.querySelector('button[onclick="paginaAnterior()"]').disabled = paginaAtual <= 1;
    document.querySelector('button[onclick="proximaPagina()"]').disabled = paginaAtual >= totalPaginas;
    
    // Atualiza UI dos processos selecionados
    atualizarUIProcessosSelecionados();
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

// Mostrar/ocultar campos de despesa
document.querySelectorAll('input[name="tipoInclusao"]').forEach(radio => {
    radio.addEventListener('change', function() {
        document.getElementById('despesaFields').style.display = 
            this.value === 'despesas' ? 'block' : 'none';
    });
});

// Função para enviar lote
async function enviarLote() {
    if (processosSelecionados.length === 0) {
        mostrarResultadoLote({
            status: "error",
            message: "Selecione um processo antes de enviar"
        });
        return;
    }
    
    if (arquivosLote.length === 0) {
        mostrarResultadoLote({
            status: "error",
            message: "Adicione pelo menos um arquivo"
        });
        return;
    }
    
    const tipo = document.querySelector('input[name="tipoInclusao"]:checked').value;
    const btnEnviar = document.querySelector('#acoesEmLote .btn-primary');
    
    try {
        btnEnviar.disabled = true;
        btnEnviar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
        
        const formData = new FormData();
        arquivosLote.forEach(file => formData.append('files', file));
        formData.append('processo', processosSelecionados[0]);
        formData.append('tipo', tipo);
        
        console.log("Enviando requisição para /busca/api/enviar_lote");
        console.log("Dados do formulário:", {
            processo: processosSelecionados[0],
            tipo: tipo,
            arquivos: arquivosLote.map(f => f.name)
        });

        const response = await fetch('/busca/api/enviar_lote', {
            method: 'POST',
            body: formData,
            headers: {
                'Accept': 'application/json'
            }
        });

        console.log("Resposta recebida:", response);

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Erro na resposta:", errorText);
            throw new Error(errorText || "Erro no servidor");
        }

        const result = await response.json();
        console.log("Resultado do upload:", result);

        // ✅ Agora verificamos se o arquivo já existe
        if (result.status === "exists") {
            let confirmar = confirm(
                `Os seguintes arquivos já existem:\n\n${result.arquivos.join("\n")}\n\nDeseja enviar mesmo assim (eles serão renomeados com data e hora)?`
            );
            if (confirmar) {
                const formData2 = new FormData();
                arquivosLote.forEach(file => formData2.append('files', file));
                formData2.append('processo', processosSelecionados[0]);
                formData2.append('tipo', tipo);
                formData2.append('forceRename', 'true');

                const response2 = await fetch('/busca/api/enviar_lote', {
                    method: 'POST',
                    body: formData2,
                    headers: {'Accept': 'application/json'}
                });
                const result2 = await response2.json();
                mostrarResultadoLote(result2);

                if (result2.status === "success") {
                    arquivosLote = [];
                    atualizarListaArquivos();
                }

                return;
            } else {
                mostrarResultadoLote({
                    status: "warning",
                    message: "Envio cancelado pelo usuário"
                });
                return;
            }
        }
        
        mostrarResultadoLote(result);
        
        if (result.status === "success") {
            arquivosLote = [];
            atualizarListaArquivos();
        }
    } catch (error) {
        console.error("Erro no envio:", error);
        mostrarResultadoLote({
            status: "error",
            message: "Erro no envio: " + (error.message || "Verifique o console para detalhes")
        });
    } finally {
        btnEnviar.disabled = false;
        btnEnviar.innerHTML = '<i class="fas fa-paper-plane"></i> Enviar Arquivos';
    }
}


function mostrarResultadoLote(result) {
    const resultDiv = document.getElementById('uploadResultLote');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = result.message;
    
    if (result.status === "success") {
        resultDiv.style.backgroundColor = '#d4edda';
        resultDiv.style.color = '#155724';
        resultDiv.style.border = '1px solid #c3e6cb';
    } else {
        resultDiv.style.backgroundColor = '#f8d7da';
        resultDiv.style.color = '#721c24';
        resultDiv.style.border = '1px solid #f5c6cb';
    }
}

// Adicione estas funções para gerenciar seleção de processos:
function toggleSelecaoProcesso(numeroProcesso) {
    // Se já está selecionado, desmarca
    if (processosSelecionados.includes(numeroProcesso)) {
        processosSelecionados = [];
    } 
    // Se não está selecionado, desmarca qualquer outro e seleciona este
    else {
        processosSelecionados = [numeroProcesso];
    }
    atualizarTabela();
    atualizarUIProcessosSelecionados();
}

function limparSelecao() {
    processosSelecionados = [];
    atualizarTabela();
    atualizarUIProcessosSelecionados();
}

function atualizarUIProcessosSelecionados() {
    const acoesEmLote = document.getElementById('acoesEmLote');
    const contadorSelecionados = document.getElementById('contadorSelecionados');
    
    if (processosSelecionados.length > 0) {
        acoesEmLote.style.display = 'block';
        contadorSelecionados.textContent = `${processosSelecionados.length} processo(s) selecionado(s)`;
    } else {
        acoesEmLote.style.display = 'none';
    }
}

function configurarDragAndDrop() {
    const dragArea = document.getElementById('dragAreaLote');
    const fileInput = document.getElementById('fileInputLote');

    // Clique na área para abrir o seletor de arquivos
    dragArea.addEventListener('click', () => fileInput.click());

    // Quando arquivos são escolhidos manualmente
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            Array.from(e.target.files).forEach(file => {
                if (!arquivosLote.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
                    arquivosLote.push(file);
                }
            });
            atualizarListaArquivos();
            e.target.value = ''; // Permite escolher o mesmo arquivo novamente
        }
    });

    // Previne o comportamento padrão do navegador nos eventos de drag
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dragArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Destaque visual quando o usuário arrasta um arquivo para dentro da área
    ['dragenter', 'dragover'].forEach(eventName => {
        dragArea.addEventListener(eventName, highlight, false);
    });

    // Remove destaque quando sai da área
    ['dragleave', 'drop'].forEach(eventName => {
        dragArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dragArea.style.borderColor = '#2980b9';
        dragArea.style.backgroundColor = '#ebf5fb';
    }

    function unhighlight() {
        dragArea.style.borderColor = '#3498db';
        dragArea.style.backgroundColor = '';
    }

    // Quando arquivos são soltos na área de drag-and-drop
    dragArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        Array.from(files).forEach(file => {
            if (!arquivosLote.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
                arquivosLote.push(file);
            }
        });

        atualizarListaArquivos();
    }
}

function atualizarListaArquivos() {
    const fileList = document.getElementById('fileListLote');
    fileList.innerHTML = '';
    
    arquivosLote.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>${file.name}</span>
            <button onclick="removerArquivoLote(${index})">
                <i class="fas fa-times"></i>
            </button>
        `;
        fileList.appendChild(fileItem);
    });
}

function removerArquivoLote(index) {
    arquivosLote.splice(index, 1);
    atualizarListaArquivos();
}

// Chame esta função no DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    configurarDragAndDrop();
    
    // Mostrar/ocultar campos de despesa
    document.querySelectorAll('input[name="tipoInclusao"]').forEach(radio => {
        radio.addEventListener('change', function() {
            document.getElementById('despesaFields').style.display = 
                this.value === 'despesas' ? 'block' : 'none';
        });
    });
});


document.getElementById('vencimento').addEventListener('blur', function() {
    if (!/^\d{2}-\d{2}$/.test(this.value)) {
        alert("Formato inválido. Use DD-MM (ex: 25-07)");
        this.focus();
    }
});

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