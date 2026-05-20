import logging
import threading
from typing import Callable, Dict, List, Any
from enum import Enum, auto

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Tipos de eventos estándar en el sistema Ícaro."""
    # Audio / STT
    SPEECH_STARTED = auto()     # Detectó que el usuario empezó a hablar
    SPEECH_DETECTED = auto()    # Audio transcrito a texto
    
    # Brain / AI
    INTENT_ROUTED = auto()      # La IA clasificó la intención
    THINKING_STARTED = auto()   # Iniciando llamada a LLM
    
    # Actions
    ACTION_STARTED = auto()     # Iniciando ejecución de comando OS
    ACTION_COMPLETED = auto()   # Comando terminado
    
    # Output / TTS
    RESPONSE_READY = auto()     # Hay un texto listo para ser hablado
    SPEAKING_STARTED = auto()   # El TTS empezó a reproducir
    SPEAKING_FINISHED = auto()  # El TTS terminó
    
    # System
    STATE_CHANGED = auto()      # Cambio en la máquina de estados
    ERROR_OCCURRED = auto()     # Error en algún subsistema
    SHUTDOWN = auto()           # Señal de apagado

class EventBus:
    """
    Bus de eventos centralizado (Singleton).
    Permite comunicación desacoplada entre componentes.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._listeners: Dict[EventType, List[Callable]] = {}
        return cls._instance

    def subscribe(self, event_type: EventType, listener: Callable[[Any], None]):
        """Suscribe un callback a un tipo de evento."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            logger.debug(f"Subscripción: {listener.__name__} a {event_type.name}")

    def publish(self, event_type: EventType, data: Any = None):
        """Publica un evento a todos los suscriptores (de forma síncrona)."""
        if event_type not in self._listeners:
            return

        logger.debug(f"Evento: {event_type.name} | Data: {str(data)[:100]}")
        
        # Iteramos sobre una copia para evitar errores si un listener se desuscribe durante la ejecución
        for listener in self._listeners[event_type][:]:
            try:
                # Se podría usar threading.Thread aquí si queremos que sea asíncrono por defecto,
                # pero por ahora lo dejamos síncrono para trazabilidad simple.
                listener(data)
            except Exception as e:
                logger.error(f"Error en listener {listener.__name__} para {event_type.name}: {e}")

# Instancia global para facilitar el acceso
bus = EventBus()
