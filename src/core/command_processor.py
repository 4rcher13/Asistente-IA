import logging

logger = logging.getLogger(__name__)

class CommandProcessor:
    """
    Enrutador principal de la lógica.
    Actúa como puente unidireccional entre la IA que decide y el servicio que ejecuta.
    """
    
    def __init__(self, ai_service, action_service):
        self.ai = ai_service
        self.action = action_service

    def process(self, comando: str) -> str:
        """Procesa un comando del usuario completo de inicio a fin."""
        # 1. IA decide qué hacer (Intención)
        intent_data = self.ai.route_command(comando)
        respuesta_hablada = intent_data.get("respuesta", "Entendido.")
        
        # 2. Si hay una intención clara para el sistema operativo
        if intent_data.get("intent"):
            resultado_accion = self.action.execute(intent_data)
            # En ciertos comandos como hora/fecha, el resultado ES lo que hay que decir
            if intent_data.get("intent") in ("dar_hora_fecha",):
                return resultado_accion
                
            # Log interno del resultado real
            if resultado_accion:
                logger.info(f"Sistema: {resultado_accion}")
                
        # 3. Retornar la respuesta natural formulada por la IA
        return respuesta_hablada
