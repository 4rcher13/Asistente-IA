import os
import sys
import time

print("[DEBUG] Iniciando diagnóstico...")

# Simular asistente_voz.py
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

print(f"[DEBUG] Path configurado: {project_root}")

try:
    print("[DEBUG] Importando AudioManager...")
    from herramientas.audio import AudioManager
    print("[DEBUG] AudioManager importado.")
    
    print("[DEBUG] Importando CerebroIcaro...")
    from logica.memorias import CerebroIcaro
    print("[DEBUG] CerebroIcaro importado.")
    
    print("[DEBUG] Instando CerebroIcaro...")
    memoria = CerebroIcaro()
    print("[DEBUG] CerebroIcaro instanciado.")
    
    print("[DEBUG] Instanciando AudioManager...")
    audio = AudioManager()
    print("[DEBUG] AudioManager instanciado.")
    
    print("[DEBUG] Probando TTS persistente...")
    audio.hablar("Diagnóstico de audio completado satisfactoriamente.")
    
    print("[DEBUG] IA habilitada:", memoria.ia_habilitada)
    print("[DEBUG] Ollama habilitado:", memoria.ollama_habilitado)
    
except Exception as e:
    print(f"[ERROR CRITICO] {e}")
    import traceback
    traceback.print_exc()

print("[DEBUG] Diagnóstico finalizado.")
