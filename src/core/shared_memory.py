"""
Singleton compartido para acceso global a memoria desde todos los componentes.

Este módulo proporciona un punto de acceso único a MemoryManager desde cualquier
componente del sistema (MCPs, servicios, etc.), permitiendo que todos registren
eventos y tengan visibilidad de lo que ocurre en el sistema completo.
"""
import logging
import threading
from typing import Optional, Union

from .memory_manager import MemoryManager
from .protocols import MemoryProtocol

logger = logging.getLogger(__name__)

# Singleton global (inicializado una sola vez desde Icaro)
_shared_memory_instance: Optional[Union[MemoryManager, MemoryProtocol]] = None
_memory_lock = threading.Lock()


def set_shared_memory(manager: Union[MemoryManager, MemoryProtocol]) -> None:
    """
    Registra la instancia global de MemoryManager.
    
    Llamado una sola vez desde Icaro.__init__ después de crear MemoryManager.
    
    Args:
        manager: Instancia de MemoryManager a compartir globalmente.
    """
    global _shared_memory_instance
    with _memory_lock:
        _shared_memory_instance = manager
        logger.info("Memoria compartida registrada (shared_memory singleton)")


def get_shared_memory() -> Optional[Union[MemoryManager, MemoryProtocol]]:
    """
    Obtiene la instancia global de MemoryManager.
    
    Returns:
        La instancia compartida de MemoryManager, o None si aún no está inicializada.
    """
    with _memory_lock:
        return _shared_memory_instance


def log_event(source: str, event_type: str, content: str) -> None:
    """
    Registra un evento del sistema en la memoria compartida de forma no-bloqueante.
    
    El evento se guarda en el historial con rol="system" para distinguirlo de
    user/model, y también en VectorMemory con metadata intent=event_type para
    recuperación semántica RAG.
    
    Esta función es no-bloqueante (fire-and-forget): se ejecuta en un thread
    separado para no afectar la latencia del pipeline de respuesta.
    
    Args:
        source: Componente que genera el evento (ej: "ActionService", "SequentialThinkingMCP")
        event_type: Tipo de evento (ej: "action_executed", "step_recorded")
        content: Contenido descriptivo del evento.
    
    Example:
        >>> log_event("ActionService", "open_app", "Abrió aplicación: chrome")
        >>> log_event("SequentialThinkingMCP", "step_recorded", "Paso 1/5: Analizar problema")
    """
    def _log_async() -> None:
        memory = get_shared_memory()
        if memory is None:
            logger.warning(f"shared_memory no inicializada. Evento perdido: {source}|{event_type}")
            return
        
        try:
            # Formato: [source|event_type] content
            full_message = f"[{source}|{event_type}] {content}"
            memory.guardar_evento(source, event_type, full_message)
        except Exception as e:
            logger.error(f"Error registrando evento {source}|{event_type}: {e}")
    
    # Ejecutar en thread separado para no bloquear
    thread = threading.Thread(target=_log_async, daemon=True)
    thread.start()
