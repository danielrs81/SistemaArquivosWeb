# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request, render_template
from logica import obter_info_processos, abrir_pasta_processo, obter_processo_por_numero
from clientes import obter_clientes, obter_tipos_despesa
import os
import json
import logging
import subprocess
import re
import datetime
from configparser import ConfigParser
from werkzeug.utils import secure_filename

# Carregar configurações
config = ConfigParser()
config.read('config.ini')
BASE_DIR = config.get('PATHS', 'BASE_DIR', fallback="C:/Arquivo_Digital_Compartilhado")

busca_bp = Blueprint('busca', __name__)

@busca_bp.route('/busca')
def busca():
    try:
        clientes = obter_clientes()
        tipos_despesa = obter_tipos_despesa()
        return render_template('busca.html', 
                            clientes=clientes,
                            tipos_despesa=tipos_despesa)
    except Exception as e:
        logging.error(f"Erro na rota /busca: {str(e)}")
        return render_template('busca.html', 
                            clientes=[], 
                            tipos_despesa=[], 
                            error=str(e))

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
        
        # Verificação adicional para caminhos de rede
        if caminho.startswith('\\\\'):
            # Testa conexão com o servidor primeiro
            servidor = caminho.split('\\')[2]
            try:
                subprocess.run(['ping', '-n', '1', servidor], check=True)
            except subprocess.CalledProcessError:
                return jsonify({
                    "status": "error",
                    "message": f"Servidor {servidor} não está respondendo"
                }), 404
        
        if abrir_pasta_processo(caminho):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Falha ao abrir pasta"}), 500
            
    except Exception as e:
        logging.error(f"Erro ao abrir pasta: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
@busca_bp.route("/api/clientes", methods=["GET"])
def api_clientes():
    try:
        clientes = obter_clientes()
        return jsonify(clientes)
    except Exception as e:
        logging.error(f"Erro ao obter lista de clientes: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@busca_bp.route("/api/processos_selecionados", methods=["POST"])
def obter_processos_selecionados():
    try:
        data = request.get_json()
        numeros = data.get('numeros', [])
        
        processos = []
        for numero in numeros:
            processo = obter_processo_por_numero(numero)
            if processo:
                processos.append(processo)
        
        return jsonify(processos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@busca_bp.route("/api/tipos_despesa", methods=["GET"])
def api_tipos_despesa():
    try:
        tipos = obter_tipos_despesa()
        return jsonify(tipos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@busca_bp.route("/api/enviar_lote", methods=["POST"])
def api_enviar_lote():
    try:
        processo_num = request.form.get('processo')
        tipo = request.form.get('tipo')
        files = request.files.getlist('files')

        #  Novos campos para renomear
        renomear = request.form.get('renomear', 'false').lower() == 'true'
        nome_despesa = request.form.get('nome_despesa', '').strip()
        data_vencimento = request.form.get('data_vencimento', '').strip()

        if data_vencimento:
            try:
                partes = data_vencimento.split('-')
                if len(partes) == 3:
                    data_vencimento = f"{partes[2]}-{partes[1]}-{partes[0]}"
            except:
                pass

        if not processo_num:
            return jsonify({"status": "error", "message": "Número do processo não informado"}), 400

        from logica import obter_processo_por_numero
        processo = obter_processo_por_numero(processo_num)
        if not processo:
            return jsonify({"status": "error", "message": "Processo não encontrado"}), 404

        destino = processo['caminho']
        if tipo == 'despesas':
            destino = os.path.join(destino, "DESPESAS")
            os.makedirs(destino, exist_ok=True)

        enviados = []
        arquivos_existentes = []

        # Define force_rename from request form, defaulting to False
        force_rename = request.form.get('forceRename', 'false').lower() == 'true'

        for file in files:
            if renomear:
                cliente = processo['cliente']
                numero_proc = processo_num
                referencia = processo['referencia']
                base, ext = os.path.splitext(file.filename)
                novo_nome = f"{cliente} - ER{numero_proc} - {nome_despesa} - {referencia} - {data_vencimento}{ext}"
                filename = re.sub(r'[<>:"/\\|?*]', '', novo_nome).strip()
            else:
                filename = re.sub(r'[<>:"/\\|?*]', '', file.filename).strip()

            # ✅ Sempre define destino_final, independente do renomear
            destino_final = os.path.join(destino, filename)

            # ✅ Se o arquivo já existe e estamos renomeando, adiciona hora
            if renomear and os.path.exists(destino_final):
                base, ext = os.path.splitext(filename)
                hora = datetime.datetime.now().strftime("%H%M%S")
                filename = f"{base} {hora}{ext}"
                destino_final = os.path.join(destino, filename)

            # ✅ Checagem de conflito normal (force_rename)
            if os.path.exists(destino_final):
                if force_rename:
                    base, ext = os.path.splitext(filename)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base}_{timestamp}{ext}"
                    destino_final = os.path.join(destino, filename)
                    file.save(destino_final)
                    enviados.append(filename)
                else:
                    arquivos_existentes.append(filename)
            else:
                file.save(destino_final)
                enviados.append(filename)

        if arquivos_existentes and not force_rename:
            return jsonify({
                "status": "exists",
                "message": "Alguns arquivos já existem",
                "arquivos": arquivos_existentes
            })

        return jsonify({
            "status": "success",
            "message": f"{len(enviados)} arquivo(s) enviado(s) com sucesso",
            "details": {"enviados": enviados}
        })
    
    except Exception as e:
        import logging
        logging.error(f"Erro no envio em lote: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
