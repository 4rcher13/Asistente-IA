import logging
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Vocabulario canónico de intents locales reconocibles por fonética
_INTENT_KEYWORDS = [
    "hora", "fecha", "calculadora", "notepad", "código", "abrir",
    "cerrar", "buscar", "youtube", "volumen", "subir", "bajar",
    "salir", "apagar", "suspender", "carpeta", "copiar", "pegar",
]

class CommandProcessor:
    """
    Router principal de la lógica.
    Pipeline unidireccional: normalizar → enrutar → ejecutar → responder
    """
    
    def __init__(self, ai_service, action_service):
        self.ai = ai_service
        self.action = action_service

    def process(self, comando: str) -> str:
        """Procesa un comando completo siguiendo el pipeline de 4 etapas."""
        # Etapa 1: Normalizar (limpia, corrige fonética)
        clean = self._normalize(comando)
        
        # Etapa 2: Enrutar (IA decidir intención)
        intent_data = self._route(clean)
        
        # Etapa 3: Ejecutar acción si aplica
        respuesta = self._execute(intent_data)
        
        # Etapa 4: Postprocesar (retornar texto final para el audio)
        return respuesta

    def _normalize(self, text: str) -> str:
        """
        Limpia el texto crudo del reconocedor.
        Aplica corrección fonética básica via difflib para errores de voz comunes.
        """
        text = text.lower().strip()
        words = text.split()
        corrected = []
        for word in words:
            matches = get_close_matches(word, _INTENT_KEYWORDS, n=1, cutoff=0.75)
            corrected.append(matches[0] if matches else word)
        result = " ".join(corrected)
        if result != text:
            logger.debug(f"Corrección fonética: '{text}' → '{result}'")
        return result

    def _route(self, clean: str) -> dict:
        """Delega a la IA para clasificar la intención del comando."""
        return self.ai.route_command(clean)

    def _execute(self, intent_data: dict) -> str:
        """Ejecuta la acción del sistema operativo si hay intent, devuelve la respuesta hablada."""
        respuesta_hablada = intent_data.get("respuesta", "Entendido.")
        
        if intent_data.get("intent"):
            resultado_accion = self.action.execute(intent_data)
            # Comandos como hora/fecha, el resultado de la acción ES la respuesta
            if intent_data.get("intent") in ("dar_hora_fecha",):
                return resultado_accion
            if resultado_accion:
                logger.info(f"Sistema: {resultado_accion}")
                
        return respuesta_hablada

