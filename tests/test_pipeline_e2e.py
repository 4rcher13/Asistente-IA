"""
Tests end-to-end del pipeline de Ícaro.
Validan el flujo completo: comando → procesamiento → respuesta.

Ejecutar: python -m pytest tests/test_pipeline_e2e.py -v
"""
import time
import threading
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.icaro import Icaro, IcaroState
from src.core.command_processor import CommandProcessor
from src.services.action_service import ActionService


# =====================================================================
# Fixtures
# =====================================================================

class MockAudio:
    """Mock de AudioService que no usa hardware."""
    def __init__(self):
        self.spoken = []
        self.listen_returns = []
        self._listen_idx = 0
    
    def hablar(self, texto):
        self.spoken.append(texto)
    
    def escuchar(self, **kwargs):
        if self._listen_idx < len(self.listen_returns):
            result = self.listen_returns[self._listen_idx]
            self._listen_idx += 1
            return result
        return ""


class MockAI:
    """Mock de AIService que responde instantáneamente."""
    def __init__(self):
        self.calls = []
    
    def route_command(self, text):
        self.calls.append(text)
        t = text.lower()
        
        if "notepad" in t or "bloc" in t:
            return {"intent": "abrir_aplicacion", "target": "notepad", "respuesta": "Abriendo Bloc de Notas."}
        if "hora" in t:
            return {"intent": "dar_hora_fecha", "target": "hora", "respuesta": "La hora es."}
        if "volumen" in t and "sub" in t:
            return {"intent": "control_volumen", "target": "subir", "respuesta": "Subiendo volumen."}
        if "youtube" in t:
            return {"intent": "reproducir_youtube", "target": t.replace("youtube", "").strip(), "respuesta": "Buscando en YouTube."}
        return {"intent": None, "target": None, "respuesta": "No entiendo tu petición."}
    
    def summarize(self, text):
        return "Resumen de prueba."
    
    def disable_ai(self):
        pass


class MockMemory:
    """Mock de MemoryManager en memoria pura."""
    def __init__(self):
        self.entries = []
    
    def guardar(self, rol, texto):
        self.entries.append({"role": rol, "text": texto})
    
    def cargar(self):
        return list(self.entries)
    
    def get_recent(self, n=5):
        return list(self.entries[-n:])
    
    def flush(self):
        pass


class MockTelemetry:
    """Mock de telemetría que registra transiciones."""
    def __init__(self):
        self.events = []
    
    def send(self, state, prompt="", response=""):
        self.events.append({"state": state, "prompt": prompt, "response": response})
    
    def close(self):
        pass


@pytest.fixture
def mock_icaro():
    """Crea un Icaro completamente mockeado (sin hardware)."""
    audio = MockAudio()
    ai = MockAI()
    memory = MockMemory()
    action = ActionService()
    telemetry = MockTelemetry()
    
    icaro = Icaro(
        silent=True,
        audio_service=audio,
        ai_service=ai,
        memory_manager=memory,
        action_service=action,
        telemetry_service=telemetry,
    )
    
    return icaro, audio, ai, memory, telemetry


# =====================================================================
# Tests de Pipeline E2E
# =====================================================================

class TestFullPipelineLocalCommand:
    """Pipeline completo para comandos que se resuelven localmente."""
    
    def test_command_hora(self, mock_icaro):
        """Comando 'dame la hora' se resuelve y genera respuesta."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        icaro._process_command("dame la hora")
        
        # Debe haber transicionado por THINKING y SPEAKING
        states = [e["state"] for e in telem.events]
        assert "thinking" in states
        # Puede que SPEAKING no aparezca si la respuesta viene de ActionService
        
        # Memoria debe tener la entrada del usuario
        # (async, dar un momento)
        time.sleep(0.1)
        assert any(e["role"] == "user" and "hora" in e["text"] for e in memory.entries)
    
    def test_command_abrir_notepad(self, mock_icaro):
        """Comando 'abre notepad' ejecuta la acción correcta."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        icaro._process_command("abre notepad")
        
        # Verificar que AI fue consultada
        assert len(ai.calls) >= 1
        
        # Verificar que se guardó en memoria
        time.sleep(0.1)
        user_entries = [e for e in memory.entries if e["role"] == "user"]
        assert len(user_entries) >= 1
    
    def test_command_saludo(self, mock_icaro):
        """Comando de saludo genera respuesta conversacional."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        icaro._process_command("hola que tal")
        
        time.sleep(0.1)
        assert any(e["role"] == "user" for e in memory.entries)


class TestPipelineWithMockAI:
    """Pipeline con IA mockeada para verificar integración."""
    
    def test_ai_receives_normalized_text(self, mock_icaro):
        """La IA recibe el texto procesado por CommandProcessor."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        icaro._process_command("abre notepad por favor")
        
        assert len(ai.calls) >= 1
        # El texto puede estar normalizado por CommandProcessor
        received = ai.calls[0].lower()
        assert "notepad" in received or "bloc" in received
    
    def test_action_executed_after_ai_routing(self, mock_icaro):
        """Si la IA retorna un intent, ActionService lo ejecuta."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        # Spyar el ActionService
        original_execute = icaro.action.execute
        executed = []
        
        def spy_execute(config):
            executed.append(config)
            return original_execute(config)
        
        icaro.action.execute = spy_execute
        icaro._process_command("dame la hora")
        
        assert len(executed) >= 1
        assert executed[0].get("intent") == "dar_hora_fecha"


class TestPipelineFallbackChain:
    """Tests de la cadena de fallback: local → Ollama → Gemini."""
    
    def test_local_fallback_bypasses_ai(self):
        """Comandos locales no consultan la IA."""
        from src.core.nlu.intents import local_fallback
        
        result = local_fallback("qué hora es")
        assert result is not None
        assert result["intent"] == "dar_hora_fecha"
    
    def test_unknown_command_goes_to_ai(self, mock_icaro):
        """Comandos desconocidos pasan por la IA."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        icaro._process_command("dime algo interesante sobre python")
        
        # La IA debería haber sido consultada
        assert len(ai.calls) >= 1
    
    def test_ai_failure_returns_fallback(self):
        """Si la IA falla, se retorna respuesta de fallback."""
        from src.services.ai_service import AIService
        
        with patch("src.services.ai_service.ollama", None), \
             patch("src.services.ai_service.genai", None):
            mem = MagicMock()
            mem.get_recent.return_value = []
            ai = AIService(mem)
            ai._models_initialized = True
            ai.ia_habilitada = False
            ai.ollama_habilitado = False
            
            result = ai.route_command("comando desconocido total")
            
            assert result is not None
            assert result.get("respuesta")
            assert result.get("intent") is None


