---
name: Desarrollo de Ícaro (Manual Maestro V3)
description: Guía de arquitectura, estilo JARVIS y reglas de oro para expandir el ecosistema Ícaro.
---

# Proyecto Ícaro: Manual de Desarrollo V3

Ícaro es un asistente de voz avanzado con personalidad de J.A.R.V.I.S. desarrollado para Windows.
Usa un cerebro híbrido: Motor Local (Qwen 1.5B via Ollama) para tareas rápidas y Motor Nube (Gemini 2.5 Flash) para razonamiento profundo.

## Arquitectura del Sistema (V3)

| Componente | Ruta | Función |
| :--- | :--- | :--- |
| Núcleo | asistente_voz.py | Orquestador principal con tabla de enrutamiento declarativa. |
| Cerebro | logica/memorias.py | IA híbrida (Qwen Local + Gemini Nube), memoria de 3 capas. |
| Plugins | logica/plugins.py | Capacidades externas (WhatsApp, etc.). |
| Perfil | logica/perfil.json | Memoria permanente del usuario (nunca se borra). |
| Interfaz | ui/widget.py + widget.html + style.css | Orbe Web animado vía PyWebView con telemetría UDP. |
| Memoria | data/historial.json | Persistencia dinámica con filtrado de basura. |
| Skills | __skillsIA__/ | Base de conocimiento interna inyectada al arrancar. |
| Utils | herramientas/ | Scripts de diagnóstico y benchmarks. |

## Reglas de Oro

1. Salidas de Voz (TTS): Cero emojis, cero markdown, cero viñetas. Texto natural para oído humano. Máximo 3-4 oraciones.
2. Personalidad: Leal, ingenioso, analítico, sarcástico. Usa analogías de programación. Trata a Chucho con respeto y confianza.
3. Plugins: Cada plugin aislado con try/except. Errores reportados con elegancia, no con códigos técnicos crudos.
4. Prioridad de IA: Qwen Local para TODO por defecto. Gemini solo cuando el usuario diga "usa Gemini".
5. Skills: Cada carpeta en __skillsIA__/ contiene un SKILL.md que se carga automáticamente al arrancar.

## Ciclo de Vida de Comandos

1. Escucha: El núcleo detecta "Icaro" (Wake Word con alias fonéticos).
2. Enrutamiento: La tabla declarativa busca el primer detector que coincida.
3. Inferencia: Si no hay comando local, se consulta a Qwen (o Gemini si se pide).
4. Respuesta: Se limpia de markdown, se guarda en historial (si no es desechable) y se sintetiza por voz.
