import threading
from typing import Dict, Any, Optional

_context_lock = threading.Lock()
_current_context: Optional[Dict[str, Any]] = None

def update_editor_context(context_data: Dict[str, Any]) -> None:
    """Actualiza el contexto actual del editor en VS Code de forma thread-safe."""
    global _current_context
    with _context_lock:
        _current_context = context_data

def get_editor_context() -> Optional[Dict[str, Any]]:
    """Obtiene el contexto actual del editor de forma thread-safe."""
    global _current_context
    with _context_lock:
        return _current_context
