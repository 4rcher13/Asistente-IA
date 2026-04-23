import json
import time
import unicodedata
import logging

try:
    import google.genai as genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    import ollama
except ImportError:
    ollama = None

from ..config.settings import GEMINI_API_KEY, MODELO_LOCAL

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


# ---------------------------------------------------------------------------
# Respuestas locales (sin IA) para comandos frecuentes
# ---------------------------------------------------------------------------

_LOCAL_PATTERNS: list[tuple[list[str], dict]] = [
    # Hora y fecha
    (["hora", "time", "qué hora"],
     {"intent": "dar_hora_fecha", "target": "hora", "respuesta": "Te digo la hora."}),
    (["fecha", "día", "date", "qué día"],
     {"intent": "dar_hora_fecha", "target": "fecha", "respuesta": "Te digo la fecha."}),
    # Volumen
    (["sube el volumen", "más volumen", "subir volumen", "aumenta"],
     {"intent": "control_volumen", "target": "subir", "respuesta": "Subiendo el volumen."}),
    (["baja el volumen", "menos volumen", "bajar volumen", "baja volumen"],
     {"intent": "control_volumen", "target": "bajar", "respuesta": "Bajando el volumen."}),
    (["silencio", "mute", "silencia", "silenciar"],
     {"intent": "control_volumen", "target": "silenciar", "respuesta": "Silenciando el audio."}),
    # YouTube
    (["youtube", "pon música", "reproduce", "música"],
     None),  # Necesita query → se maneja con extracción dinámica
    # Google
    (["busca", "búscame", "google", "buscar"],
     None),  # Necesita query → se maneja con extracción dinámica
    # Abrir apps
    (["abre", "abrir", "open"],
     None),  # Necesita app name → dinámica
    # Calculadora / notepad
    (["calculadora", "calcula"],
     {"intent": "abrir_aplicacion", "target": "calculadora", "respuesta": "Abriendo calculadora."}),
    (["notepad", "bloc de notas"],
     {"intent": "abrir_aplicacion", "target": "notepad", "respuesta": "Abriendo Bloc de Notas."}),
    (["código", "vscode", "visual studio"],
     {"intent": "abrir_aplicacion", "target": "vscode", "respuesta": "Abriendo Visual Studio Code."}),
    # Saludos
    (["hola", "hey", "buenas", "buenos", "qué tal"],
     {"intent": None, "target": None, "respuesta": "Hola, ¿en qué te ayudo?"}),
]


def _local_fallback(text: str) -> dict | None:
    """
    Intenta resolver el comando con reglas locales sin necesidad de IA.
    Devuelve un intent dict o None si no puede resolverlo localmente.
    """
    t = _strip_accents(text.lower().strip())

    # Saludos
    if any(w in t for w in ["hola", "hey", "buenas", "buenos dias", "que tal"]):
        return {"intent": None, "target": None, "respuesta": "Hola, ¿en qué te ayudo?"}

    # Hora y fecha
    if any(w in t for w in ["hora", "time", "que hora"]):
        return {"intent": "dar_hora_fecha", "target": "hora", "respuesta": "Te digo la hora."}
    if any(w in t for w in ["fecha", "dia", "date", "que dia", "que fecha"]):
        return {"intent": "dar_hora_fecha", "target": "fecha", "respuesta": "Te digo la fecha."}

    # Volumen
    if any(w in t for w in ["sube", "aumenta", "mas volumen", "subir volumen"]):
        return {"intent": "control_volumen", "target": "subir", "respuesta": "Subiendo el volumen."}
    if any(w in t for w in ["baja", "menos volumen", "bajar volumen"]):
        return {"intent": "control_volumen", "target": "bajar", "respuesta": "Bajando el volumen."}
    if any(w in t for w in ["silencio", "mute", "silenciar"]):
        return {"intent": "control_volumen", "target": "silenciar", "respuesta": "Silenciando."}

    # Calculadora / Notepad / VSCode
    if any(w in t for w in ["calculadora", "calcula"]):
        return {"intent": "abrir_aplicacion", "target": "calculadora", "respuesta": "Abriendo calculadora."}
    if any(w in t for w in ["notepad", "bloc de notas"]):
        return {"intent": "abrir_aplicacion", "target": "notepad", "respuesta": "Abriendo Bloc de Notas."}
    if any(w in t for w in ["codigo", "vscode", "visual studio"]):
        return {"intent": "abrir_aplicacion", "target": "vscode", "respuesta": "Abriendo Visual Studio Code."}

    # YouTube — extrae la query
    if "youtube" in t or any(w in t for w in ["pon musica", "reproduce", "musica"]):
        query = t.replace("abre", "").replace("pon", "").replace("reproduce", "")
        query = query.replace("musica", "").replace("youtube", "").strip()
        return {"intent": "reproducir_youtube", "target": query, "respuesta": f"Buscando en YouTube: {query}."}

    # Google — extrae la query
    if any(w in t for w in ["busca", "buscame", "google"]):
        query = (
            t.replace("busca", "").replace("buscame", "")
            .replace("en google", "").replace("google", "").strip()
        )
        return {"intent": "buscar_google", "target": query, "respuesta": f"Buscando {query}."}

    # Abrir app genérica
    if any(w in t for w in ["abre", "abrir", "open"]):
        app = t.replace("abre", "").replace("abrir", "").replace("open", "").strip()
        if app:
            return {"intent": "abrir_aplicacion", "target": app, "respuesta": f"Intentando abrir {app}."}

    return None  # No se pudo resolver localmente


