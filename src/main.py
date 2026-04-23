import sys
import logging

from src.config.settings import LOG_DIR, LOG_FILE
from src.core.icaro import Icaro

# Asegurar existencia de carpeta logs
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configuración básica de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == "__main__":
    logging.info("Arrancando Ícaro desde main.")
    app = Icaro()
    app.iniciar()