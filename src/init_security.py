"""
Script para inicializar la seguridad de la aplicación.
Ejecutar en startup de la aplicación.
"""

import logging

from .config.settings import (
    ENVIRONMENT,
    DEBUG,
    LOG_LEVEL,
    SECRET_KEY,
    DB_HOST,
    DB_PORT,
    DB_NAME,
    validate_config,
)

logger = logging.getLogger(__name__)


def init_security() -> None:
    """Inicializa y valida la configuración de seguridad."""
    logging.basicConfig(level=LOG_LEVEL)

    try:
        validate_config()
        logger.info("Configuración validada exitosamente")
    except ValueError as e:
        logger.error(f"Error de configuración: {e}")
        raise

    logger.info(f"Ambiente: {ENVIRONMENT}")
    logger.info(f"Debug: {DEBUG}")
    logger.info(f"Base de datos: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    if DEBUG and ENVIRONMENT == "production":
        logger.warning("DEBUG está activado en PRODUCCIÓN - Desactivarlo inmediatamente")

    if SECRET_KEY.startswith("dev-"):
        logger.warning("Usando SECRET_KEY de desarrollo - Cambiar en producción")


if __name__ == "__main__":
    init_security()
    print("Inicialización de seguridad completada")
