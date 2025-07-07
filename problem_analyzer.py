import logging
import os
import google.generativeai as genai

def load_prompt_analyzer():
    PROMPT_ANALYZER_PATH = os.environ.get("PROMPT_ANALYZER_PATH", "prompt_analyzer.txt")
    logging.info(f"Carregando prompt do caminho: {PROMPT_ANALYZER_PATH}")
    try:
        with open(PROMPT_ANALYZER_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Erro ao carregar o prompt do analisador: {e}")
        return None

def is_valid_model_name(model_name):
    modelos_validos = [
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro",
        "models/gemini-pro",
        "models/gemini-ultra",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
        "gemini-ultra"
    ]
    if not isinstance(model_name, str):
        return False
    if model_name in modelos_validos:
        return True
    if model_name.startswith("models/gemini"):
        return True
    return False

def analyze_full_text(transcription, model="models/gemini-1.5-flash"):
    """
    Analisa a transcrição completa usando IA Gemini e retorna a análise única e concentrada.
    """
    logging.info(f"Modelo Gemini solicitado: {repr(model)}")
    if not is_valid_model_name(model):
        logging.error(f"Nome de modelo inválido ou não suportado: {model}")
        return "Erro: Nome de modelo inválido ou não suportado."
    prompt_analyzer = load_prompt_analyzer()
    if not prompt_analyzer:
        logging.error("Prompt do analisador não encontrado ou inválido.")
        return "Erro: Prompt do analisador não encontrado ou inválido."
    if not transcription or not isinstance(transcription, str) or not transcription.strip():
        logging.error("Transcrição inválida para análise do problema.")
        return "Erro: Transcrição inválida para análise do problema."

    prompt = prompt_analyzer.replace("{transcricao}", transcription)
    logging.info(f"Prompt enviado ao Gemini (primeiros 300 chars): {prompt[:300]!r}")

    try:
        response = genai.GenerativeModel(model).generate_content(prompt)
        if hasattr(response, "text"):
            logging.info("Análise concentrada processada com sucesso.")
            return response.text
        else:
            logging.warning("Resposta da IA sem campo .text.")
            return str(response)
    except Exception as e:
        logging.error(f"Erro ao analisar o texto completo: {e}")
        return f"Erro ao analisar o texto completo: {str(e)}"

def extract_joined_text(result_struct, error_placeholder="<<ERRO AO ANALISAR TRECHO>>"):
    if not isinstance(result_struct, dict):
        return str(result_struct)
    if "results" not in result_struct:
        return str(result_struct)
    partes = []
    for r in result_struct["results"]:
        if r.get("status") == "success":
            partes.append(r.get("text", ""))
        elif r.get("status") == "warning":
            partes.append(r.get("text", ""))
        else:
            partes.append(error_placeholder)
    return "\n\n".join(partes)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    example_transcription = "Texto de exemplo para análise."
    result = analyze_full_text(example_transcription)
    print("\n--- Análise Concentrada ---\n")
    print(result)
