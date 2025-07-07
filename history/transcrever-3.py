import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

# --- Funções de Instalação e Importação ---
def install_package(package):
    try:
        print(f"Tentando instalar o pacote: {package}")
        # Use --break-system-packages para sistemas que bloqueiam instalações globais,
        # ou remova se estiver usando um ambiente virtual e preferir não usar.
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Pacote '{package}' instalado com sucesso.")
        return True
    except subprocess.CalledProcessError:
        print(f"Erro ao instalar o pacote '{package}'.")
        return False
    except Exception as e:
        print(f"Ocorreu uma exceção ao instalar '{package}': {e}")
        return False

# Tenta importar faster_whisper e torch globalmente
# Se não estiverem presentes, a GUI será inicializada e as mensagens de instalação
# serão mostradas via messagebox antes da tentativa de instalação.
try:
    from faster_whisper import WhisperModel
    import torch
    # Verifica se CUDA está disponível. Isso pode gerar um aviso, mas é informativo.
    if not torch.cuda.is_available():
        print("Aviso: CUDA não está disponível. A transcrição será executada na CPU, mesmo se a GPU for selecionada.")
except ImportError:
    # Se a importação falhar, tentamos instalar. Isso pode ocorrer antes da GUI iniciar,
    # então usamos print() e, em caso de erro, exit().
    print(" faster-whisper e/ou torch não encontrados. Iniciando instalação automática...")
    if not install_package("faster-whisper"):
        sys.exit(1)
    if not install_package("torch"): # torch é uma dependência de faster-whisper
        sys.exit(1)
    
    # Após a instalação, tenta importar novamente para confirmar
    try:
        from faster_whisper import WhisperModel
        import torch
    except ImportError:
        print("Erro Fatal: faster-whisper e/ou torch não puderam ser instalados ou importados após a tentativa automática.")
        sys.exit(1)


# --- Lógica de Transcrição ---
def transcribe_audio_logic(audio_path, model_size, use_gpu, output_path, progress_label_callback=None, progress_bar_callback=None):
    try:
        # Garante que torch foi importado corretamente
        if 'torch' not in sys.modules:
            raise ImportError("O módulo 'torch' não está carregado. Por favor, reinicie e verifique a instalação.")

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            device = "cpu"

        print(f"Usando o dispositivo: {device}")
        
        compute_type = "float16" if device == "cuda" else "int8"
        
        # Garante que o modelo é carregado no dispositivo correto
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            return

        # Transcreve o áudio
        segments_generator, info = model.transcribe(audio_path, beam_size=5)

        full_transcription = ""
        audio_duration = info.duration # Duração total do áudio em segundos

        # Atualiza a barra de progresso com base no tempo de cada segmento
        for segment in segments_generator:
            text = segment.text.strip()
            full_transcription += text + " "
            
            if progress_label_callback and progress_bar_callback:
                progress_percentage = (segment.end / audio_duration) * 100
                progress_bar_callback(progress_percentage)
                progress_label_callback(f"Progresso: {int(progress_percentage)}% - {text[:50]}...")
                
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_transcription.strip())
        
        messagebox.showinfo("Sucesso", f"Transcrição concluída e salva em '{output_path}'")

    except Exception as e:
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
    finally:
        if progress_label_callback:
            progress_label_callback("Pronto.")
        if progress_bar_callback:
            progress_bar_callback(0) # Zera a barra de progresso no final

