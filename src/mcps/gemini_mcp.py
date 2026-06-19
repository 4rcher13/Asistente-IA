"""
GeminiMCP — Conector al servidor MCP oficial de documentación de Gemini.
Servidor público: https://gemini-api-docs-mcp.dev

Permite a Ícaro recuperar información actualizada sobre la API de Gemini
en tiempo real, sin depender de datos de entrenamiento desactualizados.
"""
import logging
from typing import Optional

from ..core.shared_memory import log_event

logger = logging.getLogger(__name__)

# Importación opcional de requests para no bloquear el inicio si no está instalado
try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    logger.warning("[GeminiMCP] 'requests' no instalado. MCP desactivado.")


class GeminiMCP:
    """
    Cliente para el MCP de Documentación de Gemini.
    Conecta con https://gemini-api-docs-mcp.dev para documentación en tiempo real.
    """

    MCP_BASE_URL = "https://gemini-api-docs-mcp.dev"
    TIMEOUT_S = 5  # Timeout bajo para no bloquear el pipeline de respuesta

    def __init__(self):
        self.enabled = _REQUESTS_AVAILABLE

    def search_documentation(self, query: str) -> Optional[str]:
        """
        Busca en la documentación oficial de Gemini.
        Retorna texto relevante o None si falla / no está disponible.
        """
        if not self.enabled or not query:
            return None

        try:
            # Endpoint de búsqueda del servidor MCP público
            response = requests.get(
                f"{self.MCP_BASE_URL}/search",
                params={"q": query},
                timeout=self.TIMEOUT_S,
            )
            if response.ok:
                data = response.json()
                # El servidor devuelve una lista de fragmentos relevantes
                snippets = data.get("snippets", [])
                if snippets:
                    # Registrar en memoria compartida
                    log_event("GeminiMCP", "docs_searched", f"Búsqueda: '{query}' - {len(snippets)} fragmentos encontrados")
                    return "\n".join(snippets[:2])  # Máximo 2 fragmentos para no saturar el contexto
                else:
                    log_event("GeminiMCP", "docs_searched", f"Búsqueda: '{query}' - sin fragmentos")
            return None
        except requests.exceptions.Timeout:
            logger.debug("[GeminiMCP] Timeout al consultar documentación.")
            log_event("GeminiMCP", "docs_search_error", f"Timeout buscando: '{query}'")
            return None
        except Exception as e:
            logger.debug(f"[GeminiMCP] Error: {e}")
            log_event("GeminiMCP", "docs_search_error", f"Error buscando '{query}': {str(e)}")
            return None
