import os
import sys
import json
import re
from pathlib import Path

# Configurar rutas para importar desde src
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from src.services.ai_service import AIService
    from src.services.action_service import ALLOWED_APPS
    from src.config.settings import GEMINI_API_KEY
except ImportError:
    print("Error: No se pudieron importar los módulos de Ícaro. Asegúrate de ejecutar el script desde la raíz o que la estructura sea correcta.")
    sys.exit(1)

import google.generativeai as genai

def extract_intents():
    """Extrae los intents válidos de AIService."""
    return list(AIService.INTENTS_VALIDOS)

def load_logs(limit=100):
    """Carga las últimas líneas de logs para contexto de errores."""
    log_path = ROOT_DIR / "src" / "logs" / "icaro.log"
    if not log_path.exists():
        return ""
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        return "".join(lines[-limit:])

def generate_samples(n_samples=50):
    """Usa Gemini para generar muestras sintéticas."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY no encontrada en .env")
        return []

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

    apps = ", ".join(ALLOWED_APPS.keys())
    intents = ", ".join(extract_intents())
    logs_context = load_logs(30)

    prompt = f"""
Eres un experto en ingeniería de datos para LLMs. Tu tarea es generar un dataset de entrenamiento para "Ícaro", un asistente virtual avanzado.

CONTEXTO DE ÍCARO:
- Personalidad: Técnico, amigable, experto programador, buen profesor (mentor), experto en IA y ciberseguridad.
- Apps Permitidas: {apps}
- Intents Soportados: {intents}
- Contexto de errores recientes:
{logs_context}

OBJETIVO:
Genera {n_samples} ejemplos de interacción en formato JSONL. Cada ejemplo debe tener:
1. "instruction": El sistema o contexto (opcional pero recomendado para ChatML).
2. "input": Lo que dice el usuario.
3. "output": La respuesta de Ícaro en formato JSON (como lo espera el sistema) y un texto amigable.

REGLAS DE SALIDA:
- El output debe ser un JSON que contenga: "intent", "target" y "respuesta".
- La "respuesta" debe reflejar la personalidad de Ícaro: amigable pero profesional, explicando brevemente si es necesario (estilo profesor).
- Incluye casos de:
  - Comandos directos (abrir apps, buscar en google).
  - Consultas técnicas (programación, seguridad).
  - Errores o confusiones (autodiagnóstico basado en logs).
  - Conversación amigable.

FORMATO REQUERIDO (JSONL):
{{"instruction": "...", "input": "...", "output": "{{\\"intent\\": \\"...\\", \\"target\\": \\"...\\", \\"respuesta\\": \\"...\\"}}"}}

Genera solo el contenido JSONL, una línea por ejemplo.
"""

    print(f"Generando {n_samples} muestras con Gemini...")
    response = model.generate_content(prompt)
    
    # Limpiar la respuesta de bloques de código markdown si los hay
    text = response.text.strip()
    if text.startswith("```json"):
        text = text.replace("```json", "").replace("```", "").strip()
    elif text.startswith("```"):
        text = text.replace("```", "").strip()
        
    return text.split("\n")

def save_dataset(samples):
    output_path = Path(__file__).parent / "dataset.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for sample in samples:
            if sample.strip():
                f.write(sample.strip() + "\n")
    print(f"Dataset guardado en: {output_path}")

if __name__ == "__main__":
    samples = generate_samples(n_samples=50) # Podemos subir este número
    if samples:
        save_dataset(samples)
