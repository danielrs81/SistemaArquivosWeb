import tkinter as tk
from tkinter import ttk, messagebox
from logica import obter_info_processos, abrir_pasta_processo

class TelaBusca:
    def __init__(self, root):
        self.root = root
        self.janela = tk.Toplevel(root)
        self.janela.title("Busca Avançada")
        self.janela.geometry("900x600")
        self.janela.minsize(800, 500)
        
        # Variáveis para paginação
        self.pagina_atual = 1
        self.itens_por_pagina = 50
        self.total_processos = 0
        self.ordenacao_coluna = None
        self.ordenacao_reversa = False
        
        self.criar_interface()

    def criar_interface(self):
        # Frame principal
        main_frame = ttk.Frame(self.janela)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame de filtros
        frame_filtros = ttk.LabelFrame(main_frame, text="Filtros de Busca", padding=10)
        frame_filtros.pack(fill="x", pady=(0, 10))
        
        # Configuração do grid de filtros
        for i in range(6):
            frame_filtros.columnconfigure(i % 2, weight=1 if i % 2 == 1 else 0)
        
        # Variáveis de controle
        self.cliente_var = tk.StringVar()
        self.numero_var = tk.StringVar()
        self.ano_var = tk.StringVar()
        self.area_var = tk.StringVar()
        self.servico_var = tk.StringVar()
        self.referencia_var = tk.StringVar()
        
        # Componentes dos filtros
        ttk.Label(frame_filtros, text="Cliente:").grid(row=0, column=0, sticky="w", pady=2)
        self.cliente_combobox = ttk.Combobox(frame_filtros, textvariable=self.cliente_var)
        self.cliente_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_filtros, text="Número do Processo:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(frame_filtros, textvariable=self.numero_var).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_filtros, text="Ano:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(frame_filtros, textvariable=self.ano_var, width=8).grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(frame_filtros, text="Área:").grid(row=3, column=0, sticky="w", pady=2)
        self.area_combobox = ttk.Combobox(frame_filtros, textvariable=self.area_var, 
                                        values=["", "IMPORTAÇÃO", "EXPORTAÇÃO"], state="readonly")
        self.area_combobox.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_filtros, text="Serviço:").grid(row=4, column=0, sticky="w", pady=2)
        self.servico_combobox = ttk.Combobox(frame_filtros, textvariable=self.servico_var,
                                           values=["", "Aéreo", "Rodoviário", "Marítimo"], state="readonly")
        self.servico_combobox.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(frame_filtros, text="Referência:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(frame_filtros, textvariable=self.referencia_var).grid(row=5, column=1, sticky="ew", padx=5, pady=2)
        
        # Frame de botões
        frame_botoes = ttk.Frame(main_frame)
        frame_botoes.pack(fill="x", pady=5)
        
        ttk.Button(frame_botoes, text="Buscar", command=self.executar_busca).pack(side="left", padx=5)
        ttk.Button(frame_botoes, text="Limpar", command=self.limpar_filtros).pack(side="left", padx=5)
        
        # Frame de resultados
        frame_resultados = ttk.LabelFrame(main_frame, text="Resultados", padding=10)
        frame_resultados.pack(fill="both", expand=True)
        
        # Treeview com barra de rolagem
        self.tree = ttk.Treeview(frame_resultados, 
                               columns=("Numero", "Cliente", "Area", "Servico", "Ano", "Referencia"), 
                               show="headings")
        
        # Configuração das colunas com ordenação
        colunas = [
            ("Numero", "Número", 100),
            ("Cliente", "Cliente", 150),
            ("Area", "Área", 100),
            ("Servico", "Serviço", 100),
            ("Ano", "Ano", 50),
            ("Referencia", "Referência", 200)
        ]
        
        for col_id, col_text, col_width in colunas:
            self.tree.heading(col_id, text=col_text, 
                            command=lambda c=col_id: self.ordenar_por_coluna(c))
            self.tree.column(col_id, width=col_width, anchor="w")
        
        # Barra de rolagem
        scroll_y = ttk.Scrollbar(frame_resultados, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(frame_resultados, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        # Layout da treeview
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        
        # Configurar grid para expansão
        frame_resultados.columnconfigure(0, weight=1)
        frame_resultados.rowconfigure(0, weight=1)
        
        # Botão duplo-clique
        self.tree.bind("<Double-1>", self.abrir_pasta_selecionada)
        
        # Controles de paginação
        self.criar_controles_paginacao(main_frame)
        
        # Atualizar lista de clientes
        self.atualizar_lista_clientes()

    def criar_controles_paginacao(self, parent):
        """Cria controles de paginação na parte inferior"""
        frame_paginacao = ttk.Frame(parent)
        frame_paginacao.pack(fill="x", pady=(10, 0))
        
        ttk.Label(frame_paginacao, text="Itens por página:").pack(side="left", padx=5)
        
        self.combo_paginacao = ttk.Combobox(
            frame_paginacao, 
            values=[10, 25, 50, 100], 
            state="readonly",
            width=5
        )
        self.combo_paginacao.set(self.itens_por_pagina)
        self.combo_paginacao.pack(side="left", padx=5)
        self.combo_paginacao.bind("<<ComboboxSelected>>", self.atualizar_itens_por_pagina)
        
        ttk.Button(frame_paginacao, text="⏮ Primeira", command=self.primeira_pagina).pack(side="left", padx=5)
        ttk.Button(frame_paginacao, text="⏪ Anterior", command=self.pagina_anterior).pack(side="left", padx=5)
        
        self.label_paginacao = ttk.Label(frame_paginacao, text="")
        self.label_paginacao.pack(side="left", padx=10)
        
        ttk.Button(frame_paginacao, text="Próxima ⏩", command=self.proxima_pagina).pack(side="left", padx=5)
        ttk.Button(frame_paginacao, text="Última ⏭", command=self.ultima_pagina).pack(side="left", padx=5)

    def ordenar_por_coluna(self, coluna):
        """Ordena os resultados pela coluna clicada"""
        if self.ordenacao_coluna == coluna:
            self.ordenacao_reversa = not self.ordenacao_reversa
        else:
            self.ordenacao_coluna = coluna
            self.ordenacao_reversa = False
        
        items = [(self.tree.set(child, coluna), child) for child in self.tree.get_children('')]
        
        # Ordenação especial para coluna numérica
        if coluna == "Numero":
            items.sort(key=lambda x: int(x[0]), reverse=self.ordenacao_reversa)
        else:
            items.sort(reverse=self.ordenacao_reversa)
        
        for index, (val, child) in enumerate(items):
            self.tree.move(child, '', index)

    def atualizar_itens_por_pagina(self, event=None):
        self.itens_por_pagina = int(self.combo_paginacao.get())
        self.pagina_atual = 1
        self.executar_busca()

    def primeira_pagina(self):
        self.pagina_atual = 1
        self.executar_busca()

    def pagina_anterior(self):
        if self.pagina_atual > 1:
            self.pagina_atual -= 1
            self.executar_busca()

    def proxima_pagina(self):
        if self.pagina_atual < (self.total_processos // self.itens_por_pagina) + 1:
            self.pagina_atual += 1
            self.executar_busca()

    def ultima_pagina(self):
        self.pagina_atual = (self.total_processos // self.itens_por_pagina) + 1
        self.executar_busca()

    def atualizar_lista_clientes(self):
        processos = obter_info_processos()
        clientes = sorted({dados['cliente'] for dados in processos.values()}, key=str.lower)
        self.cliente_combobox['values'] = clientes

    def abrir_pasta_selecionada(self, event):
        item = self.tree.selection()[0]
        valores = self.tree.item(item, 'values')
        numero_processo = valores[0]
        area = valores[2]
        
        processos = obter_info_processos()
        for proc in processos.values():
            if proc['numero'] == numero_processo and proc['area'] == area:
                abrir_pasta_processo(proc['caminho'])
                break

    def executar_busca(self):
        filtros = {
            'cliente': self.cliente_var.get().strip(),
            'numero': self.numero_var.get().strip(),
            'ano': self.ano_var.get().strip(),
            'area': self.area_var.get().strip(),
            'servico': self.servico_var.get().strip(),
            'referencia': self.referencia_var.get().strip()
        }
        
        resultados = self.buscar_processos(**filtros)
        self.total_processos = len(resultados)
        
        # Aplicar paginação
        inicio = (self.pagina_atual - 1) * self.itens_por_pagina
        fim = inicio + self.itens_por_pagina
        resultados_paginados = resultados[inicio:fim]
        
        # Atualizar exibição
        self.tree.delete(*self.tree.get_children())
        for num, dados in resultados_paginados:
            self.tree.insert("", "end", values=(
                num,
                dados['cliente'],
                dados['area'],
                dados['servico'],
                dados['ano'],
                dados['referencia']
            ))
        
        # Atualizar label de paginação
        total_paginas = max(1, (self.total_processos + self.itens_por_pagina - 1) // self.itens_por_pagina)
        self.label_paginacao.config(
            text=f"Página {self.pagina_atual} de {total_paginas} - Total: {self.total_processos} processos"
        )

    def limpar_filtros(self):
        self.cliente_var.set("")
        self.numero_var.set("")
        self.ano_var.set("")
        self.area_var.set("")
        self.servico_var.set("")
        self.referencia_var.set("")
        self.tree.delete(*self.tree.get_children())
        self.pagina_atual = 1
        self.label_paginacao.config(text="")

    @staticmethod
    def buscar_processos(cliente="", numero="", ano="", area="", servico="", referencia=""):
        processos = obter_info_processos()
        resultados = []
        
        for id_proc, dados in processos.items():
            match = True
            
            if cliente and cliente.upper() not in dados['cliente'].upper():
                match = False
            
            if numero and numero not in dados['numero']:
                match = False
            
            if ano and ano != dados['ano']:
                match = False
            
            if area and area != dados['area']:
                match = False
            
            if servico and servico != dados['servico']:
                match = False
            
            if referencia and referencia.upper() not in dados['referencia'].upper():
                match = False
                
            if match:
                resultados.append((dados['numero'], dados))
        
        # Ordenar por número e depois por área
        resultados.sort(key=lambda x: (x[0], x[1]['area']))
        return resultados