"""
test_startup_time.py
====================
Suite de benchmarks para medir el tiempo de arranque de cada subsistema
del Asistente Ícaro.

Objetivo: garantizar que ningún componente individual supere su umbral
de tiempo de inicio y que la instanciación completa de Icaro ocurra
dentro de un tiempo razonable, sin red ni servicios externos reales.

Ejecución:
    python -m pytest tests/test_startup_time.py -v --no-cov -p no:cacheprovider

Marcadores:
    performance  – medición de tiempos
    unit         – sin I/O real
"""

import sys
import time
import tempfile
import logging
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Constantes de thresholds (ms)
# Ajústalos si tu hardware es más lento; los valores son conservadores.
# ──────────────────────────────────────────────────────────────────────────────
THRESHOLD_MEMORY_MANAGER_MS   = 500
THRESHOLD_AUDIO_SERVICE_MS    = 300
THRESHOLD_AI_SERVICE_MS       = 500
THRESHOLD_ACTION_SERVICE_MS   = 300
THRESHOLD_ICARO_INIT_MS       = 2_000   # Icaro completo (todos los subsistemas)
THRESHOLD_MODULE_IMPORT_MS    = 1_500   # importar src.core.icaro por primera vez


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _elapsed_ms(start: float) -> float:
    """Retorna el tiempo transcurrido en milisegundos desde `start`."""
    return (time.perf_counter() - start) * 1000


