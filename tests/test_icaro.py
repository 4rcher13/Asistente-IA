"""
Tests unitarios del orquestador Icaro.
Actualizados para la API con _process_command (antes _ciclo_procesamiento).
"""
import unittest
from unittest.mock import patch, MagicMock

from src.core.icaro import Icaro, IcaroState


class TestIcaro(unittest.TestCase):
    
    def _create_icaro(self, **overrides):
        """Helper para crear Icaro con todos los servicios mockeados."""
        defaults = dict(
            silent=True,
            audio_service=MagicMock(),
            ai_service=MagicMock(),
            memory_manager=MagicMock(),
            action_service=MagicMock(),
            telemetry_service=MagicMock(),
        )
        defaults.update(overrides)
        return Icaro(**defaults)

    def test_icaro_init_state(self):
        """El estado inicial debe ser INITIALIZING, luego el constructor termina."""
        icaro = self._create_icaro()
        self.assertTrue(icaro.running)
        # Después del constructor, el telemetry debió recibir "initializing"
        icaro.telemetry.send.assert_called()
    
    def test_icaro_detener(self):
        """detener() cambia running a False."""
        icaro = self._create_icaro()
        self.assertTrue(icaro.running)
        icaro.detener()
        self.assertFalse(icaro.running)
    
    def test_icaro_procesamiento_con_respuesta(self):
        """_process_command guarda en memoria y habla si hay respuesta."""
        icaro = self._create_icaro()
        icaro.processor = MagicMock()
        icaro.processor.process.return_value = "Hecho"
        
        icaro._process_command("abre youtube")
        
        icaro.processor.process.assert_called_with("abre youtube")
        # Memory guardado es async ahora, verificar que se llamó en un thread
        # Dar un momento para que el thread ejecute
        import time
        time.sleep(0.1)
        icaro.memory.guardar.assert_any_call("user", "abre youtube")
        icaro.memory.guardar.assert_any_call("model", "Hecho")

    def test_icaro_procesamiento_sin_respuesta(self):
        """Si el processor retorna vacío, no se habla."""
        icaro = self._create_icaro()
        icaro.processor = MagicMock()
        icaro.processor.process.return_value = ""
        
        icaro._process_command("comando desconocido")
        
        # No debería haber llamado a hablar
        icaro.audio.hablar.assert_not_called()
    
    def test_contains_wake_word(self):
        """Detecta variantes del wake word."""
        icaro = self._create_icaro()
        
        self.assertTrue(icaro._contains_wake_word("ícaro abre youtube"))
        self.assertTrue(icaro._contains_wake_word("icaro dame la hora"))
        self.assertFalse(icaro._contains_wake_word("abre youtube"))
    
    def test_remove_wake_word(self):
        """Elimina el wake word y limpia espacios."""
        icaro = self._create_icaro()
        
        result = icaro._remove_wake_word("icaro abre youtube")
        self.assertNotIn("icaro", result.lower())
        self.assertIn("abre", result.lower())
    
    def test_get_greeting(self):
        """El saludo varía según la hora del día."""
        icaro = self._create_icaro()
        greeting = icaro._get_greeting()
        
        # Debe contener algún saludo válido
        self.assertTrue(
            any(s in greeting for s in ["Buenos días", "Buenas tardes", "Buenas noches"]),
            f"Saludo no reconocido: {greeting}"
        )
    
    def test_state_transitions(self):
        """Las transiciones de estado se emiten correctamente."""
        telemetry = MagicMock()
        icaro = self._create_icaro(telemetry_service=telemetry)
        
        icaro._transition_to(IcaroState.LISTENING)
        icaro._transition_to(IcaroState.THINKING, transcript="test")
        icaro._transition_to(IcaroState.SPEAKING, response="respuesta")
        
        # Verificar que se enviaron las transiciones
        calls = telemetry.send.call_args_list
        states = [c.args[0] if c.args else c.kwargs.get('state', '') for c in calls]
        self.assertIn("listening", states)
        self.assertIn("thinking", states)
        self.assertIn("speaking", states)
    
    def test_no_ai_mode(self):
        """Modo --no-ai desactiva la IA."""
        ai_mock = MagicMock()
        icaro = self._create_icaro(no_ai=True, ai_service=ai_mock)
        
        # Debe haber llamado disable_ai (si existe)
        if hasattr(ai_mock, 'disable_ai'):
            ai_mock.disable_ai.assert_called()


if __name__ == "__main__":
    unittest.main()
