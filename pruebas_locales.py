import os
import sys
import logging
from typing import List

# Configuración básica de logging
# Se establece el nivel INFO para ver la ejecución normal y los errores.
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Ajuste de rutas para asegurar que los módulos internos sean accesibles.
# Esto es crucial para la estructura de tu proyecto.
script_dir: str = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Importaciones de módulos internos de Ícaro.
# Se añade un manejo de errores explícito para una carga fallida.
try:
    from logica.memorias import CerebroIcaro
    from main.cerebro import Cerebro
except ImportError as e:
    logger.error(f"Error crítico al importar módulos de Ícaro: {e}. "
                 "Asegúrate de que 'logica' y 'main' estén correctamente estructurados y accesibles.")
    sys.exit(1) # Salir si no podemos cargar los componentes esenciales.

def simular_pruebas() -> None:
    """
    Simula una serie de comandos de voz para probar la nueva arquitectura
    del asistente Ícaro, incluyendo la carga de memoria y el procesamiento
    de comandos. Reporta el estado de cada paso utilizando logging.
    """
    logger.info("=== INICIANDO PRUEBAS DE LA NUEVA ARQUITECTURA ===")
    
    # 1. Instanciar memoria (CerebroIcaro inicializará Qwen2.5:3b)
    logger.info("\n[Paso 1] Cargando módulos de memoria e IA...")
    memoria: CerebroIcaro
    try:
        memoria = CerebroIcaro()
        if not memoria.ollama_habilitado:
             logger.error("Ollama no está detectado o no está en ejecución. "
                          "Asegúrate de ejecutar la app de Ollama para que Ícaro funcione correctamente.")
             return # Salir de la función si Ollama no está disponible.
    except Exception as e:
        logger.error(f"Fallo inesperado al inicializar CerebroIcaro: {e}")
        return # Salir en caso de cualquier error durante la inicialización.
         
    # 2. Instanciar Orquestador del Cerebro
    logger.info("[Paso 2] Cargando enrutador principal del cerebro...")
    cerebro: Cerebro
    try:
        cerebro = Cerebro(memoria)
    except Exception as e:
        logger.error(f"Fallo inesperado al inicializar el Orquestador del Cerebro: {e}")
        return # Salir en caso de error.
    
    # 3. Lista de comandos simulados (No requieren interacción con micrófono)
    comandos_prueba: List[str] = [
        "¿Qué hora es?",
        "Abre la calculadora",
        "Busca en internet tutoriales de python",
        "¿Cuál es la capital de Francia?" # Añadido para simular una consulta más compleja
    ]
    
    logger.info("\n=== EJECUTANDO COMANDOS SIMULADOS ===")
    for test_command in comandos_prueba:
        logger.info(f"\n=> Usuario dice: '{test_command}'")
        respuesta: str
        try:
            respuesta = cerebro.procesar_comando(test_command)
            logger.info(f"<= Ícaro responde: '{respuesta}'")
        except Exception as e:
            logger.error(f"Error al procesar el comando '{test_command}': {e}")
            
    logger.info("\n=== PRUEBAS FINALIZADAS CON ÉXITO ===")

if __name__ == "__main__":
    simular_pruebas()