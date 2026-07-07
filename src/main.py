import sys
import logging
import argparse
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Añadir el directorio raíz al path si es necesario (para ejecución directa)
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import LOGS_DIR, LOG_FILE
from src.core.icaro import Icaro

def main():
    parser = argparse.ArgumentParser(description="Ícaro — Asistente de Voz Modular")
    parser.add_argument("--debug",   action="store_true", help="Activa logs nivel DEBUG")
    parser.add_argument("--silent",  action="store_true", help="Desactiva síntesis de voz al arrancar")
    parser.add_argument("--no-ai",   action="store_true", help="Desactiva la IA; solo comandos locales")
    args = parser.parse_args()

    # Asegurar existencia de carpeta logs
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Configurar logging según flag (UTF-8 para evitar errores cp1252 en Windows)
    log_level = logging.DEBUG if args.debug else logging.INFO
    # B5 FIX: reconfigurar stdout para UTF-8 de forma segura (sin abrir un nuevo FD)
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    stream_handler = logging.StreamHandler(sys.stdout)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB por archivo
        backupCount=3,
        encoding='utf-8',
    )
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler],
    )

    logging.info("Arrancando Ícaro desde main principal.")
    
    # Arrancar servidor FastAPI en segundo plano para recibir el contexto de VS Code
    import uvicorn
    import threading
    
    def start_api_server():
        try:
            logging.info("Iniciando servidor de contexto VS Code en http://localhost:8000")
            uvicorn.run("src.server:app", host="127.0.0.1", port=8000, log_level="warning")
        except Exception as e:
            logging.error(f"Error al iniciar el servidor de contexto VS Code: {e}")
            
    api_thread = threading.Thread(target=start_api_server, daemon=True, name="IcaroApiServer")
    api_thread.start()

    asistente = Icaro(silent=args.silent, no_ai=args.no_ai)
    asistente.iniciar()

if __name__ == "__main__":
    main()