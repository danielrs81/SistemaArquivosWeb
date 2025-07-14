import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter import font as tkfont
from PIL import Image, ImageTk
import shutil
import tempfile
import configparser
import logging
import sys
from logica import obter_info_processos, criar_pasta, copiar_arquivos, abrir_pasta_processo
from clientes import obter_clientes, adicionar_cliente, remover_cliente
from busca import TelaBusca

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='sistema_arquivos.log'
)

# Configuração inicial
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    logging.warning("tkinterdnd2 não instalado. Drag-and-drop não estará disponível.")

def validar_arquivo(filepath):
    """Valida se o arquivo possui uma extensão permitida."""
    extensoes_permitidas = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.txt']
    _, ext = os.path.splitext(filepath)
    return ext.lower() in extensoes_permitidas

def is_outlook_temp_file(filepath):
    """Identifica arquivos temporários do Outlook com maior precisão"""
    try:
        if not filepath:  # Se o caminho estiver vazio
            return False
            
        filepath = filepath.lower().replace('/', '\\')
        outlook_signs = [
            'content.outlook',  # Pasta típica do Outlook
            '\\temp\\',        # Pasta temporária
            '~$',              # Prefixo de arquivos temporários do Office
            '.tmp',            # Extensão temporária
            'outlook_attach_'  # Prefixo comum do Outlook
        ]
        return any(sign in filepath for sign in outlook_signs)
    except Exception:
        return False

class OutlookIntegration:
    """Classe para integração com o Microsoft Outlook"""
    def __init__(self, callback):
        self.callback = callback
        self._setup_clipboard_monitoring()

    def _setup_clipboard_monitoring(self):
        """Configura monitoramento da área de transferência como fallback"""
        try:
            import win32clipboard
            from win32con import WM_DRAWCLIPBOARD
            self.clipboard_viewer = None
            self._clipboard_format = None
            
            # Tenta registrar um formato personalizado para o Outlook
            try:
                self._clipboard_format = win32clipboard.RegisterClipboardFormat("OutlookAttachments")
            except:
                pass
            
            logging.info("Monitoramento de área de transferência ativado")
        except ImportError:
            logging.warning("pywin32 não instalado. Monitoramento de área de transferência desativado")

    def check_clipboard(self):
        """Verifica a área de transferência por arquivos do Outlook"""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            
            # Verifica se há arquivos na área de transferência
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                files = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                if files:
                    self.callback(files)
            
            win32clipboard.CloseClipboard()
        except Exception as e:
            logging.error(f"Erro ao verificar área de transferência: {e}")

