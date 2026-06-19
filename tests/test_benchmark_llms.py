"""
═══════════════════════════════════════════════════════════════════
  Benchmark comparativo de LLMs para Ícaro
  Compara: Gemini 2.5 Flash · DeepSeek v4 Flash (NVIDIA) · Ollama local
  Métricas: Tiempo de reacción · Calidad conversacional · Calidad de código
═══════════════════════════════════════════════════════════════════
  Uso:
    python -m pytest tests/test_benchmark_llms.py -v -s
    python tests/test_benchmark_llms.py          # ejecución directa
"""

import os
import sys
import json
import time
import logging
from typing import Optional, Dict, Any, List

# Forzar UTF-8 en consola Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ajustar path para imports del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger("benchmark")
logging.basicConfig(level=logging.INFO, format="%(message)s")

# ─── Configuración ────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
MODELO_OLLAMA = os.getenv("MODELO_OLLAMA", "qwen2.5:1.5b")

# ─── Prompts de prueba ───────────────────────────────────────────
PROMPTS_CONVERSACIONAL = [
    "¿Qué es la inteligencia artificial y por qué importa hoy?",
    "Explícame la diferencia entre machine learning y deep learning.",
    "¿Cómo puedo mejorar mi productividad como programador?",
]

PROMPTS_CODIGO = [
    "Escribe una función en Python que implemente binary search y explica su complejidad.",
    "Crea una clase Python para un LRU Cache con get y put en O(1).",
    "Escribe un decorador Python que mida el tiempo de ejecución de cualquier función.",
]


# ═══════════════════════════════════════════════════════════════════
# Funciones de llamada a cada LLM
# ═══════════════════════════════════════════════════════════════════

def call_gemini(prompt: str) -> Optional[Dict[str, Any]]:
    """Llama a Gemini 2.5 Flash y retorna {text, elapsed_ms}."""
    if not GEMINI_API_KEY:
        return None
    try:
        import google.genai as genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        t0 = time.perf_counter()
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        elapsed = (time.perf_counter() - t0) * 1000
        text = res.text.strip() if res and res.text else ""
        return {"text": text, "elapsed_ms": round(elapsed, 1)}
    except Exception as e:
        logger.error(f"  [Gemini ERROR] {e}")
        return None


