from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_from_directory
import os
import shutil
import re
from werkzeug.utils import secure_filename
from configparser import ConfigParser
from clientes import obter_clientes, adicionar_cliente, remover_cliente
from logica import criar_pasta, copiar_arquivos, obter_info_processos
import logging

app = Flask(__name__)
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
    <style>
        body { font-family: Arial; margin: 40px; background-color: #f4f4f4; }
        h2 { color: #333; }
        form { background: #fff; padding: 20px; border-radius: 8px; }
        input, select, button { margin: 5px 0; padding: 8px; width: 100%; }
        .file-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .file-list { margin-top: 10px; }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 5px;
        }
        .remove-btn {
            background: none;
            border: none;
            cursor: pointer;
        }
        .drag-area {
            border: 2px dashed #aaa;
            padding: 20px;
            text-align: center;
            background: #fafafa;
            margin-top: 10px;
        }
        .row { display: flex; gap: 10px; }
        .col { flex: 1; }
        .modal {
            display: none;
            position: fixed;
            z-index: 1;
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
            max-width: 400px;
        }
        .modal-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h2>Sistema de Arquivos Digitais</h2>

    <form id="clienteForm" method="post" action="/cliente">
        <div class="row">
            <div class="col">
                <input type="text" name="novo_cliente" placeholder="Nome do Cliente" required>
            </div>
            <div class="col">
                <button type="submit" name="acao" value="cadastrar">Cadastrar Cliente</button>
                <button type="submit" name="acao" value="excluir">Excluir Cliente</button>
            </div>
        </div>
    </form>

    <form id="uploadForm" method="post" action="/upload" enctype="multipart/form-data">
        <label>Cliente:</label>
        <select name="cliente" required>
            <option value="">Selecione o Cliente</option>
            {% for c in clientes %}
            <option value="{{c}}">{{c}}</option>
            {% endfor %}
        </select>

        <label>Área:</label>
        <select name="area" required>
            <option value="">Selecione</option>
            <option value="IMPORTAÇÃO">IMPORTAÇÃO</option>
            <option value="EXPORTAÇÃO">EXPORTAÇÃO</option>
        </select>

        <label>Serviço:</label>
        <select name="servico" required>
            <option value="">Selecione</option>
            <option value="Aéreo">Aéreo</option>
            <option value="Rodoviário">Rodoviário</option>
            <option value="Marítimo">Marítimo</option>
        </select>

        <label>Nº Processo (6 dígitos):</label>
        <input type="text" name="numero_processo" maxlength="6" required pattern="\d{6}">

        <label>Ano (2 dígitos):</label>
        <input type="text" name="ano" maxlength="2" required pattern="\d{2}">

        <label>Referência:</label>
        <input type="text" name="referencia" required pattern="^[A-Za-z0-9. \-]+$" title="Apenas letras, números, ponto(.), hífen(-) e espaço são permitidos">

        <label>Arquivos:</label>
        <div class="file-controls">
            <button type="button" id="btnEscolherArquivos">Escolher arquivos</button>
        </div>
        <input type="file" name="files" multiple id="fileInput" style="display: none;">
        <div id="fileList" class="file-list"></div>

        <div class="drag-area" id="dragArea">
            Arraste e solte arquivos aqui
        </div>

        <button type="submit">Enviar</button>
    </form>
    <button type="button" onclick="limparCampos()">Limpar Campos</button>

    <form method="get" action="/busca">
        <button type="submit">Busca Avançada</button>
    </form>

    <!-- Modal para confirmação de pasta vazia -->
    <div id="emptyFolderModal" class="modal">
        <div class="modal-content">
            <p>Deseja criar a pasta sem arquivos?</p>
            <div class="modal-buttons">
                <button onclick="confirmEmptyFolder(true)">Sim</button>
                <button onclick="confirmEmptyFolder(false)">Não</button>
            </div>
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
                        <img src="/static/c_redX.png" alt="Remover" width="16">
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
                fileList = [];
                Array.from(e.target.files).forEach(file => {
                    fileList.push(file);
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
                    alert(result.message);
                    if (result.status === "success") {
                        fileList = [];
                        updateFileList();
                    }
                })
                .catch(error => {
                    alert("Erro ao criar pasta.");
                });
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

            if (!cliente || !area || !servico || !numero_processo || !ano || !referencia) {
                alert("Todos os campos são obrigatórios!");
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
                
                // Adicionar arquivos
                fileList.forEach(file => {
                    formData.append('files', file);
                });

                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (result.status === "confirmacao_necessaria") {
                    const confirmado = confirm(`${result.message}\nArquivos: ${result.arquivos.join(', ')}`);
                    
                    if (confirmado) {
                        const confirmResponse = await fetch('/confirmar_upload', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                confirmado: true,
                                arquivos: result.arquivos,
                                dados: {
                                    cliente: cliente,
                                    area: area,
                                    servico: servico,
                                    numero_processo: numero_processo,
                                    ano: ano,
                                    referencia: referencia
                                }
                            })
                        });
                        
                        const finalResult = await confirmResponse.json();
                        alert(finalResult.message);
                        
                        if (finalResult.status === "success") {
                            fileList = [];
                            updateFileList();
                        }
                    } else {
                        alert("Upload cancelado");
                        fileList = [];
                        updateFileList();
                    }
                } else {
                    alert(result.message);
                    if (result.status === "success") {
                        fileList = [];
                        updateFileList();
                    }
                }
            } catch (error) {
                console.error("Erro no envio:", error);
                alert("Erro ao enviar os arquivos.");
                fileList = [];
                updateFileList();
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

@app.route("/upload", methods=["POST"])
def upload():
    try:
        cliente = request.form.get("cliente", "").strip().upper()
        area = request.form.get("area", "").strip().upper()
        servico = request.form.get("servico", "").strip().capitalize()
        numero_processo = request.form.get("numero_processo", "").strip()
        ano = request.form.get("ano", "").strip()
        referencia = request.form.get("referencia", "").strip()

        # Validação da referência
        if not re.match(r'^[A-Za-z0-9. \-]+$', referencia): 
            return jsonify({
                "status": "error",
                "message": "Referência inválida. Use apenas letras, números, ponto(.), hífen(-) e espaço."
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

        # Processar arquivos se existirem
        arquivos_para_upload = []
        if 'files' in request.files:
            for file in request.files.getlist('files'):
                if file.filename == '':
                    continue
                
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = secure_filename(file.filename)
                temp_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(temp_path)
                arquivos_para_upload.append({
                    "path": temp_path,
                    "name": filename
                })

        if arquivos_para_upload:
            # Verificar se algum arquivo já existe
            arquivos_existentes = []
            for arq in arquivos_para_upload:
                destino = os.path.join(pasta_destino, arq['name'])
                if os.path.exists(destino):
                    arquivos_existentes.append(arq['name'])

            if arquivos_existentes:
                return jsonify({
                    "status": "confirmacao_necessaria",
                    "message": "Um ou mais arquivos já existem. Deseja substituir?",
                    "arquivos": arquivos_existentes
                }), 200

            # Se não há arquivos existentes, copia diretamente
            sucesso = copiar_arquivos(pasta_destino, arquivos_para_upload)
            
            # Limpar arquivos temporários
            for arq in arquivos_para_upload:
                if os.path.exists(arq["path"]):
                    os.remove(arq["path"])
            
            if sucesso:
                return jsonify({
                    "status": "success",
                    "message": f"{len(arquivos_para_upload)} arquivo(s) enviado(s) com sucesso!"
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": "Erro ao copiar arquivos"
                }), 500
        
        return jsonify({
            "status": "success",
            "message": "Pasta criada com sucesso sem arquivos!"
        }), 200

    except Exception as e:
        logging.error(f"Erro no upload: {str(e)}")
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
    return "Busca Avançada ainda não implementada nesta interface web."

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5001)