# -*- coding: utf-8 -*-
from configparser import ConfigParser
import os
import shutil
import re
from tkinter import messagebox
import tkinter as tk
import subprocess
import sys
import logging
import locale
from pathlib import Path

# Configurar logging
logging.basicConfig(filename='sistema.log', level=logging.ERROR)

# Inicializar root invisível para messagebox funcionar corretamente
root = tk.Tk()
root.withdraw()
root.lift()
root.attributes('-topmost', True)

# Carregar configurações
config = ConfigParser()
config.read('config.ini', encoding='utf-8')

BASE_DIR = config.get('PATHS', 'BASE_DIR', fallback="D:/Arquivo Digital")
EXTENSOES_BLOQUEADAS = {'.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.jar', '.msi', '.dll'}

# Configurar locale para tratar caracteres especiais
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

def corrigir_codificacao_caminho(caminho):
    """Corrige problemas de codificação em caminhos existentes"""
    try:
        if isinstance(caminho, bytes):
            return caminho.decode('utf-8')
        return str(caminho.encode('latin1').decode('utf-8'))
    except:
        return str(caminho)

def get_path(area=None):
    """Retorna o caminho base conforme a área especificada"""
    try:
        if area == "IMPORTAÇÃO":
            path = config.get('PATHS', 'IMPORTACAO_DIR', 
                           fallback=os.path.join(BASE_DIR, "IMPORTAÇÃO"))
        elif area == "EXPORTAÇÃO":
            path = config.get('PATHS', 'EXPORTACAO_DIR',
                           fallback=os.path.join(BASE_DIR, "EXPORTAÇÃO"))
        else:
            path = BASE_DIR
        
        return corrigir_codificacao_caminho(path)
    except Exception as e:
        logging.error(f"Erro ao obter caminho para {area}: {str(e)}")
        return BASE_DIR

def criar_pasta(cliente, area, servico, numero_processo, ano, referencia):
    """Cria a estrutura de pastas com tratamento de caracteres especiais"""
    try:
        # Normalização dos dados de entrada
        referencia = re.sub(r'[^A-Za-z0-9. \-+]', '', referencia).strip()
        sigla_area = "I" if area == "IMPORTAÇÃO" else "E"
        sigla_servico = servico[0].upper()
        ano_completo = f"20{ano}" if len(ano) == 2 else ano
        
        # Criação do caminho com pathlib
        base_path = Path(get_path(area))
        cliente_path = base_path / cliente.upper()
        ano_path = cliente_path / ano_completo
        nome_pasta = f"{sigla_area}{sigla_servico}-{numero_processo}-{ano} - {referencia}"
        
        # Garante que o caminho está em UTF-8
        caminho_final = ano_path / nome_pasta
        
        # Cria a estrutura de pastas
        caminho_final.mkdir(parents=True, exist_ok=True)
        
        # Força a codificação UTF-8 no Windows
        if os.name == 'nt':
            from ctypes import windll
            windll.kernel32.SetFileAttributesW(str(caminho_final), 0x00000080)
        
        return str(caminho_final)
    except Exception as e:
        error_msg = f"Erro ao criar pasta em {area}: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

def obter_info_processos():
    """Obtém informações dos processos com tratamento de codificação"""
    processos = {}
    
    for area in ["IMPORTAÇÃO", "EXPORTAÇÃO"]:
        area_path = get_path(area)
        if not os.path.exists(area_path):
            logging.warning(f"Diretório de {area} não encontrado: {area_path}")
            continue
            
        for root, dirs, _ in os.walk(area_path):
            for dir_name in dirs:
                match = re.search(r'([IE])([ARM])-(\d{6})-(\d{2}) - (.+)', dir_name)
                if match:
                    caminho_completo = os.path.join(root, dir_name)
                    add_processo(processos, match, area, caminho_completo)

    return processos

def add_processo(processos, match, area, caminho):
    """Adiciona um processo ao dicionário"""
    numero_processo = match.group(3)
    chave = f"{numero_processo}_{match.group(1)}{match.group(2)}{match.group(4)}"
    
    processos[chave] = {
        "numero": numero_processo,
        "cliente": os.path.basename(os.path.dirname(os.path.dirname(caminho))),
        "area": area,
        "servico": {"A": "Aéreo", "R": "Rodoviário", "M": "Marítimo"}[match.group(2)],
        "ano": match.group(4),
        "referencia": match.group(5),
        "caminho": corrigir_codificacao_caminho(caminho)
    }

def validar_arquivo(arquivo_path):
    """Valida se o arquivo tem extensão permitida"""
    _, ext = os.path.splitext(arquivo_path)
    return ext.lower() not in EXTENSOES_BLOQUEADAS

def copiar_arquivos(pasta_destino, arquivos):
    """Copia arquivos para a pasta de destino com tratamento de codificação"""
    pasta_destino = Path(corrigir_codificacao_caminho(pasta_destino))
    
    for arquivo in arquivos:
        try:
            destino = pasta_destino / arquivo['name']
            
            if 'outlook_attach_' in arquivo['path'].lower():
                Path(arquivo['path']).rename(destino)
                continue
                
            if not validar_arquivo(arquivo['path']):
                return False, "Tipo de arquivo não permitido"
                
            if destino.exists():
                return False, "arquivo_existente"
            
            shutil.copy2(arquivo['path'], destino)
            
        except Exception as e:
            return False, str(e)
    
    return True,

def abrir_pasta_processo(caminho_pasta):
    """Abre a pasta do processo no explorador"""
    try:
        caminho_pasta = corrigir_codificacao_caminho(caminho_pasta)
        if not os.path.exists(caminho_pasta):
            raise Exception("Pasta não encontrada")
            
        caminho_pasta = os.path.normpath(caminho_pasta)
        
        if os.name == 'nt':
            os.startfile(caminho_pasta)
        elif sys.platform == 'darwin':
            subprocess.run(['open', caminho_pasta])
        else:
            subprocess.run(['xdg-open', caminho_pasta])
            
        return True
    except Exception as e:
        logging.error(f"Erro ao abrir pasta {caminho_pasta}: {str(e)}")
        raise Exception(f"Não foi possível abrir a pasta: {str(e)}")
