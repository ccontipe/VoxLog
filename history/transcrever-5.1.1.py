import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
import logging

# --- Configuração do Logging ---
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

# --- Funções de Instalação e Importação ---
def install_package(package):
    try:
        logger.info(f"Tentando instalar o pacote: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])
        logger.info(f"Pacote '{package}' instalado com sucesso.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao instalar o pacote '{package}': {e}", exc_info=True)
        print("Certifique-se de ter permissão de escrita ou execute como administrador, se necessário.")
        messagebox.showerror("Erro de Instalação", f"Falha ao instalar o pacote '{package}'. Por favor, tente instalar manualmente ou execute o script com permissões adequadas.")
        return False
    except Exception as e:
        logger.critical(f"Ocorreu uma exceção crítica ao instalar '{package}': {e}", exc_info=True)
        messagebox.showerror("Erro de Instalação", f"Ocorreu um erro inesperado ao instalar '{package}': {e}")
        return False

# Tenta importar faster_whisper, torch e google.generativeai globalmente.
try:
    from faster_whisper import WhisperModel
    import torch
    import google.generativeai as genai
    if not torch.cuda.is_available():
        logger.warning("Aviso: CUDA não está disponível. A transcrição será executada na CPU, mesmo se a GPU for selecionada.")
except ImportError:
    logger.warning("Módulos necessários não encontrados. Iniciando instalação automática...")
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
        logger.critical("Erro Fatal: Um ou mais módulos necessários não puderam ser instalados ou importados após a tentativa automática. Encerrando.")
        messagebox.showerror("Erro Fatal", "Módulos de transcrição e/ou análise não puderam ser instalados ou importados. Por favor, verifique sua conexão com a internet e permissões, e tente instalar manualmente: pip install faster-whisper torch google-generativeai")
        sys.exit(1)

# --- Configuração da API Google Gemini ---
API_KEY = "AIzaSyBrFE5AJuUzdRc9ysfasimGTfeowywvkFs" # Lembre-se de substituir pela sua chave real ou usar variável de ambiente
genai.configure(api_key=API_KEY)
logger.info("API Key do Gemini configurada.")

# --- Funções de geração de prompt ---
def get_analysis_prompt(transcription_text):
    """
    Retorna o prompt para a análise de transcrições.
    """
    return (
        "Você é um analista de negócios e sintetizador de informações altamente proficiente. "
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
        f"Transcrição:\n{transcription_text}"
    )

def get_solution_prompt(transcription_text):
    """
    Retorna o prompt para a geração de proposta de solução técnica.
    """
    return (
        "Esta GEM recebe a análise de transcrições de reuniões de negócios, focando em requisitos de negócios, e gera uma proposta de solução técnica completa baseada em Azure, com arquitetura bem definida, componentes e diagramas PlantUML.\n\n"
        "Além disso, esta GEM foi criada para também fornecer um guia técnico e estratégico sobre os principais padrões de arquitetura de software, com foco específico em aplicações e sistemas implantados na nuvem Microsoft Azure. A inteligência artificial deverá ser capaz de interpretar, aplicar e adaptar os padrões clássicos de arquitetura para os serviços e práticas recomendadas na Azure, incluindo microsserviços, event-driven, Clean Architecture e mais.\n\n"
        "Você é uma inteligência artificial especializada em arquitetura de soluções em nuvem Azure. Sua missão PRINCIPAL é analisar as informações fornecidas por uma outra GEM (de análise de transcrição de textos de reuniões de negócios) e gerar uma proposta de solução técnica detalhada. \n\n"
        "**Sua resposta DEVE seguir rigorosamente a seguinte estrutura:**\n\n"
        "---\n\n"
        "### Proposta de Solução Técnica: Projeto [Nome do Projeto - inferir da transcrição] em Azure\n\n"
        "**1. Análise do Problema e Requisitos:**\n\n"
        "   * Faça um resumo conciso do problema de negócio exposto na transcrição, incluindo os desafios principais (ex: prazo, complexidade de componentes, segurança, etc.).\n\n"
        "   * Liste os requisitos funcionais e não funcionais relevantes (ex: autenticação, autorização, exposição de serviços em API Gateway, integração com sistemas legados via arquivos ou chamadas à API, escalabilidade, segurança).\n\n"
        "   * Mencione explicitamente os modelos de autenticação, autorização, integração entre plataformas (cloud, on-premises, mainframe e open shift, etc.) e as preferências/preocupações levantadas.\n\n"
        "**2. Premissas de Negócio Essenciais:**\n\n"
        "   * Identifique e liste as principais premissas que a solução técnica deve respeitar (ex: faseamento da implementação, preferência por determinada forma de faturamento, restrições técnicas e orçamentárias se mencionadas, etc.).\n\n"
        "   * **NÃO É NECESSÁRIO INCLUIR ESTA PREMISSA, MAS MANTENHA-A EM CONSIDERAÇÃO:** \"O uso de AKS, Functions e Logic Apps é desencorajado pela administração de TI da empresa. Substitua o uso do AKS pelo ARO.\"\n\n"
        "**3. Visão Geral da Solução em Azure (Well-Architected Infrastructure):**\n\n"
        "   * Descreva a abordagem geral da solução em Azure.\n\n"
        "   * Mencione a adesão aos pilares do Azure Well-Architected Framework (Confiabilidade, Segurança, Excelência Operacional, Otimização de Custos, Eficiência de Desempenho).\n\n"
        "   * **UTILIZE AS SEGUINTES INFORMAÇÕES SALVAS:**\n\n"
        "       * \"O padrão de artefato inclui: Azure Tenant, On-premises, Acesso Externo, Hub Interno, Shared Infrastructure, VNETs e subscriptions associadas ao serviço Transacionar em cada ambiente (PR, HO, DV).\"\n\n"
        "       * \"Visão geral dos 10 componentes chave da arquitetura de microsserviços: Cliente, CDN, Load Balancer, API Gateway, Microsserviços, Message Broker, Databases, Identity Provider, Service Registry e Discovery, Service Coordenação (e.g., Zookeeper).\"\n\n"
        "       * Identifique o padrão de arquitetura que mais se adapta ao problema identificado.\n\n"
        "       * Explique como o padrão de arquitetura adotado (ex.: de microsserviços, Event-Driven Architecture, etc. ) é o modelo mais adequado para ser o pilar da solução.\n\n"
        "**4. Componentes da Solução Azure e sua Relação com o Problema/Solução:**\n\n"
        "   * Para cada componente Azure que você propor, siga este formato:\n\n"
        "       * **Nome do Componente Azure:** (Ex: Azure App Service / Azure Resources for Openshift (ARO))\n\n"
        "       * **Relação com o Problema/Solução:** Explique como o componente atende a um requisito ou resolve parte do problema. Faça referência explícita aos \"10 componentes chave da arquitetura de microsserviços\" sempre que aplicável (ex: \"Servirá como plataforma para hospedar os **Microsserviços**\").\n\n"
        "       * **Well-Architected:** Descreva como o componente contribui para os pilares do Well-Architected Framework (ex: \"Promove a **Excelência de Desempenho**...\"). **Para os microsserviços implantados no ARO, detalhe a contribuição individual de cada microsserviço para os pilares do Well-Architected Framework.**\n\n"
        "Detalhe os serviços Azure propostos e sua relação com a solução, bem como sua contribuição para os pilares do Well-Architected Framework, especialmente para os microsserviços implantados no ARO.\n\n"
        "   * Certifique-se de abordar componentes que cobrem os requisitos de:\n\n"
        "       * Hospedagem de aplicações (microsserviços, portal administrativo interno, portal de consumo externo para parceiros, etc.).\n\n"
        "       * Gerenciamento de APIs.\n\n"
        "       * Bancos de dados.\n\n"
        "       * Comunicação síncrona/assíncrona.\n\n"
        "       * Gerenciamento de identidades.\n\n"
        "       * Monitoramento.\n\n"
        "       * Balanceamento de carga e CDN.\n\n"
        "       * Conectividade híbrida (on-premises).\n\n"
        "       * Segurança de segredos.\n\n"
        "**5. Segurança e Conformidade (PCI SSC):**\n\n"
        "* Com base na necessidade de lidar com dados sensíveis, especialmente dados de cartão (se aplicável), detalhe como a solução proposta atende ou se alinha aos padrões do **PCI Security Standards Council (PCI SSC)**, conforme lembrado: \"O PCI Security Standards Council (PCI SSC) estabelece padrões de segurança para proteger dados de cartão, desde o design de software até o manuseio de dispositivos físicos. Os principais padrões incluem PCI DSS, PCI P2PE, Secure Software Standard & Secure SLC, e PTS POI. O PCI SSC oferece recursos suplementares e programas de qualificação para profissionais. A conformidade com os padrões PCI é crucial para organizações que lidam com dados de cartões.\"\n"
        "* Explique como os componentes Azure escolhidos contribuem para a conformidade com o PCI DSS (Data Security Standard) e outros padrões relevantes do PCI SSC, incluindo aspectos como:\n"
        "    * **Proteção de Dados de Titular de Cartão:** Como os dados sensíveis são armazenados e transmitidos de forma segura.\n"
        "    * **Segurança de Redes e Sistemas:** Medidas para proteger a rede e os sistemas de acessos não autorizados.\n"
        "    * **Controle de Acesso:** Como o acesso aos dados é restrito e monitorado.\n"
        "    * **Monitoramento e Testes Regulares:** Como a segurança será continuamente monitorada e testada.\n"
        "    * **Manutenção de uma Política de Segurança da Informação:** A importância da documentação e conscientização sobre as políticas de segurança.\n\n"
        "**6. Diagramas PlantUML:**\n\n"
        "   * Gere o código PlantUML para os seguintes diagramas:\n\n"
        "       * **Diagrama C1 - Diagrama de Contexto do Sistema:** Mostra o sistema em seu ambiente, interagindo com usuários e sistemas externos.\n\n"
        "       * **Diagrama C2 - Diagrama de Contêineres:** Detalha as aplicações principais dentro do sistema, suas tecnologias e interações.\n\n"
        "       * **Diagrama C3 - Diagrama de Componentes (Microsserviços):** Apresenta todos os contêineres da solução e mostra seus componentes internos e interações. **Certifique-se de que não haja menção a \"fidelidade\" na construção deste arquivo.**\n\n"
        "       * **Diagrama de Sequência:** Um diagrama de sequência **OBRIGATÓRIO** detalhando as chamadas de API e os passos entre os sistemas.\n\n"
        "   * **Instruções para o PlantUML:**\n\n"
        "       * Utilize `!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml` (e variantes para C2/C3) no início de cada diagrama para usar a notação C4.\n\n"
        "       * Use `LAYOUT_WITH_LEGEND()` para incluir a legenda.\n\n"
        "       * Assegure-se de que os nomes dos elementos nos diagramas sejam consistentes com a descrição da solução.\n\n"
        "       * A entrada para esta GEM será a transcrição analisada. \n\n"
        "   * **Template sugerido para todos os diagramas C4:**\n\n"
        "   ```plantuml\n"
        "   @startuml <NomeDoDiagrama>\n\n"
        "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml)\n"
        "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml)\n"
        "   !include [https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml](https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml)\n"
        "   ' Opcional: !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml) para diagramas de código\n\n"
        "   LAYOUT_WITH_LEGEND()\n\n"
        "   title <Título do Diagrama>\n\n"
        "   ' SEUS ELEMENTOS C4 AQUI (Person, System, System_Boundary, Container, Container_Boundary, Component, etc.)\n\n"
        "   @enduml\n"
        "```\n\n"
        f"Transcrição analisada:\n{transcription_text}"
    )

### MODIFICADO: Função call_gemini_analysis para aceitar o tipo de prompt ###
def call_gemini_api(prompt_text, prompt_purpose):
    """
    Chama o modelo Gemini com o texto do prompt fornecido.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info(f"Chamando o modelo Gemini para: {prompt_purpose}.")
        logger.debug(f"Prompt enviado para Gemini (primeiros 200 chars): {prompt_text[:200]}...")
        
        response = model.generate_content(prompt_text)
        logger.info(f"Resposta da GEM para {prompt_purpose} recebida com sucesso.")
        return response.text
    except Exception as e:
        logger.error(f"Erro ao chamar a API da GEM para {prompt_purpose}: {e}", exc_info=True)
        messagebox.showerror(f"Erro na {prompt_purpose} GEM", f"Não foi possível obter a resposta da GEM: {e}")
        return None

# --- Lógica de Transcrição ---
def transcribe_audio_logic(audio_path, model_size, use_gpu, output_path, generate_analysis_option, generate_solution_option, progress_label_callback=None, progress_bar_callback=None, stop_event=None, clear_fields_callback=None):
    transcription_interrupted = False
    logger.info(f"Iniciando lógica de transcrição para: {audio_path}")
    try:
        if 'torch' not in sys.modules:
            raise ImportError("O módulo 'torch' não está carregado. Por favor, reinicie e verifique a instalação.")

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Dispositivo de transcrição selecionado: {device}")

        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            logger.warning("GPU selecionada, mas CUDA não disponível. Revertendo para CPU.")
            device = "cpu"

        logger.info(f"Usando o dispositivo: {device}")

        compute_type = "float16" if device == "cuda" else "int8"
        logger.info(f"Tipo de computação: {compute_type}")

        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"Modelo Whisper carregado: {model_size}")

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            logger.error(f"Arquivo de áudio não encontrado: {audio_path}")
            return

        segments_generator, info = model.transcribe(audio_path, beam_size=5)
        logger.info(f"Iniciando transcrição de áudio com duração: {info.duration:.2f} segundos.")

        full_transcription = ""
        audio_duration = info.duration

        for segment in segments_generator:
            if stop_event and stop_event.is_set():
                transcription_interrupted = True
                messagebox.showinfo("Transcrição Cancelada", "A transcrição foi cancelada pelo usuário.")
                logger.info("Transcrição cancelada pelo usuário.")
                break

            text = segment.text.strip()
            full_transcription += text + " "

            if progress_label_callback and progress_bar_callback:
                progress_percentage = (segment.end / audio_duration) * 100
                progress_bar_callback(progress_percentage)
                progress_label_callback(f"Progresso: {int(progress_percentage)}%\n[{text}]")

        if not transcription_interrupted:
            transcribed_text = full_transcription.strip()
            logger.info(f"Transcrição completa. Salvando em: {output_path}")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(transcribed_text)

            messagebox.showinfo("Sucesso", f"Transcrição concluída e salva em '{output_path}'")
            logger.info("Transcrição salva com sucesso.")

            # --- Lógica para gerar análise e/ou solução com a GEM ---
            if generate_analysis_option or generate_solution_option:
                if 'google.generativeai' not in sys.modules:
                    messagebox.showerror("Erro de Dependência", "A biblioteca 'google-generativeai' não está disponível. Por favor, reinicie o script para tentar a instalação automática ou instale manualmente.")
                    progress_label_callback("Erro: 'google.generativeai' não encontrado.")
                    logger.error("A biblioteca 'google.generativeai' não está carregada para análise da GEM.")
                    return
                
                base_name = os.path.basename(output_path)
                file_name_without_ext = os.path.splitext(base_name)[0]

                if generate_analysis_option:
                    progress_label_callback("Chamando Analisador de Transcrições (GEM)...")
                    analysis_output = call_gemini_api(get_analysis_prompt(transcribed_text), "Análise de Transcrições")
                    
                    if analysis_output:
                        analysis_output_path = os.path.join(os.path.dirname(output_path), f"GEM - Analise {file_name_without_ext}.txt")
                        logger.info(f"Análise da GEM gerada. Salvando em: {analysis_output_path}")
                        with open(analysis_output_path, "w", encoding="utf-8") as f:
                            f.write(analysis_output)
                        messagebox.showinfo("Análise Concluída", f"Análise da GEM gerada e salva em '{analysis_output_path}'")
                        logger.info("Análise da GEM salva com sucesso.")
                    else:
                        messagebox.showwarning("Análise GEM", "A análise da GEM não foi gerada devido a um erro.")
                        logger.warning("Análise da GEM não foi gerada ou retornou vazia.")

                if generate_solution_option:
                    progress_label_callback("Chamando Gerador de Solução (GEM)...")
                    # Para a solução, o prompt de solução deve ser baseado na transcrição completa
                    # A IA deve ser capaz de inferir os problemas e requisitos da transcrição
                    solution_output = call_gemini_api(get_solution_prompt(transcribed_text), "Geração de Solução")
                    
                    if solution_output:
                        solution_output_path = os.path.join(os.path.dirname(output_path), f"GEM - Solucao Tecnica {file_name_without_ext}.txt")
                        logger.info(f"Solução Técnica da GEM gerada. Salvando em: {solution_output_path}")
                        with open(solution_output_path, "w", encoding="utf-8") as f:
                            f.write(solution_output)
                        messagebox.showinfo("Solução Concluída", f"Solução Técnica da GEM gerada e salva em '{solution_output_path}'")
                        logger.info("Solução Técnica da GEM salva com sucesso.")
                    else:
                        messagebox.showwarning("Solução GEM", "A solução técnica da GEM não foi gerada devido a um erro.")
                        logger.warning("Solução técnica da GEM não foi gerada ou retornou vazia.")
            else:
                logger.info("Nenhuma opção de análise ou solução da GEM selecionada. Pulando chamada à API.")

        else:
            if progress_label_callback:
                progress_label_callback("Cancelado.")

    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante a transcrição: {e}", exc_info=True)
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
    finally:
        logger.info("Processo de transcrição finalizado.")
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
        self.solution_var = tk.BooleanVar(value=False) # Variável para o checkbox "Gerar Solução"
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
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.analysis_var).pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(checkbox_frame, text="Gerar Solução:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.solution_var).pack(side=tk.LEFT)

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

    def clear_input_fields(self):
        self.audio_file_path.set("")
        self.output_file_path.set("")

    def start_transcription_thread(self):
        self.stop_transcription_event.clear()

        audio_path = self.audio_file_path.get()
        model_size = self.model_var.get()
        use_gpu = self.gpu_var.get()
        generate_analysis_option = self.analysis_var.get()
        generate_solution_option = self.solution_var.get() # Obter o estado do checkbox "Gerar Solução"
        output_path = self.output_file_path.get()

        if not audio_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, selecione um arquivo de áudio para transcrever.")
            logger.warning("Tentativa de transcrição sem arquivo de áudio selecionado.")
            return
        if not output_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, defina o nome e local do arquivo de saída.")
            logger.warning("Tentativa de transcrição sem local de saída definido.")
            return

        # MODIFICADO: Verificar se pelo menos uma opção da GEM está selecionada
        if (generate_analysis_option or generate_solution_option) and not API_KEY:
            messagebox.showwarning("API Key Ausente", "Para gerar a análise ou solução com a GEM, você precisa configurar sua chave de API do Google Gemini no script.")
            logger.warning("Análise/Solução da GEM solicitada, mas API Key do Gemini não configurada.")
            return

        self.transcribe_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.update_progress_label("Iniciando transcrição...")
        self.update_progress_bar_value(0)
        logger.info(f"Iniciando thread de transcrição para '{audio_path}' (Modelo: {model_size}, GPU: {use_gpu}, Análise GEM: {generate_analysis_option}, Solução GEM: {generate_solution_option})")

        transcription_thread = threading.Thread(
            target=transcribe_audio_logic,
            args=(audio_path, model_size, use_gpu, output_path, generate_analysis_option,
                  generate_solution_option, # Passando o novo parâmetro
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
            logger.info("Solicitação de cancelamento de transcrição enviada.")

    def check_transcription_thread(self, thread): 
        if thread.is_alive():
            self.master.after(100, lambda: self.check_transcription_thread(thread))
        else:
            self.transcribe_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            logger.info("Thread de transcrição finalizada e botões reativados.")
            
# --- Execução Principal ---
if __name__ == "__main__":
    logger.info("Aplicação 'CesarVox' iniciada.")
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()
    logger.info("Aplicação 'CesarVox' encerrada.")