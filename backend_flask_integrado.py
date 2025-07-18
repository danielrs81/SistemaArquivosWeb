from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_from_directory
import os
import shutil
import re
from werkzeug.utils import secure_filename
from configparser import ConfigParser
from clientes import obter_clientes, adicionar_cliente, remover_cliente
from logica import criar_pasta, copiar_arquivos, obter_info_processos
import logging
from datetime import datetime
from flask import render_template
from busca import busca_bp
from flask import Blueprint

app = Flask(__name__)
app.register_blueprint(busca_bp, url_prefix='/busca')
config = ConfigParser()
config.read('config.ini')

# Configurar logging
logging.basicConfig(filename='flask.log', level=logging.ERROR)

# Criar pastas necessárias
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

STATIC_FOLDER = os.path.join(os.getcwd(), 'static')
os.makedirs(STATIC_FOLDER, exist_ok=True)

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sistema de Arquivos Digitais</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --light-color: #ecf0f1;
            --dark-color: #34495e;
            --success-color: #2ecc71;
            --border-radius: 8px;
            --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f7fa;
            color: #333;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary-color), var(--dark-color));
            color: white;
            padding: 20px;
            border-radius: var(--border-radius);
            margin-bottom: 25px;
            box-shadow: var(--box-shadow);
            text-align: center;
        }
        
        .header h1 {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            margin: 0;
        }
        
        .header h1 i {
            color: var(--secondary-color);
        }
        
        .card {
            background: white;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            padding: 25px;
            margin-bottom: 25px;
        }
        
        .card-title {
            color: var(--primary-color);
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--light-color);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card-title i {
            color: var(--secondary-color);
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: var(--dark-color);
        }
        
        .form-group select, 
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            background-color: var(--light-color);
            transition: all 0.3s;
        }
        
        .form-group select:focus, 
        .form-group input:focus {
            border-color: var(--secondary-color);
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
            outline: none;
        }
        
        .action-buttons {
            display: flex;
            gap: 15px;
            margin-top: 10px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: var(--border-radius);
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background-color: var(--secondary-color);
            color: white;
        }
        
        .btn-secondary {
            background-color: var(--dark-color);
            color: white;
        }
        
        .btn-success {
            background-color: var(--success-color);
            color: white;
        }
        
        .btn-danger {
            background-color: var(--accent-color);
            color: white;
        }
        
        .btn:hover {
            opacity: 0.9;
            transform: translateY(-2px);
        }
        
        /* Estilos para a área de arquivos */
        .file-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .file-list {
            margin-top: 10px;
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: var(--border-radius);
            padding: 10px;
        }
        
        .file-item {
            display: grid;
            grid-template-columns: 1fr auto;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 5px;
        }
        
        .file-item span {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .remove-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 4px;
            color: var(--accent-color);
        }
        
        .drag-area {
            border: 2px dashed #aaa;
            padding: 20px;
            text-align: center;
            background: #fafafa;
            margin-top: 10px;
            border-radius: var(--border-radius);
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .drag-area:hover {
            background-color: #f0f0f0;
        }
        
        .upload-status {
            margin-top: 20px;
            padding: 15px;
            border-radius: var(--border-radius);
        }
        
        .status-success {
            background-color: #dff0d8;
            color: #3c763d;
            border: 1px solid #d6e9c6;
        }
        
        .status-warning {
            background-color: #fcf8e3;
            color: #8a6d3b;
            border: 1px solid #faebcc;
        }
        
        .status-error {
            background-color: #f2dede;
            color: #a94442;
            border: 1px solid #ebccd1;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.4);
        }
        
        .modal-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
            max-width: 500px;
            border-radius: var(--border-radius);
        }
        
        .modal-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            gap: 10px;
        }
        
        .modal-btn {
            padding: 12px 24px;
            border: none;
            border-radius: var(--border-radius);
            cursor: pointer;
            font-weight: bold;
            flex: 1;
        }
        
        .btn-substituir {
            background-color: var(--success-color);
            color: white;
        }
        
        .btn-pular {
            background-color: var(--secondary-color);
            color: white;
        }
        
        .btn-cancelar {
            background-color: var(--accent-color);
            color: white;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            margin-top: 30px;
        }
        
        @media (max-width: 768px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            .action-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-folder-open"></i> Sistema de Arquivos Digitais</h1>
        </div>
        
        <div class="card">
            <h2 class="card-title"><i class="fas fa-users"></i> Gerenciamento de Clientes</h2>
            
            <form id="clienteForm" method="post" action="/cliente">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="novo_cliente">Nome do Cliente:</label>
                        <input type="text" name="novo_cliente" placeholder="Nome do Cliente" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Ações:</label>
                        <div class="action-buttons">
                            <button class="btn btn-success" type="submit" name="acao" value="cadastrar">
                                <i class="fas fa-plus-circle"></i> Cadastrar Cliente
                            </button>
                            <button class="btn btn-danger" type="submit" name="acao" value="excluir">
                                <i class="fas fa-trash-alt"></i> Excluir Cliente
                            </button>
                        </div>
                    </div>
                </div>
            </form>
        </div>
        
        <div class="card">
            <h2 class="card-title"><i class="fas fa-upload"></i> Upload de Arquivos</h2>
            
            <form id="uploadForm" method="post" action="/upload" enctype="multipart/form-data">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="cliente">Cliente:</label>
                        <select name="cliente" required>
                            <option value="">Selecione o Cliente</option>
                            {% for c in clientes %}
                            <option value="{{c}}">{{c}}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="area">Área:</label>
                        <select name="area" required>
                            <option value="">Selecione</option>
                            <option value="IMPORTAÇÃO">IMPORTAÇÃO</option>
                            <option value="EXPORTAÇÃO">EXPORTAÇÃO</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="servico">Serviço:</label>
                        <select name="servico" required>
                            <option value="">Selecione</option>
                            <option value="Aéreo">Aéreo</option>
                            <option value="Rodoviário">Rodoviário</option>
                            <option value="Marítimo">Marítimo</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="numero_processo">Nº Processo (6 dígitos):</label>
                        <input type="text" name="numero_processo" maxlength="6" required pattern="\d{6}" placeholder="Ex: 000123">
                    </div>
                    
                    <div class="form-group">
                        <label for="ano">Ano (2 dígitos):</label>
                        <input type="text" name="ano" maxlength="2" required pattern="\d{2}" placeholder="Ex: 23">
                    </div>
                    
                    <div class="form-group">
                        <label for="referencia">Referência:</label>
                        <input type="text" name="referencia" required pattern="^[A-Za-z0-9. \-+]+$" 
                               title="Apenas letras, números, ponto(.), hífen(-), espaço e sinal de mais(+) são permitidos"
                               placeholder="Descrição do processo">
                    </div>
                    
                    <div class="form-group">
                        <label for="file_action">Ação para arquivos existentes:</label>
                        <select name="file_action" required>
                            <option value="substituir">Substituir</option>
                            <option value="renomear">Renomear (adicionar data)</option>
                            <option value="pular">Pular</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Arquivos:</label>
                    <div class="file-controls">
                        <button type="button" id="btnEscolherArquivos" class="btn btn-secondary">
                            <i class="fas fa-folder-open"></i> Escolher arquivos
                        </button>
                    </div>
                    <input type="file" name="files" multiple id="fileInput" style="display: none;">
                    <div id="fileList" class="file-list"></div>
                </div>
                
                <div class="drag-area" id="dragArea">
                    <i class="fas fa-cloud-upload-alt" style="font-size: 48px; margin-bottom: 10px;"></i>
                    <h3>Arraste e solte arquivos aqui</h3>
                    <p>ou clique para selecionar</p>
                </div>
                
                <div class="action-buttons" style="margin-top: 20px;">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-paper-plane"></i> Enviar
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="limparCampos()">
                        <i class="fas fa-broom"></i> Limpar Campos
                    </button>
                    <a href="/busca" class="btn btn-success" target="_blank">
                        <i class="fas fa-search"></i> Busca Avançada
                    </a>
                </div>
            </form>
        </div>
        
        <!-- Modal para confirmação de pasta vazia -->
        <div id="emptyFolderModal" class="modal">
            <div class="modal-content">
                <p>Deseja criar a pasta sem arquivos?</p>
                <div class="modal-buttons">
                    <button class="modal-btn btn-substituir" onclick="confirmEmptyFolder(true)">Sim</button>
                    <button class="modal-btn btn-cancelar" onclick="confirmEmptyFolder(false)">Não</button>
                </div>
            </div>
        </div>
        
        <!-- Área para mostrar resultados do upload -->
        <div id="uploadResult" class="upload-status" style="display: none;"></div>
        
        <div class="footer">
            Sistema de Arquivos Digitais © 2025
        </div>
    </div>

    <script>
        // Lista global de arquivos
        let fileList = [];
        const fileInput = document.getElementById('fileInput');

        // Configurar drag and drop
        const dragArea = document.getElementById('dragArea');
        dragArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragArea.style.backgroundColor = '#e9e9e9';
        });
        
        dragArea.addEventListener('dragleave', () => {
            dragArea.style.backgroundColor = '#fafafa';
        });
        
        dragArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dragArea.style.backgroundColor = '#fafafa';
            const files = e.dataTransfer.files;
            addFilesToList(files);
        });
        
        dragArea.addEventListener('click', () => {
            fileInput.click();
        });

        function addFilesToList(files) {
            for (let i = 0; i < files.length; i++) {
                if (!fileList.some(f => f.name === files[i].name && f.size === files[i].size && f.lastModified === files[i].lastModified)) {
                    fileList.push(files[i]);
                }
            }
            updateFileList();
        }

        function removeFile(index) {
            fileList.splice(index, 1);
            updateFileList();
        }

        function updateFileList() {
            const fileListDiv = document.getElementById('fileList');
            fileListDiv.innerHTML = '';

            fileList.forEach((file, index) => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <span>${file.name}</span>
                    <button type="button" onclick="removeFile(${index})" class="remove-btn">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                fileListDiv.appendChild(fileItem);
            });

            // Atualiza o input de arquivos do formulário
            const dataTransfer = new DataTransfer();
            fileList.forEach(file => dataTransfer.items.add(file));
            fileInput.files = dataTransfer.files;
        }

        // Evento para o botão "Escolher arquivos"
        document.getElementById('btnEscolherArquivos').addEventListener('click', () => {
            fileInput.click();
        });

        // Evento quando arquivos são selecionados
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                Array.from(e.target.files).forEach(file => {
                    // Verifica se o arquivo já não está na lista
                    if (!fileList.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
                        fileList.push(file);
                    }
                });
                updateFileList();
                e.target.value = '';
            }
        });

        // Função para limpar campos
        function limparCampos() {
            document.querySelector('select[name=cliente]').value = "";
            document.querySelector('select[name=area]').value = "";
            document.querySelector('select[name=servico]').value = "";
            document.querySelector('input[name=numero_processo]').value = "";
            document.querySelector('input[name=ano]').value = "";
            document.querySelector('input[name=referencia]').value = "";
            fileList = [];
            updateFileList();
            document.getElementById('uploadResult').style.display = 'none';
        }

        // Modal para pasta vazia
        function confirmEmptyFolder(confirm) {
            const modal = document.getElementById('emptyFolderModal');
            modal.style.display = 'none';
            
            if (confirm) {
                const form = document.getElementById('uploadForm');
                const tempFormData = new FormData(form);
                
                fetch('/upload', {
                    method: 'POST',
                    body: tempFormData
                })
                .then(response => response.json())
                .then(result => {
                    showUploadResult(result);
                    if (result.status === "success") {
                        fileList = [];
                        updateFileList();
                    }
                })
                .catch(error => {
                    showUploadResult({
                        status: "error",
                        message: "Erro ao criar pasta."
                    });
                });
            }
        }

        // Mostrar resultado do upload
        function showUploadResult(result) {
            const resultDiv = document.getElementById('uploadResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = result.message;
            
            // Aplicar classes CSS conforme o status
            resultDiv.className = 'upload-status';
            if (result.status === "success") {
                resultDiv.classList.add('status-success');
            } else if (result.status === "warning") {
                resultDiv.classList.add('status-warning');
            } else {
                resultDiv.classList.add('status-error');
            }
            
            // Mostrar detalhes se existirem
            if (result.details) {
                if (result.details.enviados && result.details.enviados.length > 0) {
                    resultDiv.innerHTML += `<br><strong>Arquivos enviados:</strong><ul>`;
                    result.details.enviados.forEach(file => {
                        resultDiv.innerHTML += `<li>${file}</li>`;
                    });
                    resultDiv.innerHTML += `</ul>`;
                }
                if (result.details.substituidos && result.details.substituidos.length > 0) {
                    resultDiv.innerHTML += `<br><strong>Arquivos substituídos:</strong><ul>`;
                    result.details.substituidos.forEach(file => {
                        resultDiv.innerHTML += `<li>${file}</li>`;
                    });
                    resultDiv.innerHTML += `</ul>`;
                }
                if (result.details.renomeados && result.details.renomeados.length > 0) {
                    resultDiv.innerHTML += `<br><strong>Arquivos renomeados:</strong><ul>`;
                    result.details.renomeados.forEach(file => {
                        resultDiv.innerHTML += `<li>${file}</li>`;
                    });
                    resultDiv.innerHTML += `</ul>`;
                }
                if (result.details.pulados && result.details.pulados.length > 0) {
                    resultDiv.innerHTML += `<br><strong>Arquivos pulados:</strong><ul>`;
                    result.details.pulados.forEach(file => {
                        resultDiv.innerHTML += `<li>${file}</li>`;
                    });
                    resultDiv.innerHTML += `</ul>`;
                }
            }
        }

        // Envio do formulário via AJAX
        document.getElementById("uploadForm").addEventListener("submit", async function(event) {
            event.preventDefault();

            // Validar campos antes de continuar
            const cliente = document.querySelector('select[name=cliente]').value;
            const area = document.querySelector('select[name=area]').value;
            const servico = document.querySelector('select[name=servico]').value;
            const numero_processo = document.querySelector('input[name=numero_processo]').value;
            const ano = document.querySelector('input[name=ano]').value;
            const referencia = document.querySelector('input[name=referencia]').value;
            const file_action = document.querySelector('select[name=file_action]').value;

            if (!cliente || !area || !servico || !numero_processo || !ano || !referencia) {
                showUploadResult({
                    status: "error",
                    message: "Todos os campos são obrigatórios!"
                });
                return;
            }

            if (fileList.length === 0) {
                document.getElementById('emptyFolderModal').style.display = 'block';
                return;
            }

            try {
                const formData = new FormData();
                
                // Adicionar campos do formulário
                formData.append('cliente', cliente);
                formData.append('area', area);
                formData.append('servico', servico);
                formData.append('numero_processo', numero_processo);
                formData.append('ano', ano);
                formData.append('referencia', referencia);
                formData.append('file_action', file_action);
                
                // Adicionar arquivos
                fileList.forEach(file => {
                    formData.append('files', file);
                });

                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                showUploadResult(result);
                
                if (result.status === "success") {
                    fileList = [];
                    updateFileList();
                }
            } catch (error) {
                console.error("Erro no envio:", error);
                showUploadResult({
                    status: "error",
                    message: "Erro ao enviar os arquivos."
                });
            }
        });
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    clientes = obter_clientes()
    return render_template_string(HTML_TEMPLATE, clientes=clientes)

@app.route("/cliente", methods=["POST"])
def cliente():
    nome = request.form.get("novo_cliente", "").strip().upper()
    acao = request.form.get("acao")
    if not nome:
        return jsonify({"status": "error", "message": "Nome do cliente não pode estar vazio"}), 400
    if acao == "cadastrar":
        sucesso, msg = adicionar_cliente(nome)
    elif acao == "excluir":
        sucesso, msg = remover_cliente(nome)
    else:
        return jsonify({"status": "error", "message": "Ação inválida"}), 400
    return redirect(url_for("index"))

def processar_arquivo(file, pasta_destino, file_action):
    """Processa um arquivo de acordo com a ação escolhida"""
    filename = secure_filename(file.filename)
    temp_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(temp_path)
    
    destino = os.path.join(pasta_destino, filename)
    resultado = {
        'nome': filename,
        'status': 'enviado',
        'novo_nome': filename
    }

    if os.path.exists(destino):
        if file_action == "substituir":
            os.remove(destino)
            shutil.move(temp_path, destino)
            resultado['status'] = 'substituido'
        elif file_action == "renomear":
            base, ext = os.path.splitext(filename)
            novo_nome = f"{base}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
            shutil.move(temp_path, os.path.join(pasta_destino, novo_nome))
            resultado['status'] = 'renomeado'
            resultado['novo_nome'] = novo_nome
        else:  # pular
            os.remove(temp_path)
            resultado['status'] = 'pulado'
    else:
        shutil.move(temp_path, destino)
    
    return resultado

@app.route("/upload", methods=["POST"])
def upload():
    try:
        cliente = request.form.get("cliente", "").strip().upper()
        area = request.form.get("area", "").strip().upper()
        servico = request.form.get("servico", "").strip().capitalize()
        numero_processo = request.form.get("numero_processo", "").strip()
        ano = request.form.get("ano", "").strip()
        referencia = request.form.get("referencia", "").strip().upper()  # Convertendo para maiúsculas aqui
        file_action = request.form.get("file_action", "pular")
        

        # Validações
        if not re.match(r'^[A-Za-z0-9. \-+]+$', referencia):
            return jsonify({
                "status": "error",
                "message": "Referência inválida. Use apenas letras, números, ponto(.), hífen(-), espaço e sinal de mais(+)."
            }), 400

        if not all([cliente, area, servico, numero_processo, ano, referencia]):
            return jsonify({
                "status": "error",
                "message": "Todos os campos são obrigatórios!"
            }), 400

        if len(numero_processo) != 6 or not numero_processo.isdigit():
            return jsonify({
                "status": "error",
                "message": "Número do processo inválido"
            }), 400

        if len(ano) != 2 or not ano.isdigit():
            return jsonify({
                "status": "error",
                "message": "Ano inválido"
            }), 400

        # Verificar se já existe processo com mesmo número
        processos_existentes = obter_info_processos()
        for proc in processos_existentes.values():
            mesmo_processo = (
                proc['cliente'].upper() == cliente and
                proc['area'].upper() == area and
                proc['numero'] == numero_processo
            )
            if mesmo_processo:
                if proc['ano'] != ano:
                    return jsonify({
                        "status": "error",
                        "message": f"Já existe um processo com o número {numero_processo}, mas com o ano '{proc['ano']}'. Use o mesmo ano para continuar."
                    }), 400
                if proc['servico'].capitalize() != servico:
                    return jsonify({
                        "status": "error",
                        "message": f"Já existe um processo com o número {numero_processo} e ano {ano} para esse cliente/área, mas com o serviço '{proc['servico']}'. Use o mesmo serviço para continuar."
                    }), 400
                if proc['referencia'].upper() != referencia.upper():
                    return jsonify({
                        "status": "error",
                        "message": f"Já existe um processo com o número {numero_processo} e ano {ano} para esse cliente/área/serviço, com referência '{proc['referencia']}'. Use a mesma referência para evitar duplicação."
                    }), 400

        # Criar pasta de destino
        pasta_destino = criar_pasta(cliente, area, servico, numero_processo, ano, referencia)

        # Processar arquivos
        resultados = {
            "enviados": [],
            "substituidos": [],
            "renomeados": [],
            "pulados": []
        }

        if 'files' not in request.files:
            return jsonify({
                "status": "success",
                "message": "Pasta criada com sucesso sem arquivos!"
            }), 200

        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({
                "status": "success",
                "message": "Pasta criada com sucesso sem arquivos!"
            }), 200

        for file in files:
            if file.filename == '':
                continue

            resultado = processar_arquivo(file, pasta_destino, file_action)
            
            if resultado['status'] == 'enviado':
                resultados['enviados'].append(resultado['nome'])
            elif resultado['status'] == 'substituido':
                resultados['substituidos'].append(resultado['nome'])
            elif resultado['status'] == 'renomeado':
                resultados['renomeados'].append(resultado['novo_nome'])
            elif resultado['status'] == 'pulado':
                resultados['pulados'].append(resultado['nome'])

        # Montar mensagem de resultado
        mensagem = "Upload concluído com sucesso!<br>"
        if resultados['enviados']:
            mensagem += f"<strong>Novos arquivos enviados:</strong> {len(resultados['enviados'])}<br>"
        if resultados['substituidos']:
            mensagem += f"<strong>Arquivos substituídos:</strong> {len(resultados['substituidos'])}<br>"
        if resultados['renomeados']:
            mensagem += f"<strong>Arquivos renomeados:</strong> {len(resultados['renomeados'])}<br>"
        if resultados['pulados']:
            mensagem += f"<strong>Arquivos pulados (já existiam):</strong> {len(resultados['pulados'])}"

        return jsonify({
            "status": "success",
            "message": mensagem,
            "details": resultados
        }), 200

    except Exception as e:
        logging.error(f"Erro no upload: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Erro interno: {str(e)}"
        }), 500

