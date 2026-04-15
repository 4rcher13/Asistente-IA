---
name: Python & VS Code: Ingeniería de Software
description: Guía avanzada para programar en Python usando Visual Studio Code, enfocada en productividad, limpieza y estándares profesionales.
---

# 🚀 Python en VS Code: Guía de Ingeniería Superior

Esta Skill proporciona los pilares para transformar scripts en **Ingeniería de Software**. Mantén estos estándares para que Ícaro siga siendo un sistema robusto.

---

## 🏗️ 1. El Entorno de Desarrollo (Virtualización)

No instales librerías globales. Usa entornos virtuales para que Ícaro sea portable.

- **Comando de creación:** `python -m venv .venv`
- **Configuración de VS Code:** Presiona `Ctrl+Shift+P` y selecciona `Python: Select Interpreter` apuntando a `.venv`.
- **Requirements:** Mantén tu archivo `requirements.txt` actualizado con `pip freeze > requirements.txt`.

---

## 💎 2. Calidad de Código (Clean Code)

Ícaro debe leer código limpio, no un laberinto de lógica.

| Estándar | Herramienta | ¿Por qué? |
| :--- | :--- | :--- |
| **PEP 8** | `Ruff` o `Black` | Estilo consistente (Snake Case, espaciado). |
| **Tipado** | `Pylance` | Autocompletado inteligente y reducción de errores. |
| **Docstrings** | `Google Format` | Documentación legible para humanos e IAs. |

---

## 🛡️ 3. Manejo de Errores Profesional

Evita el `try...except Exception:`. Sé un cirujano del código.

- **Específicos:** Captura solo lo que esperas (`FileNotFoundError`, `ValueError`).
- **Resiliencia:** Usa bloques `finally` o context managers (`with`) para asegurar que el hardware o los archivos se liberen siempre.
- **DEBUG:** Usa puntos de interrupción (`F5`) en VS Code en lugar de llenar el código de `print()`.

---

## ⚡ 4. Extensiones Recomendadas (Premium Setup)

Instala estas extensiones para programar 10x más rápido:

- **Pylance:** El motor de inteligencia de Python definitivo.
- **Error Lens:** No busques el error, deja que el error aparezca en tu línea de código.
- **Python Debugger:** Para depuración en tiempo real.
- **Bracket Pair Colorizer:** Mejora la visibilidad de tu estructura.

---

## 📂 5. Estructura de Proyecto Sugerida

Sigue este patrón para cada nuevo módulo de Ícaro:

```text
Asistente IA/
├── core/         <-- Lógica pura (clases y funciones)
├── tests/        <-- Unit tests para validar cada módulo
├── data/         <-- Archivos de entrada/salida (JSON, CSV)
└── main.py       <-- Punto de entrada limpio
```
