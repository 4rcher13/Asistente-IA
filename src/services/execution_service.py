import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ExecutionService:
    """
    Servicio encargado de ejecutar secuencialmente un plan de tareas
    generado por el TaskPlanner.
    """

    def __init__(self, action_service, audio_service=None):
        self.action_service = action_service
        self.audio_service = audio_service

    def execute_plan(self, steps: List[Dict[str, Any]]) -> str:
        """
        Itera sobre cada paso del plan y lo ejecuta usando el ActionService.
        Devuelve un resumen final o el resultado de la última acción importante.
        """
        if not steps:
            return "No se pudo generar un plan válido para esta solicitud."

        logger.info(f"ExecutionService: Iniciando ejecución de {len(steps)} pasos.")
        
        resultados = []
        
        for index, step in enumerate(steps):
            intent = step.get("intent")
            target = step.get("target", "")
            
            logger.info(f"Ejecutando paso {index + 1}/{len(steps)}: Intent='{intent}', Target='{target}'")
            
            if not intent:
                logger.warning(f"Paso {index + 1} ignorado porque no tiene intent.")
                continue

            # Creamos el formato de intent_data que espera action_service.execute()
            intent_data = {
                "intent": intent,
                "target": target
            }

            try:
                # Ejecutar acción sincrónicamente
                resultado_accion = self.action_service.execute(intent_data)
                
                # Guardamos el resultado si no es nulo/vacío
                if resultado_accion and not resultado_accion.startswith("Acción desconocida"):
                    resultados.append(resultado_accion)
                    logger.info(f"Resultado paso {index + 1}: {resultado_accion}")
                else:
                    logger.debug(f"Paso {index + 1} no retornó un resultado útil.")
                    
            except Exception as e:
                error_msg = f"Error ejecutando paso '{intent}': {str(e)}"
                logger.error(error_msg)
                resultados.append(error_msg)
                # Decisión: Por ahora continuamos con el siguiente paso en caso de error, 
                # a menos que queramos abortar el plan completo.

        logger.info("ExecutionService: Plan completado.")
        
        # Consolidar respuesta
        if resultados:
            # Si hay múltiples resultados, podríamos concatenarlos o dejar que Ícaro los lea.
            # Como la ejecución es bloqueante, devolveremos un resumen de las acciones.
            if len(resultados) == 1:
                return resultados[0]
            else:
                return "He completado las tareas solicitadas. " + ". ".join(resultados)
        else:
            return "He finalizado el plan, pero no hubo resultados visibles."
