import unittest
from unittest.mock import patch, MagicMock
from src.services.ai_service import AIService
from src.core.memory_manager import MemoryManager

class TestAPI(unittest.TestCase):
    @patch("src.services.ai_service.ollama", None) # Deshabilitar ollama para probar nube
    @patch("src.services.ai_service.genai")
    @patch("src.services.ai_service.GEMINI_API_KEY", "fake_key")
    def test_gemini_init_and_mocked_call(self, mock_genai):
        # Configurar mock
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat
        
        # Simular respuesta
        mock_response = MagicMock()
        mock_response.text = '{"intent": "buscar_google", "target": "clima"}'
        mock_chat.send_message.return_value = mock_response

        mem = MagicMock()
        ai = AIService(mem)
        
        # Inicializar (lazy)
        ai._ensure_models_initialized()
        
        self.assertTrue(ai.ia_habilitada)
        mock_genai.Client.assert_called_once_with(api_key="fake_key")

if __name__ == "__main__":
    unittest.main()
