# utils_instalador.py (ampliação)
import subprocess
import sys
import logging
from tkinter import messagebox

logger = logging.getLogger(__name__)

def instalar_pacote(package):
    try:
        logger.info(f"Tentando instalar o pacote: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"], timeout=180)
        logger.info(f"Pacote '{package}' instalado com sucesso.")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout ao tentar instalar o pacote '{package}'.")
        messagebox.showerror("Erro de Instalação", f"Timeout ao tentar instalar o pacote '{package}'. Verifique sua conexão.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao instalar o pacote '{package}': {e}", exc_info=True)
        messagebox.showerror("Erro de Instalação", f"Falha ao instalar o pacote '{package}'. Por favor, tente instalar manualmente ou execute o script com permissões adequadas.")
        return False
    except Exception as e:
        logger.critical(f"Ocorreu uma exceção crítica ao instalar '{package}': {e}", exc_info=True)
        messagebox.showerror("Erro de Instalação", f"Ocorreu um erro inesperado ao instalar '{package}': {e}")
        return False

def instalar_multiplos_pacotes(pacotes):
    """Tenta instalar todos os pacotes da lista. Retorna True se todos instalados com sucesso."""
    sucesso = True
    for pacote in pacotes:
        if not instalar_pacote(pacote):
            sucesso = False
    return sucesso

# Lista recomendada de dependências para text_file_reader.py
DEPENDENCIAS_TEXTO = [
    "python-docx",
    "mammoth",
#   "textract",  #removido, temporariamente
    "extract-msg",
    "pdfplumber",
    "PyPDF2",
    "beautifulsoup4"
]

if __name__ == "__main__":
    instalar_multiplos_pacotes(DEPENDENCIAS_TEXTO)