@app.route("/confirmar_upload", methods=["POST"])
def confirmar_upload():
    try:
        data = request.json
        confirmado = data.get('confirmado', False)
        
        if not confirmado:
            return jsonify({
                "status": "canceled",
                "message": "Upload cancelado pelo usuário"
            }), 200

        # Recupera os dados do formulário
        dados = data.get('dados', {})
        arquivos = data.get('arquivos', [])
        
        # Recria a pasta de destino
        pasta_destino = criar_pasta(
            dados.get('cliente', ''),
            dados.get('area', ''),
            dados.get('servico', ''),
            dados.get('numero_processo', ''),
            dados.get('ano', ''),
            dados.get('referencia', '')
        )

        # Processa os arquivos temporários
        arquivos_para_upload = []
        for filename in arquivos:
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(temp_path):
                arquivos_para_upload.append({
                    "path": temp_path,
                    "name": filename
                })

        # Copia os arquivos com substituição
        for arq in arquivos_para_upload:
            destino = os.path.join(pasta_destino, arq['name'])
            if os.path.exists(destino):
                os.remove(destino)
            shutil.copy2(arq['path'], destino)
            if os.path.exists(arq["path"]):
                os.remove(arq["path"])

        return jsonify({
            "status": "success",
            "message": "Arquivos substituídos com sucesso"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro: {str(e)}"
        }), 500

@app.route("/busca", methods=["GET"])
def busca():
    return render_template("busca.html")

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5001)