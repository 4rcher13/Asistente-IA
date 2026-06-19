import logging
import json
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TaskPlanner:
    """
    Planificador de tareas múltiples.
    Recibe un comando complejo, utiliza el modelo Gemini para dividirlo 
    en una secuencia de pasos lógicos.
    """

    def __init__(self, ai_service):
        self.ai = ai_service

    def create_plan(self, command: str) -> List[Dict[str, Any]]:
        """
        Pide a Gemini que divida el comando en pasos ordenados.
        Retorna una lista de pasos, donde cada paso es un dict con 'intent' y opcionalmente 'target'.
        Si ocurre un error o el plan no se puede generar, retorna una lista vacía.
        """
        logger.info(f"TaskPlanner generando plan para: '{command}'")
        
        # Validamos que Gemini esté inicializado
        if not self.ai.ia_habilitada or not self.ai.client:
            logger.warning("Gemini no está habilitado, no se puede generar el plan.")
            return []

        from google.genai import types

        intents_validos = [i for i in self.ai.INTENTS_VALIDOS if i != "plan_task"]
        intents_str = ", ".join(intents_validos)
        
        prompt = f"""\
Eres el Task Planner de Ícaro. Tu único trabajo es recibir una instrucción del usuario 
y dividirla en una lista secuencial de pasos para que el sistema los ejecute.

Intents válidos para los pasos: {intents_str}

Reglas:
1. Responde ÚNICAMENTE con un JSON válido. No uses markdown de código (` ```json `), solo texto en crudo.
2. El JSON debe contener una única clave "steps" que es una lista.
3. Cada elemento de la lista debe tener la estructura: {{"intent": "nombre_intent", "target": "parametro"}}.
4. Si un paso no requiere "target", ponlo como una cadena vacía "".
5. No intentes responder al usuario, solo divide la tarea en acciones del sistema.

Comando del usuario: "{command}"
JSON:"""

        try:
            res = self.ai.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="Eres Ícaro Task Planner. Responde SIEMPRE en formato JSON.",
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            texto_generado = res.text.strip() if res.text else ""
            if not texto_generado:
                logger.warning("Respuesta vacía de Gemini en TaskPlanner.")
                return []

            datos = self.ai._extraer_json(texto_generado)
            if datos and "steps" in datos and isinstance(datos["steps"], list):
                logger.info(f"Plan generado exitosamente: {datos['steps']}")
                return datos["steps"]
            else:
                logger.warning(f"Formato JSON inesperado del Planner: {texto_generado}")
                return []
                
        except Exception as exc:
            logger.error(f"Error en TaskPlanner al llamar a Gemini: {exc}")
            return []
