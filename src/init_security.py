"""
Script para inicializar la seguridad de la aplicación
Ejecutar en startup de la aplicación
"""

import logging
from .config import config

logger = logging.getLogger(__name__)

def init_security():
    """Inicializa configuración de seguridad"""
    
    logging.basicConfig(level=config.LOG_LEVEL)
    
    # Validar configuración
    try:
        config.validate()
        logger.info("Configuración validada exitosamente")
    except ValueError as e:
        logger.error(f"Error de configuración: {e}")
        raise
    
    # Log información (sin secretos)
    logger.info(f"Ambiente: {config.ENVIRONMENT}")
    logger.info(f"Debug: {config.DEBUG}")
    logger.info(f"Base de datos: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    
    # Advertencias de seguridad
    if config.DEBUG and config.ENVIRONMENT == "production":
        logger.warning("DEBUG está activado en PRODUCCIÓN - Desactivarlo inmediatamente")
    
    if config.SECRET_KEY.startswith("dev-"):
        logger.warning("Usando SECRET_KEY de desarrollo - Cambiar en producción")

if __name__ == "__main__":
    init_security()
    print("Inicialización de seguridad completada")
