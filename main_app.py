import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
import logging
import sys
import os
import time
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import audio_transcriber
import problem_analyzer
import solution_generator
import text_file_reader
from utils_instalador import instalar_multiplos_pacotes, DEPENDENCIAS_TEXTO

LOG_FILE = "voxLOG.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY or API_KEY.strip() == "":
    logger.critical("API Key do Gemini NÃO encontrada. Defina a variável de ambiente GEMINI_API_KEY ou crie um arquivo .env com a linha: GEMINI_API_KEY=SUACHAVEAQUI")
    messagebox.showerror(
        "Chave de API não encontrada",
        "A chave de API do Gemini não foi encontrada!\n\n"
        "Por favor, crie um arquivo .env na mesma pasta do programa com o conteúdo:\n\n"
        "GEMINI_API_KEY=SUACHAVEAQUI\n\n"
        "Ou defina a variável de ambiente GEMINI_API_KEY no seu sistema.\n"
        "O programa será encerrado."
    )
    sys.exit(1)
else:
    logger.info("API Key do Gemini carregada com sucesso de variável de ambiente ou .env.")

instalar_multiplos_pacotes(DEPENDENCIAS_TEXTO)

AUDIO_EXTS = ['.mp3', '.wav', '.m4a', '.flac']
TEXT_EXTS = ['.txt', '.md', '.doc', '.docx', '.rtf', '.eml', '.pdf', '.html']

