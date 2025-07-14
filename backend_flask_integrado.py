from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import os
import shutil
from werkzeug.utils import secure_filename
from configparser import ConfigParser
from clientes import obter_clientes, adicionar_cliente, remover_cliente
from logica import criar_pasta, copiar_arquivos, obter_info_processos

app = Flask(__name__)
config = ConfigParser()
config.read('config.ini')
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        .file-list { margin-top: 10px; }
        .file-item { display: flex; justify-content: space-between; background: #eee; padding: 5px; margin-bottom: 5px; }
        .file-item button { background: red; color: white; border: none; padding: 2px 8px; }
        .drag-area { border: 2px dashed #aaa; padding: 20px; text-align: center; background: #fafafa; margin-top: 10px; }
        .row { display: flex; gap: 10px; }
        .col { flex: 1; }
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
        <input type="text" name="referencia" required pattern="^[A-Za-z0-9.-]+$" title="Apenas letras, números, hífen e ponto são permitidos">

        <label>Arquivos:</label>
        <input type="file" name="files" multiple>
        <div id="fileList" class="file-list"></div>

        <div class="drag-area" ondrop="dropHandler(event);" ondragover="dragOverHandler(event);">
            Arraste e solte arquivos aqui
        </div>

        <button type="submit">Enviar</button>
    </form>
        <button type="button" onclick="limparCampos()">Limpar Campos</button>

    <form method="get" action="/busca">
        <button type="submit">Busca Avançada</button>
    </form>

    <script>
        function dropHandler(ev) {
            ev.preventDefault();
            const input = document.querySelector('input[type=file]');
            const dt = new DataTransfer();
            for (const file of ev.dataTransfer.files) {
                dt.items.add(file);
            }
            for (const f of input.files) {
                dt.items.add(f);
            }
            input.files = dt.files;
        }

        function dragOverHandler(ev) {
            ev.preventDefault();
        }
    </script>
    <script>
const inputFile = document.querySelector('input[type=file]');
const fileListDiv = document.getElementById('fileList');

inputFile.addEventListener('change', updateFileList);

function updateFileList() {
    fileListDiv.innerHTML = '';
    const dt = new DataTransfer();

    for (let i = 0; i < inputFile.files.length; i++) {
        const file = inputFile.files[i];
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            ${file.name}
            <button type="button" onclick="removeFile(${i})">X</button>
        `;
        fileListDiv.appendChild(item);
        dt.items.add(file);
    }

    inputFile.files = dt.files;
}

function removeFile(index) {
    const dt = new DataTransfer();
    const { files } = inputFile;

    for (let i = 0; i < files.length; i++) {
        if (i !== index) dt.items.add(files[i]);
    }

    inputFile.files = dt.files;
    updateFileList();
}
</script>

<script>
document.getElementById("uploadForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const formData = new FormData(this);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const text = await response.text();
        alert(text);  // Exibe a quantidade de arquivos enviados com sucesso
    } catch (error) {
        alert("Erro ao enviar os arquivos.");
    }
});
</script>

<script>
function limparCampos() {
    document.querySelector('select[name=cliente]').value = "";
    document.querySelector('select[name=area]').value = "";
    document.querySelector('select[name=servico]').value = "";
    document.querySelector('input[name=numero_processo]').value = "";
    document.querySelector('input[name=ano]').value = "";
    document.querySelector('input[name=referencia]').value = "";
    document.querySelector('input[type=file]').value = "";
    document.getElementById('fileList').innerHTML = "";
}
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
        return "Nome do cliente não pode estar vazio", 400
    if acao == "cadastrar":
        sucesso, msg = adicionar_cliente(nome)
    elif acao == "excluir":
        sucesso, msg = remover_cliente(nome)
    else:
        return "Ação inválida", 400
    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload():
    try:
        cliente = request.form.get("cliente", "").strip().upper()
        area = request.form.get("area", "").strip().upper()
        servico = request.form.get("servico", "").strip().capitalize()
        numero_processo = request.form.get("numero_processo", "").strip()
        ano = request.form.get("ano", "").strip()
        referencia = request.form.get("referencia", "").strip().upper()

        if not all([cliente, area, servico, numero_processo, ano, referencia]):
            return "Todos os campos são obrigatórios!", 400

        if len(numero_processo) != 6 or not numero_processo.isdigit():
            return "Número do processo inválido", 400

        if len(ano) != 2 or not ano.isdigit():
            return "Ano inválido", 400

        # Verificar se já existe processo com mesmo número, mas com ano, referência ou serviço diferentes
        processos_existentes = obter_info_processos()
        for proc in processos_existentes.values():
            mesmo_processo = (
                proc['cliente'].upper() == cliente and
                proc['area'].upper() == area and
                proc['numero'] == numero_processo
            )
            if mesmo_processo:
                if proc['ano'] != ano:
                    return (
                        f"Já existe um processo com o número {numero_processo}, mas com o ano '{proc['ano']}'. "
                        f"Use o mesmo ano para continuar.",
                        400
                    )
                if proc['servico'].capitalize() != servico:
                    return (
                        f"Já existe um processo com o número {numero_processo} e ano {ano}, "
                        f"mas com o serviço '{proc['servico']}'. "
                        f"Use o mesmo serviço para continuar.",
                        400
                    )
                if proc['referencia'].upper() != referencia.upper():
                    return (
                        f"Já existe um processo com o número {numero_processo} e ano {ano} "
                        f"para esse cliente/área/serviço, com referência '{proc['referencia']}'. "
                        f"Use a mesma referência para evitar duplicação.",
                        400
                    )

        arquivos = request.files.getlist("files")
        arquivos_para_upload = []

        for file in arquivos:
            filename = secure_filename(file.filename)
            temp_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(temp_path)
            arquivos_para_upload.append({
                "path": temp_path,
                "name": filename
            })

        pasta_destino = criar_pasta(cliente, area, servico, numero_processo, ano, referencia)

        if not arquivos_para_upload:
            return "Nenhum arquivo foi enviado. Pasta criada sem documentos!", 200

        sucesso = copiar_arquivos(pasta_destino, arquivos_para_upload)

        for arq in arquivos_para_upload:
            if os.path.exists(arq["path"]):
                os.remove(arq["path"])

        if sucesso:
            return f"{len(arquivos_para_upload)} arquivo(s) enviado(s) com sucesso!"
        else:
            return "Erro ao copiar arquivos", 500

    except Exception as e:
        return f"Erro interno: {str(e)}", 500

@app.route("/busca", methods=["GET"])
def busca():
    return "Busca Avançada ainda não implementada nesta interface web."

if __name__ == "__main__":
    app.run(debug=True, port=5001)
