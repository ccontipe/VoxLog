import subprocess
import sys
import os

# Função para instalar pacotes Python
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"Pacote '{package}' instalado com sucesso.")
    except subprocess.CalledProcessError:
        print(f"Erro ao instalar o pacote '{package}'. Por favor, tente instalar manualmente: pip install {package}")
        sys.exit(1) # Sai do script se a instalação falhar

# Tenta importar faster_whisper, instala se não estiver presente
try:
    from faster_whisper import WhisperModel
    import torch # Importa torch para verificar o dispositivo
except ImportError:
    print("faster-whisper não encontrado. Tentando instalar...")
    install_package("faster-whisper")
    install_package("torch") # faster-whisper depende de torch
    try:
        from faster_whisper import WhisperModel
        import torch
    except ImportError:
        print("Erro: faster-whisper e/ou torch não puderam ser instalados ou importados. Por favor, verifique sua conexão com a internet e permissões.")
        sys.exit(1)


# --- Configuração do Modelo e Dispositivo ---
# Verifica se uma GPU está disponível
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Usando o dispositivo: {device}")

# Carrega o modelo Faster Whisper
# 'small' é um bom ponto de partida. 'compute_type' pode ser 'float16' para GPU (mais rápido) ou 'int8' para CPU (mais eficiente em memória)
compute_type = "float16" if device == "cuda" else "int8"
model = WhisperModel("small", device=device, compute_type=compute_type)

# Nome do arquivo de áudio
audio_file = "Dp47.m4a"  # Altere aqui para o nome do seu arquivo

# Verifica se o arquivo de áudio existe
if not os.path.exists(audio_file):
    print(f"Erro: O arquivo de áudio '{audio_file}' não foi encontrado.")
    print("Por favor, certifique-se de que o arquivo está no mesmo diretório do script ou forneça o caminho completo.")
    sys.exit(1)

# --- Faz a transcrição ---
print(f"Iniciando transcrição de '{audio_file}' usando o modelo 'small' no dispositivo '{device}'...")
segments, info = model.transcribe(audio_file, beam_size=5) # beam_size pode ser ajustado para precisão vs. velocidade

print(f"Idioma detectado: {info.language} com probabilidade {info.language_probability:.2f}")

full_transcription = ""
print("\n--- Transcrição ---")
for segment in segments:
    # Opcional: imprime os timestamps de cada segmento
    # print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    full_transcription += segment.text + " "

# Mostra a transcrição no terminal
print(full_transcription.strip())

# Salva a transcrição em um arquivo texto
output_filename = "transcricao_faster_whisper.txt"
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(full_transcription.strip())

print(f"\nTranscrição salva em '{output_filename}'")