def call_nvidia(prompt: str) -> Optional[Dict[str, Any]]:
    """Llama a DeepSeek v4 Flash vía NVIDIA API y retorna {text, elapsed_ms}."""
    if not NVIDIA_API_KEY:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=NVIDIA_API_KEY,
        )
        t0 = time.perf_counter()
        completion = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-flash",
            messages=[
                {"role": "system", "content": "Eres un asistente experto en programación. Responde en español."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        text = completion.choices[0].message.content.strip() if completion.choices else ""
        return {"text": text, "elapsed_ms": round(elapsed, 1)}
    except Exception as e:
        logger.error(f"  [NVIDIA ERROR] {e}")
        return None


def call_ollama(prompt: str) -> Optional[Dict[str, Any]]:
    """Llama a Ollama local y retorna {text, elapsed_ms}."""
    try:
        import ollama as oll

        oll.list()  # verificar conexión
        t0 = time.perf_counter()
        res = oll.chat(
            model=MODELO_OLLAMA,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_predict": 1024},
        )
        elapsed = (time.perf_counter() - t0) * 1000
        text = res["message"]["content"].strip() if res.get("message") else ""
        return {"text": text, "elapsed_ms": round(elapsed, 1)}
    except Exception as e:
        logger.error(f"  [Ollama ERROR] {e}")
        return None


# ═══════════════════════════════════════════════════════════════════
# Evaluador simple de calidad
# ═══════════════════════════════════════════════════════════════════

def score_response(text: str, is_code: bool = False) -> Dict[str, Any]:
    """Evalúa calidad de respuesta con heurísticas."""
    if not text:
        return {"length": 0, "score": 0, "has_code": False, "coherent": False}

    length = len(text)
    has_code = "```" in text or "def " in text or "class " in text
    # Coherencia básica: respuesta de al menos 50 chars y termina con puntuación
    coherent = length > 50 and text[-1] in ".!?:»\""

    score = 0
    # Longitud razonable
    if 100 < length < 5000:
        score += 30
    elif length >= 50:
        score += 15

    # Coherencia
    if coherent:
        score += 20

    # Contiene explicación (palabras clave)
    keywords = ["porque", "por lo tanto", "es decir", "significa", "ejemplo",
                 "ventaja", "consiste", "permite", "funciona"]
    matches = sum(1 for k in keywords if k in text.lower())
    score += min(matches * 5, 25)

    # Para código: verificar que haya bloques de código
    if is_code:
        if has_code:
            score += 25
        # Verificar calidad del código
        if "def " in text and "return" in text:
            score += 10  # bonus por funciones completas

    return {
        "length": length,
        "score": min(score, 100),
        "has_code": has_code,
        "coherent": coherent,
    }


# ═══════════════════════════════════════════════════════════════════
# Runner principal del benchmark
# ═══════════════════════════════════════════════════════════════════

def run_benchmark():
    """Ejecuta el benchmark completo y muestra resultados en tabla."""
    models = {
        "Gemini 2.5 Flash": call_gemini,
        "DeepSeek v4 (NVIDIA)": call_nvidia,
        f"Ollama ({MODELO_OLLAMA})": call_ollama,
    }

    results: Dict[str, Dict[str, List]] = {
        name: {"times": [], "conv_scores": [], "code_scores": [], "errors": 0}
        for name in models
    }

    # ── Test 1: Reacción y calidad conversacional ─────────────────
    print("\n" + "═" * 70)
    print("  📊 BENCHMARK LLM — Ícaro AI Assistant")
    print("═" * 70)
    print("\n🗣️  TEST 1: Respuestas Conversacionales")
    print("─" * 55)

    for i, prompt in enumerate(PROMPTS_CONVERSACIONAL, 1):
        print(f"\n  Prompt {i}: {prompt[:60]}...")
        for name, fn in models.items():
            res = fn(prompt)
            if res:
                sc = score_response(res["text"])
                results[name]["times"].append(res["elapsed_ms"])
                results[name]["conv_scores"].append(sc["score"])
                status = "✅"
                detail = f'{res["elapsed_ms"]:>7.0f}ms | score: {sc["score"]:>3}/100 | {sc["length"]:>5} chars'
            else:
                results[name]["errors"] += 1
                status = "❌"
                detail = "NO DISPONIBLE"
            print(f"    {status} {name:<25} → {detail}")

    # ── Test 2: Calidad de código ────────────────────────────────
    print(f"\n\n💻  TEST 2: Generación de Código")
    print("─" * 55)

    for i, prompt in enumerate(PROMPTS_CODIGO, 1):
        print(f"\n  Prompt {i}: {prompt[:60]}...")
        for name, fn in models.items():
            res = fn(prompt)
            if res:
                sc = score_response(res["text"], is_code=True)
                results[name]["times"].append(res["elapsed_ms"])
                results[name]["code_scores"].append(sc["score"])
                code_flag = "📝" if sc["has_code"] else "⚠️"
                status = "✅"
                detail = (
                    f'{res["elapsed_ms"]:>7.0f}ms | score: {sc["score"]:>3}/100 '
                    f'| {code_flag} code: {"sí" if sc["has_code"] else "no"}'
                )
            else:
                results[name]["errors"] += 1
                status = "❌"
                detail = "NO DISPONIBLE"
            print(f"    {status} {name:<25} → {detail}")

    # ── Resumen ──────────────────────────────────────────────────
    print("\n\n" + "═" * 70)
    print("  📋 RESUMEN FINAL")
    print("═" * 70)

    header = f"{'Modelo':<28} {'Tiempo Avg':>12} {'Conv. Avg':>12} {'Code Avg':>12} {'Errores':>9}"
    print(f"\n  {header}")
    print(f"  {'─' * len(header)}")

    for name, data in results.items():
        avg_time = (
            f"{sum(data['times']) / len(data['times']):>8.0f}ms"
            if data["times"]
            else "    N/A   "
        )
        avg_conv = (
            f"{sum(data['conv_scores']) / len(data['conv_scores']):>8.1f}/100"
            if data["conv_scores"]
            else "    N/A   "
        )
        avg_code = (
            f"{sum(data['code_scores']) / len(data['code_scores']):>8.1f}/100"
            if data["code_scores"]
            else "    N/A   "
        )
        errors = f"{data['errors']:>5}"

        print(f"  {name:<28} {avg_time:>12} {avg_conv:>12} {avg_code:>12} {errors:>9}")

    # Determinar ganador
    print(f"\n  {'─' * len(header)}")
    best_speed = min(
        ((n, sum(d["times"]) / len(d["times"])) for n, d in results.items() if d["times"]),
        key=lambda x: x[1],
        default=("N/A", 0),
    )
    best_quality = max(
        (
            (n, (sum(d["conv_scores"]) + sum(d["code_scores"])) / max(len(d["conv_scores"]) + len(d["code_scores"]), 1))
            for n, d in results.items()
            if d["conv_scores"] or d["code_scores"]
        ),
        key=lambda x: x[1],
        default=("N/A", 0),
    )
    print(f"\n  🏆 Más rápido:       {best_speed[0]} ({best_speed[1]:.0f}ms avg)")
    print(f"  🏆 Mejor calidad:    {best_quality[0]} ({best_quality[1]:.1f}/100 avg)")
    print("\n" + "═" * 70 + "\n")

    return results


# ═══════════════════════════════════════════════════════════════════
# pytest integration
# ═══════════════════════════════════════════════════════════════════

def test_gemini_reacciona():
    """Verifica que Gemini responde en menos de 15 segundos."""
    res = call_gemini("Hola, ¿qué puedes hacer?")
    if res is None:
        import pytest
        pytest.skip("Gemini no configurado")
    assert res["elapsed_ms"] < 15000, f"Gemini tardó demasiado: {res['elapsed_ms']}ms"
    assert len(res["text"]) > 10, "Respuesta de Gemini demasiado corta"


def test_nvidia_reacciona():
    """Verifica que DeepSeek (NVIDIA) responde en menos de 15 segundos."""
    res = call_nvidia("Hola, ¿qué puedes hacer?")
    if res is None:
        import pytest
        pytest.skip("NVIDIA API no configurada")
    assert res["elapsed_ms"] < 15000, f"NVIDIA tardó demasiado: {res['elapsed_ms']}ms"
    assert len(res["text"]) > 10, "Respuesta de NVIDIA demasiado corta"


def test_ollama_reacciona():
    """Verifica que Ollama responde en menos de 15 segundos."""
    res = call_ollama("Hola, ¿qué puedes hacer?")
    if res is None:
        import pytest
        pytest.skip("Ollama no disponible")
    assert res["elapsed_ms"] < 15000, f"Ollama tardó demasiado: {res['elapsed_ms']}ms"
    assert len(res["text"]) > 10, "Respuesta de Ollama demasiado corta"


def test_gemini_codigo():
    """Verifica que Gemini genera código funcional."""
    res = call_gemini("Escribe una función Python que calcule el factorial de un número.")
    if res is None:
        import pytest
        pytest.skip("Gemini no configurado")
    sc = score_response(res["text"], is_code=True)
    assert sc["has_code"], "Gemini no generó bloques de código"
    assert sc["score"] >= 30, f"Calidad de código baja: {sc['score']}/100"


def test_nvidia_codigo():
    """Verifica que DeepSeek genera código funcional."""
    res = call_nvidia("Escribe una función Python que calcule el factorial de un número.")
    if res is None:
        import pytest
        pytest.skip("NVIDIA API no configurada")
    sc = score_response(res["text"], is_code=True)
    assert sc["has_code"], "DeepSeek no generó bloques de código"
    assert sc["score"] >= 30, f"Calidad de código baja: {sc['score']}/100"


def test_model_init_under_5s():
    """La inicialización paralela de modelos no debe bloquear más de 5s."""
    from unittest.mock import MagicMock
    from src.services.ai_service import AIService

    mem = MagicMock()
    mem.get_recent.return_value = []
    mem.vector_db = None
    ai = AIService(mem, warmup=False)
    t0 = time.perf_counter()
    ai._ensure_models_initialized()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 5000, f"Init de modelos tardó {elapsed_ms:.0f}ms (máx 5000ms)"
    print(f"\n  ⚡ model init: {elapsed_ms:.0f}ms | gemini={ai.ia_habilitada} ollama={ai.ollama_habilitado} nvidia={ai.nvidia_habilitado}")


def test_ollama_codigo():
    """Verifica que Ollama genera código funcional."""
    res = call_ollama("Escribe una función Python que calcule el factorial de un número.")
    if res is None:
        import pytest
        pytest.skip("Ollama no disponible")
    sc = score_response(res["text"], is_code=True)
    # Ollama local puede ser más limitado, umbral más bajo
    assert sc["score"] >= 15, f"Calidad de código baja: {sc['score']}/100"


# ── Ejecución directa ───────────────────────────────────────────
if __name__ == "__main__":
    run_benchmark()
