"""
Telemetría UDP — Envía eventos de estado al widget UI de Ícaro.

Protocolo: "estado|transcripcion|respuesta"
  - Separado por pipes (|), máximo 4000 chars por campo para soportar textos largos.
  - El receptor es ui/widget.py escuchando en 127.0.0.1:5005.

Estados válidos: initializing | sleeping | listening | thinking | speaking | error
"""
import socket
import logging

logger = logging.getLogger(__name__)

_MAX_FIELD_LEN = 4000
_UDP_ADDR = ("127.0.0.1", 5005)


def _sanitize(text: str) -> str:
    """Elimina caracteres que rompen el protocolo o el eval JS."""
    return (
        text.replace("|", " ")
            .replace("'", "\u2019")   # comilla tipográfica (no rompe JS)
            .replace('"', "\u201d")
            .replace("\n", " ")
            .replace("\r", "")
            [:_MAX_FIELD_LEN]
    )


class Telemetry:
    """
    Singleton thread-safe que emite señales de estado vía UDP.

    Uso:
        t = Telemetry()
        t.send("listening", "abre youtube")
        t.send("speaking",  "abre youtube", "Abriendo YouTube...")
    """

    _instance: "Telemetry | None" = None

    def __new__(cls) -> "Telemetry":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._sock: socket.socket | None = None
            inst._addr = _UDP_ADDR
            inst._init_socket()
            cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------------
    # Privados
    # ------------------------------------------------------------------

    def _init_socket(self) -> None:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Sin bloqueo: si el receptor no está levantado simplemente se pierde el paquete.
            self._sock.setblocking(False)
        except Exception as exc:
            logger.error(f"[Telemetry] No se pudo crear socket UDP: {exc}")
            self._sock = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def send(self, state: str, transcript: str = "", response: str = "") -> None:
        """
        Envía una actualización de estado al widget.

        Args:
            state:      Estado de la máquina (initializing/sleeping/listening/thinking/speaking/error).
            transcript: Texto que el usuario dijo (opcional).
            response:   Texto que Ícaro va a responder (opcional).
        """
        if not self._sock:
            return
        try:
            payload = f"{state}|{_sanitize(transcript)}|{_sanitize(response)}"
            # B12 FIX: truncar el STRING (no los bytes) para evitar cortar un carácter
            # UTF-8 multibyte (emojis, tildes) que causaría UnicodeDecodeError en C#.
            # Estimamos el límite de chars a ~20000 (muy por debajo del límite UDP de 65507)
            if len(payload) > 20000:
                payload = payload[:20000]
            self._sock.sendto(payload.encode("utf-8"), self._addr)
        except BlockingIOError:
            pass  # El socket en modo non-blocking puede lanzar esto; es seguro ignorar.
        except Exception as exc:
            logger.warning(f"[Telemetry] Error enviando estado '{state}': {exc}")

    def close(self) -> None:
        """Cierra el socket al apagar el asistente."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            finally:
                self._sock = None
