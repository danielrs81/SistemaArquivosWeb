from flask import Blueprint, jsonify, request, render_template
from logica import obter_info_processos, abrir_pasta_processo
from clientes import obter_clientes
import os
import logging
from configparser import ConfigParser

# Carregar configurações
config = ConfigParser()
config.read('config.ini')
BASE_DIR = config.get('PATHS', 'BASE_DIR', fallback="C:/Arquivo_Digital_Compartilhado")

busca_bp = Blueprint('busca', __name__)

@busca_bp.route('/busca')
def busca():
    try:
        clientes = obter_clientes()
        return render_template('busca.html', clientes=clientes)
    except Exception as e:
        logging.error(f"Erro na rota /busca: {str(e)}")
        return render_template('busca.html', clientes=[], error=str(e))

@busca_bp.route("/api/buscar_processos", methods=["GET"])
def api_buscar_processos():
    try:
        processos = obter_info_processos()
        filtros = request.args
        
        resultados = []
        for proc in processos.values():
            # Filtro por intervalo de número do processo
            numero_processo = int(proc['numero'])
            
            # Verifica se foi fornecido um intervalo
            numero_inicio = filtros.get('numero_inicio')
            numero_fim = filtros.get('numero_fim')
            
            # Se ambos os campos estão preenchidos, filtra por intervalo
            if numero_inicio and numero_fim:
                try:
                    inicio = int(numero_inicio)
                    fim = int(numero_fim)
                    if not (inicio <= numero_processo <= fim):
                        continue
                except ValueError:
                    pass  # Se não for número, ignora este filtro
            # Se apenas o início foi preenchido
            elif numero_inicio:
                try:
                    inicio = int(numero_inicio)
                    if numero_processo < inicio:
                        continue
                except ValueError:
                    pass
            # Se apenas o fim foi preenchido
            elif numero_fim:
                try:
                    fim = int(numero_fim)
                    if numero_processo > fim:
                        continue
                except ValueError:
                    pass
            
            # Os outros filtros permanecem
            if (not filtros.get('cliente') or proc['cliente'].upper() == filtros.get('cliente').upper()) and \
               (not filtros.get('ano') or proc['ano'] == filtros.get('ano')) and \
               (not filtros.get('area') or proc['area'].upper() == filtros.get('area').upper()) and \
               (not filtros.get('servico') or proc['servico'].upper() == filtros.get('servico').upper()) and \
               (not filtros.get('referencia') or proc['referencia'].upper().find(filtros.get('referencia').upper()) != -1):
                resultados.append(proc)
        
        return jsonify(resultados)
    except Exception as e:
        logging.error(f"Erro na busca de processos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@busca_bp.route("/api/abrir_pasta", methods=["POST"])
def api_abrir_pasta():
    try:
        data = request.get_json()
        if not data or 'caminho' not in data:
            return jsonify({"status": "error", "message": "Dados inválidos"}), 400
            
        caminho = data['caminho']
        
        # Verificar se o caminho existe e é seguro
        if not os.path.exists(caminho) or not os.path.isdir(caminho):
            return jsonify({"status": "error", "message": "Pasta não encontrada"}), 404
        
        # Converter para caminho absoluto e normalizar
        caminho = os.path.abspath(os.path.normpath(caminho))
        
        # Verificar se o caminho está dentro do BASE_DIR por segurança
        base_dir = os.path.abspath(BASE_DIR)
        if not caminho.startswith(base_dir):
            return jsonify({"status": "error", "message": "Acesso não permitido"}), 403
        
        # Tentar abrir a pasta
        if abrir_pasta_processo(caminho):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Falha ao abrir pasta"}), 500
            
    except Exception as e:
        logging.error(f"Erro ao abrir pasta: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@busca_bp.route("/api/clientes", methods=["GET"])
def api_clientes():
    try:
        clientes = obter_clientes()
        return jsonify(clientes)
    except Exception as e:
        logging.error(f"Erro ao obter lista de clientes: {str(e)}")
        return jsonify({"error": str(e)}), 500