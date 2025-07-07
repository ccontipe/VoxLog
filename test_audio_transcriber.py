import unittest
from unittest import mock
import threading

import audio_transcriber

class TestAudioTranscriber(unittest.TestCase):

    def setUp(self):
        # Prepara mocks para callbacks usados na interface
        self.progress_label_callback = mock.Mock()
        self.progress_bar_callback = mock.Mock()
        self.stop_event = threading.Event()

    def test_audio_file_not_found(self):
        # Simula transcrição de arquivo inexistente
        result = audio_transcriber.transcribe_audio(
            audio_path="arquivo_inexistente.wav",
            model_size="small",
            use_gpu=False,
            output_path="saida.txt",
            progress_label_callback=self.progress_label_callback,
            progress_bar_callback=self.progress_bar_callback,
            stop_event=self.stop_event,
            timeout_seconds=5,
            beam_size=5,
            compute_type="float16"
        )
        self.assertIsNone(result, "Transcrição deve retornar None para arquivo inexistente.")

    @mock.patch("audio_transcriber.importar_dependencias")
    def test_dependencies_missing(self, mock_importar):
        # Simula dependências ausentes
        mock_importar.return_value = (None, None)
        with mock.patch("audio_transcriber.WhisperModel", None), \
             mock.patch("audio_transcriber.torch", None):
            result = audio_transcriber.transcribe_audio(
                audio_path="qualquer.wav",
                model_size="small",
                use_gpu=False,
                output_path="saida.txt",
                progress_label_callback=self.progress_label_callback,
                progress_bar_callback=self.progress_bar_callback,
                stop_event=self.stop_event,
                timeout_seconds=5,
                beam_size=5,
                compute_type="float16"
            )
        self.assertIsNone(result, "Deve retornar None se dependências não puderem ser importadas.")

    @mock.patch("audio_transcriber._transcribe_worker")
    def test_timeout_triggered(self, mock_worker):
        # Simula thread travada para forçar timeout
        def long_running_worker(*args, **kwargs):
            import time
            time.sleep(2)
            return None
        mock_worker.side_effect = long_running_worker

        result = audio_transcriber.transcribe_audio(
            audio_path="qualquer.wav",
            model_size="small",
            use_gpu=False,
            output_path="saida.txt",
            progress_label_callback=self.progress_label_callback,
            progress_bar_callback=self.progress_bar_callback,
            stop_event=self.stop_event,
            timeout_seconds=1,  # timeout curto para garantir disparo
            beam_size=5,
            compute_type="float16"
        )
        self.assertIsNone(result, "Deve retornar None se timeout for atingido.")

    @mock.patch("audio_transcriber._transcribe_worker")
    def test_stop_event_interrupt(self, mock_worker):
        # Simula interrupção pelo usuário
        def worker_with_interrupt(audio_path, model_size, use_gpu, output_path,
                                 progress_label_callback, progress_bar_callback, stop_event, result_holder,
                                 beam_size, compute_type):
            stop_event.set()  # Simula usuário interrompendo rapidamente
            result_holder["value"] = None
        mock_worker.side_effect = worker_with_interrupt

        self.stop_event.clear()
        result = audio_transcriber.transcribe_audio(
            audio_path="qualquer.wav",
            model_size="small",
            use_gpu=False,
            output_path="saida.txt",
            progress_label_callback=self.progress_label_callback,
            progress_bar_callback=self.progress_bar_callback,
            stop_event=self.stop_event,
            timeout_seconds=5,
            beam_size=5,
            compute_type="float16"
        )
        self.assertIsNone(result, "Deve retornar None se a transcrição for interrompida.")

    @mock.patch("audio_transcriber.WhisperModel")
    @mock.patch("audio_transcriber.torch")
    def test_successful_transcription_mocked(self, mock_torch, mock_WhisperModel):
        # Simula transcrição bem-sucedida com mocks
        mock_torch.cuda.is_available.return_value = False

        class DummyModel:
            def transcribe(self, audio_path, beam_size):
                class DummyInfo:
                    duration = 10.0
                def segments_gen():
                    class Seg:
                        def __init__(self, start, end, text):
                            self.start = start
                            self.end = end
                            self.text = text
                    yield Seg(0, 5, "Primeira parte.")
                    yield Seg(5, 10, "Segunda parte.")
                return segments_gen(), DummyInfo()

        mock_WhisperModel.return_value = DummyModel()

        result = audio_transcriber.transcribe_audio(
            audio_path="dummy.wav",
            model_size="small",
            use_gpu=False,
            output_path="saida.txt",
            progress_label_callback=self.progress_label_callback,
            progress_bar_callback=self.progress_bar_callback,
            stop_event=self.stop_event,
            timeout_seconds=5,
            beam_size=5,
            compute_type="float16"
        )
        self.assertIsNotNone(result, "Deve retornar string de transcrição para caso de sucesso.")
        self.assertIn("Primeira parte.", result)
        self.assertIn("Segunda parte.", result)

if __name__ == "__main__":
    unittest.main()
