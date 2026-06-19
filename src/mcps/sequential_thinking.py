"""
SequentialThinkingMCP — Motor de razonamiento paso a paso para Ícaro.

Permite desglosar preguntas complejas en pasos lógicos antes de responder,
mejorando la coherencia y precisión en tareas de programación, ciberseguridad y análisis.
"""
import logging
from typing import List, Dict, Any, Optional

from ..core.shared_memory import log_event

logger = logging.getLogger(__name__)


class SequentialThinkingMCP:
    """
    MCP de razonamiento secuencial.
    Divide problemas complejos en una cadena de pensamientos (Chain of Thought).
    """

    MAX_STEPS = 10  # Evita bucles de razonamiento infinitos

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def record_step(self, thought: str, step: int, total_steps: int, is_revision: bool = False) -> None:
        """Registra un paso del proceso de razonamiento."""
        entry = {
            "step": step,
            "total": total_steps,
            "thought": thought,
            "is_revision": is_revision,
        }
        self._history.append(entry)
        tag = "[REVISIÓN]" if is_revision else f"[Paso {step}/{total_steps}]"
        logger.debug(f"[SequentialThinking] {tag}: {thought[:80]}...")
        
        # Registrar en memoria compartida
        event_type = "step_revision" if is_revision else "step_recorded"
        log_event("SequentialThinkingMCP", event_type, f"{tag}: {thought}")

    def get_chain_of_thought(self) -> str:
        """Retorna el razonamiento completo como texto formateado."""
        if not self._history:
            return ""
        lines = []
        for entry in self._history:
            prefix = "↺ Revisión" if entry["is_revision"] else f"→ Paso {entry['step']}"
            lines.append(f"{prefix}: {entry['thought']}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Limpia el historial de razonamiento (nueva sesión de pensamiento)."""
        if self._history:
            # Registrar resumen de la sesión completada
            summary = f"Sesión de razonamiento completada: {len(self._history)} pasos"
            if self.has_revisions:
                revision_count = sum(1 for e in self._history if e["is_revision"])
                summary += f" ({revision_count} revisiones)"
            log_event("SequentialThinkingMCP", "session_completed", summary)
        
        self._history.clear()

    @property
    def step_count(self) -> int:
        return len(self._history)

    @property
    def has_revisions(self) -> bool:
        return any(e["is_revision"] for e in self._history)
