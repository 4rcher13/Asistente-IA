import sys
import os
sys.path.append(os.getcwd())
from src.core.icaro import Icaro
print("Icaro imported successfully")
try:
    assistant = Icaro(silent=True)
    print("Icaro initialized successfully")
    # No llamar a iniciar() porque es un bucle infinito
except Exception as e:
    print(f"Error during initialization: {e}")
    import traceback
    traceback.print_exc()
