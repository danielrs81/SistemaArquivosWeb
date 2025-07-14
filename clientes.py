import sqlite3
import os
from threading import Lock
from configparser import ConfigParser
import logging

# Configurar logging
logging.basicConfig(filename='sistema.log', level=logging.ERROR)

# Obter caminho do banco de dados
config = ConfigParser()
config.read('config.ini')
CLIENTES_DB = config.get('PATHS', 'CLIENTES_FILE')

# Garantir que o diretório existe
os.makedirs(os.path.dirname(CLIENTES_DB), exist_ok=True)

db_lock = Lock()

def init_db():
    """Inicializa o banco de dados se não existir"""
    try:
        with db_lock:
            conn = sqlite3.connect(CLIENTES_DB)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nome TEXT UNIQUE
                            )''')
            conn.commit()
    except Exception as e:
        logging.error(f"Erro ao inicializar banco de dados: {str(e)}")
        raise

def obter_clientes():
    """Retorna lista de clientes em ordem alfabética"""
    try:
        init_db()  # Garante que o banco está criado
        
        with db_lock:
            conn = sqlite3.connect(CLIENTES_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM clientes ORDER BY nome")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Erro ao obter clientes: {str(e)}")
        return []  # Retorna lista vazia em caso de erro

def adicionar_cliente(novo_cliente):
    novo_cliente = novo_cliente.strip().upper()
    
    try:
        init_db()
        
        with db_lock:
            conn = sqlite3.connect(CLIENTES_DB)
            cursor = conn.cursor()
            
            # Verifica se já existe
            cursor.execute("SELECT id FROM clientes WHERE nome = ?", (novo_cliente,))
            if cursor.fetchone():
                return False, "Este cliente já está cadastrado!"
            
            # Adiciona novo
            cursor.execute("INSERT INTO clientes (nome) VALUES (?)", (novo_cliente,))
            conn.commit()
            
            return True, "Cliente cadastrado com sucesso!"
    except Exception as e:
        logging.error(f"Erro ao adicionar cliente: {str(e)}")
        return False, f"Erro de banco de dados: {str(e)}"

def remover_cliente(nome_cliente):
    nome_cliente = nome_cliente.strip().upper()
    
    try:
        init_db()
        
        with db_lock:
            conn = sqlite3.connect(CLIENTES_DB)
            cursor = conn.cursor()
            
            # Verifica se existe
            cursor.execute("SELECT id FROM clientes WHERE nome = ?", (nome_cliente,))
            if not cursor.fetchone():
                return False, "Cliente não encontrado!"
            
            # Remove
            cursor.execute("DELETE FROM clientes WHERE nome = ?", (nome_cliente,))
            conn.commit()
            
            return True, "Cliente removido com sucesso!"
    except Exception as e:
        logging.error(f"Erro ao remover cliente: {str(e)}")
        return False, f"Erro de banco de dados: {str(e)}"