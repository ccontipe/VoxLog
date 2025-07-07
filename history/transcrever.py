import whisper

# Carrega o modelo Whisper (você pode usar 'base', 'tiny', 'small', 'medium', 'large')
model = whisper.load_model("small")

# Nome do arquivo de áudio
audio_file = "Voz 001.m4a"  # Altere aqui para o nome do seu arquivo

# Faz a transcrição
result = model.transcribe(audio_file, verbose=True)

# Mostra a transcrição no terminal
print("\n--- Transcrição ---\n")
print(result["text"])

# Salva a transcrição em um arquivo texto
with open("transcricao.txt", "w", encoding="utf-8") as f:
    f.write(result["text"])
