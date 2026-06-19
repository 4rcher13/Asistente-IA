"""
GitHubMCP — Conector a la API de GitHub para Ícaro.

Permite leer archivos, listar repositorios y buscar código.
Configura tu token en el .env: GITHUB_TOKEN=ghp_xxxxxxxxxxxx

Permisos mínimos del token (classic): repo:read o public_repo
"""
import logging
import base64
from typing import Optional, List, Dict, Any

from ..core.shared_memory import log_event

logger = logging.getLogger(__name__)

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    logger.warning("[GitHubMCP] 'requests' no instalado. GitHub MCP desactivado.")


class GitHubMCP:
    """
    Cliente para la API REST de GitHub v3.
    Operaciones de solo lectura por defecto; escritura disponible con scopes adicionales.
    """

    API_BASE = "https://api.github.com"
    TIMEOUT_S = 8

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.enabled = _REQUESTS_AVAILABLE and token is not None
        self._session: Optional[requests.Session] = None

        if self.enabled:
            # Reutilizar sesión HTTP para evitar overhead de TCP por cada llamada
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Icaro-Assistant/1.0",
            })
            logger.info("[GitHubMCP] Activo con token configurado.")
        else:
            logger.warning(
                "[GitHubMCP] Desactivado. "
                "Configura GITHUB_TOKEN en tu .env para activarlo."
            )

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Llamada GET genérica con manejo de errores."""
        if not self.enabled or not self._session:
            return None
        try:
            resp = self._session.get(
                f"{self.API_BASE}{endpoint}",
                params=params,
                timeout=self.TIMEOUT_S
            )
            if resp.ok:
                return resp.json()
            logger.debug(f"[GitHubMCP] HTTP {resp.status_code} para {endpoint}")
            return None
        except requests.exceptions.Timeout:
            logger.debug(f"[GitHubMCP] Timeout en {endpoint}")
            return None
        except Exception as e:
            logger.debug(f"[GitHubMCP] Error: {e}")
            return None

    def list_repos(self, username: Optional[str] = None) -> List[str]:
        """Lista los repositorios del usuario autenticado o de un usuario específico."""
        endpoint = f"/users/{username}/repos" if username else "/user/repos"
        data = self._get(endpoint, params={"per_page": 10, "sort": "updated"})
        if not data:
            return []
        return [r.get("full_name", "") for r in data if isinstance(r, dict)]

    def read_file(self, owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
        """
        Lee el contenido de un archivo de un repositorio.
        Retorna el texto decodificado o None si no se puede leer.
        """
        data = self._get(f"/repos/{owner}/{repo}/contents/{path}", params={"ref": branch})
        if not data or data.get("encoding") != "base64":
            return None
        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
            # Registrar en memoria compartida
            log_event("GitHubMCP", "file_read", f"Archivo leído: {owner}/{repo}/{path}")
            return content
        except Exception as e:
            logger.debug(f"[GitHubMCP] Error decodificando {path}: {e}")
            log_event("GitHubMCP", "file_read_error", f"Error leyendo {owner}/{repo}/{path}: {str(e)}")
            return None

    def get_repo_tree(self, owner: str, repo: str, branch: str = "main") -> List[str]:
        """Lista todos los archivos de un repositorio (útil para dar contexto a Ícaro)."""
        data = self._get(
            f"/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"}
        )
        if not data:
            return []
        return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]

    def search_code(self, query: str, owner: Optional[str] = None) -> Optional[str]:
        """Busca código en GitHub (requiere token con scope 'repo')."""
        q = f"{query}+user:{owner}" if owner else query
        data = self._get("/search/code", params={"q": q, "per_page": 3})
        if not data or not data.get("items"):
            log_event("GitHubMCP", "search_code", f"Búsqueda: '{query}' - sin resultados")
            return None
        results = []
        for item in data["items"]:
            results.append(f"- [{item['repository']['full_name']}] {item['path']}")
        
        # Registrar en memoria compartida
        log_event("GitHubMCP", "search_code", f"Búsqueda: '{query}' - {len(results)} resultados")
        
        return "Código encontrado en GitHub:\n" + "\n".join(results)
