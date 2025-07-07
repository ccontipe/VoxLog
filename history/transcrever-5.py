import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
import logging # Importar o módulo logging

# --- Configuração do Logging ---
LOG_FILE = "voxLOG.txt"
# Configura o logger raiz
logging.basicConfig(
    level=logging.INFO,  # Nível mínimo para registrar (INFO, WARNING, ERROR, CRITICAL, DEBUG)
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'), # Saída para arquivo
        logging.StreamHandler(sys.stdout) # Saída para console também
    ]
)
logger = logging.getLogger(__name__)

# --- Funções de Instalação e Importação ---
def install_package(package):
    try:
        logger.info(f"Tentando instalar o pacote: {package}") # Log da tentativa de instalação
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])
        logger.info(f"Pacote '{package}' instalado com sucesso.") # Log de sucesso
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao instalar o pacote '{package}': {e}", exc_info=True) # Log de erro com stack trace
        print("Certifique-se de ter permissão de escrita ou execute como administrador, se necessário.")
        messagebox.showerror("Erro de Instalação", f"Falha ao instalar o pacote '{package}'. Por favor, tente instalar manualmente ou execute o script com permissões adequadas.")
        return False
    except Exception as e:
        logger.critical(f"Ocorreu uma exceção crítica ao instalar '{package}': {e}", exc_info=True) # Log de erro crítico
        messagebox.showerror("Erro de Instalação", f"Ocorreu um erro inesperado ao instalar '{package}': {e}")
        return False

# Tenta importar faster_whisper, torch e google.generativeai globalmente.
try:
    from faster_whisper import WhisperModel
    import torch
    import google.generativeai as genai
    if not torch.cuda.is_available():
        logger.warning("Aviso: CUDA não está disponível. A transcrição será executada na CPU, mesmo se a GPU for selecionada.") # Log de aviso
except ImportError:
    logger.warning("Módulos necessários não encontrados. Iniciando instalação automática...") # Log de aviso
    if not install_package("faster-whisper"):
        logger.error("Falha na instalação de faster-whisper. Encerrando.")
        sys.exit(1)
    if not install_package("torch"):
        logger.error("Falha na instalação de torch. Encerrando.")
        sys.exit(1)
    if not install_package("google-generativeai"):
        logger.error("Falha na instalação de google-generativeai. Encerrando.")
        sys.exit(1)

    try:
        from faster_whisper import WhisperModel
        import torch
        import google.generativeai as genai
    except ImportError:
        logger.critical("Erro Fatal: Um ou mais módulos necessários não puderam ser instalados ou importados após a tentativa automática. Encerrando.") # Log de erro crítico
        messagebox.showerror("Erro Fatal", "Módulos de transcrição e/ou análise não puderam ser instalados ou importados. Por favor, verifique sua conexão com a internet e permissões, e tente instalar manualmente: pip install faster-whisper torch google-generativeai")
        sys.exit(1)

# --- Configuração da API Google Gemini ---
### MODIFICADO: API_KEY agora é lida de uma variável de ambiente ###
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("Variável de ambiente 'GEMINI_API_KEY' não encontrada. A análise da GEM não funcionará sem ela.")
    # Não messagebox.showwarning aqui para não bloquear o início se o usuário só quer transcrever
else:
    genai.configure(api_key=API_KEY)
    logger.info("API Key do Gemini configurada a partir da variável de ambiente.")
### FIM MODIFICADO ###