# ---------------------------------------------------------------------------

class AIService:
    """Motor Cognitivo y Router Lógico de Ícaro."""

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.ia_habilitada = False
        self.ollama_habilitado = False
        self.modelo_local = MODELO_LOCAL
        self.client = None
        self.chat = None
        self._models_initialized = False

        self.herramientas_schema = """\
- buscar_google(query="texto a buscar")
- control_volumen(accion="subir" o "bajar" o "silenciar")
- reproducir_youtube(query="nombre video")
- cerrar_ventana(nombre_ventana="nombre")
- abrir_aplicacion(nombre_app="nombre de aplicacion como vscode, word, etc.")
- crear_carpeta(nombre="nombre")
- escribir_texto(texto="texto a escribir")
- dar_hora_fecha(tipo="hora" o "fecha")
- suspender_equipo()
- hacer_click()
"""

    # ------------------------------------------------------------------

    def _ensure_models_initialized(self) -> bool:
        if self._models_initialized:
            return self.ia_habilitada or self.ollama_habilitado

        self._models_initialized = True

        # Nube: Gemini
        if genai and types and GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                self.chat = self.client.chats.create(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "Eres Ícaro, asistente inteligente. "
                            "Habla en español, de forma natural, directa y concisa."
                        ),
                        temperature=0.7,
                    ),
                )
                self.ia_habilitada = True
                logger.info("Gemini inicializado correctamente.")
            except Exception as exc:
                logger.error(f"Fallo Gemini: {exc}")
        else:
            logger.warning("Gemini no configurado (sin API KEY o librería).")

        # Local: Ollama
        if ollama:
            try:
                ollama.list()
                self.ollama_habilitado = True
                logger.info("Ollama disponible.")
            except Exception:
                logger.warning("Ollama offline o no instalado.")

        return self.ia_habilitada or self.ollama_habilitado

    # ------------------------------------------------------------------

    def route_command(self, text: str) -> dict:
        """
        Pipeline de enrutamiento:
          1. Respuesta local rápida (keywords, sin latencia)
          2. Ollama local (si está disponible)
          3. Gemini nube (fallback)
          4. Respuesta local básica (si todo falla)
        """
        # ── Paso 1: Respuesta local inmediata ──
        local = _local_fallback(text)
        if local:
            logger.info(f"Respuesta LOCAL para: '{text}'")
            return local

        # ── Paso 2: Intentar inicializar modelos ──
        ai_available = self._ensure_models_initialized()
        if not ai_available:
            logger.warning("Ningún modelo de IA disponible, usando fallback local extendido.")
            return {
                "intent": None,
                "target": None,
                "respuesta": "Mis sistemas de IA están offline, pero puedo hacer cosas básicas como decirte la hora o abrir apps. ¿Qué necesitas?",
            }

        prompt = f"""\
Comando del usuario: "{text}"
HERRAMIENTAS disponibles:
{self.herramientas_schema}
Devuelve EXCLUSIVAMENTE un JSON:
{{"intent": "nombre_o_null", "target": "parametro", "respuesta": "que dirias tu"}}
Si no aplica ninguna herramienta, usa intent null y responde normalmente.
NO uses bloques ```json, solo texto plano JSON.
"""
        # ── Paso 3: Ollama (local, rápido) ──
        if self.ollama_habilitado:
            try:
                res = ollama.chat(
                    model=self.modelo_local,
                    messages=[{"role": "user", "content": prompt}],
                    format="json",
                    options={"temperature": 0.1, "num_predict": 150},
                )
                datos = json.loads(res["message"]["content"])
                logger.info(f"Ollama respondió: {datos}")
                return self._parse_routing_data(datos)
            except Exception as exc:
                logger.warning(f"Ollama falló: {exc}. Probando Gemini...")

        # ── Paso 4: Gemini (nube) ──
        if self.ia_habilitada:
            try:
                res = self.chat.send_message(prompt)
                texto_limpio = res.text.replace("```json", "").replace("```", "").strip()
                datos = json.loads(texto_limpio)
                logger.info(f"Gemini respondió: {datos}")
                return self._parse_routing_data(datos)
            except Exception as exc:
                logger.error(f"Gemini falló: {exc}")

        # ── Fallback total ──
        return {
            "intent": None,
            "target": None,
            "respuesta": "Lo siento, no pude procesar eso ahora mismo.",
        }

    def _parse_routing_data(self, datos: dict) -> dict:
        intent = datos.get("intent")
        target = datos.get("target") or datos.get("params", {}).get("nombre_app", "")
        if isinstance(target, dict) and target:
            target = list(target.values())[0]
        respuesta = datos.get("respuesta", "Entendido.")
        if intent in ("null", "None", "", None):
            intent = None
        return {"intent": intent, "target": target, "respuesta": respuesta}

    def summarize(self, text: str) -> str:
        """Respuesta directa de conversación sin lanzar acciones."""
        if not self._ensure_models_initialized():
            return "Las capacidades de IA están apagadas."
        if self.ia_habilitada:
            try:
                return self.chat.send_message(text).text or "Sin respuesta."
            except Exception:
                pass
        return "Resumen no disponible ahora."

    def fallback_response(self) -> str:
        return "No pude entender eso, ¿puedes repetirlo?"
