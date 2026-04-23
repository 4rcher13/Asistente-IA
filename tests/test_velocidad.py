import os
import sys
import time

# Ajuste de rutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def medir_tiempos():
    print("=== ANÁLISIS DE RENDIMIENTO DE ÍCARO (Qwen2.5:3b) ===\n")
    
    # 1. TIEMPO DE DESPERTAR (Inicialización completa)
    print("[1] Midiendo tiempo de despertar (arranque)...")
    t0_arranque = time.time()
    from main.icaro import Icaro
    asistente = Icaro()
    # Forzar una llamada ligera para asegurar que Ollama carga el modelo en VRAM/RAM
    asistente.memoria.consultar_local("test de carga de ram")
    t_arranque_total = time.time() - t0_arranque
    print(f" -> Tiempo total de arranque (Audio + IA): {t_arranque_total:.2f} segundos\n")

    # 2. TIEMPO DE RAZONAMIENTO (Enrutamiento puro IA)
    print("[2] Midiendo velocidad de análisis cognitivo (JSON)...")
    comando_test = "icaro cierra la pestaña del navegador por favor"
    herramientas = asistente.cerebro.desc_herramientas
    
    t0_ia = time.time()
    hrrm, params, resp = asistente.memoria.enrutar_comando(comando_test, herramientas)
    t_ia_total = time.time() - t0_ia
    print(f" -> La IA tardó en analizar y decidir: {t_ia_total:.2f} segundos")
    print(f"    (Decisión: Herramienta='{hrrm}', Respuesta='{resp}')\n")

    # 3. TIEMPO DE EJECUCIÓN (Latencia Total)
    print("[3] Midiendo ejecución completa ciclo Cerrado (Sin hardware micrófono)...")
    comando_latencia = "dime la hora actual"
    t0_ciclo = time.time()
    respuesta_final = asistente.cerebro.procesar_comando(comando_latencia)
    t_ciclo_total = time.time() - t0_ciclo
    print(f" -> Latencia total desde que recibe texto hasta tener respuesta: {t_ciclo_total:.2f} segundos")
    print(f"    (Respuesta final: '{respuesta_final}')\n")
    
    print("=== FIN DEL REPORTE ===")

if __name__ == "__main__":
    medir_tiempos()