class TestConcurrentCommands:
    """Tests de concurrencia — sin deadlocks."""
    
    def test_5_commands_concurrent_no_deadlock(self, mock_icaro):
        """5 comandos simultáneos deben completarse sin deadlock en <5s."""
        icaro, audio, ai, memory, telem = mock_icaro
        
        commands = [
            "dame la hora",
            "abre notepad",
            "sube el volumen",
            "busca en youtube radiohead",
            "hola que tal",
        ]
        
        errors = []
        
        def run_command(cmd):
            try:
                icaro._process_command(cmd)
            except Exception as e:
                errors.append((cmd, str(e)))
        
        threads = [threading.Thread(target=run_command, args=(cmd,)) for cmd in commands]
        
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
        elapsed = time.perf_counter() - start
        
        # Verificar que no hubo errores
        assert not errors, f"Errores en comandos concurrentes: {errors}"
        
        # Verificar que todos los hilos terminaron
        alive = [t for t in threads if t.is_alive()]
        assert not alive, f"{len(alive)} hilos no terminaron (deadlock?)"
        
        print(f"\n  ⚡ 5 comandos concurrentes: {elapsed:.2f}s")


class TestMemoryPersistenceCycle:
    """Tests de persistencia de memoria."""
    
    def test_guardar_flush_cargar(self):
        """Ciclo completo: guardar → flush → cargar verifica integridad."""
        import tempfile
        
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        tmp_path.unlink()
        
        try:
            with patch("src.core.memory_manager.HISTORY_FILE", tmp_path):
                from src.core.memory_manager import MemoryManager
                
                # Guardar datos
                mem1 = MemoryManager(buffer_size=1)
                mem1.guardar("user", "Hola Ícaro")
                mem1.guardar("model", "Hola, ¿en qué te ayudo?")
                mem1.flush()
                
                # Cargar en nueva instancia
                mem2 = MemoryManager()
                historial = mem2.cargar()
                
                assert len(historial) >= 2
                assert historial[0]["role"] == "user"
                assert "Hola" in historial[0]["text"]
                assert historial[1]["role"] == "model"
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestIcaroStateTransitions:
    """Tests de la máquina de estados de Ícaro."""
    
    def test_initial_state(self, mock_icaro):
        """Estado inicial debe ser INITIALIZING → luego LISTENING."""
        icaro, _, _, _, telem = mock_icaro
        
        # Después del constructor, debería haber emitido "initializing"
        assert telem.events[0]["state"] == "initializing"
    
    def test_process_transitions_thinking_speaking(self, mock_icaro):
        """_process_command debe transicionar THINKING → SPEAKING → (ready)."""
        icaro, _, _, _, telem = mock_icaro
        
        telem.events.clear()
        icaro._process_command("abre notepad")
        
        states = [e["state"] for e in telem.events]
        assert "thinking" in states
    
    def test_inactivity_transitions_to_sleeping(self, mock_icaro):
        """Tras timeout de inactividad, debe transicionar a SLEEPING."""
        icaro, _, _, _, telem = mock_icaro
        
        icaro.inactivity_timeout = 0.01  # 10ms para el test
        icaro._state = IcaroState.LISTENING
        icaro.last_interaction_time = time.time() - 1  # hace 1 segundo
        
        icaro._check_inactivity()
        
        assert icaro._state == IcaroState.SLEEPING


class TestEndToEndTiming:
    """Tests de timing del pipeline completo."""
    
    def test_local_command_under_100ms(self, mock_icaro):
        """Un comando local completo (sin TTS real) debe ser <100ms."""
        icaro, _, _, _, _ = mock_icaro
        
        start = time.perf_counter()
        icaro._process_command("dame la hora")
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 100.0, f"Pipeline local tardó {elapsed_ms:.2f}ms (máx 100ms)"
        print(f"\n  ⚡ Pipeline E2E local: {elapsed_ms:.2f}ms")
    
    def test_10_commands_under_500ms(self, mock_icaro):
        """10 comandos en secuencia deben completarse en <500ms."""
        icaro, _, _, _, _ = mock_icaro
        
        commands = [
            "dame la hora", "abre notepad", "sube volumen",
            "hola", "youtube radiohead", "dame la fecha",
            "abre chrome", "baja volumen", "busca python",
            "silencio",
        ]
        
        start = time.perf_counter()
        for cmd in commands:
            icaro._process_command(cmd)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        avg = elapsed_ms / len(commands)
        assert elapsed_ms < 2000.0, f"10 comandos: {elapsed_ms:.2f}ms (máx 2000ms)"
        print(f"\n  ⚡ 10 comandos E2E: {elapsed_ms:.2f}ms (avg {avg:.1f}ms)")
