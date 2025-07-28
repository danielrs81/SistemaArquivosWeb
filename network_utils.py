# -*- coding: utf-8 -*-
import subprocess
import os
import logging
from configparser import ConfigParser
import ctypes

config = ConfigParser()
config.read('config.ini')

def verificar_conexao_servidor():
    """Verifica se o servidor de rede está acessível"""
    try:
        exportacao_dir = config.get('PATHS', 'EXPORTACAO_DIR', '')
        if exportacao_dir.startswith('\\\\'):
            servidor = exportacao_dir.split('\\')[2]
            try:
                # Testa ping ao servidor
                subprocess.run(['ping', '-n', '1', servidor], check=True, stdout=subprocess.PIPE)
                logging.info(f"Conexão com servidor {servidor} OK")
                return True
            except subprocess.CalledProcessError:
                logging.error(f"Servidor {servidor} não responde ao ping")
                return False
        return True
    except Exception as e:
        logging.error(f"Erro ao verificar conexão: {str(e)}")
        return False

def mapear_unidade_rede():
    """Mapeia o caminho de rede para uma unidade local (Windows)"""
    try:
        exportacao_dir = config.get('PATHS', 'EXPORTACAO_DIR', '')
        if exportacao_dir.startswith('\\\\'):
            # Configuração do mapeamento
            letra_unidade = 'Z:'
            caminho_completo = f"{letra_unidade}\\{exportacao_dir.split('E$\\')[1]}"
            
            # Remove mapeamento existente se houver
            ctypes.windll.WNetCancelConnection2W(letra_unidade, 0, True)
            
            # Cria novo mapeamento
            resultado = ctypes.windll.WNetAddConnection2W(
                0,  # Tipo de recurso
                None,  # Nome local (None para padrão)
                letra_unidade,  # Letra da unidade
                exportacao_dir  # Caminho de rede
            )
            
            if resultado == 0:
                logging.info(f"Mapeamento criado: {letra_unidade} -> {exportacao_dir}")
                return caminho_completo
            else:
                logging.error(f"Falha no mapeamento (código {resultado})")
                return exportacao_dir
        return exportacao_dir
    except Exception as e:
        logging.error(f"Erro no mapeamento de rede: {str(e)}")
        return exportacao_dir
    
def verificar_permissao_pasta(caminho):
    """Verifica se o serviço tem acesso à pasta"""
    try:
        # Teste de leitura
        os.listdir(caminho)
        # Teste de escrita (tenta criar arquivo temporário)
        teste_arquivo = os.path.join(caminho, 'teste_permissao.tmp')
        with open(teste_arquivo, 'w') as f:
            f.write('teste')
        os.remove(teste_arquivo)
        return True
    except Exception as e:
        logging.error(f"Falha de permissão em {caminho}: {str(e)}")
        return False