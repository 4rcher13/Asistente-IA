import unittest
from unittest.mock import MagicMock, patch
from src.services.audio_service import AudioService


class TestAudio(unittest.TestCase):
    @patch("src.services.audio_service.sr.Recognizer")
    def setUp(self, mock_recognizer):
        self.mock_mic = MagicMock()
        self.audio = AudioService(microphone=self.mock_mic)

    def test_tts_queue_initialized(self):
        """El worker TTS debe arrancar con una cola activa."""
        self.assertIsNotNone(self.audio._tts_queue)
        self.assertTrue(self.audio._tts_worker_thread.is_alive())

    @patch("src.services.audio_service.pyttsx3.init")
    def test_find_voice_id(self, mock_pyttsx3_init):
        mock_engine = MagicMock()
        mock_engine.getProperty.return_value = [MagicMock(id="v1", name="Spanish")]
        mock_pyttsx3_init.return_value = mock_engine
        voice_id = self.audio._find_voice_id()
        self.assertEqual(voice_id, "v1")

    def test_hablar_sin_texto(self):
        self.audio.hablar("")  # No debe lanzar excepción

    @patch("src.services.audio_service.SD_AVAILABLE", False)
    def test_escuchar_legacy_unknown_value(self):
        import speech_recognition as sr

        self.audio.recognizer.recognize_google.side_effect = sr.UnknownValueError()
        res = self.audio.escuchar(timeout_silencio=0.1, limite_segundos=1)
        self.assertEqual(res, "")

    @patch("src.services.audio_service.SD_AVAILABLE", False)
    def test_escuchar_legacy_request_error(self):
        import speech_recognition as sr

        self.audio.recognizer.recognize_google.side_effect = sr.RequestError("API no disponible")
        res = self.audio.escuchar(timeout_silencio=0.1, limite_segundos=1)
        self.assertEqual(res, "")

    @patch("src.services.audio_service.SD_AVAILABLE", False)
    def test_escuchar_legacy_oserror_permisos(self):
        """Simula fallo de hardware; debe degradarse sin excepción al caller."""
        self.audio.microphone.__enter__ = MagicMock(side_effect=OSError("Dispositivo no encontrado"))
        res = self.audio.escuchar(timeout_silencio=0.1, limite_segundos=1)
        self.assertIsInstance(res, str)

    @patch("src.services.audio_service.SD_AVAILABLE", False)
    def test_escuchar_compat_limite_segundo(self):
        """Alias legado limite_segundo sigue funcionando."""
        self.audio.recognizer.listen = MagicMock(side_effect=Exception("stop"))
        res = self.audio.escuchar(timeout_silencio=0.1, limite_segundo=1)
        self.assertEqual(res, "")


if __name__ == "__main__":
    unittest.main()