class Aplicativo:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Arquivos Digitais")
        self.root.geometry("900x850")
        self.root.configure(bg='#f0f0f0')
        
        # Variáveis de controle
        self.cliente_var = tk.StringVar()
        self.area_var = tk.StringVar()
        self.servico_var = tk.StringVar()
        self.arquivos_para_upload = []
        self.bg_image = None
        self.bg_photo = None
        self.bg_label = None

        # Configurações de estilo
        self._configure_styles()
        
        # Inicialização dos componentes
        self.criar_interface()
        self.configurar_drag_drop()
        self.configurar_validacoes()
        
        # Configura o evento de fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_styles(self):
        """Configura os estilos visuais da interface"""
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TButton', font=('Arial', 10), padding=5)
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Highlight.TFrame', background='#e0e0ff')
        self.style.configure('Accent.TButton', foreground='black', background='#4CAF50')
        self.style.map('Accent.TButton', 
                     background=[('active', '#45a049'), ('disabled', '#cccccc')])
        
    def on_close(self):
        """Executa ao fechar a janela"""
        self._limpar_arquivos_temporarios()
        self.root.destroy()

    def criar_interface(self):
        """Cria todos os widgets da interface"""
        self.criar_menu()
        self.carregar_logo()
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Frame de cadastro de clientes
        frame_clientes = ttk.LabelFrame(main_frame, text="Gerenciamento de Clientes", padding=10)
        frame_clientes.pack(fill="x", pady=5)
        
        # Cadastro de novo cliente
        ttk.Label(frame_clientes, text="Nome do Cliente:").grid(row=0, column=0, sticky="w")
        self.cliente_entry = ttk.Entry(frame_clientes)
        self.cliente_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        frame_botoes_cliente = ttk.Frame(frame_clientes)
        frame_botoes_cliente.grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Button(frame_botoes_cliente, text="Cadastrar", command=self.cadastrar_cliente).pack(side="left", padx=2)
        ttk.Button(frame_botoes_cliente, text="Excluir", command=self.excluir_cliente).pack(side="left", padx=2)
        
        # Dropdown de clientes
        ttk.Label(frame_clientes, text="Selecione o Cliente:").grid(row=2, column=0, sticky="w")
        self.clientes_combobox = ttk.Combobox(frame_clientes, textvariable=self.cliente_var, state="normal")
        self.clientes_combobox.grid(row=2, column=1, sticky="ew", padx=5)
        self.atualizar_lista_clientes()
        
        # Frame de processo
        frame_processo = ttk.LabelFrame(main_frame, text="Arquivamento de Processos", padding=10)
        frame_processo.pack(fill="x", pady=5)
        
        # Área e serviço
        ttk.Label(frame_processo, text="Área:").grid(row=0, column=0, sticky="w")
        self.area_combobox = ttk.Combobox(frame_processo, textvariable=self.area_var, 
                                        values=["IMPORTAÇÃO", "EXPORTAÇÃO"], state="readonly")
        self.area_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_processo, text="Serviço:").grid(row=1, column=0, sticky="w")
        self.servico_combobox = ttk.Combobox(frame_processo, textvariable=self.servico_var,
                                           values=["Aéreo", "Rodoviário", "Marítimo"], state="readonly")
        self.servico_combobox.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        # Campos de processo
        ttk.Label(frame_processo, text="Nº Processo (6 dígitos):").grid(row=2, column=0, sticky="w")
        self.numero_processo_entry = ttk.Entry(frame_processo)
        self.numero_processo_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_processo, text="Ano (2 dígitos):").grid(row=3, column=0, sticky="w")
        self.ano_entry = ttk.Entry(frame_processo)
        self.ano_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_processo, text="Referência:").grid(row=4, column=0, sticky="w")
        self.referencia_entry = ttk.Entry(frame_processo)
        self.referencia_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        
        # Área de upload
        self.upload_frame = ttk.LabelFrame(main_frame, text="Arquivos para Upload", padding=10)
        self.upload_frame.pack(fill="both", expand=True, pady=5)
        
        self.upload_label = ttk.Label(
            self.upload_frame, 
            text="Arraste e solte arquivos aqui (incluindo do Outlook) ou clique nos botões abaixo",
            font=('Arial', 10, 'italic')
        )
        self.upload_label.pack(pady=20)
        
        # Botões principais
        frame_botoes = ttk.Frame(main_frame)
        frame_botoes.pack(pady=10)
        
        ttk.Button(
            frame_botoes, 
            text="Adicionar Arquivos", 
            command=self.selecionar_arquivos
        ).pack(side="left", padx=5)
        
        ttk.Button(
            frame_botoes, 
            text="Adicionar Pasta", 
            command=self.selecionar_pasta
        ).pack(side="left", padx=5)
        
        ttk.Button(
            frame_botoes, 
            text="Importar do Outlook", 
            command=self.importar_do_outlook,
            style='Accent.TButton'
        ).pack(side="left", padx=5)
        
        ttk.Button(
            frame_botoes, 
            text="Processar Arquivos", 
            command=self.fazer_upload,
            style='Accent.TButton'
        ).pack(side="left", padx=5)
        
        ttk.Button(
            frame_botoes, 
            text="Busca Avançada", 
            command=self.abrir_tela_busca
        ).pack(side="left", padx=5)

        btn_limpar = ttk.Button(
            frame_processo,
            text="Limpar Campos",
            command=self.limpar_campos_processo,
            style='TButton'
        )
        btn_limpar.grid(row=5, column=1, sticky="e", pady=10)

    def criar_menu(self):
        menubar = tk.Menu(self.root)
        
        # Menu Configurações
        menu_config = tk.Menu(menubar, tearoff=0)
        menu_config.add_command(label="Definir Pasta Base", command=self.definir_pasta_base)
        menu_config.add_command(label="Definir Pasta de Clientes", command=self.definir_pasta_clientes)
        menubar.add_cascade(label="Configurações", menu=menu_config)
        
        # Menu Aparência
        menu_aparencia = tk.Menu(menubar, tearoff=0)
        menu_aparencia.add_command(label="Alterar Logo", command=self.alterar_logo)
        menubar.add_cascade(label="Aparência", menu=menu_aparencia)
        
        # Menu Ajuda
        menu_ajuda = tk.Menu(menubar, tearoff=0)
        menu_ajuda.add_command(label="Sobre", command=self.mostrar_sobre)
        menubar.add_cascade(label="Ajuda", menu=menu_ajuda)
        
        self.root.config(menu=menubar)

    def validar_processo_existente(self, numero_processo, ano, servico, referencia):
        """Valida se os campos correspondem ao processo existente"""
        processos = obter_info_processos()
        for proc in processos.values():
            if proc['numero'] == numero_processo:
                if proc['ano'] != ano:
                    messagebox.showwarning(
                        "Ano Incorreto",
                        f"Já existe um processo com o número {numero_processo} "
                        f"para o ano {proc['ano']}. Corrija o ano para continuar."
                    )
                    return False
                if proc['servico'] != servico:
                    messagebox.showwarning(
                        "Serviço Incorreto",
                        f"Já existe um processo com o número {numero_processo} "
                        f"para o serviço {proc['servico']}. Corrija o serviço para continuar."
                    )
                    return False
                if proc['referencia'].upper() != referencia.upper():
                    messagebox.showwarning(
                        "Referência Incorreta",
                        f"Já existe um processo com o número {numero_processo} "
                        f"com a referência {proc['referencia']}. Corrija a referência para continuar."
                    )
                    return False
        return True

    def configurar_drag_drop(self):
        """Configura o drag-and-drop com tratamento especial para Outlook"""
        if HAS_DND:
            self.upload_frame.drop_target_register(DND_FILES)
            self.upload_frame.dnd_bind('<<Drop>>', self._handle_complex_drop)
            self.upload_frame.bind('<Enter>', lambda e: self.upload_frame.config(style='Highlight.TFrame'))
            self.upload_frame.bind('<Leave>', lambda e: self.upload_frame.config(style='TFrame'))
            self.upload_label.config(text="Arraste e solte arquivos aqui (incluindo do Outlook)")
        else:
            self.upload_label.config(text="Clique em 'Adicionar Arquivos' ou 'Adicionar Pasta'")

    def _handle_complex_drop(self, event):
        """Processa eventos de drop com tratamento especial para Outlook"""
        try:
            if not hasattr(event, 'data'):
                return

            files = self.root.tk.splitlist(event.data)
            for f in files:
                try:
                    f = f.strip()
                    if not f:
                        continue
                        
                    # Corrige caminhos com espaços
                    if not os.path.exists(f):
                        f = f.replace('{', '').replace('}', '')  # Remove chaves que o Outlook pode adicionar
                    
                    if os.path.exists(f):
                        if os.path.isdir(f):
                            for root, _, files_in_dir in os.walk(f):
                                for file in files_in_dir:
                                    self._processar_arquivo_individual(os.path.join(root, file))
                        else:
                            self._processar_arquivo_individual(f)
                except Exception as e:
                    logging.error(f"Erro ao processar {f}: {str(e)}")
                    continue

            self.atualizar_lista_arquivos()
            
        except Exception as e:
            logging.error(f"Erro no drag-and-drop: {str(e)}")
            messagebox.showerror("Erro", f"Falha ao processar arquivos arrastados: {str(e)}")

    def _handle_outlook_files(self, files):
        """Processa arquivos recebidos do Outlook"""
        for f in files:
            self._processar_arquivo_individual(f)
        self.atualizar_lista_arquivos()

    def importar_do_outlook(self):
        """Alternativa para quando o drag-and-drop não funciona"""
        try:
            from win32com.client import Dispatch
            outlook = Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            
            # Seleciona a caixa de entrada
            inbox = namespace.GetDefaultFolder(6)
            
            # Mostra diálogo para selecionar mensagem
            selected_item = outlook.Session.PickFolder()
            
            if selected_item:
                messagebox.showinfo("Outlook", f"Processando e-mails de: {selected_item.Name}")
                
                # Processa os anexos de cada mensagem
                for message in selected_item.Items:
                    for attachment in message.Attachments:
                        temp_path = os.path.join(tempfile.gettempdir(), attachment.FileName)
                        attachment.SaveAsFile(temp_path)
                        self._processar_arquivo_individual(temp_path)
                
                self.atualizar_lista_arquivos()
                
        except Exception as e:
            messagebox.showerror("Erro Outlook", f"Não foi possível acessar o Outlook: {e}")
            logging.error(f"Erro no Outlook: {e}")

    def _processar_arquivo_individual(self, filepath):
        """Processa um único arquivo com tratamento especial para Outlook"""
        try:
            if not filepath or not os.path.exists(filepath):
                return

            is_temp = False
            
            if is_outlook_temp_file(filepath):
                # Cria diretório temporário seguro
                temp_dir = os.path.join(tempfile.gettempdir(), 'outlook_attachments')
                os.makedirs(temp_dir, exist_ok=True)
                
                # Gera nome limpo para o arquivo
                original_name = os.path.basename(filepath)
                clean_name = original_name.replace('~$', '').replace('outlook_attach_', '')
                new_path = os.path.join(temp_dir, clean_name)
                
                # Tenta mover o arquivo (evita bloqueios)
                try:
                    shutil.move(filepath, new_path)
                    filepath = new_path
                    is_temp = True
                except Exception as move_error:
                    logging.warning(f"Falha ao mover, tentando copiar: {move_error}")
                    shutil.copy2(filepath, new_path)
                    filepath = new_path
                    is_temp = True

            # Adiciona à lista de upload
            self.arquivos_para_upload.append({
                'path': filepath,
                'name': os.path.basename(filepath),
                'is_temp': is_temp
            })

        except Exception as e:
            logging.error(f"Erro ao processar arquivo {filepath}: {e}")

    def carregar_logo(self):
        try:
            if hasattr(self, 'logo_label'):
                self.logo_label.destroy()
            
            if os.path.exists('logo.png'):
                self.logo = Image.open("logo.png")
                self.logo = self.logo.resize((200, 60), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(self.logo)
                self.logo_label = ttk.Label(self.root, image=self.logo_img)
                self.logo_label.pack(pady=(10, 20))
        except Exception as e:
            print(f"Erro ao carregar logo: {str(e)}")

    def configurar_validacoes(self):
        # Validação para aceitar apenas números
        vcmd_num = (self.root.register(self.validar_numerico), '%P')
        self.numero_processo_entry.config(validate="key", validatecommand=vcmd_num)
        self.ano_entry.config(validate="key", validatecommand=vcmd_num)
        
        # Validação de tamanho máximo
        self.numero_processo_entry.config(validatecommand=(self.root.register(lambda P: len(P) <= 6), '%P'))
        self.ano_entry.config(validatecommand=(self.root.register(lambda P: len(P) <= 2), '%P'))
        
        # Validação de referência
        self.vcmd_referencia = (self.root.register(self.validar_referencia), '%P')
        self.referencia_entry.config(validate="key", validatecommand=self.vcmd_referencia)

    def validar_numerico(self, texto):
        """Valida se o texto contém apenas números"""
        if texto == "" or texto.isdigit():
            return True
        messagebox.showwarning("Atenção", "Este campo aceita apenas números!")
        return False

    def validar_referencia(self, texto):
        caracteres_proibidos = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        if any(caracter in texto for caracter in caracteres_proibidos):
            messagebox.showwarning("Atenção", "Referência não pode conter: \\ / : * ? \" < > |")
            return False
        return True

    def definir_pasta_base(self):
        """Permite ao usuário definir a pasta base para armazenamento"""
        pasta = filedialog.askdirectory(title="Selecionar Pasta Base para Arquivos")
        if pasta:
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            if not config.has_section('PATHS'):
                config.add_section('PATHS')
            
            config.set('PATHS', 'BASE_DIR', pasta)
            
            with open('config.ini', 'w') as f:
                config.write(f)
            
            messagebox.showinfo("Sucesso", f"Pasta base definida como:\n{pasta}")

    def definir_pasta_clientes(self):
        """Permite ao usuário definir a pasta para o arquivo de clientes"""
        pasta = filedialog.askdirectory(title="Selecionar Pasta para Clientes")
        if pasta:
            config = configparser.ConfigParser()
            config.read('config.ini')
            
            if not config.has_section('PATHS'):
                config.add_section('PATHS')
            
            clientes_file = os.path.join(pasta, 'clientes.txt')
            config.set('PATHS', 'CLIENTES_FILE', clientes_file)
            
            with open('config.ini', 'w') as f:
                config.write(f)
            
            messagebox.showinfo("Sucesso", f"Arquivo de clientes definido como:\n{clientes_file}")

    def alterar_logo(self):
        arquivo = filedialog.askopenfilename(
            title="Selecionar Logo",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg")]
        )
        if arquivo:
            try:
                if not hasattr(self, 'logo_label'):
                    self.logo_label = ttk.Label(self.root)
                    self.logo_label.pack(pady=10)
                
                self.logo = Image.open(arquivo)
                self.logo = self.logo.resize((200, 60), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(self.logo)
                self.logo_label.config(image=self.logo_img)
                
                # Salva a logo selecionada
                shutil.copy(arquivo, 'logo.png')
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível carregar a imagem: {str(e)}")

    def mostrar_sobre(self):
        messagebox.showinfo("Sobre", "Sistema de Arquivos Digitais\nVersão 2.0\nDesenvolvido por [Sua Empresa]")

    def limpar_campos_processo(self):
        """Limpa todos os campos do formulário de processo"""
        self.area_var.set("")
        self.servico_var.set("")
        self.numero_processo_entry.delete(0, tk.END)
        self.ano_entry.delete(0, tk.END)
        self.referencia_entry.delete(0, tk.END)
        messagebox.showinfo("Sucesso", "Campos do processo limpos com sucesso!")

    def selecionar_arquivos(self, event=None):
        files = filedialog.askopenfilenames(title="Selecione os arquivos")
        if files:
            for f in files:
                self.arquivos_para_upload.append({'path': f, 'name': os.path.basename(f)})
            self.atualizar_lista_arquivos()

    def selecionar_pasta(self):
        folder = filedialog.askdirectory(title="Selecione uma pasta")
        if folder:
            for root, _, files in os.walk(folder):
                for file in files:
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, folder)
                    self.arquivos_para_upload.append({'path': path, 'name': rel_path})
            self.atualizar_lista_arquivos()

    def atualizar_lista_arquivos(self):
        for widget in self.upload_frame.winfo_children():
            if widget != self.upload_label:
                widget.destroy()
        
        if not self.arquivos_para_upload:
            self.upload_label.pack()
            return
        
        self.upload_label.pack_forget()
        
        # Cria um canvas com barra de rolagem
        container = ttk.Frame(self.upload_frame)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all"),
                width=e.width
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for i, arquivo in enumerate(self.arquivos_para_upload):
            ttk.Label(scrollable_frame, text=arquivo['name']).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            ttk.Button(scrollable_frame, text="Remover", 
                      command=lambda idx=i: self.remover_arquivo(idx)).grid(row=i, column=1, padx=5)
        
        # Configura o canvas para redimensionar com a janela
        container.bind("<Configure>", lambda e: canvas.configure(width=e.width))

    def remover_arquivo(self, index):
        if 0 <= index < len(self.arquivos_para_upload):
            self.arquivos_para_upload.pop(index)
            self.atualizar_lista_arquivos()

    def abrir_tela_busca(self):
        TelaBusca(self.root)

    def atualizar_lista_clientes(self):
        clientes = sorted(obter_clientes(), key=str.lower)
        self.clientes_combobox['values'] = clientes
        self.cliente_var.set("")

    def cadastrar_cliente(self):
        novo_cliente = self.cliente_entry.get().strip()
        if not novo_cliente:
            messagebox.showwarning("Atenção", "O nome do cliente não pode estar vazio!")
            return
        
        sucesso, mensagem = adicionar_cliente(novo_cliente)
        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            self.atualizar_lista_clientes()
            self.cliente_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Atenção", mensagem)

    def excluir_cliente(self):
        cliente_selecionado = self.cliente_var.get()
        if not cliente_selecionado:
            messagebox.showwarning("Atenção", "Nenhum cliente selecionado!")
            return
        
        if messagebox.askyesno("Confirmação", f"Tem certeza que deseja excluir o cliente '{cliente_selecionado}'?"):
            sucesso, mensagem = remover_cliente(cliente_selecionado)
            if sucesso:
                messagebox.showinfo("Sucesso", mensagem)
                self.atualizar_lista_clientes()
            else:
                messagebox.showwarning("Atenção", mensagem)

    def fazer_upload(self):
        cliente = self.cliente_var.get()
        area = self.area_var.get()
        servico = self.servico_var.get()
        numero_processo = self.numero_processo_entry.get()
        ano = self.ano_entry.get()
        referencia = self.referencia_entry.get().strip().upper()
        
        # Validações básicas
        if len(numero_processo) != 6 or not numero_processo.isdigit():
            messagebox.showwarning("Atenção", "O número do processo deve ter exatamente 6 dígitos numéricos!")
            return
        if len(ano) != 2 or not ano.isdigit():
            messagebox.showwarning("Atenção", "O ano do processo deve ter exatamente 2 dígitos numéricos!")
            return
        if not all([cliente, area, servico, referencia]):
            messagebox.showwarning("Atenção", "Todos os campos devem ser preenchidos!")
            return
        
        # Validação de processo existente
        if not self.validar_processo_existente(numero_processo, ano, servico, referencia):
            return
        
        # Confirmação se não houver arquivos
        if not self.arquivos_para_upload:
            resposta = messagebox.askyesno(
                "Pasta Vazia", 
                "Nenhum arquivo foi selecionado. Deseja criar a pasta sem documentos?",
                icon='warning'
            )
            if not resposta:
                return
        
        # Executa o upload/criação da pasta
        pasta_destino = criar_pasta(cliente, area, servico, numero_processo, ano, referencia)
        
        if not self.arquivos_para_upload:
            messagebox.showinfo("Sucesso", "Pasta criada sem documentos!")
            return
        
        if copiar_arquivos(pasta_destino, self.arquivos_para_upload):
            messagebox.showinfo("Sucesso", f"{len(self.arquivos_para_upload)} arquivo(s) copiado(s) com sucesso!")
            self.arquivos_para_upload = []
            self.atualizar_lista_arquivos()
            
        for arquivo in self.arquivos_para_upload:
            try:
                destino = os.path.join(pasta_destino, arquivo['name'])
                
                # Se for arquivo temporário, já foi movido - apenas copiar
                if arquivo.get('is_temp'):
                    shutil.copy2(arquivo['path'], destino)
                else:
                    # Processamento normal para outros arquivos
                    if not validar_arquivo(arquivo['path']):
                        raise ValueError(f"Tipo de arquivo não permitido: {os.path.splitext(arquivo['path'])[1]}")
                    
                    if os.path.exists(destino):
                        resposta = messagebox.askyesno("Arquivo Existente", f"Substituir {arquivo['name']}?")
                        if not resposta:
                            continue
                    
                    shutil.copy2(arquivo['path'], destino)
            
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao copiar {arquivo['name']}: {str(e)}")
    
    def _limpar_arquivos_temporarios(self):
        """Remove arquivos temporários marcados para exclusão"""
        temp_files = [f for f in self.arquivos_para_upload if f.get('is_temp')]
        
        for arquivo in temp_files:
            try:
                if os.path.exists(arquivo['path']):
                    os.remove(arquivo['path'])
            except Exception as e:
                logging.error(f"Falha ao remover arquivo temporário {arquivo['path']}: {str(e)}")
        
        # Remover apenas os temporários da lista
        self.arquivos_para_upload = [f for f in self.arquivos_para_upload if not f.get('is_temp')]

if __name__ == "__main__":
    # Configuração para Windows (DPI)
    if os.name == 'nt':
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    # Cria a janela principal corretamente
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = Aplicativo(root)
    root.mainloop()