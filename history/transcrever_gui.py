import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading # Para executar a transcrição em segundo plano

# --- Funções de Instalação e Importação (mantidas para robustez) ---
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Pacote '{package}' instalado com sucesso.")
    except subprocess.CalledProcessError:
        messagebox.showerror("Erro de Instalação", f"Erro ao instalar o pacote '{package}'. Por favor, tente instalar manualmente: pip install {package}")
        sys.exit(1) # Sai do script se a instalação falhar

# Tenta importar faster_whisper e torch
try:
    from faster_whisper import WhisperModel
    import torch
except ImportError:
    # Se estivermos em um ambiente gráfico, mostramos uma mensagem ao usuário
    if 'root' in locals(): # Verifica se a janela principal já foi criada
        messagebox.showinfo("Instalação Necessária", "Os pacotes 'faster-whisper' e 'torch' não foram encontrados. Eles serão instalados automaticamente. Isso pode levar alguns minutos.")
    
    print("faster-whisper e/ou torch não encontrados. Tentando instalar...")
    install_package("faster-whisper")
    install_package("torch")
    try:
        from faster_whisper import WhisperModel
        import torch
    except ImportError:
        messagebox.showerror("Erro Fatal", "faster-whisper e/ou torch não puderam ser instalados ou importados. Por favor, verifique sua conexão com a internet e permissões.")
        sys.exit(1)

# --- Lógica de Transcrição ---
def transcribe_audio_logic(audio_path, model_size, use_gpu, output_path, progress_callback=None):
    try:
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            device = "cpu"

        print(f"Usando o dispositivo: {device}")
        
        # 'float16' é geralmente uma boa escolha para GPUs modernas
        # 'int8' é mais eficiente em memória para CPUs, mas pode ser um pouco mais lento
        compute_type = "float16" if device == "cuda" else "int8"
        
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            return

        # Transcreve o áudio. faster-whisper retorna um gerador.
        # Adicionamos um callback de progresso para a interface gráfica
        segments, info = model.transcribe(audio_path, beam_size=5)

        full_transcription = ""
        # print(f"Idioma detectado: {info.language} com probabilidade {info.language_probability:.2f}")

        for segment in segments:
            text = segment.text.strip()
            full_transcription += text + " "
            if progress_callback:
                progress_callback(f"Progresso: {int((segment.end / info.duration) * 100)}% - {text[:50]}...")
                
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_transcription.strip())
        
        messagebox.showinfo("Sucesso", f"Transcrição concluída e salva em '{output_path}'")

    except Exception as e:
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
    finally:
        if progress_callback:
            progress_callback("Pronto.") # Limpa a mensagem de progresso

# --- Interface Gráfica Tkinter ---
class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("Transcritor de Áudio Faster Whisper")
        master.geometry("600x400") # Tamanho inicial da janela
        master.resizable(False, False) # Impede redimensionamento para layout mais simples

        # Variáveis de controle
        self.gpu_var = tk.BooleanVar(value=False) # Default: Não usar GPU
        self.model_var = tk.StringVar(value="small")
        self.audio_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()

        # Configurar grid para melhor layout
        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=3) # Coluna para entry fields e botões

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
        audio_frame.columnconfigure(0, weight=1) # Entry field pode expandir
        ttk.Entry(audio_frame, textvariable=self.audio_file_path, state="readonly", width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(audio_frame, text="Procurar...", command=self.browse_audio_file).grid(row=0, column=1, padx=5)
        row_idx += 1

        # 4. Local e Nome do Arquivo Transcrito
        tk.Label(self.master, text="Salvar Transcrição Como:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        output_frame = ttk.Frame(self.master)
        output_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1) # Entry field pode expandir
        ttk.Entry(output_frame, textvariable=self.output_file_path, width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_frame, text="Salvar Como...", command=self.save_output_file).grid(row=0, column=1, padx=5)
        
        # Define um nome de arquivo de saída padrão
        self.output_file_path.set("transcricao_final.txt")
        row_idx += 1

        # Botão Transcrever
        ttk.Button(self.master, text="Transcrever Áudio", command=self.start_transcription_thread).grid(row=row_idx, column=0, columnspan=2, pady=20)
        row_idx += 1

        # Barra de Progresso e Mensagens
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

    def update_progress(self, message):
        self.progress_label.config(text=message)
        self.master.update_idletasks() # Força a atualização da GUI

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
        self.master.children["!button3"].config(state=tk.DISABLED) # Obtém o botão "Transcrever Áudio"
        self.update_progress("Iniciando transcrição...")

        # Inicia a transcrição em uma thread separada para não travar a GUI
        transcription_thread = threading.Thread(
            target=transcribe_audio_logic,
            args=(audio_path, model_size, use_gpu, output_path, self.update_progress)
        )
        transcription_thread.start()

        # Habilita o botão novamente quando a thread terminar (ou em caso de erro)
        # Isso pode ser feito monitorando a thread ou com um callback ao final da transcrição
        self.master.after(100, lambda: self.check_transcription_thread(transcription_thread))

    def check_transcription_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_transcription_thread(thread))
        else:
            self.master.children["!button3"].config(state=tk.NORMAL) # Habilita o botão

# --- Execução Principal ---
if __name__ == "__main__":
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()