import os
import shutil
import re
from tkinter import messagebox
import subprocess
import sys
import configparser

# Carregar configurações
config = configparser.ConfigParser()
config.read('config.ini')

BASE_DIR = config.get('PATHS', 'BASE_DIR', fallback="D:/Arquivo Digital")
EXTENSOES_BLOQUEADAS = {'.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.jar', '.msi', '.dll'}

def obter_info_processos():
    processos = {}
    if os.path.exists(BASE_DIR):
        for area in os.listdir(BASE_DIR):
            area_path = os.path.join(BASE_DIR, area)
            if os.path.isdir(area_path):
                for cliente in os.listdir(area_path):
                    cliente_path = os.path.join(area_path, cliente)
                    if os.path.isdir(cliente_path):
                        for pasta in os.listdir(cliente_path):
                            match = re.search(r'([IE])([ARM])-(\d{6})-(\d{2}) - (.+)', pasta)
                            if match:
                                numero_processo = match.group(3)
                                processos[f"{numero_processo}_{match.group(1)}{match.group(2)}{match.group(4)}"] = {
                                    "numero": numero_processo,
                                    "cliente": cliente,
                                    "area": "IMPORTAÇÃO" if match.group(1) == "I" else "EXPORTAÇÃO",
                                    "servico": {"A": "Aéreo", "R": "Rodoviário", "M": "Marítimo"}[match.group(2)],
                                    "ano": match.group(4),
                                    "referencia": match.group(5),
                                    "caminho": os.path.join(area_path, cliente, pasta)
                                }
    return processos

def validar_arquivo(arquivo_path):
    """Valida se o arquivo tem extensão permitida"""
    _, ext = os.path.splitext(arquivo_path)
    return ext.lower() not in EXTENSOES_BLOQUEADAS

def criar_pasta(cliente, area, servico, numero_processo, ano, referencia):
    sigla_area = "I" if area == "IMPORTAÇÃO" else "E"
    sigla_servico = servico[0].upper()
    nome_pasta = f"{sigla_area}{sigla_servico}-{numero_processo}-{ano} - {referencia.upper()}"
    caminho_pasta = os.path.join(BASE_DIR, area, cliente, nome_pasta)
    os.makedirs(caminho_pasta, exist_ok=True)
    return caminho_pasta

def copiar_arquivos(pasta_destino, arquivos):
    for arquivo in arquivos:
        try:
            destino = os.path.join(pasta_destino, arquivo['name'])
            
            # Verifica se é um arquivo temporário do Outlook
            if 'outlook_attach_' in arquivo['path'].lower():
                # Move o arquivo em vez de copiar
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                shutil.move(arquivo['path'], destino)
                continue
                
            # Processamento normal para outros arquivos
            if not validar_arquivo(arquivo['path']):
                messagebox.showerror("Erro", f"Tipo de arquivo não permitido: {os.path.splitext(arquivo['path'])[1]}")
                return False
                
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            
            if os.path.exists(destino):
                resposta = messagebox.askyesno("Arquivo Existente", f"Substituir {arquivo['name']}?")
                if not resposta:
                    return False
            
            shutil.copy2(arquivo['path'], destino)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao copiar {arquivo['name']}: {str(e)}")
            return False
    
    return True

def abrir_pasta_processo(caminho_pasta):
    """Abre a pasta do processo no explorador de arquivos"""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(caminho_pasta)
        elif os.name == 'posix':  # Mac e Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', caminho_pasta])
        return True
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir a pasta: {str(e)}")
        return False