class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("LOGVox - Transcritor e Analisador Inteligente de Áudio/Textos")
        master.geometry("620x600")
        master.resizable(False, False)

        self.gpu_var = tk.BooleanVar(value=False)
        self.analysis_var = tk.BooleanVar(value=False)
        self.solution_var = tk.BooleanVar(value=False)
        self.model_var = tk.StringVar(value="small")
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.progress_value = tk.DoubleVar(value=0)
        self.cloud_platform_var = tk.StringVar(value="Azure")
        self.file_type_label_var = tk.StringVar(value="Nenhum arquivo selecionado.")
        self.main_button_text = tk.StringVar(value="Transcrever/Processar")
        self.text_preview = None
        self.text_file_selected = False

        self.beam_size_var = tk.IntVar(value=5)
        self.compute_type_var = tk.StringVar(value="float32")

        self.stop_transcription_event = threading.Event()

        self.start_time = None
        self.elapsed_seconds = 0
        self.timer_running = False

        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=3)

        self.create_widgets()

    def toggle_cloud_platform_dropdown(self):
        if self.solution_var.get():
            for child in self.cloud_platform_frame.winfo_children():
                child.config(state=tk.NORMAL)
        else:
            for child in self.cloud_platform_frame.winfo_children():
                child.config(state=tk.DISABLED)

    def show_text_preview(self, event=None):
        if not self.text_file_selected or not self.text_preview:
            messagebox.showinfo("Preview", "Nenhum conteúdo disponível para visualização.")
            return
        preview_win = tk.Toplevel(self.master)
        preview_win.title("Prévia do Arquivo de Texto")
        preview_win.geometry("600x600")
        text_area = scrolledtext.ScrolledText(preview_win, wrap=tk.WORD, font=("Consolas", 10))
        text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        text_area.insert(tk.END, self.text_preview)
        text_area.config(state=tk.DISABLED)
        ttk.Button(preview_win, text="Fechar", command=preview_win.destroy).pack(pady=8)

    def create_widgets(self):
        style = ttk.Style()
        style.configure("Small.TButton", font=('Helvetica', 10), padding=8)
        style.map("Small.TButton",
                  foreground=[('pressed', 'red'), ('active', 'blue')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        style.configure("Green.TButton", font=('Helvetica', 10, 'bold'), padding=8, foreground="green")
        style.map("Green.TButton",
                  foreground=[('pressed', 'darkgreen'), ('active', 'lime green')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        style.configure("Red.TButton", font=('Helvetica', 10, 'bold'), padding=8, foreground="red")
        style.map("Red.TButton",
                  foreground=[('pressed', 'darkred'), ('active', 'salmon')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        row_idx = 0

        checkbox_frame = ttk.Frame(self.master)
        checkbox_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 10))
        tk.Label(checkbox_frame, text="Usar GPU (se disponível):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.gpu_var).pack(side=tk.LEFT, padx=(0, 20)) 
        tk.Label(checkbox_frame, text="Gerar Análise:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.analysis_var).pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(checkbox_frame, text="Gerar Solução:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.solution_var,
                        command=self.toggle_cloud_platform_dropdown).pack(side=tk.LEFT)
        row_idx += 1

        type_frame = ttk.Frame(self.master)
        type_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=10, pady=2)
        type_frame.columnconfigure(0, weight=1)
        tk.Label(type_frame, text="Tipo de Entrada: ").pack(side=tk.LEFT)
        self.type_label = tk.Label(type_frame, textvariable=self.file_type_label_var, fg="blue", font=('Helvetica', 10, 'bold'))
        self.type_label.pack(side=tk.LEFT)
        self.visualizar_link = tk.Label(type_frame, text="Visualizar Conteúdo", fg="blue", cursor="hand2", font=('Helvetica', 10, 'underline'))
        self.visualizar_link.pack(side=tk.RIGHT)
        self.visualizar_link.bind("<Button-1>", self.show_text_preview)
        self.visualizar_link.pack_forget()
        row_idx += 1

        tk.Label(self.master, text="").grid(row=row_idx, column=0, columnspan=2)
        row_idx += 1

        model_frame = ttk.Frame(self.master)
        model_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(2,2))
        tk.Label(model_frame, text="Modelo Whisper:").pack(side=tk.LEFT)
        models = ["tiny", "base", "small", "medium", "large"]
        ttk.OptionMenu(model_frame, self.model_var, self.model_var.get(), *models).pack(side=tk.LEFT, padx=(8,0))
        row_idx += 1

        params_frame = ttk.Frame(self.master)
        params_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(2,10))
        tk.Label(params_frame, text="Beam Size:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Spinbox(params_frame, from_=1, to=10, textvariable=self.beam_size_var, width=5).pack(side=tk.LEFT, padx=(0,12))
        tk.Label(params_frame, text="Compute Type:").pack(side=tk.LEFT, padx=(0,5))
        ttk.OptionMenu(params_frame, self.compute_type_var, self.compute_type_var.get(), "float16", "int8", "float32").pack(side=tk.LEFT)
        row_idx += 1

        tk.Label(self.master, text="").grid(row=row_idx, column=0, columnspan=2)
        row_idx += 1

        fields_frame = ttk.Frame(self.master)
        fields_frame.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        fields_frame.columnconfigure(1, weight=1)

        tk.Label(fields_frame, text="Arquivo de Entrada:").grid(row=0, column=0, sticky="w")
        entry1 = ttk.Entry(fields_frame, textvariable=self.input_file_path, state="readonly", width=45)
        entry1.grid(row=0, column=1, sticky="ew")
        btn_procurar = ttk.Button(fields_frame, text="Procurar", command=self.browse_input_file, style="Small.TButton")
        btn_procurar.grid(row=0, column=2, padx=(5, 0))

        tk.Label(fields_frame, text="Salvar Saída Como:").grid(row=1, column=0, sticky="w", pady=(7,0))
        entry2 = ttk.Entry(fields_frame, textvariable=self.output_file_path, width=45)
        entry2.grid(row=1, column=1, sticky="ew", pady=(7,0))
        btn_salvar = ttk.Button(fields_frame, text="Salvar", command=self.save_output_file, style="Small.TButton")
        btn_salvar.grid(row=1, column=2, padx=(5, 0), pady=(7,0))

        row_idx += 1

        self.cloud_platform_frame = ttk.Frame(self.master)
        self.cloud_platform_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self.cloud_platform_frame.columnconfigure(1, weight=1) 
        
        tk.Label(self.cloud_platform_frame, text="Plataforma Cloud para Solução:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        cloud_options = ["Azure", "AWS", "GCP"]
        self.cloud_platform_dropdown = ttk.OptionMenu(self.cloud_platform_frame, self.cloud_platform_var,
                                                     self.cloud_platform_var.get(), *cloud_options)
        self.cloud_platform_dropdown.grid(row=0, column=1, sticky="ew")
        self.toggle_cloud_platform_dropdown()
        row_idx += 1

        tk.Label(self.master, text="").grid(row=row_idx, column=0, columnspan=2, pady=1)
        row_idx += 1
        tk.Label(self.master, text="").grid(row=row_idx, column=0, columnspan=2, pady=1)
        row_idx += 1

        buttons_frame = ttk.Frame(self.master)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=18)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)

        self.transcribe_button = ttk.Button(buttons_frame, textvariable=self.main_button_text, command=self.start_processing_thread, style="Green.TButton")
        self.transcribe_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_button = ttk.Button(buttons_frame, text="Cancelar", command=self.cancel_processing, style="Red.TButton")
        self.cancel_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.cancel_button.config(state=tk.DISABLED)

        self.close_button = ttk.Button(buttons_frame, text="Fechar", command=self.master.quit, style="Red.TButton")
        self.close_button.grid(row=0, column=2, padx=5, sticky="ew")
        row_idx += 1

        self.timer_label = ttk.Label(self.master, text="Tempo decorrido: 00:00:00", font=("Helvetica", 10, "bold"), foreground="blue")
        self.timer_label.grid(row=row_idx, column=0, sticky="w", padx=10, pady=(8, 0))
        row_idx += 1

        tk.Label(self.master, text="Progresso:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=400, mode="determinate", variable=self.progress_value)
        self.progress_bar.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        self.progress_label = ttk.Label(self.master, text="Pronto.", foreground="blue", wraplength=500)
        self.progress_label.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=7)
        row_idx += 1

    def start_timer(self):
        self.start_time = time.time()
        self.timer_running = True
        self.update_timer()

    def update_timer(self):
        if self.timer_running:
            self.elapsed_seconds = int(time.time() - self.start_time)
            h, m, s = self.elapsed_seconds // 3600, (self.elapsed_seconds % 3600) // 60, self.elapsed_seconds % 60
            self.timer_label.config(text=f"Tempo decorrido: {h:02}:{m:02}:{s:02}")
            self.master.after(1000, self.update_timer)

    def stop_timer(self):
        self.timer_running = False

    def reset_timer(self):
        self.start_time = None
        self.elapsed_seconds = 0
        self.timer_label.config(text="Tempo decorrido: 00:00:00")
        self.timer_running = False

    def browse_input_file(self):
        AUDIO_TYPES = [("Áudio", "*.mp3 *.wav *.m4a *.flac")]
        TEXT_TYPES = [("Texto", "*.txt *.md *.doc *.docx *.rtf *.eml *.pdf *.html")]
        ALL_TYPES = AUDIO_TYPES + TEXT_TYPES + [("Todos os Arquivos", "*.*")]
        file_path = filedialog.askopenfilename(
            title="Selecionar Arquivo de Áudio ou Texto",
            filetypes=ALL_TYPES
        )
        if file_path:
            self.input_file_path.set(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            if ext in AUDIO_EXTS:
                self.file_type_label_var.set("Áudio")
                self.text_file_selected = False
                self.visualizar_link.pack_forget()
                self.main_button_text.set("Transcrever")
                self.update_progress_label("Arquivo de áudio detectado e pronto para transcrição.")
            elif ext in TEXT_EXTS:
                self.file_type_label_var.set("Texto")
                self.text_file_selected = True
                self.visualizar_link.pack(side=tk.RIGHT)
                self.main_button_text.set("Processar")
                try:
                    content = text_file_reader.read_text_file(file_path)
                    self.text_preview = content[:3000]
                    self.update_progress_label("Arquivo de texto detectado e pronto para análise/processamento.")
                except Exception as e:
                    self.text_preview = None
                    self.update_progress_label(f"Erro ao ler arquivo de texto para preview: {e}")
                    messagebox.showwarning("Preview", f"Erro ao gerar prévia: {e}")
            else:
                self.file_type_label_var.set("Tipo desconhecido")
                self.visualizar_link.pack_forget()
                self.text_file_selected = False
                self.main_button_text.set("Transcrever/Processar")
                self.update_progress_label("Arquivo selecionado com tipo não suportado.")

    def suggest_output_filename(self, *args):
        input_path = self.input_file_path.get()
        if input_path:
            base_name = os.path.basename(input_path)
            file_name_without_ext = os.path.splitext(base_name)[0]
            data_str = datetime.now().strftime("%Y%m%d%H%M%S")
            ext = os.path.splitext(base_name)[1].lower()
            if ext in AUDIO_EXTS:
                prefix = "Transcrição Áudio"
            elif ext in TEXT_EXTS:
                prefix = "Transcrição Texto"
            else:
                prefix = "Transcrição"
            suggested_name = f"{prefix} {file_name_without_ext} {data_str}.txt"
            self.output_file_path.set(suggested_name)
        else:
            self.output_file_path.set("Transcrição.txt")

    def save_output_file(self):
        self.suggest_output_filename()
        file_path = filedialog.asksaveasfilename(
            title="Salvar Saída",
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
            initialfile=self.output_file_path.get()
        )
        if file_path:
            self.output_file_path.set(file_path)

    def update_progress_label(self, message):
        self.master.after(0, lambda: self.progress_label.config(text=message))

    def update_progress_bar_value(self, value):
        self.master.after(0, lambda: self.progress_value.set(value))

    def clear_input_fields(self):
        self.input_file_path.set("")
        self.output_file_path.set("")
        self.file_type_label_var.set("Nenhum arquivo selecionado.")
        self.visualizar_link.pack_forget()
        self.text_preview = None
        self.text_file_selected = False
        self.main_button_text.set("Transcrever/Processar")

    def start_processing_thread(self):
        self.stop_transcription_event.clear()
        self.reset_timer()

        input_path = self.input_file_path.get()
        ext = os.path.splitext(input_path)[1].lower()
        is_audio = ext in AUDIO_EXTS
        is_text = ext in TEXT_EXTS

        model_size = self.model_var.get()
        use_gpu = self.gpu_var.get()
        generate_analysis_option = self.analysis_var.get()
        generate_solution_option = self.solution_var.get()
        selected_cloud_platform = self.cloud_platform_var.get()
        output_path = self.output_file_path.get()

        beam_size = self.beam_size_var.get()
        compute_type = self.compute_type_var.get()

        if not input_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, selecione um arquivo de entrada (áudio ou texto).")
            logger.warning("Tentativa de processamento sem arquivo selecionado.")
            return
        if not output_path:
            messagebox.showwarning("Saída Ausente", "Por favor, defina o nome e local do arquivo de saída.")
            logger.warning("Tentativa de processamento sem local de saída definido.")
            return

        if generate_solution_option and not selected_cloud_platform:
            messagebox.showwarning("Seleção Ausente", "Por favor, selecione uma Plataforma Cloud para gerar a solução.")
            logger.warning("Gerar Solução marcado, mas plataforma Cloud não selecionada.")
            return

        self.transcribe_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.start_timer()

        if is_audio:
            self.update_progress_label("Iniciando transcrição de áudio...")
        elif is_text:
            self.update_progress_label("Iniciando leitura de texto...")
        else:
            self.update_progress_label("Tipo de arquivo não suportado. Processo abortado.")
            messagebox.showerror("Tipo Inválido", "O tipo de arquivo selecionado não é suportado.")
            self.transcribe_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            self.stop_timer()
            return

        processing_thread = threading.Thread(
            target=self._run_all_modules,
            args=(input_path, ext, is_audio, is_text, model_size, use_gpu, output_path, generate_analysis_option,
                  generate_solution_option, selected_cloud_platform,
                  self.update_progress_label, self.update_progress_bar_value, self.stop_transcription_event,
                  self.clear_input_fields, beam_size, compute_type)
        )
        processing_thread.start()

        self.master.after(100, lambda: self.check_processing_thread(processing_thread))

    def cancel_processing(self):
        response = messagebox.askyesno("Confirmar Cancelamento", "Tem certeza que deseja cancelar o processamento?")
        if response:
            self.stop_transcription_event.set()
            self.update_progress_label("Sinal de cancelamento enviado...")
            logger.info("Solicitação de cancelamento de processamento enviada.")
            self.stop_timer()

    def check_processing_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_processing_thread(thread))
        else:
            self.transcribe_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            self.stop_timer()
            logger.info("Thread de processamento finalizada e botões reativados.")

    def _run_all_modules(self, input_path, ext, is_audio, is_text, model_size, use_gpu, output_path, generate_analysis_option,
                         generate_solution_option, selected_cloud_platform,
                         progress_label_callback, progress_bar_callback, stop_event, clear_fields_callback, beam_size, compute_type):
        transcribed_text = None
        base_name = os.path.basename(output_path)
        file_name_without_ext = os.path.splitext(base_name)[0]
        output_dir = os.path.dirname(output_path)

        try:
            if is_audio:
                progress_label_callback("Módulo 1/4: Iniciando Transcrição de Áudio...")
                transcribed_text = audio_transcriber.transcribe_audio(
                    input_path,
                    model_size,
                    use_gpu,
                    output_path,
                    progress_label_callback,
                    progress_bar_callback,
                    stop_event,
                    timeout_seconds=1200,
                    beam_size=beam_size,
                    compute_type=compute_type
                )
                if transcribed_text is None:
                    logger.info("Transcrição não concluída. Abortando processos subsequentes.")
                    self.stop_timer()
                    return
            elif is_text:
                progress_label_callback("Módulo 1/4: Lendo arquivo de texto...")
                try:
                    transcribed_text = text_file_reader.read_text_file(input_path)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(transcribed_text)
                    logger.info(f"Arquivo de texto salvo em {output_path}")
                    progress_label_callback("Arquivo de texto lido e salvo com sucesso.")
                except Exception as e:
                    logger.error(f"Erro ao ler arquivo de texto: {e}", exc_info=True)
                    messagebox.showerror("Erro ao Ler Arquivo de Texto", f"Não foi possível ler o arquivo de texto: {e}")
                    self.stop_timer()
                    return
            else:
                logger.warning("Tipo de arquivo não suportado na etapa de processamento.")
                self.stop_timer()
                return

            # ANÁLISE CONCENTRADA
            if generate_analysis_option:
                if not transcribed_text or not isinstance(transcribed_text, str) or not transcribed_text.strip():
                    logger.warning("Transcrição ausente ou vazia. Análise não será executada.")
                    progress_label_callback("Transcrição ausente ou vazia. Análise não será executada.")
                else:
                    logger.info(f"Texto transcrito recebido para análise (primeiros 500 chars): {repr(transcribed_text[:500])}")
                    progress_label_callback("Módulo 2/4: Gerando Análise Concentrada (GEM)...")
                    analysis_output = problem_analyzer.analyze_full_text(transcribed_text)
                    if analysis_output:
                        analysis_output_path = os.path.join(output_dir, f"GEM - Análise {file_name_without_ext}.txt")
                        with open(analysis_output_path, "w", encoding="utf-8") as f:
                            f.write(analysis_output)
                        messagebox.showinfo("Análise Concluída", f"Análise da GEM gerada e salva em '{analysis_output_path}'")
                        logger.info("Análise da GEM salva com sucesso.")
                    else:
                        logger.warning("Análise da GEM não foi gerada ou retornou vazia.")
            else:
                logger.info("Opção 'Gerar Análise' não selecionada. Pulando Módulo de Análise.")

            # MÓDULO SOLUÇÃO TÉCNICA
            if generate_solution_option:
                progress_label_callback("Módulo 3/4: Gerando Proposta de Solução (GEM)...")
                solution_text, plantuml_diagrams, terraform_files = solution_generator.generate_solution(
                    transcribed_text, selected_cloud_platform, API_KEY, output_dir, file_name_without_ext
                )
                if solution_text:
                    messagebox.showinfo("Proposta de Solução Gerada",
                                       f"A proposta de solução principal (texto) para {selected_cloud_platform} foi gerada e salva com sucesso. "
                                       "Verifique também os arquivos PlantUML e Terraform.")
                    logger.info(f"Proposta de Solução principal (texto) gerada e salva para {selected_cloud_platform}.")
                else:
                    logger.warning(f"Solução técnica da GEM para {selected_cloud_platform} não foi gerada ou retornou vazia.")
            else:
                logger.info("Opção 'Gerar Solução' não selecionada. Pulando Módulo de Solução.")

        except Exception as e:
            logger.error(f"Ocorreu um erro crítico no processo modular: {e}", exc_info=True)
            messagebox.showerror("Erro Crítico", f"Ocorreu um erro crítico durante o processamento: {e}")
        finally:
            logger.info("Processamento modular finalizado.")
            progress_label_callback("Processamento concluído.")
            progress_bar_callback(0)
            self.stop_timer()
            if clear_fields_callback:
                clear_fields_callback()
            self.master.after(0, lambda: self.transcribe_button.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.cancel_button.config(state=tk.DISABLED))

if __name__ == "__main__":
    logger.info("Aplicação 'LOGVox' iniciada.")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    solution_modules_path = os.path.join(current_dir, 'solution_modules')
    if solution_modules_path not in sys.path:
        sys.path.append(solution_modules_path)

    output_writers_path = os.path.join(current_dir, 'output_writers')
    if output_writers_path not in sys.path:
        sys.path.append(output_writers_path)

    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()
    logger.info("Aplicação 'LOGVox' encerrada.")
