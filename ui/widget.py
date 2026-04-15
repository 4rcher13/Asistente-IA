import webview
import threading
import socket
import os


def udp_listener(window):
    """Escucha telemetría UDP para cambiar el estado de la UI en tiempo real."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", 5005))
        print("[UI] Escuchando telemetría en 127.0.0.1:5005")
    except Exception as e:
        print(f"[UI ERR] No se pudo vincular puerto 5005: {e}")
        return # Finaliza el hilo si no puede escuchar

    while True:
        try:
            data, _ = sock.recvfrom(256)
            state = data.decode().strip()
            window.evaluate_js(f"changeState('{state}')")
        except Exception as e:
            print(f"Error en telemetría UDP: {e}")


if __name__ == '__main__':
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget.html')

    window = webview.create_window(
        'Icaro UI',
        url=html_path,
        width=300, height=300,
        frameless=True, transparent=True, on_top=True
    )

    threading.Thread(target=udp_listener, args=(window,), daemon=True).start()
    webview.start()
