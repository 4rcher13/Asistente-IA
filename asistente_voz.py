import os
import sys

# Ajuste de rutas para importar limpiamente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main.icaro import Icaro

if __name__ == "__main__":
    asistente = Icaro()
    asistente.arrancar()