def call_gemini_analysis(transcription_text):
    """
    Chama o modelo Gemini com as instruções da GEM "Analisador de Transcrições de Reuniões/Palestras"
    e o texto da transcrição, seguindo o novo formato de análise de negócios.
    Retorna a resposta da GEM.
    """
    # MODIFICADO: Adicionada verificação local da API_KEY antes de chamar genai
    if not API_KEY:
        messagebox.showwarning("API Key Ausente", "A variável de ambiente 'GEMINI_API_KEY' não foi configurada. A funcionalidade de análise da GEM não estará disponível.")
        logger.error("Tentativa de chamar a GEM sem a API_KEY configurada.")
        return None

    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # Usando gemini-1.5-pro como exemplo, ajuste conforme sua cota
        logger.info(f"Chamando o modelo Gemini: {model.model_name} para análise.") # Log da chamada do modelo
        
        # --- PROMPT ATUALIZADO COM AS NOVAS INSTRUÇÕES DE ANÁLISE DE NEGÓCIOS ---
        prompt = (
            "Você é um analista de negócios e sintetizador de informações altamente proficient. "
            "Seu objetivo é analisar profundamente transcrições de áudio (reuniões, palestras, discussões) "
            "e extrair as informações mais relevantes, considerando os seguintes elementos essenciais:\n\n"
            "1.  **Problema/Situação Central:**\n"
            "    * Apresente o objetivo da solução em discussão, de forma clara e direta.\n"
            "    * Qual é o problema ou a situação principal que está sendo abordada? Descreva-o de forma clara e concisa.\n"
            "    * Quais são os pontos-chave discutidos que levam a essa situação?\n\n"
            "2.  **Entendimento Detalhado:**\n"
            "    * Apresente um resumo abrangente do contexto e do estado atual da discussão.\n"
            "    * Quais são os principais tópicos, conceitos ou informações apresentadas?\n\n"
            "3.  **Premissas (Claras e Ocultas):**\n"
            "    * **Premissas Explícitas:** Quais são as suposições declaradas ou fatos considerados verdadeiros que foram mencionados?\n"
            "    * **Premissas Implícitas/Ocultas:** Com base na linguagem, no tom, nos silêncios ou na forma como certos tópicos são tratados, quais são as suposições não declaradas que parecem estar em jogo? (Ex: 'assume-se que a equipe tem os recursos X', 'parece haver uma crença de que Y é impossível').\n\n"
            "4.  **Restrições (Técnicas, Orçamentárias, Temporais, etc.):**\n"
            "    * Quais são as limitações ou obstáculos claramente identificados (orçamento, prazo, recursos, tecnologia, políticas internas)?\n"
            "    * Há restrições sugeridas ou subentendidas que podem não ter sido explicitamente ditas, mas que são evidentes na discussão?\n\n"
            "5.  **Partes Interessadas (Stakeholders) e suas Perspectivas:**\n"
            "    * Quem são os principais participantes mencionados ou implicitamente relevantes na discussão?\n"
            "    * Quais são as diferentes perspectivas, preocupações ou interesses de cada parte interessada, conforme inferido da transcrição?\n\n"
            "6.  **Próximos Passos/Ações Sugeridas (se houver):**\n"
            "    * Quais são as ações, decisões ou recomendações que surgiram da discussão?\n\n"
            "7.  **Pontos de Dúvida/Esclarecimento Necessário:**\n"
            "    * Quais são as áreas da transcrição que permanecem ambíguas, contraditórias ou que requerem mais informações/esclarecimentos?\n\n"
            "**Formato da Saída:**\n"
            "A saída deve ser um texto estruturado, idealmente em formato Markdown para facilitar a leitura e a importação para outras ferramentas. Use cabeçalhos e listas para organizar as informações de forma lógica. Evite o uso de Functions e Logic Apps, focando na análise textual pura.\n\n"
            "**Instruções Adicionais:**\n"
            "* Seja o mais objetivo e imparcial possível na extração de informações.\n"
            "* Concentre-se em sintetizar, não apenas em repetir.\n"
            "* Se alguma seção não for aplicável ou não houver informações suficientes, indique-o claramente (ex: 'Nenhuma premissa oculta clara identificada').\n\n"
            "Aqui está a transcrição completa do texto para análise:\n\n"
            f"Transcrição:\n{transcription_text}"
        )
        logger.debug(f"Prompt enviado para Gemini (primeiros 200 chars): {prompt[:200]}...") # Log do prompt (debug)
        
        response = model.generate_content(prompt)
        logger.info("Análise da GEM recebida com sucesso.") # Log de sucesso da análise
        return response.text
    except Exception as e:
        logger.error(f"Erro ao chamar a API da GEM: {e}", exc_info=True) # Log do erro da API com stack trace
        messagebox.showerror("Erro na Análise GEM", f"Não foi possível obter a análise da GEM: {e}")
        return None

