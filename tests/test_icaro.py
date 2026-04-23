import unittest
from unittest.mock import patch, MagicMock

# Evitar que settings inicialice variables indeseadas antes de parchear
with patch('dotenv.load_dotenv'):
    from src.core.icaro import Icaro

class TestIcaro(unittest.TestCase):
    @patch("src.core.icaro.AudioService")
    @patch("src.core.icaro.MemoryManager")
    @patch("src.core.icaro.CommandProcessor")
    @patch("src.core.icaro.AIService")
    @patch("src.core.icaro.ActionService")
    def test_icaro_iniciar_y_detener(self, MockAction, MockAI, MockCMD, MockMem, MockAudio):
        icaro = Icaro()
        self.assertTrue(icaro.running)
        
        # Simular que AudioService.escuchar devuelve un comando de apagado
        mock_audio_instance = MockAudio.return_value
        mock_audio_instance.escuchar.return_value = "apagar asistente"
        icaro.audio = mock_audio_instance
        
        # Evitar ciclo infinito llamando iniciar. El comando "apagar asistente" detendrá el bucle internamente
        icaro.iniciar()
        
        # Debería haber cambiado running a False
        self.assertFalse(icaro.running)
        
    @patch("src.core.icaro.AudioService")
    @patch("src.core.icaro.MemoryManager")
    @patch("src.core.icaro.CommandProcessor")
    @patch("src.core.icaro.AIService")
    @patch("src.core.icaro.ActionService")
    def test_icaro_procesamiento(self, MockAction, MockAI, MockCMD, MockMem, MockAudio):
        icaro = Icaro()
        icaro.dormido = False
        
        mock_cmd_instance = MockCMD.return_value
        mock_cmd_instance.process.return_value = "Hecho"
        icaro.processor = mock_cmd_instance
        
        icaro._ciclo_procesamiento("abre youtube")
        
        mock_cmd_instance.process.assert_called_with("abre youtube")
        icaro.memory.guardar.assert_any_call("user", "abre youtube")
        icaro.memory.guardar.assert_any_call("model", "Hecho")
        
if __name__ == "__main__":
    unittest.main()
