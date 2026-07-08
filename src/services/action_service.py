import os
import io
import platform
import webbrowser
import time
import datetime
import subprocess
import logging
from importlib import import_module
from typing import Any, Dict, Optional, cast
from ..core.event_bus import bus, EventType
from ..core.shared_memory import log_event

logger = logging.getLogger(__name__)

# ─── Lazy Imports para GUI (evitar carga pesada al arranque) ───────────────
_pyautogui: Optional[Any] = None
_pyperclip: Optional[Any] = None
_gw: Optional[Any] = None
_gui_loaded = False


def _ensure_gui_modules():
    """Carga pyautogui, pyperclip y pygetwindow solo cuando se necesitan por primera vez."""
    global _pyautogui, _pyperclip, _gw, _gui_loaded
    if _gui_loaded:
        return
    _gui_loaded = True
    try:
        _pyautogui = import_module("pyautogui")
        _pyperclip = import_module("pyperclip")
        _gw = import_module("pygetwindow")
        if _pyautogui is not None:
            _pyautogui.FAILSAFE = True  # SECURITY: Permite abortar moviendo el ratón a una esquina
    except ImportError:
        logger.warning("Módulos de automatización GUI no instalados. (pip install pyautogui pyperclip pygetwindow)")


# Whitelist de aplicaciones permitidas por seguridad
ALLOWED_APPS: Dict[str, str] = {
    "word": "winword",
    "excel": "excel",
    "notepad": "notepad",
    "calculadora": "calc",
    "code": "code",
    "vscode": "code",
    "chrome": "chrome",
    "edge": "msedge",
    "spotify": "spotify",
}

