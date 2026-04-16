import os
import platform
import webbrowser
import time
import datetime

pyautogui = None
pyperclip = None
gw = None

try:
    import pyautogui
    import pyperclip
    import pygetwindow as gw
except ImportError:
    print("[ActionService] Advertencia: Módulos de automatización GUI no instalados. (pip install pyautogui pyperclip pygetwindow)")

class ActionService:
    """Ejecuta acciones en el sistema operativo sin lógica de cerebro ni audio."""
    
    def execute(self, config: dict) -> str:
        """
        Recibe un diccionario con intent y los argumentos necesarios,
        y ejecuta la acción. Retorna el resultado string (si es necesario).
        """
        intent = config.get("intent")
        
        if not intent:
            return ""
            
        if intent == "buscar_google":
            return self._buscar_google(config.get("target", ""))
        elif intent == "control_volumen":
            return self._control_volumen(config.get("target", ""))
        elif intent == "reproducir_youtube":
            return self._reproducir_youtube(config.get("target", ""))
        elif intent == "cerrar_ventana":
            return self._cerrar_ventana(config.get("target", ""))
        elif intent in ("abrir_aplicacion", "open_app"):
            return self._abrir_aplicacion(config.get("target", ""))
        elif intent == "crear_carpeta":
            return self._crear_carpeta(config.get("target", ""))
        elif intent == "escribir_texto":
            return self._escribir_texto(config.get("target", ""))
        elif intent == "dar_hora_fecha":
            return self._dar_hora_fecha(config.get("target", "hora"))
        elif intent == "suspender_equipo":
            return self._suspender_equipo()
        elif intent == "hacer_click":
            return self._hacer_click()
            
        return f"Acción desconocida: {intent}"

    def _abrir_aplicacion(self, nombre_app):
        if not nombre_app: return "Sin aplicación destino."
        sistema = platform.system()
        apps = {
            "word": ("winword", "Microsoft Word"),
            "excel": ("excel", "Microsoft Excel"),
            "notepad": ("notepad", "Bloc de Notas"),
            "calculadora": ("calc", "Calculadora"),
            "code": ("code", "Visual Studio Code"),
            "vscode": ("code", "Visual Studio Code"),
        }
        nombre_lower = nombre_app.lower().strip()
        comando, nombre_real = apps.get(nombre_lower, (nombre_lower, nombre_app))
        try:
            if sistema == "Windows": os.system(f"start {comando}")
            elif sistema == "Darwin": os.system(f"open -a '{nombre_real}'")
            else: os.system(f"{comando} &")
            return f"Se abrió {nombre_real}"
        except Exception as e:
            return str(e)

    def _cerrar_ventana(self, nombre_ventana):
        objetivo = nombre_ventana.lower().strip()
        try:
            if gw:
                encontrada = next((v for v in gw.getAllWindows() if objetivo and objetivo in v.title.lower() and v.visible), None)
            else:
                encontrada = None
                
            if encontrada and pyautogui:
                encontrada.activate()
                time.sleep(0.2)
                es_navegador = any(k in encontrada.title.lower() for k in ("youtube", "edge", "chrome", "firefox"))
                if es_navegador: pyautogui.hotkey('ctrl', 'w')
                else: pyautogui.hotkey('alt', 'f4')
                return f"Se cerró {objetivo}."
            return f"No encontré ventana {objetivo}."
        except:
            return "No se pudo cerrar."

    def _control_volumen(self, accion):
        if platform.system() != "Windows": return "No disponible"
        mapa = {"subir": ("volumeup", 5), "bajar": ("volumedown", 5), "silenciar": ("volumemute", 1)}
        tecla, rep = mapa.get(accion.lower(), (None, 0))
        if tecla and pyautogui:
            try:
                for _ in range(rep): pyautogui.press(tecla)
                return "listo"
            except: pass
        return "error de volumen"

    def _buscar_google(self, query):
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return "busqueda abierta"

    def _reproducir_youtube(self, query):
        if query:
            import urllib.request
            import re
            try:
                keyword = query.replace(' ', '+')
                html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + keyword)
                video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
                if video_ids:
                    webbrowser.open("https://www.youtube.com/watch?v=" + video_ids[0])
                else:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={keyword}")
            except:
                webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
        else:
            webbrowser.open("https://www.youtube.com/")
        return "youtube abierto"

    def _crear_carpeta(self, nombre):
        if not nombre: nombre = "Nueva Carpeta"
        ruta = os.path.join(os.path.expanduser("~"), "Desktop", nombre.strip().title())
        os.makedirs(ruta, exist_ok=True)
        return "carpeta creada"

    def _escribir_texto(self, texto):
        if texto and pyperclip and pyautogui:
            time.sleep(0.4)
            try:
                pyperclip.copy(texto)
                pyautogui.hotkey('ctrl', 'v')
            except:
                pyautogui.write(texto, interval=0.015)
        return "escrito"

    def _dar_hora_fecha(self, tipo):
        ahora = datetime.datetime.now()
        if tipo.lower() == "hora":
            return f"Son las {ahora.strftime('%I:%M %p')}."
        return f"Hoy es {ahora.day} del {ahora.month} del {ahora.year}."

    def _hacer_click(self):
        try: 
            if pyautogui: pyautogui.click()
        except: pass
        return "click"
    
    def _suspender_equipo(self):
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "suspendido"