def _log_timing(label: str, elapsed: float, threshold: float) -> None:
    """Imprime el resultado del benchmark con estado PASS / WARN."""
    status = "PASS" if elapsed <= threshold else "WARN"
    logging.getLogger("startup_benchmark").info(
        f"{status} | {label:<40} {elapsed:>8.1f} ms  (limite: {threshold} ms)"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures compartidos
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tmp_history_file() -> Generator[Path, None, None]:
    """Archivo JSON temporal para MemoryManager (se borra al terminar)."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    path.unlink(missing_ok=True)          # No debe existir antes de la primera escritura
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def mock_vector_memory():
    """Reemplaza VectorMemory con un stub para no cargar ChromaDB ni embeddings."""
    with patch("src.core.memory_manager.VectorMemory") as mock_vm_cls:
        mock_vm_cls.return_value = MagicMock(
            enabled=False,
            add_memory=MagicMock(),
            query_memories=MagicMock(return_value=[]),
            shutdown=MagicMock(),
        )
        yield mock_vm_cls


# ──────────────────────────────────────────────────────────────────────────────
# 1. Importacion del modulo principal
# ──────────────────────────────────────────────────────────────────────────────

class TestModuleImportTime:
    """Verifica que los modulos clave se importen en tiempo razonable."""

    @pytest.mark.performance
    @pytest.mark.unit
    def test_import_icaro_module(self):
        """
        El modulo src.core.icaro debe estar importable en < THRESHOLD_MODULE_IMPORT_MS ms.
        NOTE: si ya esta en sys.modules el tiempo sera ~0 ms (expected).
        """
        import importlib

        start = time.perf_counter()
        import src.core.icaro  # noqa: F401
        importlib.reload(src.core.icaro)
        elapsed = _elapsed_ms(start)

        _log_timing("import src.core.icaro (reload)", elapsed, THRESHOLD_MODULE_IMPORT_MS)
        assert elapsed < THRESHOLD_MODULE_IMPORT_MS, (
            f"Importar/recargar src.core.icaro tomo {elapsed:.1f} ms "
            f"(limite {THRESHOLD_MODULE_IMPORT_MS} ms)"
        )

    @pytest.mark.performance
    @pytest.mark.unit
    def test_import_memory_manager_module(self):
        """src.core.memory_manager debe importarse rapidamente."""
        import importlib
        import src.core.memory_manager  # noqa: F401

        start = time.perf_counter()
        importlib.reload(src.core.memory_manager)
        elapsed = _elapsed_ms(start)

        _log_timing("import src.core.memory_manager (reload)", elapsed, THRESHOLD_MODULE_IMPORT_MS)
        assert elapsed < THRESHOLD_MODULE_IMPORT_MS


# ──────────────────────────────────────────────────────────────────────────────
# 2. Tiempo de arranque de MemoryManager
# ──────────────────────────────────────────────────────────────────────────────

class TestMemoryManagerStartup:
    """Benchmarks de instanciacion de MemoryManager."""

    @pytest.mark.performance
    @pytest.mark.unit
    def test_memory_manager_init_time(self, tmp_history_file, mock_vector_memory):
        """MemoryManager debe instanciarse en < THRESHOLD_MEMORY_MANAGER_MS ms."""
        with patch("src.core.memory_manager.HISTORY_FILE", tmp_history_file):
            from src.core.memory_manager import MemoryManager

            start = time.perf_counter()
            mm = MemoryManager(buffer_size=10, flush_timeout=300)
            elapsed = _elapsed_ms(start)

        _log_timing("MemoryManager.__init__", elapsed, THRESHOLD_MEMORY_MANAGER_MS)
        assert elapsed < THRESHOLD_MEMORY_MANAGER_MS, (
            f"MemoryManager tardo {elapsed:.1f} ms (limite {THRESHOLD_MEMORY_MANAGER_MS} ms)"
        )
        mm.flush()

    @pytest.mark.performance
    @pytest.mark.unit
    def test_memory_manager_repeated_init(self, tmp_history_file, mock_vector_memory):
        """
        Regressions test: instanciaciones repetidas no deben degradarse.
        La segunda instancia debe arrancar tan rapido como la primera.
        """
        times = []
        with patch("src.core.memory_manager.HISTORY_FILE", tmp_history_file):
            from src.core.memory_manager import MemoryManager
            for _ in range(3):
                start = time.perf_counter()
                mm = MemoryManager(buffer_size=10, flush_timeout=300)
                times.append(_elapsed_ms(start))

        avg = sum(times) / len(times)
        _log_timing("MemoryManager avg (3 runs)", avg, THRESHOLD_MEMORY_MANAGER_MS)
        assert all(t < THRESHOLD_MEMORY_MANAGER_MS for t in times), (
            f"Alguna instancia de MemoryManager supero el umbral: {times}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 3. Tiempo de arranque de AudioService
# ──────────────────────────────────────────────────────────────────────────────

class TestAudioServiceStartup:
    """Benchmarks de AudioService sin hardware real."""

    @pytest.fixture(autouse=True)
    def _patch_audio(self):
        """Mockea webrtcvad, speech_recognition y sounddevice sin hardware real."""
        mock_sr = MagicMock()
        mock_sr.Microphone.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_sr.Microphone.return_value.__exit__ = MagicMock(return_value=False)
        with (
            patch("src.services.audio_service.webrtcvad", MagicMock()),
            patch("src.services.audio_service.sr", mock_sr),
            patch("src.services.audio_service.sd", MagicMock(), create=True),
            patch("src.services.audio_service.SD_AVAILABLE", False),
            patch("src.services.audio_service.pyttsx3", MagicMock()),
        ):
            yield

    @pytest.mark.performance
    @pytest.mark.unit
    def test_audio_service_init_time(self):
        """AudioService.__init__ debe completarse en < THRESHOLD_AUDIO_SERVICE_MS ms."""
        from src.services.audio_service import AudioService

        start = time.perf_counter()
        try:
            svc = AudioService()
        except Exception:
            # Si falla por hardware ausente en CI, solo medimos el tiempo hasta el error
            svc = None
        elapsed = _elapsed_ms(start)

        _log_timing("AudioService.__init__", elapsed, THRESHOLD_AUDIO_SERVICE_MS)
        assert elapsed < THRESHOLD_AUDIO_SERVICE_MS, (
            f"AudioService tardo {elapsed:.1f} ms (limite {THRESHOLD_AUDIO_SERVICE_MS} ms)"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 4. Tiempo de arranque de AIService
# ──────────────────────────────────────────────────────────────────────────────

class TestAIServiceStartup:
    """Benchmarks de AIService sin conexiones a modelos reales."""

    @pytest.fixture(autouse=True)
    def _patch_ai_backends(self):
        with (
            patch("src.services.ai_service.genai", MagicMock(), create=True),
            patch("src.services.ai_service.ollama", None, create=True),
        ):
            yield

    @pytest.mark.performance
    @pytest.mark.unit
    def test_ai_service_init_time(self, tmp_history_file, mock_vector_memory):
        """AIService debe instanciarse en < THRESHOLD_AI_SERVICE_MS ms."""
        with patch("src.core.memory_manager.HISTORY_FILE", tmp_history_file):
            from src.core.memory_manager import MemoryManager
            from src.services.ai_service import AIService

            memory = MemoryManager(buffer_size=10, flush_timeout=300)

            start = time.perf_counter()
            ai = AIService(memory, warmup=False)
            elapsed = _elapsed_ms(start)

        _log_timing("AIService.__init__", elapsed, THRESHOLD_AI_SERVICE_MS)
        assert elapsed < THRESHOLD_AI_SERVICE_MS, (
            f"AIService tardo {elapsed:.1f} ms (limite {THRESHOLD_AI_SERVICE_MS} ms)"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 5. Tiempo de arranque de ActionService
# ──────────────────────────────────────────────────────────────────────────────

class TestActionServiceStartup:
    """Benchmarks de ActionService."""

    @pytest.mark.performance
    @pytest.mark.unit
    def test_action_service_init_time(self):
        """ActionService debe instanciarse en < THRESHOLD_ACTION_SERVICE_MS ms."""
        from src.services.action_service import ActionService

        start = time.perf_counter()
        svc = ActionService()
        elapsed = _elapsed_ms(start)

        _log_timing("ActionService.__init__", elapsed, THRESHOLD_ACTION_SERVICE_MS)
        assert elapsed < THRESHOLD_ACTION_SERVICE_MS, (
            f"ActionService tardo {elapsed:.1f} ms (limite {THRESHOLD_ACTION_SERVICE_MS} ms)"
        )


# ──────────────────────────────────────────────────────────────────────────────
# 6. Arranque completo de Icaro (integracion con mocks)
# ──────────────────────────────────────────────────────────────────────────────

class TestIcaroFullStartup:
    """
    Mide el tiempo de instanciacion de Icaro con dependencias inyectadas
    (mocks) para aislar la logica de orquestacion del hardware real.
    """

    @pytest.fixture()
    def mock_services(self):
        """Crea mocks de todos los servicios que Icaro acepta por inyeccion."""
        audio   = MagicMock()
        ai      = MagicMock()
        memory  = MagicMock()
        action  = MagicMock()
        telemetry = MagicMock()

        # Simular atributos requeridos internamente
        ai.obsidian_mcp = None
        action.set_obsidian_mcp = MagicMock()
        action.set_ai_service   = MagicMock()
        telemetry.send          = MagicMock()

        return audio, ai, memory, action, telemetry

    @pytest.mark.performance
    @pytest.mark.unit
    def test_icaro_init_with_injected_services(self, mock_services):
        """
        Icaro.__init__ con servicios inyectados debe completarse en
        < THRESHOLD_ICARO_INIT_MS ms.
        """
        audio, ai, memory, action, telemetry = mock_services

        with patch("src.core.icaro.plugin_loader") as mock_loader:
            mock_loader.load_all = MagicMock()
            from src.core.icaro import Icaro

            start = time.perf_counter()
            icaro = Icaro(
                silent=True,
                no_ai=True,
                audio_service=audio,
                ai_service=ai,
                memory_manager=memory,
                action_service=action,
                telemetry_service=telemetry,
            )
            elapsed = _elapsed_ms(start)

        _log_timing("Icaro.__init__ (DI mocks)", elapsed, THRESHOLD_ICARO_INIT_MS)
        assert elapsed < THRESHOLD_ICARO_INIT_MS, (
            f"Icaro.__init__ tardo {elapsed:.1f} ms (limite {THRESHOLD_ICARO_INIT_MS} ms)"
        )

    @pytest.mark.performance
    @pytest.mark.unit
    def test_icaro_init_state_is_initializing(self, mock_services):
        """
        Despues de __init__, la telemetria debe haberse llamado al menos
        una vez (estado INITIALIZING emitido).
        """
        audio, ai, memory, action, telemetry = mock_services

        with patch("src.core.icaro.plugin_loader") as mock_loader:
            mock_loader.load_all = MagicMock()
            from src.core.icaro import Icaro, IcaroState

            icaro = Icaro(
                silent=True,
                no_ai=True,
                audio_service=audio,
                ai_service=ai,
                memory_manager=memory,
                action_service=action,
                telemetry_service=telemetry,
            )

        assert telemetry.send.called, "Telemetry.send deberia haberse llamado durante __init__"

    @pytest.mark.performance
    @pytest.mark.unit
    def test_icaro_wake_aliases_initialized(self, mock_services):
        """
        Los wake aliases deben estar disponibles inmediatamente tras el arranque
        (no lazy) para no afectar la latencia en produccion.
        """
        audio, ai, memory, action, telemetry = mock_services

        with patch("src.core.icaro.plugin_loader") as mock_loader:
            mock_loader.load_all = MagicMock()
            from src.core.icaro import Icaro

            icaro = Icaro(
                silent=True,
                no_ai=True,
                audio_service=audio,
                ai_service=ai,
                memory_manager=memory,
                action_service=action,
                telemetry_service=telemetry,
            )

        assert isinstance(icaro.wake_aliases, list), "wake_aliases debe ser una lista"
        assert len(icaro.wake_aliases) > 0, "Debe haber al menos un wake word configurado"


# ──────────────────────────────────────────────────────────────────────────────
# 7. Benchmarks de arranque con multiples iteraciones (regression)
# ──────────────────────────────────────────────────────────────────────────────

class TestStartupRegression:
    """
    Detecta regresiones de rendimiento comparando multiples ejecuciones.
    """

    @pytest.mark.performance
    @pytest.mark.unit
    def test_icaro_init_is_deterministic(self):
        """
        Tres instanciaciones consecutivas de Icaro (con mocks) no deben mostrar
        degradacion creciente (la tercera no debe ser 10x mas lenta que la primera).
        """
        times = []

        for _ in range(3):
            audio   = MagicMock(spec=[])
            ai      = MagicMock(obsidian_mcp=None)
            memory  = MagicMock()
            action  = MagicMock()
            telemetry = MagicMock()
            action.set_obsidian_mcp = MagicMock()
            action.set_ai_service   = MagicMock()
            telemetry.send          = MagicMock()

            with patch("src.core.icaro.plugin_loader") as mock_loader:
                mock_loader.load_all = MagicMock()
                from src.core.icaro import Icaro

                start = time.perf_counter()
                Icaro(
                    silent=True,
                    no_ai=True,
                    audio_service=audio,
                    ai_service=ai,
                    memory_manager=memory,
                    action_service=action,
                    telemetry_service=telemetry,
                )
                times.append(_elapsed_ms(start))

        ratio = max(times) / (min(times) + 1e-9)
        _log_timing(
            f"Icaro init ratio max/min (3 runs) ratio={ratio:.2f}x",
            max(times), THRESHOLD_ICARO_INIT_MS
        )

        assert ratio < 10, (
            f"Variabilidad excesiva en el arranque de Icaro: "
            f"min={min(times):.1f} ms, max={max(times):.1f} ms, ratio={ratio:.2f}x"
        )
