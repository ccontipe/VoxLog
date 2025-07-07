import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import re # Importar módulo de expressões regulares para análise de texto

# --- Funções de Instalação e Importação ---
def install_package(package):
    try:
        print(f"Tentando instalar o pacote: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])
        print(f"Pacote '{package}' instalado com sucesso.")
        return True
    except subprocess.CalledwCalledProcessError as e:
        print(f"Erro ao instalar o pacote '{package}': {e}")
        print("Certifique-se de ter permissão de escrita ou execute como administrador, se necessário.")
        messagebox.showerror("Erro de Instalação", f"Falha ao instalar o pacote '{package}'. Por favor, tente instalar manualmente ou execute o script com permissões adequadas.")
        return False
    except Exception as e:
        print(f"Ocorreu uma exceção ao instalar '{package}': {e}")
        messagebox.showerror("Erro de Instalação", f"Ocorreu um erro inesperado ao instalar '{package}': {e}")
        return False

# Tenta importar faster_whisper e torch globalmente.
try:
    from faster_whisper import WhisperModel
    import torch
    if not torch.cuda.is_available():
        print("Aviso: CUDA não está disponível. A transcrição será executada na CPU, mesmo se a GPU for selecionada.")
except ImportError:
    print(" faster-whisper e/ou torch não encontrados. Iniciando instalação automática...")
    if not install_package("faster-whisper"):
        sys.exit(1)
    if not install_package("torch"):
        sys.exit(1)

    try:
        from faster_whisper import WhisperModel
        import torch
    except ImportError:
        print("Erro Fatal: faster-whisper e/ou torch não puderam ser instalados ou importados após a tentativa automática.")
        messagebox.showerror("Erro Fatal", "faster-whisper e/ou torch não puderam ser instalados ou importados. Por favor, verifique sua conexão com a internet e permissões, e tente instalar manualmente: pip install faster-whisper torch")
        sys.exit(1)

# --- Análise de Texto e Geração de Mapa Mental (NOVA SEÇÃO) ---
def analyze_text_for_mindmap(text):
    """
    Analisa o texto transcrito para extrair elementos para um mapa mental.
    Esta é uma implementação simplificada e pode ser melhorada com PLN mais avançado.
    """
    lines = [line.strip() for line in text.split('.') if line.strip()]

    if not lines:
        return None, [], {}

    # 1. Tema Central (primeira ou mais frequente sentença curta)
    # Heurística simples: a primeira sentença ou a sentença mais curta e comum
    # pode ser considerada o tema central.
    central_theme = lines[0].split('\n')[0] if lines else "Tema Central da Transcrição"
    
    # Tentativa de pegar algo mais representativo, se a primeira linha for muito genérica
    if len(central_theme) > 100: # Se for muito longa, tente algo mais conciso
        sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            central_theme = max(sentences, key=len) # A frase mais longa pode ser um bom sumário
            if len(central_theme) > 100:
                central_theme = central_theme[:100] + "..." # Truncar se ainda for muito longa


    # 2. Ideias Principais e 3. Detalhes/Subtópicos
    main_ideas = []
    details_map = {} # {ideia_principal: [detalhes]}

    current_main_idea = None
    for i, line in enumerate(lines):
        # Heurística: sentenças mais longas ou que começam com maiúsculas (novo parágrafo/ideia)
        # podem ser ideias principais. Sentenças mais curtas ou que seguem
        # podem ser detalhes.
        if len(line) > 50 and not current_main_idea: # Considera uma frase longa como potencial ideia principal
            current_main_idea = line
            main_ideas.append(current_main_idea)
            details_map[current_main_idea] = []
        elif current_main_idea:
            # Se já temos uma ideia principal, as próximas linhas são detalhes
            details_map[current_main_idea].append(line)
        else: # Se não encontrou uma ideia principal ainda e a linha é curta, tenta iniciar com ela
            current_main_idea = line
            main_ideas.append(current_main_idea)
            details_map[current_main_idea] = []

    # Se não houver main_ideas extraídas, coloque todo o texto como uma única ideia principal
    if not main_ideas and text:
        main_ideas.append(text[:200] + "...") # Pega os primeiros 200 caracteres como ideia principal
        details_map[main_ideas[0]] = [] # Sem detalhes específicos neste caso heurístico simples


    return central_theme, main_ideas, details_map


def generate_plantuml_mindmap(central_theme, main_ideas, details_map):
    plantuml_code = "@startmindmap\n"
    plantuml_code += f"* {central_theme}\n"

    for idea in main_ideas:
        plantuml_code += f"** {idea}\n"
        if idea in details_map:
            for detail in details_map[idea]:
                plantuml_code += f"*** {detail}\n"
    
    plantuml_code += "@endmindmap\n"
    return plantuml_code

# --- Lógica de Transcrição ---
def transcribe_audio_logic(audio_path, model_size, use_gpu, output_path, generate_mindmap, progress_label_callback=None, progress_bar_callback=None, stop_event=None):
    transcription_interrupted = False
    try:
        if 'torch' not in sys.modules:
            raise ImportError("O módulo 'torch' não está carregado. Por favor, reinicie e verifique a instalação.")

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"

        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            device = "cpu"

        print(f"Usando o dispositivo: {device}")

        compute_type = "float16" if device == "cuda" else "int8"

        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            return

        segments_generator, info = model.transcribe(audio_path, beam_size=5)

        full_transcription = ""
        audio_duration = info.duration

        for segment in segments_generator:
            if stop_event and stop_event.is_set():
                transcription_interrupted = True
                messagebox.showinfo("Transcrição Cancelada", "A transcrição foi cancelada pelo usuário.")
                break

            text = segment.text.strip()
            full_transcription += text + " "

            if progress_label_callback and progress_bar_callback:
                progress_percentage = (segment.end / audio_duration) * 100
                progress_bar_callback(progress_percentage)
                progress_label_callback(f"Progresso: {int(progress_percentage)}%\n[{text}]")

        if not transcription_interrupted:
            # Salvar a transcrição completa
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_transcription.strip())

            messagebox.showinfo("Sucesso", f"Transcrição concluída e salva em '{output_path}'")

            # Gerar e salvar o mapa mental se a opção estiver ativada
            if generate_mindmap:
                progress_label_callback("Gerando mapa mental...")
                central_theme, main_ideas, details_map = analyze_text_for_mindmap(full_transcription.strip())
                if central_theme:
                    plantuml_code = generate_plantuml_mindmap(central_theme, main_ideas, details_map)
                    mindmap_output_path = os.path.splitext(output_path)[0] + "_mindmap.puml"
                    with open(mindmap_output_path, "w", encoding="utf-8") as f:
                        f.write(plantuml_code)
                    messagebox.showinfo("Sucesso", f"Mapa mental PlantUML gerado e salvo em '{mindmap_output_path}'")
                else:
                    messagebox.showwarning("Mapa Mental", "Não foi possível extrair informações suficientes para gerar o mapa mental.")
        else:
            if progress_label_callback:
                progress_label_callback("Cancelado.")

    except Exception as e:
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
    finally:
        if progress_label_callback:
            if not transcription_interrupted:
                progress_label_callback("Pronto.")
        if progress_bar_callback:
            progress_bar_callback(0)


