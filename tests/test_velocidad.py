"""
Medición de tiempos de arranque y routing (API actual de Ícaro).

Ejecutar: python -m pytest tests/test_velocidad.py -v -s
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock
from src.services.ai_service import AIService


def medir_tiempos():
    print("=== ANÁLISIS DE RENDIMIENTO DE ÍCARO ===\n")

    mem = MagicMock()
    mem.get_recent.return_value = []
    mem.vector_db = None

    print("[1] Midiendo import + init AIService...")
    t0 = time.perf_counter()
    ai = AIService(mem, warmup=False)
    t_init = time.perf_counter() - t0
    print(f" -> Init AIService: {t_init:.2f}s\n")

    print("[2] Midiendo inicialización de modelos (Gemini/Ollama/NVIDIA)...")
    t0 = time.perf_counter()
    ai._ensure_models_initialized()
    t_models = time.perf_counter() - t0
    print(f" -> Modelos: {t_models:.2f}s (gemini={ai.ia_habilitada}, ollama={ai.ollama_habilitado}, nvidia={ai.nvidia_habilitado})\n")

    print("[3] Midiendo routing local (sin IA)...")
    ai.ia_habilitada = False
    ai.ollama_habilitado = False
    ai.nvidia_habilitado = False
    ai._models_initialized = True
    t0 = time.perf_counter()
    res = ai.route_command("qué hora es")
    t_local = time.perf_counter() - t0
    print(f" -> route_command local: {t_local*1000:.1f}ms | intent={res.get('intent')}\n")

    print("=== FIN DEL REPORTE ===")


if __name__ == "__main__":
    medir_tiempos()