# --- Interface Gráfica Tkinter ---
class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("Transcritor de Áudio 'CesarVox' [Faster Whisper]")
        master.geometry("600x450") # Aumenta um pouco para a barra de progresso
        master.resizable(False, False)

        # Variáveis de controle
        self.gpu_var = tk.BooleanVar(value=False)
        self.model_var = tk.StringVar(value="small")
        self.audio_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.progress_value = tk.DoubleVar(value=0) # Variável para a barra de progresso

        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=3)

        self.create_widgets()

    def create_widgets(self):
        row_idx = 0

        # 1. Usar GPU
        tk.Label(self.master, text="Usar GPU (se disponível):").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        ttk.Checkbutton(self.master, text="Sim", variable=self.gpu_var).grid(row=row_idx, column=1, sticky="w", padx=10, pady=5)
        row_idx += 1

        # 2. Modelos Whisper
        tk.Label(self.master, text="Modelo Whisper:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        ttk.OptionMenu(self.master, self.model_var, self.model_var.get(), *models).grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        # 3. Local do Arquivo de Áudio
        tk.Label(self.master, text="Arquivo de Áudio:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        audio_frame = ttk.Frame(self.master)
        audio_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        audio_frame.columnconfigure(0, weight=1)
        ttk.Entry(audio_frame, textvariable=self.audio_file_path, state="readonly", width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(audio_frame, text="Procurar...", command=self.browse_audio_file).grid(row=0, column=1, padx=5)
        row_idx += 1

        # 4. Local e Nome do Arquivo Transcrito
        tk.Label(self.master, text="Salvar Transcrição Como:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        output_frame = ttk.Frame(self.master)
        output_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_file_path, width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_frame, text="Salvar Como...", command=self.save_output_file).grid(row=0, column=1, padx=5)
        self.output_file_path.set("transcricao_final.txt")
        row_idx += 1

        # Botão Transcrever
        self.transcribe_button = ttk.Button(self.master, text="Transcrever Áudio", command=self.start_transcription_thread)
        self.transcribe_button.grid(row=row_idx, column=0, columnspan=2, pady=20)
        row_idx += 1

        # Barra de Progresso
        tk.Label(self.master, text="Progresso:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=400, mode="determinate", variable=self.progress_value)
        self.progress_bar.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        # Mensagens de Progresso
        self.progress_label = tk.Label(self.master, text="Pronto.", fg="blue")
        self.progress_label.grid(row=row_idx, column=0, columnspan=2, pady=5)
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
            title="Salvar Transcrição Como",
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )
        if file_path:
            self.output_file_path.set(file_path)

    def update_progress_label(self, message):
        # Usamos after para garantir que a atualização ocorra na thread principal da GUI
        self.master.after(0, lambda: self.progress_label.config(text=message))
        self.master.update_idletasks()

    def update_progress_bar_value(self, value):
        # Usamos after para garantir que a atualização ocorra na thread principal da GUI
        self.master.after(0, lambda: self.progress_value.set(value))
        self.master.update_idletasks()

    def start_transcription_thread(self):
        audio_path = self.audio_file_path.get()
        model_size = self.model_var.get()
        use_gpu = self.gpu_var.get()
        output_path = self.output_file_path.get()

        if not audio_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, selecione um arquivo de áudio para transcrever.")
            return
        if not output_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, defina o nome e local do arquivo de saída.")
            return

        # Desabilita o botão para evitar múltiplas execuções
        self.transcribe_button.config(state=tk.DISABLED)
        self.update_progress_label("Iniciando transcrição...")
        self.update_progress_bar_value(0) # Zera a barra ao iniciar

        # Inicia a transcrição em uma thread separada
        transcription_thread = threading.Thread(
            target=transcribe_audio_logic,
            args=(audio_path, model_size, use_gpu, output_path,
                  self.update_progress_label, self.update_progress_bar_value)
        )
        transcription_thread.start()

        # Monitora a thread e reabilita o botão ao final
        self.master.after(100, lambda: self.check_transcription_thread(transcription_thread))

    def check_transcription_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_transcription_thread(thread))
        else:
            self.transcribe_button.config(state=tk.NORMAL)
            # O `finally` em transcribe_audio_logic já zera a barra e o label
            # Podemos adicionar uma mensagem final aqui se for o caso
            # self.update_progress_label("Transcrição concluída.")


# --- Execução Principal ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()