# --- Lógica de Transcrição ---
def transcribe_audio_logic(audio_path, model_size, use_gpu, output_path, generate_analysis_option, progress_label_callback=None, progress_bar_callback=None, stop_event=None, clear_fields_callback=None):
    transcription_interrupted = False
    logger.info(f"Iniciando lógica de transcrição para: {audio_path}") # Log do início da transcrição
    try:
        if 'torch' not in sys.modules:
            raise ImportError("O módulo 'torch' não está carregado. Por favor, reinicie e verifique a instalação.")

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Dispositivo de transcrição selecionado: {device}") # Log do dispositivo

        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            logger.warning("GPU selecionada, mas CUDA não disponível. Revertendo para CPU.") # Log de aviso
            device = "cpu"

        logger.info(f"Usando o dispositivo: {device}")

        compute_type = "float16" if device == "cuda" else "int8"
        logger.info(f"Tipo de computação: {compute_type}") # Log do tipo de computação

        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"Modelo Whisper carregado: {model_size}") # Log do carregamento do modelo

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            logger.error(f"Arquivo de áudio não encontrado: {audio_path}") # Log de erro
            return

        segments_generator, info = model.transcribe(audio_path, beam_size=5)
        logger.info(f"Iniciando transcrição de áudio com duração: {info.duration:.2f} segundos.") # Log do início

        full_transcription = ""
        audio_duration = info.duration

        for segment in segments_generator:
            if stop_event and stop_event.is_set():
                transcription_interrupted = True
                messagebox.showinfo("Transcrição Cancelada", "A transcrição foi cancelada pelo usuário.")
                logger.info("Transcrição cancelada pelo usuário.") # Log de cancelamento
                break

            text = segment.text.strip()
            full_transcription += text + " "

            if progress_label_callback and progress_bar_callback:
                progress_percentage = (segment.end / audio_duration) * 100
                # logger.debug(f"Progresso: {int(progress_percentage)}% - Segmento: {text[:50]}...") # Log detalhado de progresso (descomente para mais detalhes)
                progress_bar_callback(progress_percentage)
                progress_label_callback(f"Progresso: {int(progress_percentage)}%\n[{text}]")

        if not transcription_interrupted:
            transcribed_text = full_transcription.strip()
            logger.info(f"Transcrição completa. Salvando em: {output_path}") # Log de salvamento
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(transcribed_text)

            messagebox.showinfo("Sucesso", f"Transcrição concluída e salva em '{output_path}'")
            logger.info("Transcrição salva com sucesso.") # Log de sucesso

            # Lógica para gerar análise com a GEM
            if generate_analysis_option:
                logger.info("Opção 'Gerar Análise' selecionada.") # Log da opção
                # MODIFICADO: Verifica se a API_KEY foi carregada do ambiente antes de tentar usar genai
                if not API_KEY:
                    messagebox.showwarning("API Key Ausente", "A API Key do Google Gemini não está configurada. A análise não pode ser gerada.")
                    progress_label_callback("Erro: 'google.generativeai' não configurado (API Key ausente).")
                    logger.error("A API Key do Google Gemini não está configurada para análise da GEM.")
                    return

                if 'google.generativeai' not in sys.modules:
                    messagebox.showerror("Erro de Dependência", "A biblioteca 'google-generativeai' não está disponível. Por favor, reinicie o script para tentar a instalação automática ou instale manualmente.")
                    progress_label_callback("Erro: 'google.generativeai' não encontrado.")
                    logger.error("A biblioteca 'google-generativeai' não está carregada para análise da GEM.") # Log de erro
                    return

                progress_label_callback("Chamando Analisador de Transcrições (GEM)...")
                logger.info("Chamando Analisador de Transcrições (GEM)...") # Log
                gem_analysis_output = call_gemini_analysis(transcribed_text)
                
                if gem_analysis_output:
                    base_name = os.path.basename(output_path)
                    file_name_without_ext = os.path.splitext(base_name)[0]
                    analysis_output_path = os.path.join(os.path.dirname(output_path), f"GEM - Análise {file_name_without_ext}.txt")
                    
                    logger.info(f"Análise da GEM gerada. Salvando em: {analysis_output_path}") # Log de salvamento
                    with open(analysis_output_path, "w", encoding="utf-8") as f:
                        f.write(gem_analysis_output)
                    messagebox.showinfo("Análise Concluída", f"Análise da GEM gerada e salva em '{analysis_output_path}'")
                    logger.info("Análise da GEM salva com sucesso.") # Log de sucesso
                else:
                    messagebox.showwarning("Análise GEM", "A análise da GEM não foi gerada devido a um erro.")
                    logger.warning("Análise da GEM não foi gerada ou retornou vazia.") # Log de aviso

        else:
            if progress_label_callback:
                progress_label_callback("Cancelado.")

    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante a transcrição: {e}", exc_info=True) # Log de erro com stack trace
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
    finally:
        logger.info("Processo de transcrição finalizado.") # Log de finalização
        if progress_label_callback:
            progress_label_callback("Pronto.")
        if progress_bar_callback:
            progress_bar_callback(0)
        
        if clear_fields_callback:
            clear_fields_callback()