# --- Interface Gráfica Tkinter ---
class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("Transcritor de Áudio 'CesarVox' [Faster Whisper]")
        master.geometry("600x550")
        master.resizable(False, False)

        self.gpu_var = tk.BooleanVar(value=False)
        self.mindmap_var = tk.BooleanVar(value=False)
        self.model_var = tk.StringVar(value="small")
        self.audio_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.progress_value = tk.DoubleVar(value=0)

        self.stop_transcription_event = threading.Event()

        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=3)

        self.create_widgets()

    def create_widgets(self):
        # --- DEFINIÇÃO DOS ESTILOS NO INÍCIO ---
        style = ttk.Style()
        # Estilo para os botões "Procurar" e "Salvar"
        style.configure("Small.TButton", font=('Helvetica', 10), padding=8)
        style.map("Small.TButton",
                  foreground=[('pressed', 'red'), ('active', 'blue')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        # Estilo para o botão Transcrever (verde)
        style.configure("Green.TButton", font=('Helvetica', 10, 'bold'), padding=8, foreground="green")
        style.map("Green.TButton",
                  foreground=[('pressed', 'darkgreen'), ('active', 'lime green')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        # Estilo para o botão Parar/Cancelar (vermelho)
        style.configure("Red.TButton", font=('Helvetica', 10, 'bold'), padding=8, foreground="red")
        style.map("Red.TButton",
                  foreground=[('pressed', 'darkred'), ('active', 'salmon')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])
        # --- FIM DA DEFINIÇÃO DE ESTILOS ---

        row_idx = 0

        # Frame para os checkboxes (GPU e Mapa Mental)
        # Aumentado ainda mais o pady inferior para criar mais espaço abaixo deste frame
        checkbox_frame = ttk.Frame(self.master)
        checkbox_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 30)) # pady alterado para 30
        
        # Checkbox "Usar GPU (se disponível)"
        tk.Label(checkbox_frame, text="Usar GPU (se disponível):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.gpu_var).pack(side=tk.LEFT, padx=(0, 20))

        # Novo Checkbox para "Gerar Mapa Mental"
        tk.Label(checkbox_frame, text="Gerar Mapa Mental:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.mindmap_var).pack(side=tk.LEFT)
        
        row_idx += 1

        tk.Label(self.master, text="Modelo Whisper:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        ttk.OptionMenu(self.master, self.model_var, self.model_var.get(), *models).grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        tk.Label(self.master, text="Arquivo de Áudio:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        audio_frame = ttk.Frame(self.master)
        audio_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        audio_frame.columnconfigure(0, weight=1)
        ttk.Entry(audio_frame, textvariable=self.audio_file_path, state="readonly", width=50).grid(row=0, column=0, sticky="ew")

        ttk.Button(audio_frame, text="Procurar", command=self.browse_audio_file, style="Small.TButton").grid(row=0, column=1, padx=5)
        row_idx += 1

        tk.Label(self.master, text="Salvar Transcrição Como:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        output_frame = ttk.Frame(self.master)
        output_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_file_path, width=50).grid(row=0, column=0, sticky="ew")

        ttk.Button(output_frame, text="Salvar", command=self.save_output_file, style="Small.TButton").grid(row=0, column=1, padx=5)

        self.audio_file_path.trace_add("write", self.suggest_output_filename)
        row_idx += 1

        # --- Frame para os botões Transcrever e Parar/Cancelar ---
        buttons_frame = ttk.Frame(self.master)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=20)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)

        self.transcribe_button = ttk.Button(buttons_frame, text="Transcrever", command=self.start_transcription_thread, style="Green.TButton")
        self.transcribe_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_button = ttk.Button(buttons_frame, text="Parar/Cancelar", command=self.cancel_transcription, style="Red.TButton")
        self.cancel_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.cancel_button.config(state=tk.DISABLED)
        row_idx += 1

        # Barra de Progresso
        tk.Label(self.master, text="Progresso:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=400, mode="determinate", variable=self.progress_value)
        self.progress_bar.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        # Mensagens de Progresso
        self.progress_label = ttk.Label(self.master, text="Pronto.", foreground="blue", wraplength=450)
        self.progress_label.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row_idx += 1

    def browse_audio_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecionar Arquivo de Áudio",
            filetypes=[("Arquivos de Áudio", "*.mp3 *.wav *.m4a *.flac"), ("Todos os Arquivos", "*.*")]
        )
        if file_path:
            self.audio_file_path.set(file_path)

    def save_output_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Salvar Transcrição",
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
            initialfile=self.output_file_path.get()
        )
        if file_path:
            self.output_file_path.set(file_path)

    def suggest_output_filename(self, *args):
        """Sugere um nome de arquivo de saída baseado no arquivo de áudio selecionado."""
        audio_path = self.audio_file_path.get()
        if audio_path:
            base_name = os.path.basename(audio_path)
            file_name_without_ext = os.path.splitext(base_name)[0]
            suggested_name = f"Transcricao-{file_name_without_ext}.txt"
            self.output_file_path.set(suggested_name)
        else:
            self.output_file_path.set("transcricao_final.txt")

    def update_progress_label(self, message):
        self.master.after(0, lambda: self.progress_label.config(text=message))

    def update_progress_bar_value(self, value):
        self.master.after(0, lambda: self.progress_value.set(value))

    def start_transcription_thread(self):
        self.stop_transcription_event.clear()

        audio_path = self.audio_file_path.get()
        model_size = self.model_var.get()
        use_gpu = self.gpu_var.get()
        generate_mindmap_option = self.mindmap_var.get() # Renomeada para evitar conflito
        output_path = self.output_file_path.get()

        if not audio_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, selecione um arquivo de áudio para transcrever.")
            return
        if not output_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, defina o nome e local do arquivo de saída.")
            return

        self.transcribe_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.update_progress_label("Iniciando transcrição...")
        self.update_progress_bar_value(0)

        transcription_thread = threading.Thread(
            target=transcribe_audio_logic,
            args=(audio_path, model_size, use_gpu, output_path, generate_mindmap_option,
                  self.update_progress_label, self.update_progress_bar_value, self.stop_transcription_event)
        )
        transcription_thread.start()

        self.master.after(100, lambda: self.check_transcription_thread(transcription_thread))

    def cancel_transcription(self):
        response = messagebox.askyesno("Confirmar Cancelamento", "Tem certeza que deseja cancelar a transcrição?")
        if response:
            self.stop_transcription_event.set()
            self.update_progress_label("Sinal de cancelamento enviado...")
            self.cancel_button.config(state=tk.DISABLED)

    def check_transcription_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_transcription_thread(thread))
        else:
            self.transcribe_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)


# --- Execução Principal ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()