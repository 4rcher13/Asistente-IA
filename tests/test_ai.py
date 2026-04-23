import unittest
from unittest.mock import patch, MagicMock
from src.services.ai_service import AIService

class TestAI(unittest.TestCase):
    def setUp(self):
        self.patcher_ollama = patch("src.services.ai_service.ollama", new=None)
        self.patcher_genai = patch("src.services.ai_service.genai", new=None)
        self.patcher_ollama.start()
        self.patcher_genai.start()
        
        self.mem_mock = MagicMock()
        self.ai = AIService(self.mem_mock)
        
    def tearDown(self):
        patch.stopall()
        
    def test_routing_empty_prompt(self):
        self.ai.ia_habilitada = False
        self.ai.ollama_habilitado = False
        res = self.ai.route_command("")
        self.assertIsNone(res.get("intent"))

    def test_routing_saludos(self):
        res = self.ai.route_command("hola icaro")
        self.assertEqual(res["respuesta"], "Hola, a tu servicio.")

    def test_routing_fallback_nube(self):
        self.ai.ia_habilitada = True
        self.ai.ollama_habilitado = False
        self.ai.chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"intent": "abrir_aplicacion", "target": "notepad"}'
        self.ai.chat.send_message.return_value = mock_response
        
        res = self.ai.route_command("abre notepad")
        self.assertEqual(res["intent"], "abrir_aplicacion")
        self.assertEqual(res["target"], "notepad")

    def test_routing_exception_api(self):
        self.ai.ia_habilitada = True
        self.ai.ollama_habilitado = False
        self.ai.chat = MagicMock()
        self.ai.chat.send_message.side_effect = Exception("API Caída o Timeout")
        
        res = self.ai.route_command("abre notepad")
        self.assertIsNone(res["intent"])
        
    def test_summarize_nube(self):
        self.ai.ia_habilitada = True
        self.ai.chat = MagicMock()
        self.ai.chat.send_message.return_value.text = "Resumen de texto"
        
        res = self.ai.summarize("hola")
        self.assertEqual(res, "Resumen de texto")

    def test_summarize_respuesta_vacia(self):
        """La API puede devolver None o cadena vacía — debe manejarse sin crashear."""
        self.ai.ia_habilitada = True
        self.ai.chat = MagicMock()
        self.ai.chat.send_message.return_value.text = None
        
        res = self.ai.summarize("hola")
        # No debe lanzar excepción, y retornar algo coherente
        self.assertIsNotNone(res)

    def test_routing_sin_api_key(self):
        """Sin API key configurada, debe devolver respuesta de sistema degradado."""
        with patch("src.services.ai_service.GEMINI_API_KEY", None):
            self.ai._models_initialized = False
            self.ai.ia_habilitada = False
            self.ai.ollama_habilitado = False
            
            res = self.ai.route_command("abrir notepad")
            # Sin IA ni Ollama: respuesta de fallo controlado
            self.assertIsNone(res.get("intent"))

    def test_fallback_cloud_a_local(self):
        """Si Gemini falla con excepción, debe intentar Ollama sin crashear."""
        self.ai.ia_habilitada = True
        self.ai.ollama_habilitado = True
        self.ai.chat = MagicMock()
        self.ai.chat.send_message.side_effect = Exception("Gemini timeout")
        
        # Mockear ollama para que devuelva algo válido
        mock_ollama = MagicMock()
        mock_ollama.chat.return_value = MagicMock(
            message=MagicMock(content='{"intent": "dar_hora_fecha", "target": "hora"}')
        )
        with patch("src.services.ai_service.ollama", mock_ollama):
            res = self.ai.route_command("qué hora es")
            # No importa si Gemini cayó, si Ollama responde debe retornar algo
            self.assertIsInstance(res, dict)

if __name__ == "__main__":
    unittest.main()
