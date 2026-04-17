import argparse
import logging

def main():
    parser = argparse.ArgumentParser(description="Ícaro — Asistente de Voz Modular")
    parser.add_argument("--debug",   action="store_true", help="Activa logs nivel DEBUG")
    parser.add_argument("--silent",  action="store_true", help="Desactiva síntesis de voz al arrancar")
    parser.add_argument("--no-ai",   action="store_true", help="Desactiva la IA; solo comandos locales")
    args = parser.parse_args()

    # Configurar logging según flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    from src.core.icaro import Icaro
    asistente = Icaro(silent=args.silent, no_ai=args.no_ai)
    asistente.iniciar()

if __name__ == "__main__":
    main()

