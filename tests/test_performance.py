"""
Tests de rendimiento para Ícaro.
Miden y validan tiempos máximos aceptables de cada componente.

Ejecutar: python -m pytest tests/test_performance.py -v
"""
import time
import threading
import pytest
from unittest.mock import MagicMock, patch


# =====================================================================
# Fixtures y helpers
# =====================================================================

@pytest.fixture
def memory_manager():
    """MemoryManager con archivo temporal."""
    import tempfile
    from pathlib import Path
    
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    tmp_path.unlink()  # No debe existir al inicio
    
    with patch("src.core.memory_manager.HISTORY_FILE", tmp_path):
        from src.core.memory_manager import MemoryManager
        mem = MemoryManager(buffer_size=10, flush_timeout=300)
        yield mem
    
    if tmp_path.exists():
        tmp_path.unlink()


@pytest.fixture
def ai_service_offline(memory_manager):
    """AIService con ambos modelos deshabilitados (sin red)."""
    with patch("src.services.ai_service.ollama", None), \
         patch("src.services.ai_service.genai", None):
        from src.services.ai_service import AIService
        ai = AIService(memory_manager)
        ai.ia_habilitada = False
        ai.ollama_habilitado = False
        ai._models_initialized = True
        return ai


def measure(fn, *args, **kwargs):
    """Mide el tiempo de ejecución de una función en ms."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, elapsed_ms


# =====================================================================
# Tests de rendimiento de componentes individuales
# =====================================================================

class TestLocalFallbackSpeed:
    """Velocidad del resolutor local de intents (sin IA)."""
    
    COMMANDS = [
        "qué hora es",
        "dame la fecha",
        "sube el volumen",
        "baja el volumen",
        "silencio",
        "abre la calculadora",
        "abre notepad",
        "abre vscode",
        "hola",
        "busca python tutorial",
        "pon musica de radiohead",
        "abre youtube",
        "busca en google clima",
        "que onda",
        "hey",
        "abre chrome",
        "abre word",
        "qué hora es",  # Repetido — debe ser caché hit
        "hola",         # Repetido — debe ser caché hit
        "silencio",     # Repetido — debe ser caché hit
    ]
    
    def test_local_fallback_batch_under_5ms(self):
        """20 comandos locales deben resolverse en menos de 5ms total."""
        from src.core.nlu.intents import local_fallback
        
        # Warm up caché
        local_fallback("test warmup")
        
        start = time.perf_counter()
        results = [local_fallback(cmd) for cmd in self.COMMANDS]
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Verificar que al menos 15/20 se resolvieron localmente
        resolved = sum(1 for r in results if r is not None)
        assert resolved >= 15, f"Solo {resolved}/20 se resolvieron localmente"
        
        assert elapsed_ms < 5.0, f"Batch de 20 comandos tardó {elapsed_ms:.2f}ms (máx 5ms)"
        print(f"\n  ⚡ 20 local_fallback: {elapsed_ms:.2f}ms ({resolved} resueltos)")

    def test_local_fallback_cached_near_zero(self):
        """Comandos repetidos (caché hit) deben ser ~0ms."""
        from src.core.nlu.intents import local_fallback
        
        # Prime the cache
        local_fallback("qué hora es")
        
        # Measure cache hit
        _, elapsed_ms = measure(local_fallback, "qué hora es")
        
        assert elapsed_ms < 0.5, f"Cache hit tardó {elapsed_ms:.3f}ms (máx 0.5ms)"
        print(f"\n  ⚡ Cache hit: {elapsed_ms:.4f}ms")


class TestNormalizeTextSpeed:
    """Velocidad de normalización de texto."""
    
    def test_normalize_1000_under_50ms(self):
        """1000 normalizaciones deben completarse en menos de 50ms."""
        from src.utils.text_utils import normalize_text
        
        texts = [
            "Ícaro, ábrele la puerta al señor",
            "¿Qué hora es?",
            "Búscame información sobre Python",
            "Hola, ¿cómo estás?",
            "Reproduce música de Radiohead",
        ] * 200  # 1000 textos
        
        start = time.perf_counter()
        _ = [normalize_text(t) for t in texts]
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 50.0, f"1000 normalizaciones tardaron {elapsed_ms:.2f}ms (máx 50ms)"
        print(f"\n  ⚡ 1000 normalize_text: {elapsed_ms:.2f}ms")


class TestCommandProcessorSpeed:
    """Velocidad del pipeline de normalización en CommandProcessor."""
    
    def test_normalize_pipeline_under_10ms(self):
        """La normalización con fuzzy matching debe ser <10ms por comando."""
        from src.core.command_processor import CommandProcessor
        
        mock_ai = MagicMock()
        mock_action = MagicMock()
        cp = CommandProcessor(mock_ai, mock_action, use_rapidfuzz=True)
        
        commands = [
            "calkuladora",
            "notpad",
            "yutub",
            "abrir código",
            "bajar bolumen",
        ]
        
        start = time.perf_counter()
        _ = [cp._normalize(cmd) for cmd in commands]
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 10.0, f"5 normalizaciones tardaron {elapsed_ms:.2f}ms (máx 10ms)"
        print(f"\n  ⚡ 5 normalize: {elapsed_ms:.2f}ms")


class TestMemorySpeed:
    """Velocidad de operaciones de memoria."""
    
    def test_guardar_100_under_50ms(self, memory_manager):
        """100 operaciones guardar (sin flush) deben ser <50ms."""
        # Buffer grande para no disparar flush
        memory_manager.buffer_size = 200
        
        start = time.perf_counter()
        for i in range(100):
            memory_manager.guardar("user", f"Mensaje de prueba #{i}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 50.0, f"100 guardar tardaron {elapsed_ms:.2f}ms (máx 50ms)"
        print(f"\n  ⚡ 100 guardar: {elapsed_ms:.2f}ms")
    
    def test_get_recent_under_1ms(self, memory_manager):
        """get_recent debe ser <1ms."""
        # Llenar con datos
        for i in range(20):
            memory_manager.guardar("user" if i % 2 == 0 else "model", f"msg {i}")
        
        _, elapsed_ms = measure(memory_manager.get_recent, 5)
        
        assert elapsed_ms < 1.0, f"get_recent tardó {elapsed_ms:.3f}ms (máx 1ms)"
        print(f"\n  ⚡ get_recent(5): {elapsed_ms:.4f}ms")


class TestWakeWordSpeed:
    """Velocidad de detección de wake word."""
    
    def test_wake_word_detection_100_under_20ms(self):
        """100 detecciones de wake word deben ser <20ms."""
        from src.core.icaro import Icaro
        
        # Crear Icaro con todo mockeado
        icaro = Icaro(
            silent=True,
            audio_service=MagicMock(),
            ai_service=MagicMock(),
            memory_manager=MagicMock(),
            action_service=MagicMock(),
            telemetry_service=MagicMock(),
        )
        
        commands = [
            "ícaro abre youtube",
            "icaro dame la hora",
            "hícaro busca python",
            "no contiene wake word",
            "y claro que sí",
        ] * 20  # 100 comandos
        
        start = time.perf_counter()
        _ = [icaro._contains_wake_word(cmd) for cmd in commands]
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 20.0, f"100 detecciones tardaron {elapsed_ms:.2f}ms (máx 20ms)"
        print(f"\n  ⚡ 100 wake word: {elapsed_ms:.2f}ms")


class TestRoutingLocalSpeed:
    """Velocidad del pipeline completo sin IA (solo local)."""
    
    def test_routing_local_under_15ms(self, ai_service_offline):
        """Pipeline completo para comando local debe ser <15ms."""
        _, elapsed_ms = measure(ai_service_offline.route_command, "qué hora es")
        
        assert elapsed_ms < 15.0, f"Routing local tardó {elapsed_ms:.2f}ms (máx 15ms)"
        print(f"\n  ⚡ route_command local: {elapsed_ms:.2f}ms")
    
    def test_routing_batch_local(self, ai_service_offline):
        """10 comandos locales en secuencia."""
        commands = [
            "qué hora es", "sube el volumen", "abre notepad",
            "busca python", "hola", "baja el volumen",
            "abre vscode", "que onda", "abre chrome", "dame la fecha",
        ]
        
        start = time.perf_counter()
        results = [ai_service_offline.route_command(cmd) for cmd in commands]
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        # Todos deben resolver (hay intent o respuesta)
        for i, r in enumerate(results):
            assert r.get("respuesta"), f"Comando '{commands[i]}' no generó respuesta"
        
        avg_ms = elapsed_ms / len(commands)
        print(f"\n  ⚡ 10 route_command local: {elapsed_ms:.2f}ms (avg {avg_ms:.2f}ms)")


class TestTTSQueueSpeed:
    """Velocidad de enqueue en la cola TTS (no reproduce audio)."""
    
    def test_tts_enqueue_under_5ms(self):
        """Poner un mensaje en la cola TTS debe ser <5ms."""
        import queue
        
        q = queue.Queue()
        evento = threading.Event()
        texto = "Abriendo YouTube para ti."
        
        start = time.perf_counter()
        q.put((texto, evento))
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 5.0, f"Enqueue tardó {elapsed_ms:.3f}ms (máx 5ms)"
        print(f"\n  ⚡ TTS enqueue: {elapsed_ms:.4f}ms")


class TestActionDispatchSpeed:
    """Velocidad de dispatch de acciones."""
    
    def test_hora_fecha_under_10ms(self):
        """dar_hora_fecha debe ejecutarse en <10ms."""
        from src.services.action_service import ActionService
        
        action = ActionService()
        config = {"intent": "dar_hora_fecha", "target": "hora"}
        
        _, elapsed_ms = measure(action.execute, config)
        
        assert elapsed_ms < 10.0, f"dar_hora_fecha tardó {elapsed_ms:.2f}ms (máx 10ms)"
        print(f"\n  ⚡ dar_hora_fecha: {elapsed_ms:.2f}ms")
    
    def test_dispatch_no_intent_instant(self):
        """Sin intent, el dispatch debe ser <1ms."""
        from src.services.action_service import ActionService
        
        action = ActionService()
        _, elapsed_ms = measure(action.execute, {"intent": None})
        
        assert elapsed_ms < 1.0, f"Dispatch vacío tardó {elapsed_ms:.3f}ms (máx 1ms)"
        print(f"\n  ⚡ Dispatch vacío: {elapsed_ms:.4f}ms")


class TestSmartRoutingClassifier:
    """Tests para el clasificador de complejidad del Smart Routing."""
    
    def test_simple_commands_classified_correctly(self):
        """Comandos simples deben ser clasificados como simples."""
        from src.services.ai_service import _is_complex_query
        
        simple_commands = [
            "abre youtube",
            "sube el volumen",
            "qué hora es",
            "cierra chrome",
            "pon radiohead",
            "busca gatos",
            "abre word",
        ]
        
        for cmd in simple_commands:
            assert not _is_complex_query(cmd), f"'{cmd}' fue clasificado como complejo"
    
    def test_complex_commands_classified_correctly(self):
        """Comandos complejos deben ser clasificados como complejos."""
        from src.services.ai_service import _is_complex_query
        
        complex_commands = [
            "explícame cómo funciona un puntero en C",
            "analiza este código y dime qué hace",
            "investiga las diferencias entre TCP y UDP",
            "genera una función para ordenar una lista",
            "crea un algoritmo de búsqueda binaria",
            "este es un texto bastante largo que tiene más de sesenta caracteres para probar",
        ]
        
        for cmd in complex_commands:
            assert _is_complex_query(cmd), f"'{cmd}' fue clasificado como simple"
    
    def test_classifier_speed_under_1ms(self):
        """La clasificación debe ser <1ms."""
        from src.services.ai_service import _is_complex_query
        
        start = time.perf_counter()
        for _ in range(100):
            _is_complex_query("explícame cómo funciona un puntero")
            _is_complex_query("abre youtube")
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 5.0, f"200 clasificaciones tardaron {elapsed_ms:.2f}ms"
        print(f"\n  ⚡ 200 clasificaciones: {elapsed_ms:.2f}ms")


class TestJSONExtractor:
    """Tests para la extracción de JSON del LLM."""
    
    def test_extraer_json_valid(self):
        """Extrae JSON válido de texto."""
        from src.services.ai_service import AIService
        
        cases = [
            ('{"intent": "abrir_aplicacion", "target": "notepad"}',
             {"intent": "abrir_aplicacion", "target": "notepad"}),
            ('Aquí va: {"intent": null, "respuesta": "Hola"}',
             {"intent": None, "respuesta": "Hola"}),
            ('```json\n{"intent": "dar_hora_fecha"}\n```',
             {"intent": "dar_hora_fecha"}),
        ]
        
        for text, expected in cases:
            result = AIService._extraer_json(text)
            assert result == expected, f"Para '{text[:40]}': esperado {expected}, got {result}"
    
    def test_extraer_json_invalid(self):
        """Retorna None para texto sin JSON."""
        from src.services.ai_service import AIService
        
        assert AIService._extraer_json("no hay json aquí") is None
        assert AIService._extraer_json("") is None
        assert AIService._extraer_json(None) is None
    
    def test_extraer_json_speed(self):
        """100 extracciones deben ser <10ms."""
        from src.services.ai_service import AIService
        
        text = 'Respuesta: {"intent": "abrir_aplicacion", "target": "notepad", "respuesta": "Abriendo"}'
        
        start = time.perf_counter()
        for _ in range(100):
            AIService._extraer_json(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 10.0, f"100 extracciones: {elapsed_ms:.2f}ms"
        print(f"\n  ⚡ 100 extraer_json: {elapsed_ms:.2f}ms")
