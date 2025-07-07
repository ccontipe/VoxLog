# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import subprocess
import sys
import os
import threading
import time
import logging
from tkinter import messagebox

from utils_instalador import instalar_pacote

logger = logging.getLogger(__name__)

def importar_dependencias():
    try:
        from faster_whisper import WhisperModel
        import torch
        if not torch.cuda.is_available():
            logger.warning("[audio_transcriber] CUDA não disponível. Transcrição será na CPU.")
        logger.info("[audio_transcriber] Dependências importadas com sucesso.")
        return WhisperModel, torch
    except ImportError:
        logger.warning("[audio_transcriber] Dependências não encontradas. Instalando automaticamente...")

        if not instalar_pacote("faster-whisper"):
            logger.error("[audio_transcriber] Falha na instalação de faster-whisper.")

        if not instalar_pacote("torch"):
            logger.error("[audio_transcriber] Falha na instalação de torch.")

        try:
            from faster_whisper import WhisperModel
            import torch
            if not torch.cuda.is_available():
                logger.warning("[audio_transcriber] CUDA não disponível após instalação. Usando CPU.")
            logger.info("[audio_transcriber] Dependências importadas com sucesso após instalação.")
            return WhisperModel, torch
        except ImportError:
            logger.critical("[audio_transcriber] Erro Fatal: Não foi possível importar faster-whisper e/ou torch após instalação. Transcrição desabilitada.")
            messagebox.showerror(
                "Erro Fatal",
                "Módulos de transcrição necessários não puderam ser instalados ou importados. "
                "Por favor, verifique sua conexão com a internet e permissões, e tente instalar manualmente: pip install faster-whisper torch"
            )
            return None, None

WhisperModel, torch = importar_dependencias()

def _transcribe_worker(audio_path, model_size, use_gpu, output_path,
                      progress_label_callback, progress_bar_callback, stop_event,
                      result_holder, beam_size, compute_type):
    try:
        if WhisperModel is None or torch is None:
            logger.error("[audio_transcriber] Dependências ausentes. Não é possível transcrever.")
            raise ImportError("Faster Whisper e/ou Torch não estão disponíveis. Não é possível transcrever.")

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"[audio_transcriber] Dispositivo selecionado: {device}")

        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            logger.warning("[audio_transcriber] GPU selecionada, mas CUDA não disponível. Usando CPU.")

        logger.info(f"[audio_transcriber] Tipo de computação: {compute_type}")
        logger.info(f"[audio_transcriber] beam_size configurado: {beam_size}")

        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"[audio_transcriber] Modelo Whisper carregado: {model_size}")

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            logger.error(f"[audio_transcriber] Arquivo de áudio não encontrado: {audio_path}")
            result_holder["value"] = None
            return

        segments_generator, info = model.transcribe(audio_path, beam_size=beam_size)
        logger.info(f"[audio_transcriber] Duração do áudio: {info.duration:.2f} segundos. Transcrição iniciada.")

        transcribed_text_segments = []
        audio_duration = info.duration

        for segment in segments_generator:
            if stop_event and stop_event.is_set():
                messagebox.showinfo("Transcrição Cancelada", "A transcrição foi cancelada pelo usuário.")
                logger.info("[audio_transcriber] Transcrição cancelada pelo usuário (interrupção detectada).")
                result_holder["value"] = None
                return

            text = segment.text.strip()
            logger.debug(f"[audio_transcriber] Segmento transcrito: start={segment.start:.2f}, end={segment.end:.2f}, texto='{text}'")
            transcribed_text_segments.append(text)

            if progress_label_callback and progress_bar_callback:
                progress_percentage = (segment.end / audio_duration) * 100
                progress_bar_callback(progress_percentage)
                progress_label_callback(f"Progresso Transcrição: {int(progress_percentage)}%\n[{text}]")
                logger.debug(f"[audio_transcriber] Progresso atualizado para {progress_percentage:.2f}%.")

        full_transcription = " ".join(transcribed_text_segments).strip()
        logger.info(f"[audio_transcriber] Transcrição completa. Salvando em: {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_transcription)

        messagebox.showinfo("Sucesso da Transcrição", f"Transcrição concluída e salva em '{output_path}'")
        logger.info("[audio_transcriber] Transcrição salva com sucesso.")
        result_holder["value"] = full_transcription

    except ImportError as ie:
        logger.error(f"[audio_transcriber] Erro de importação: {ie}. Verifique as dependências.")
        messagebox.showerror("Erro de Dependência", f"Erro crítico de dependência para transcrição: {ie}. Verifique o log.")
        result_holder["value"] = None
    except Exception as e:
        logger.error(f"[audio_transcriber] Erro inesperado durante transcrição: {e}", exc_info=True)
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
        result_holder["value"] = None
    finally:
        logger.info("[audio_transcriber] Processo de transcrição (worker) finalizado.")

def transcribe_audio(audio_path, model_size, use_gpu, output_path,
                     progress_label_callback, progress_bar_callback, stop_event,
                     timeout_seconds=1200, beam_size=5, compute_type="float16"):
    """
    Realiza a transcrição de um arquivo de áudio usando Faster Whisper.
    Parâmetros configuráveis: timeout_seconds, beam_size, compute_type.
    """
    logger.info(f"[audio_transcriber] Iniciando transcrição: arquivo='{audio_path}', modelo='{model_size}', usar_gpu={use_gpu}, timeout={timeout_seconds}s, beam_size={beam_size}, compute_type={compute_type}")
    result_holder = {"value": None}
    worker_thread = threading.Thread(
        target=_transcribe_worker,
        args=(audio_path, model_size, use_gpu, output_path,
              progress_label_callback, progress_bar_callback, stop_event, result_holder,
              beam_size, compute_type),
        daemon=True
    )
    start_time = time.time()
    worker_thread.start()
    worker_thread.join(timeout_seconds)

    if worker_thread.is_alive():
        logger.error(f"[audio_transcriber] Timeout atingido ({timeout_seconds}s). Encerrando transcrição do arquivo '{audio_path}'.")
        if stop_event:
            stop_event.set()
        messagebox.showerror(
            "Timeout de Transcrição",
            f"A transcrição excedeu o tempo limite de {timeout_seconds//60} minutos e foi cancelada automaticamente.\n"
            "Se o arquivo for muito longo, tente dividir em partes menores."
        )
        return None
    else:
        elapsed = time.time() - start_time
        logger.info(f"[audio_transcriber] Transcrição concluída em {elapsed:.1f} segundos.")
        return result_holder["value"]
