"""
ObsidianMCP — Conector al vault de Obsidian del usuario.

Permite a Ícaro leer y buscar en tus notas de ciberseguridad, programación e IA.
Configura la ruta en tu .env: OBSIDIAN_VAULT_PATH=C:/Users/Jesus/Documents/ObsidianVault
"""
import os
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class ObsidianMCP:
    """
    Conector para bóvedas de Obsidian (archivos .md).
    Permite a Ícaro buscar fragmentos relevantes y guardar nuevo conocimiento.
    """

    MAX_SNIPPET_CHARS = 400   # Caracteres por fragmento en los resultados
    MAX_RESULTS = 3           # Máximo de notas retornadas por búsqueda

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = Path(vault_path) if vault_path else None
        self.enabled = self.vault_path is not None and self.vault_path.exists()

        if self.enabled:
            logger.info(f"[ObsidianMCP] Bóveda cargada: {self.vault_path}")
        else:
            logger.warning(
                "[ObsidianMCP] Desactivado. "
                "Configura OBSIDIAN_VAULT_PATH en tu .env para activarlo."
            )

    def _iter_notes(self, category: Optional[str] = None):
        """Generador que itera sobre archivos .md del vault."""
        if not self.enabled:
            return
        search_dir = self.vault_path / category if category else self.vault_path
        if not search_dir.exists():
            return
        for md_file in search_dir.rglob("*.md"):
            # Excluir carpetas de sistema de Obsidian
            if ".obsidian" not in str(md_file):
                yield md_file

    def search_notes(self, query: str, category: Optional[str] = None) -> Optional[str]:
        """
        Busca notas relevantes en el vault.
        Retorna un string con los fragmentos más relevantes, o None si no hay resultados.
        """
        if not self.enabled or not query:
            return None

        query_lower = query.lower()
        results: List[str] = []

        for note_path in self._iter_notes(category):
            try:
                content = note_path.read_text(encoding="utf-8", errors="ignore")
                # Búsqueda simple pero efectiva: nombre del archivo y contenido
                name_match = query_lower in note_path.stem.lower()
                content_match = query_lower in content.lower()

                if name_match or content_match:
                    # Extraer el fragmento más relevante
                    rel_path = note_path.relative_to(self.vault_path)
                    snippet = content[:self.MAX_SNIPPET_CHARS].replace("\n", " ").strip()
                    results.append(f"📄 [{rel_path}]: {snippet}...")

                    if len(results) >= self.MAX_RESULTS:
                        break
            except Exception as e:
                logger.debug(f"[ObsidianMCP] Error leyendo {note_path}: {e}")

        return "Notas de Obsidian relevantes:\n" + "\n".join(results)

    def create_or_append_note(self, title: str, content: str, folder: str = "Icaro_Knowledge") -> bool:
        """
        Crea una nota nueva o añade contenido a una existente.
        """
        if not self.enabled:
            return False

        try:
            # Asegurar que el título termine en .md
            filename = title if title.endswith(".md") else f"{title}.md"
            
            # Crear la carpeta si no existe
            target_dir = self.vault_path / folder
            target_dir.mkdir(parents=True, exist_ok=True)
            
            note_path = target_dir / filename
            
            mode = "a" if note_path.exists() else "w"
            with open(note_path, mode, encoding="utf-8") as f:
                if mode == "a":
                    f.write("\n\n--- Actualización ---\n")
                f.write(content)
            
            logger.info(f"[ObsidianMCP] Nota {'actualizada' if mode == 'a' else 'creada'}: {note_path}")
            return True
        except Exception as e:
            logger.error(f"[ObsidianMCP] Fallo al escribir nota: {e}")
            return False