class ActionService:
    """Ejecuta acciones en el sistema operativo sin lógica de cerebro ni audio."""
    
    def __init__(self):
        self.obsidian_mcp = None
        self.ai_service = None  # Inyectado para visión multimodal

    def set_obsidian_mcp(self, mcp: Optional[Any]) -> None:
        """Inyección de dependencia para acciones de conocimiento."""
        self.obsidian_mcp = mcp

    def set_ai_service(self, ai_svc: Optional[Any]) -> None:
        """Inyección de dependencia para acciones que necesitan el motor de IA (e.g. visión)."""
        self.ai_service = ai_svc

    def execute(self, config: Dict[str, Any]) -> str:
        """
        Recibe un diccionario con intent y los argumentos necesarios,
        y ejecuta la acción. Retorna el resultado string (si es necesario).
        """
        intent = config.get("intent")
        
        if not intent:
            return ""
            
        bus.publish(EventType.ACTION_STARTED, config)
        
        if intent == "buscar_google":
            res = self._buscar_google(config.get("target", ""))
        elif intent == "control_volumen":
            res = self._control_volumen(config.get("target", ""))
        elif intent == "reproducir_youtube":
            res = self._reproducir_youtube(config.get("target", ""))
        elif intent == "cerrar_ventana":
            res = self._cerrar_ventana(config.get("target", ""))
        elif intent in ("abrir_aplicacion", "open_app"):
            res = self._abrir_aplicacion(config.get("target", ""))
        elif intent == "crear_carpeta":
            res = self._crear_carpeta(config.get("target", ""))
        elif intent == "escribir_texto":
            res = self._escribir_texto(config.get("target", ""))
        elif intent == "dar_hora_fecha":
            res = self._dar_hora_fecha(config.get("target", "hora"))
        elif intent == "suspender_equipo":
            res = self._suspender_equipo()
        elif intent == "hacer_click":
            res = self._hacer_click()
        elif intent == "ver_pantalla":
            res = self._ver_pantalla(config.get("target", ""))
        elif intent == "guardar_en_obsidian":
            res = self._guardar_en_obsidian(config)
            
        else:
            res = f"Acción desconocida: {intent}"
        
        # Registrar en memoria compartida
        log_event("ActionService", "action_executed", f"{intent}: {res}")
        
        bus.publish(EventType.ACTION_COMPLETED, {"intent": intent, "result": res})
        return res

    def _abrir_aplicacion(self, nombre_app: Optional[str]) -> str:
        """Abre una aplicación de forma segura usando una whitelist."""
        if not nombre_app: 
            return "Sin aplicación destino."
            
        nombre_lower = nombre_app.lower().strip()
        
        # Validación contra whitelist
        if nombre_lower not in ALLOWED_APPS:
            return f"Acceso denegado: '{nombre_app}' no está en la lista blanca de seguridad."
            
        comando = ALLOWED_APPS[nombre_lower]
        sistema = platform.system()
        
        try:
            if sistema == "Windows":
                # Usamos shell=True solo porque los comandos vienen de una whitelist controlada
                # 'start' es un comando interno de cmd.exe
                subprocess.run(["cmd", "/c", "start", comando], shell=False)
            elif sistema == "Darwin":
                subprocess.run(["open", "-a", comando], check=True)
            else:
                subprocess.run([comando], check=True, start_new_session=True)
            return f"Se abrió {nombre_app}"
        except Exception as e:
            return f"Error al abrir {nombre_app}: {str(e)}"

    def _cerrar_ventana(self, nombre_ventana: str) -> str:
        _ensure_gui_modules()
        objetivo = nombre_ventana.lower().strip()
        try:
            encontrada: Optional[Any] = None
            if _gw is not None:
                ventanas = getattr(_gw, "getAllWindows", None)
                if callable(ventanas):
                    all_windows = cast(list[Any], ventanas() or [])
                    encontrada = next(
                        (
                            window
                            for window in all_windows
                            if objetivo
                            and objetivo in str(getattr(window, "title", "")).lower()
                            and bool(getattr(window, "visible", False))
                        ),
                        None,
                    )

            if encontrada and _pyautogui:
                window = encontrada
                activate = getattr(window, "activate", None)
                if callable(activate):
                    activate()
                time.sleep(0.2)
                title = str(getattr(window, "title", "")).lower()
                es_navegador = any(k in title for k in ("youtube", "edge", "chrome", "firefox"))
                if es_navegador:
                    _pyautogui.hotkey("ctrl", "w")
                else:
                    _pyautogui.hotkey("alt", "f4")
                return f"Se cerró {objetivo}."
            return f"No encontré ventana {objetivo}."
        except Exception as e:
            return f"Error al cerrar ventana: {str(e)}"

    def _control_volumen(self, accion: Optional[str]) -> str:
        if platform.system() != "Windows": return "No disponible"
        _ensure_gui_modules()
        mapa = {"subir": ("volumeup", 5), "bajar": ("volumedown", 5), "silenciar": ("volumemute", 1)}
        accion_str = (accion or "").lower()
        tecla, rep = mapa.get(accion_str, (None, 0))
        if tecla and _pyautogui:
            try:
                for _ in range(rep): _pyautogui.press(tecla)
                return "listo"
            except Exception:
                pass
        return "error de volumen"

    def _buscar_google(self, query: str) -> str:
        if query:
            # B1 FIX: usar quote_plus para encoding RFC-3986 correcto
            import urllib.parse
            query_sanitizada = urllib.parse.quote_plus(str(query))
            webbrowser.open(f"https://www.google.com/search?q={query_sanitizada}")
        return "búsqueda abierta"

    def _reproducir_youtube(self, query: str) -> str:
        if query:
            import urllib.request
            import urllib.parse
            import re
            try:
                # B2 FIX: añadir User-Agent real para evitar HTTP 403 de YouTube
                keyword = urllib.parse.quote_plus(str(query))
                req = urllib.request.Request(
                    f"https://www.youtube.com/results?search_query={keyword}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    html_text = response.read().decode("utf-8", errors="replace")
                # B3 FIX: validar que el ID tenga exactamente 11 chars alfanuméricos
                video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html_text)
                if video_ids:
                    webbrowser.open("https://www.youtube.com/watch?v=" + video_ids[0])
                else:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={keyword}")
            except Exception as e:
                logger.warning(f"YouTube search falló ({e}), abriendo búsqueda directa.")
                fallback = urllib.parse.quote_plus(str(query))
                webbrowser.open(f"https://www.youtube.com/results?search_query={fallback}")
        else:
            webbrowser.open("https://www.youtube.com/")
        return "youtube abierto"

    def _crear_carpeta(self, nombre: str) -> str:
        if not nombre: nombre = "Nueva Carpeta"
        # Sanitizar nombre para evitar path traversal
        nombre_seguro = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).strip()
        ruta = os.path.join(os.path.expanduser("~"), "Desktop", nombre_seguro.title())
        os.makedirs(ruta, exist_ok=True)
        return f"Carpeta '{nombre_seguro}' creada en el escritorio."

    def _escribir_texto(self, texto: str) -> str:
        _ensure_gui_modules()
        if texto and _pyperclip and _pyautogui:
            time.sleep(0.4)
            try:
                _pyperclip.copy(texto)
                _pyautogui.hotkey('ctrl', 'v')
            except Exception:
                _pyautogui.write(texto, interval=0.015)
        return "escrito"

    def _dar_hora_fecha(self, tipo: str) -> str:
        ahora = datetime.datetime.now()
        if tipo.lower() == "hora":
            return f"Son las {ahora.strftime('%I:%M %p')}."
        return f"Hoy es {ahora.day} del {ahora.month} del {ahora.year}."

    def _hacer_click(self) -> str:
        _ensure_gui_modules()
        try: 
            if _pyautogui: _pyautogui.click()
        except Exception: 
            pass
        return "click"
    
    def _suspender_equipo(self) -> str:
        if platform.system() == "Windows":
            # Comando de sistema seguro
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=False)
        return "equipo suspendido"

    def _ver_pantalla(self, pregunta: str = "") -> str:
        """Captura la pantalla y la envía a Gemini para análisis visual multimodal."""
        _ensure_gui_modules()
        if not _pyautogui:
            return "No puedo capturar la pantalla sin pyautogui instalado."

        # Verificar que el motor de IA con capacidad multimodal esté disponible
        if not self.ai_service or not self.ai_service.ia_habilitada or not self.ai_service.client:
            return "No puedo analizar la pantalla: Gemini no está disponible."

        try:
            # 1. Capturar pantalla
            screenshot = _pyautogui.screenshot()

            # 2. Redimensionar para reducir tokens (max 1280px ancho)
            width, height = screenshot.size
            if width > 1280:
                ratio = 1280 / width
                screenshot = screenshot.resize(
                    (1280, int(height * ratio)),
                )

            # 3. Convertir a bytes PNG en memoria
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG", optimize=True)
            image_bytes = buf.getvalue()
            buf.close()

            # 4. Construir prompt multimodal
            if not pregunta:
                pregunta = "Describe detalladamente lo que ves en esta captura de pantalla."

            # Lazy import del SDK de Gemini (ya cargado por ai_service)
            try:
                from google.genai import types as gtypes
            except ImportError:
                return "SDK de Gemini no disponible para visión."

            # 5. Llamar a Gemini con imagen + texto
            response = self.ai_service.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    gtypes.Content(
                        role="user",
                        parts=[
                            gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                            gtypes.Part.from_text(
                                text=f"Eres Ícaro, un asistente de IA experto en programación y ciberseguridad. "
                                     f"El usuario te muestra su pantalla. {pregunta} "
                                     f"Responde en español de forma clara y concisa."
                            ),
                        ],
                    )
                ],
                config=gtypes.GenerateContentConfig(temperature=0.3),
            )

            if response and response.text:
                logger.info(f"Visión completada: {len(response.text)} chars")
                return response.text.strip()
            return "No pude interpretar la captura de pantalla."

        except Exception as e:
            logger.error(f"Error en visión de pantalla: {e}")
            return f"Error al analizar la pantalla: {str(e)}"

    def _guardar_en_obsidian(self, config: Dict[str, Any]) -> str:
        """Guarda conocimiento crítico en el vault de Obsidian."""
        if not self.obsidian_mcp:
            return "Error: Obsidian no está configurado."
        
        titulo = config.get("target", "Nueva_Nota_Icaro")
        contenido = config.get("contenido_nota", config.get("respuesta", ""))
        
        if self.obsidian_mcp.create_or_append_note(titulo, contenido):
            return f"He guardado la información en tu Obsidian como '{titulo}'."
        return "No pude escribir en Obsidian. Verifica la ruta en el .env."