# --- Interface Gráfica Tkinter ---
class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("Transcritor de Áudio 'CesarVox' [Faster Whisper]")
        master.geometry("600x550")
        master.resizable(False, False)

        self.gpu_var = tk.BooleanVar(value=False)
        self.analysis_var = tk.BooleanVar(value=False) 
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
        # --- FIM DA DEFINIÇÃO DE ESTILOS ---

        row_idx = 0

        checkbox_frame = ttk.Frame(self.master)
        checkbox_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 30))
        
        tk.Label(checkbox_frame, text="Usar GPU (se disponível):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.gpu_var).pack(side=tk.LEFT, padx=(0, 20)) 

        tk.Label(checkbox_frame, text="Gerar Análise:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.analysis_var).pack(side=tk.LEFT)
        
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

        tk.Label(self.master, text="Progresso:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=400, mode="determinate", variable=self.progress_value)
        self.progress_bar.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        self.progress_label = ttk.Label(self.master, text="Pronto.", foreground="blue", wraplength=450)
        self.progress_label.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row_idx += 1

        # --- Botão "Fechar" ---
        self.close_button = ttk.Button(self.master, text="Fechar", command=self.master.quit, style="Red.TButton")
        self.close_button.grid(row=row_idx, column=1, sticky="se", padx=10, pady=10) 
        row_idx +=1 


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

    # --- NOVO: Função para limpar os campos ---
    def clear_input_fields(self):
        self.audio_file_path.set("")
        self.output_file_path.set("")

    def start_transcription_thread(self):
        self.stop_transcription_event.clear()

        audio_path = self.audio_file_path.get()
        model_size = self.model_var.get()
        use_gpu = self.gpu_var.get()
        generate_analysis_option = self.analysis_var.get()
        output_path = self.output_file_path.get()

        if not audio_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, selecione um arquivo de áudio para transcrever.")
            logger.warning("Tentativa de transcrição sem arquivo de áudio selecionado.") # Log de aviso
            return
        if not output_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, defina o nome e local do arquivo de saída.")
            logger.warning("Tentativa de transcrição sem local de saída definido.") # Log de aviso
            return

        if generate_analysis_option and not API_KEY: # Corrigido: Verifica se a API_KEY está vazia
            messagebox.showwarning("API Key Ausente", "Para gerar a análise com a GEM, você precisa configurar sua chave de API do Google Gemini no script.")
            logger.warning("Análise da GEM solicitada, mas API Key do Gemini não configurada.") # Log de aviso
            return

        self.transcribe_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.update_progress_label("Iniciando transcrição...")
        self.update_progress_bar_value(0)
        logger.info(f"Iniciando thread de transcrição para '{audio_path}' (Modelo: {model_size}, GPU: {use_gpu}, Análise GEM: {generate_analysis_option})") # Log de info

        transcription_thread = threading.Thread(
            target=transcribe_audio_logic,
            args=(audio_path, model_size, use_gpu, output_path, generate_analysis_option,
                  self.update_progress_label, self.update_progress_bar_value, self.stop_transcription_event,
                  self.clear_input_fields)
        )
        transcription_thread.start()

        self.master.after(100, lambda: self.check_transcription_thread(transcription_thread))

    def cancel_transcription(self):
        response = messagebox.askyesno("Confirmar Cancelamento", "Tem certeza que deseja cancelar a transcrição?")
        if response:
            self.stop_transcription_event.set()
            self.update_progress_label("Sinal de cancelamento enviado...")
            logger.info("Solicitação de cancelamento de transcrição enviada.") # Log de info

    def check_transcription_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_transcription_thread(thread))
        else:
            self.transcribe_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            logger.info("Thread de transcrição finalizada e botões reativados.") # Log de info
            
# --- Execução Principal ---
if __name__ == "__main__":
    logger.info("Aplicação 'CesarVox' iniciada.") # Log de início da aplicação
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()
    logger.info("Aplicação 'CesarVox' encerrada.") # Log de encerramento