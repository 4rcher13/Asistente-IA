import os
import importlib.util
import logging
from pathlib import Path
from typing import List, Dict, Any, Type

logger = logging.getLogger(__name__)

class BasePlugin:
    """Clase base que todos los plugins Python deben heredar."""
    name = "UnnamedPlugin"
    
    def initialize(self):
        pass

    def execute(self, context: Dict[str, Any]) -> str:
        return ""

class PluginLoader:
    """
    Cargador híbrido de habilidades (Skills).
    Carga lógica ejecutable desde archivos .py y contexto desde archivos .md.
    """
    
    def __init__(self, skills_dir: str = "__skillsIA__"):
        # Usar la ruta del proyecto raíz (relativa a este archivo) para evitar
        # errores cuando se ejecuta desde un directorio diferente al del proyecto.
        _project_root = Path(__file__).resolve().parent.parent.parent
        self.skills_dir = str(_project_root / skills_dir)
        self.plugins: Dict[str, BasePlugin] = {}
        self.semantic_knowledge: List[str] = []
        
    def load_all(self):
        """Escanea el directorio y carga scripts y markdown."""
        if not os.path.exists(self.skills_dir):
            logger.debug("Directorio de skills '%s' no existe; omitiendo carga.", self.skills_dir)
            return

        logger.info(f"Escaneando skills en {self.skills_dir}...")
        
        # Escanear todos los subdirectorios
        for root, dirs, files in os.walk(self.skills_dir):
            for file in files:
                filepath = os.path.join(root, file)
                
                if file.endswith(".py") and not file.startswith("__"):
                    self._load_python_plugin(filepath)
                elif file.endswith(".md"):
                    self._load_markdown_context(filepath)
                    
        logger.info(f"Skills cargadas: {len(self.plugins)} plugins ejecutables, {len(self.semantic_knowledge)} contextos semánticos.")

    def _load_python_plugin(self, filepath: str):
        """Carga un script Python dinámicamente."""
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Buscar clases que hereden de BasePlugin
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                        plugin_instance = attr()
                        plugin_instance.initialize()
                        self.plugins[plugin_instance.name] = plugin_instance
                        logger.debug(f"Plugin Python cargado: {plugin_instance.name}")
        except Exception as e:
            logger.error(f"Error cargando plugin desde {filepath}: {e}")

    def _load_markdown_context(self, filepath: str):
        """Lee un archivo Markdown para inyectarlo como conocimiento base."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    # Guardamos el nombre del archivo y su contenido
                    skill_name = os.path.basename(os.path.dirname(filepath))
                    if not skill_name or skill_name == "__skillsIA__":
                        skill_name = os.path.basename(filepath)
                        
                    context_entry = f"--- Skill Context: {skill_name} ---\n{content}\n"
                    self.semantic_knowledge.append(context_entry)
                    logger.debug(f"Contexto Markdown cargado desde: {skill_name}")
        except Exception as e:
            logger.error(f"Error leyendo contexto desde {filepath}: {e}")

    def get_context_injection(self) -> str:
        """Devuelve todo el conocimiento Markdown como un solo bloque de texto para el System Prompt."""
        if not self.semantic_knowledge:
            return ""
        return "\n".join(self.semantic_knowledge) + "\n"

# Instancia global (singleton pattern)
plugin_loader = PluginLoader()
