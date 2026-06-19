"""
Tests de integración para Ícaro.
Verifica que los componentes trabajan juntos correctamente.

Ejecutar: python -m pytest tests/test_integration.py -v
"""
import pytest
from pathlib import Path
from unittest.mock import patch
from src.core.icaro import Icaro
from src.core.protocols import AudioProtocol, AIProtocol, MemoryProtocol, ActionProtocol
from src.services.action_service import ActionService
from src.core.memory_manager import MemoryManager
from src.core.command_processor import CommandProcessor


class MockAudio:
    def __init__(self):
        self.ultima_interaccion = 0
    def hablar(self, texto): pass
    def escuchar(self, **kwargs): return "abre notepad"


class MockAI:
    def route_command(self, text):
        if "notepad" in text:
            return {"intent": "abrir_aplicacion", "target": "notepad", "respuesta": "Abriendo bloc de notas"}
        return {"intent": None, "target": None, "respuesta": "No entiendo"}
    def summarize(self, text): return "Resumen"
    def disable_ai(self): pass


class MockTelemetry:
    def send(self, state, prompt="", response=""): pass
    def close(self): pass


def test_integration_flow(tmp_path):
    """Test de flujo completo: comando → IA → acción → memoria."""
    history_file = tmp_path / "historial.json"
    
    with patch("src.core.memory_manager.HISTORY_FILE", history_file):
        # Initialize services
        audio = MockAudio()
        ai = MockAI()
        memory = MemoryManager(buffer_size=1)  # Flush immediately for testing
        action = ActionService()
        telemetry = MockTelemetry()
        
        # Initialize Icaro with DI
        icaro = Icaro(
            silent=True,
            audio_service=audio,
            ai_service=ai,
            memory_manager=memory,
            action_service=action,
            telemetry_service=telemetry,
        )
        
        # Execute a cycle
        icaro._process_command("abre notepad")
        
        # Dar tiempo al thread de guardado async
        import time
        time.sleep(0.2)
        
        # Verify memory
        history = memory.cargar()
        assert len(history) >= 2
        
        # Buscar mensajes user y model en el historial (puede haber eventos del sistema intercalados)
        user_msgs = [h for h in history if h["role"] == "user"]
        model_msgs = [h for h in history if h["role"] == "model"]
        system_msgs = [h for h in history if h["role"] == "system"]
        
        # Verificar que tenemos ambos tipos de mensajes
        assert len(user_msgs) >= 1, "Debe haber al menos un mensaje del usuario"
        assert len(model_msgs) >= 1, "Debe haber al menos un mensaje del modelo"
        
        # Verificar contenido
        assert "abre notepad" in user_msgs[0]["text"]
        assert "Abriendo bloc de notas" in model_msgs[0]["text"]
        
        # Verificar que se registraron eventos del sistema (nueva funcionalidad)
        assert len(system_msgs) >= 1, "Debe haber eventos del sistema registrados (ActionService)"


def test_normalization_integration():
    """Test que CommandProcessor usa la normalización correctamente."""
    cp = CommandProcessor(
        ai_service=MockAI(),
        action_service=ActionService(),
        use_rapidfuzz=True
    )
    
    # "notepadd" should match "notepad" if rapidfuzz is working
    clean = cp._normalize("notepadd")
    assert clean == "notepad"


def test_local_fallback_integration():
    """Test que local_fallback resuelve comandos comunes sin IA."""
    from src.core.nlu.intents import local_fallback
    
    # Hora
    result = local_fallback("qué hora es")
    assert result is not None
    assert result["intent"] == "dar_hora_fecha"
    
    # Volumen
    result = local_fallback("sube el volumen")
    assert result is not None
    assert result["intent"] == "control_volumen"
    assert result["target"] == "subir"
    
    # YouTube
    result = local_fallback("pon musica de radiohead")
    assert result is not None
    assert result["intent"] == "reproducir_youtube"
    assert "radiohead" in result["target"]
    
    # Google
    result = local_fallback("busca clima en google")
    assert result is not None
    assert result["intent"] == "buscar_google"


def test_action_service_hora():
    """Test que ActionService devuelve la hora correctamente."""
    action = ActionService()
    result = action.execute({"intent": "dar_hora_fecha", "target": "hora"})
    assert "Son las" in result


def test_action_service_fecha():
    """Test que ActionService devuelve la fecha correctamente."""
    action = ActionService()
    result = action.execute({"intent": "dar_hora_fecha", "target": "fecha"})
    assert "Hoy es" in result


def test_command_processor_pipeline():
    """Test del pipeline completo del CommandProcessor."""
    ai = MockAI()
    action = ActionService()
    cp = CommandProcessor(ai, action, use_rapidfuzz=True)
    
    # Comando que la IA reconoce
    result = cp.process("abre notepad")
    assert result  # Debe devolver algo
    
    # La hora debe devolver el resultado de ActionService
    result = cp.process("dame la hora")
    assert result


def test_smart_routing_classifier():
    """Test del clasificador de complejidad del Smart Routing."""
    from src.services.ai_service import _is_complex_query
    
    # Simples
    assert not _is_complex_query("abre youtube")
    assert not _is_complex_query("sube volumen")
    assert not _is_complex_query("qué hora es")
    
    # Complejos
    assert _is_complex_query("explícame cómo funciona un puntero en C")
    assert _is_complex_query("investiga las diferencias entre TCP y UDP")
    assert _is_complex_query("genera una función para ordenar una lista")
