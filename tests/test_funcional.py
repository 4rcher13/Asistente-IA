import sys
import time
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent.parent))

from src.core.icaro import Icaro
from unittest.mock import MagicMock


def test_funcional():
    print("\n=== INICIANDO PRUEBA FUNCIONAL DETALLADA ===\n")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("[1/4] Inicializando Ícaro...")
    asistente = Icaro(silent=True)

    asistente.audio.hablar = MagicMock()
    asistente.audio.escuchar = MagicMock(return_value="prueba")

    print("[OK] Subsistemas inicializados.")

    print("\n[2/4] Probando procesamiento de comando 'dame la hora'...")
    comando = "dame la hora"
    asistente._process_command(comando)
    time.sleep(0.2)  # guardado async en memoria

    ultima_entrada = asistente.memory.historial[-2]
    ultima_respuesta = asistente.memory.historial[-1]

    print(f"  Usuario: {ultima_entrada['text']}")
    print(f"  Respuesta: {ultima_respuesta['text']}")

    assert "Son las" in ultima_respuesta["text"] or "son las" in ultima_respuesta["text"].lower()
    print("[OK] Acción 'dar_hora_fecha' ejecutada con éxito.")

    print("\n[3/4] Probando intención de abrir aplicación (Notepad)...")
    comando_app = "abre el bloc de notas"
    asistente._process_command(comando_app)
    time.sleep(0.2)

    respuesta_app = asistente.memory.historial[-1]["text"]
    print(f"  Respuesta: {respuesta_app}")
    resp_lower = respuesta_app.lower()
    assert any(k in resp_lower for k in ("abrió", "abriendo", "notepad", "bloc de notas"))
    print("[OK] Intención de apertura de app detectada y ejecutada.")

    print("\n[4/4] Verificando persistencia en JSON...")
    historial_path = Path(__file__).parent.parent / "src" / "data" / "historial.json"
    if not historial_path.exists():
        historial_path = Path("src/data/historial.json")
    assert historial_path.exists(), "No se encontró historial.json"
    tamano = historial_path.stat().st_size
    print(f"[OK] El archivo historial existe ({tamano} bytes).")

    print("\n=== PRUEBA COMPLETADA CON ÉXITO ===")


if __name__ == "__main__":
    test_funcional()
