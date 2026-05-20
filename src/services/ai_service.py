import json
import re
import logging
import threading
import sys
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurar stdout para UTF-8 en Windows para evitar caídas por codificación de emojis en consola
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


from ..core.nlu.intents import local_fallback

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

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from ..config.settings import GEMINI_API_KEY, MODELO_LOCAL, OBSIDIAN_VAULT_PATH, GITHUB_TOKEN, USER_NAME, NVIDIA_API_KEY
from ..core.event_bus import bus, EventType
from ..core.plugin_loader import plugin_loader

# Importación segura de MCPs — el asistente arranca aunque alguno falle
try:
    from ..mcps.gemini_mcp import GeminiMCP
except ImportError:
    GeminiMCP = None  # type: ignore

try:
    from ..mcps.sequential_thinking import SequentialThinkingMCP
except ImportError:
    SequentialThinkingMCP = None  # type: ignore

try:
    from ..mcps.cybersecurity_mcp import CybersecurityMCP
except ImportError:
    CybersecurityMCP = None  # type: ignore

try:
    from ..mcps.obsidian_mcp import ObsidianMCP
except ImportError:
    ObsidianMCP = None  # type: ignore

try:
    from ..mcps.github_mcp import GitHubMCP
except ImportError:
    GitHubMCP = None  # type: ignore

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Clasificador de complejidad: decide si usar Ollama (rápido) o Gemini (complejo)
# --------------------------------------------------------------------------
_SIMPLE_INTENTS = {
    "buscar_google", "control_volumen", "reproducir_youtube",
    "cerrar_ventana", "abrir_aplicacion", "crear_carpeta",
    "escribir_texto", "dar_hora_fecha", "suspender_equipo", "hacer_click"
}

# Palabras clave que indican tareas complejas → Gemini
_COMPLEX_KEYWORDS = frozenset([
    "investiga", "investigacion", "analiza", "analisis", "explica", "explicame",
    "codigo", "programa", "funcion", "clase", "algoritmo", "refactoriza",
    "compara", "diferencia", "ventaja", "desventaja", "opinion",
    "resumen", "resume", "resena", "tutorial", "como funciona",
    "arquitectura", "patron", "diseno", "estrategia", "optimiza",
    "depura", "debug", "error", "bug", "solucion", "arregla",
    "traduce", "traduccion", "genera", "crea un", "escribe un",
    "modifica", "cambia el codigo", "agrega", "implementa",
    # Variantes con acentos (el input de voz puede traerlos)
    "explicá", "explícame", "explícalo", "investigación", "análisis",
    "código", "función", "patrón", "diseño", "solución", "traducción",
    "opinión",
])


def _is_complex_query(text: str) -> bool:
    """Determina si un comando requiere razonamiento avanzado (Gemini)."""
    t = text.lower()
    # Si contiene palabras clave de complejidad
    if any(kw in t for kw in _COMPLEX_KEYWORDS):
        return True
    # Si el texto es largo (>60 chars), probablemente es conversación o pregunta compleja
    if len(t) > 60:
        return True
    return False


class AIService:
    """Motor Cognitivo y Router Lógico de Ícaro (optimizado con Smart Routing)."""

    # Constantes configurables
    MAX_RESPUESTA_TTS = 4000            # caracteres máximos para respuesta hablada y escrita
    TIMEOUT_SEGUNDOS = 10               # timeout para llamadas a modelos
    REINTENTOS_LLM = 2                  # reintentos ante fallo transitorio

    INTENTS_VALIDOS = {
        "buscar_google", "control_volumen", "reproducir_youtube",
        "cerrar_ventana", "abrir_aplicacion", "crear_carpeta",
        "escribir_texto", "dar_hora_fecha", "suspender_equipo", "hacer_click",
        "guardar_en_obsidian"
    }

    # Prompt compacto para clasificación de intents (Ollama - tareas simples)
    _PROMPT_SIMPLE = """\
{{contexto}}Eres Ícaro, el asistente de IA personal de {user_name}. Clasifica el comando del usuario. Responde SOLO JSON válido.
Intents posibles: {{intents}}
Si es conversación general, intent=null.
Comando: {{text}}
JSON:"""

    # Prompt completo para Gemini (tareas complejas)
    _PROMPT_COMPLEX = """\
{{contexto}}Eres Ícaro, el asistente de IA inteligente, amigable y mentor de programación/ciberseguridad de {user_name}. Analiza el comando y responde SOLO JSON.

Intents: {{intents}}
Reglas:
- "intent": uno de los intents o null (conversación).
- "target": objeto de la acción o título de la nota si es para Obsidian.
- "respuesta": Si hay intent, confirmación corta (max 15 palabras). Si es conversación, respuesta natural hablando amigablemente con {user_name}.
- "contenido_nota": (Opcional) Si el intent es guardar_en_obsidian, el texto formateado en Markdown para la nota.

Comando: {{text}}
JSON:"""

    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.ia_habilitada = False
        self.ollama_habilitado = False
        self.nvidia_habilitado = False
        self.modelo_local = MODELO_LOCAL
        self.client = None          # Cliente Gemini
        self.chat = None            # Sesión de chat Gemini
        self.nvidia_client = None   # Cliente NVIDIA (DeepSeek)
        self._models_initialized = False
        self._init_lock = threading.Lock()

        # Pre-formatear prompts con el nombre del usuario
        self._PROMPT_SIMPLE = self._PROMPT_SIMPLE.format(user_name=USER_NAME)
        self._PROMPT_COMPLEX = self._PROMPT_COMPLEX.format(user_name=USER_NAME)

        # Inicializar MCPs (opcionales — no bloquean el arranque)
        self.gemini_mcp = GeminiMCP() if GeminiMCP else None
        self.thinking_mcp = SequentialThinkingMCP() if SequentialThinkingMCP else None
        self.security_mcp = CybersecurityMCP() if CybersecurityMCP else None
        self.obsidian_mcp = ObsidianMCP(OBSIDIAN_VAULT_PATH) if ObsidianMCP else None
        self.github_mcp = GitHubMCP(GITHUB_TOKEN) if GitHubMCP else None
        
        # Executor para llamadas asíncronas a MCPs (evita bloqueos)
        self.mcp_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="MCPCalls")

    # ------------------------------------------------------------------
    # Inicialización paralela de modelos
    # ------------------------------------------------------------------
    def _init_gemini(self) -> None:
        """Inicializa Gemini (nube). Thread-safe."""
        if not (genai and types and GEMINI_API_KEY):
            logger.warning("Gemini no configurado (API key o librería faltante).")
            return
        try:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.ia_habilitada = True
            logger.info("Gemini iniciado correctamente de forma stateless.")
        except Exception as exc:
            logger.error(f"Fallo al iniciar Gemini: {exc}")

    def _init_ollama(self) -> None:
        """Inicializa Ollama (local). Thread-safe."""
        if not ollama:
            logger.warning("Librería ollama no instalada.")
            return
        try:
            ollama.list()   # prueba conexión
            self.ollama_habilitado = True
            logger.info("Ollama disponible localmente.")
        except Exception as exc:
            logger.warning(f"Ollama no disponible: {exc}")

    def _init_nvidia(self) -> None:
        """Inicializa el cliente de NVIDIA API (DeepSeek). Thread-safe."""
        if not (OpenAI and NVIDIA_API_KEY):
            logger.warning("NVIDIA API no configurada (API key o librería faltante).")
            return
        try:
            self.nvidia_client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=NVIDIA_API_KEY
            )
            self.nvidia_habilitado = True
            logger.info("NVIDIA API (DeepSeek) iniciada correctamente.")
        except Exception as exc:
            logger.error(f"Fallo al iniciar NVIDIA API: {exc}")

    def _ensure_models_initialized(self) -> bool:
        """Inicializa Gemini, Ollama y NVIDIA en paralelo (una sola vez)."""
        if self._models_initialized:
            return self.ia_habilitada or self.ollama_habilitado or self.nvidia_habilitado

        with self._init_lock:
            if self._models_initialized:
                return self.ia_habilitada or self.ollama_habilitado or self.nvidia_habilitado

            self._models_initialized = True

            # Inicializar modelos en paralelo
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="IAInit") as pool:
                futures = [
                    pool.submit(self._init_gemini),
                    pool.submit(self._init_ollama),
                    pool.submit(self._init_nvidia),
                ]
                for f in as_completed(futures, timeout=15):
                    try:
                        f.result()
                    except Exception as exc:
                        logger.error(f"Error en inicialización de modelo: {exc}")

        return self.ia_habilitada or self.ollama_habilitado or self.nvidia_habilitado

    # ------------------------------------------------------------------
    # Llamada a LLM con Smart Routing
    # ------------------------------------------------------------------
    @staticmethod
    def _extraer_json(texto: str) -> Optional[Dict]:
        """Extrae el primer bloque JSON válido de un texto."""
        if not texto:
            return None
        # Busca el primer bloque que parece JSON: { ... }
        match = re.search(r'\{[^{}]*\}(?:\s*\{[^{}]*\})*', texto, re.DOTALL)
        if not match:
            # Intenta con algo más permisivo
            match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            candidato = match.group(0)
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                logger.debug(f"JSON inválido encontrado: {candidato[:100]}")
        return None

    def _call_nvidia(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Llama a Nvidia API (DeepSeek v4 Flash) optimizado para latencia ultrabaja."""
        if not self.nvidia_habilitado or not self.nvidia_client:
            return None

        for intento in range(self.REINTENTOS_LLM):
            try:
                # Instrucción de sistema para evitar emojis y forzar velocidad
                messages = [
                    {"role": "system", "content": "Eres Ícaro. NO uses emojis bajo ninguna circunstancia. Responde de forma directa, muy concisa y rápida."},
                    {"role": "user", "content": prompt}
                ]
                
                # Llamada síncrona sin reasoning_effort para latencia de ~1 segundo
                completion = self.nvidia_client.chat.completions.create(
                    model="deepseek-ai/deepseek-v4-flash",
                    messages=messages,
                    temperature=0.1,
                    top_p=0.9,
                    max_tokens=1024,
                    stream=False
                )

                contenido_completo = completion.choices[0].message.content
                
                datos = self._extraer_json(contenido_completo)
                if datos:
                    logger.info(f"NVIDIA (DeepSeek) respondió rápido: {datos}")
                    return datos
                else:
                    if contenido_completo.strip():
                        logger.warning(f"NVIDIA sin JSON (rescatando texto): {contenido_completo[:50]}...")
                        return {"intent": None, "target": None, "respuesta": contenido_completo.strip()}
            except Exception as exc:
                logger.error(f"NVIDIA API falló (intento {intento+1}): {exc}")
                if intento < self.REINTENTOS_LLM - 1:
                    import time
                    time.sleep(0.3)

        return None

    def _call_secondary_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Llama al modelo secundario configurado (NVIDIA DeepSeek o Ollama local)."""
        if self.nvidia_habilitado:
            return self._call_nvidia(prompt)
        return self._call_ollama(prompt)

    def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Llama a Ollama con parámetros optimizados para CPU."""
        if not self.ollama_habilitado:
            return None

        for intento in range(self.REINTENTOS_LLM):
            try:
                res = ollama.chat(
                    model=self.modelo_local,
                    messages=[{"role": "user", "content": prompt}],
                    format="json",
                    options={
                        "temperature": 0.0,
                        "num_predict": 256,     # Aumentado para respuestas conversacionales
                        "top_p": 0.9,
                        "num_ctx": 8192,        # Expandido para retener la memoria (RAG, skills, historial) sin truncamiento
                        "stop": ["\n```", "```"],
                    }
                )
                contenido = res["message"]["content"]
                datos = self._extraer_json(contenido)
                if datos:
                    logger.info(f"Ollama respondió (intento {intento+1}): {datos}")
                    return datos
                else:
                    logger.warning(f"Respuesta de Ollama sin JSON válido: {contenido[:100]}")
            except Exception as exc:
                logger.warning(f"Ollama falló (intento {intento+1}): {exc}")
                if intento < self.REINTENTOS_LLM - 1:
                    import time
                    time.sleep(0.3)

        logger.warning("Ollama no dio respuesta válida después de reintentos.")
        return None

    def _call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Llama a Gemini de forma stateless (sin historial interno) para evitar bucles de contexto."""
        if not self.ia_habilitada or not self.client:
            return None

        for intento in range(self.REINTENTOS_LLM):
            try:
                res = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            f"Eres Ícaro, el asistente de IA para programación avanzada y ciberseguridad de {USER_NAME}. "
                            "Analiza el contexto y responde SIEMPRE en formato JSON."
                        ),
                        temperature=0.2,
                        response_mime_type="application/json",
                    )
                )
                
                texto_limpio = res.text.strip()
                datos = self._extraer_json(texto_limpio)
                if datos:
                    logger.info(f"Gemini respondió: {datos}")
                    return datos
                else:
                    if texto_limpio and len(texto_limpio) > 5:
                        logger.warning(f"Gemini sin JSON (rescatando texto): {texto_limpio[:50]}...")
                        return {"intent": None, "target": None, "respuesta": texto_limpio}
                    logger.warning(f"Gemini devolvió vacío o inválido.")
            except Exception as exc:
                logger.error(f"Gemini falló (intento {intento+1}): {exc}")
                if intento < self.REINTENTOS_LLM - 1:
                    import time
                    time.sleep(0.5)

        return None

    # ------------------------------------------------------------------
    # Enrutamiento principal con Smart Routing
    # ------------------------------------------------------------------
    def route_command(self, text: str) -> Dict[str, Any]:
        """
        Pipeline con Smart Routing:
          1. Respuesta local rápida (local_fallback) — 0ms
          2. Clasificar complejidad del comando
          3a. Simple → Ollama (rápido, local) → Gemini fallback
          3b. Complejo → Gemini (potente, nube) → Ollama fallback
          4. Fallback humanoide
        """
        # --- Paso 1: local inmediato (sin IA) ---
        local = local_fallback(text)
        if local:
            logger.info(f"Respuesta LOCAL para: '{text}'")
            bus.publish(EventType.INTENT_ROUTED, local)
            return self._sanitize_response(local)

        # Emitir evento de que estamos pensando
        bus.publish(EventType.THINKING_STARTED, text)

        # --- Paso 2: inicializar IA si no lo estaba ---
        ai_available = self._ensure_models_initialized()
        if not ai_available:
            logger.warning("Ningún modelo IA disponible.")
            return {
                "intent": None,
                "target": None,
                "respuesta": "Mis sistemas de IA están offline. Puedo hacer cosas básicas como dar la hora o abrir apps. ¿Qué necesitas?"
            }

        # --- Paso 3: Smart Routing ---
        is_complex = _is_complex_query(text)
        user_text_escaped = json.dumps(text, ensure_ascii=False)
        intents_str = ", ".join(self.INTENTS_VALIDOS)

        if is_complex:
            # Tareas complejas: Gemini primero (mejor razonamiento)
            logger.info(f"Smart Routing -> GEMINI (complejo): '{text[:50]}'")
            contexto = self._build_context(text)
            prompt = self._PROMPT_COMPLEX.format(
                contexto=contexto,
                intents=intents_str,
                text=user_text_escaped
            )
            datos = self._call_gemini(prompt)
            if not datos:
                # Fallback al LLM secundario si Gemini falla
                prompt_simple = self._PROMPT_SIMPLE.format(
                    contexto=contexto,
                    intents=intents_str,
                    text=user_text_escaped
                )
                datos = self._call_secondary_llm(prompt_simple)
        else:
            # Tareas simples: LLM Secundario primero
            logger.info(f"Smart Routing -> SECUNDARIO (simple/rápido): '{text[:50]}'")
            contexto = self._build_context(text)
            prompt = self._PROMPT_SIMPLE.format(
                contexto=contexto,
                intents=intents_str,
                text=user_text_escaped
            )
            datos = self._call_secondary_llm(prompt)
            if not datos or (datos.get("intent") is None and not datos.get("respuesta")):
                # Si no detectó acción o es conversación pura, delegar a Gemini con contexto
                logger.info("LLM Secundario no detectó acción o respuesta, delegando a Gemini...")
                contexto = self._build_context(text)
                prompt_complex = self._PROMPT_COMPLEX.format(
                    contexto=contexto,
                    intents=intents_str,
                    text=user_text_escaped
                )
                datos = self._call_gemini(prompt_complex)

        if datos:
            result = self._parse_routing_data(datos)
            bus.publish(EventType.INTENT_ROUTED, result)
            return result

        # --- Paso 4: fallback total ---
        return {
            "intent": None,
            "target": None,
            "respuesta": "Lo siento, no pude procesar eso ahora mismo. ¿Puedes repetirlo?"
        }

    def _build_context(self, query: str = "") -> str:
        """Construye contexto histórico ligero y semántico (RAG)."""
        if not self.memory:
            return ""
        
        contexto_final = ""
        
        # 1. Recuperación Semántica (RAG) - Prioridad alta
        if hasattr(self.memory, 'vector_db') and self.memory.vector_db and query:
            try:
                contexto_semantico = self.memory.vector_db.get_context_string(query)
                if contexto_semantico:
                    contexto_final += contexto_semantico + "\n"
            except Exception as e:
                logger.debug(f"Fallo en RAG semántico: {e}")

        # 2. Conocimiento Semántico de los Plugins (SKILLS .md)
        contexto_plugins = plugin_loader.get_context_injection()
        if contexto_plugins:
            contexto_final += "Conocimiento de Habilidades (Skills):\n" + contexto_plugins + "\n"

        # 3. Conocimiento Dinámico vía MCPs (Asíncrono con timeout)
        mcp_tasks = []
        
        if self.gemini_mcp and ("gemini" in query.lower() or "api" in query.lower()):
            mcp_tasks.append(self.mcp_executor.submit(self.gemini_mcp.search_documentation, query))

        if self.security_mcp and any(w in query.lower() for w in ["seguridad", "vulnerabilidad", "exploit", "hash"]):
            mcp_tasks.append(self.mcp_executor.submit(self.security_mcp.get_security_best_practice, query))

        if self.obsidian_mcp and any(w in query.lower() for w in ["nota", "obsidian", "mi conocimiento"]):
            mcp_tasks.append(self.mcp_executor.submit(self.obsidian_mcp.search_notes, query))

        # Esperar resultados con timeout de 3 segundos para no ralentizar la respuesta
        for future in as_completed(mcp_tasks, timeout=3):
            try:
                res = future.result()
                if res:
                    contexto_final += f"\n--- Información Externa ---\n{res}\n"
            except Exception as e:
                logger.debug(f"Error en llamada asíncrona a MCP: {e}")

        # 4. Historial Reciente (Short-term)
        try:
            # Aumentamos a 10 mensajes para dar más coherencia a la charla
            historial = self.memory.get_recent(10)
            if historial:
                contexto_final += "Historial reciente:\n" + "\n".join(
                    f"{'U' if h['role'] == 'user' else 'I'}: {h['text']}"
                    for h in historial
                ) + "\n"
        except Exception as e:
            logger.debug(f"No se pudo acceder a memoria: {e}")
            
        return contexto_final

    # ------------------------------------------------------------------
    # Parseo y sanitización de respuestas
    # ------------------------------------------------------------------
    def _parse_routing_data(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae y valida intent, target, respuesta. Trunca respuesta para TTS."""
        # Normalizar intent
        intent = datos.get("intent")
        if isinstance(intent, str):
            intent = intent.strip().lower()
            if intent == "null" or intent not in self.INTENTS_VALIDOS:
                intent = None
        else:
            intent = None

        # Normalizar target
        target = datos.get("target")
        if target is None:
            # soporte legacy: buscar dentro de params si existe (por compatibilidad)
            params = datos.get("params", {})
            if "nombre_app" in params:
                target = params["nombre_app"]
            elif "query" in params:
                target = params["query"]
        if isinstance(target, dict):
            target = next(iter(target.values())) if target else None
        if not isinstance(target, str):
            target = str(target) if target is not None else ""

        # Respuesta y truncado inteligente
        respuesta = datos.get("respuesta", "Entendido.")
        if not isinstance(respuesta, str):
            respuesta = str(respuesta)

        # Truncar para TTS, respetando límite de caracteres y cortando en punto o coma
        if len(respuesta) > self.MAX_RESPUESTA_TTS:
            truncado = respuesta[:self.MAX_RESPUESTA_TTS]
            # Buscar último separador de oración
            for sep in (". ", "? ", "! ", ", "):
                pos = truncado.rfind(sep)
                if pos > self.MAX_RESPUESTA_TTS // 2:
                    truncado = truncado[:pos + 1]
                    break
            respuesta = truncado.strip() + ("." if not truncado.endswith((".", "?", "!")) else "")
            logger.debug(f"Respuesta truncada de {len(respuesta)} a {len(truncado)} caracteres.")

        return {"intent": intent, "target": target, "respuesta": respuesta}

    def _sanitize_response(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        """Asegura que la respuesta local tenga la estructura correcta."""
        return {
            "intent": resp.get("intent"),
            "target": resp.get("target", ""),
            "respuesta": resp.get("respuesta", "")
        }

    # ------------------------------------------------------------------
    # Conversación directa (sin acciones)
    # ------------------------------------------------------------------
    def summarize(self, text: str) -> str:
        """Respuesta conversacional usando la misma lógica prioritaria."""
        if not self._ensure_models_initialized():
            return "Las capacidades de IA están apagadas."

        contexto = self._build_context(text)
        prompt = f"{contexto}\nEres Ícaro. El usuario dice: {json.dumps(text)}\nResponde brevemente en español:"

        # Para summarize, preferir Gemini (mejor calidad conversacional)
        datos_text = None
        if self.ia_habilitada:
            datos = self._call_gemini(prompt)
            if datos and "respuesta" in datos:
                return datos["respuesta"]
            # Si Gemini devuelve texto plano (no JSON)
            if self.client:
                try:
                    res = self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.4)
                    )
                    if res and res.text:
                        return res.text.strip()[:self.MAX_RESPUESTA_TTS]
                except Exception:
                    pass

        # Fallback al LLM secundario
        datos = self._call_secondary_llm(prompt)
        if datos and "respuesta" in datos:
            return datos["respuesta"]

        return "No pude generar una respuesta en este momento."

    def summarize_session(self, messages: list) -> Optional[str]:
        """
        Genera un resumen de conocimiento crítico de una sesión.
        """
        if not messages or not (self.ia_habilitada or self.nvidia_habilitado):
            return None

        # Formatear la conversación para el prompt
        conv = "\n".join([f"{'U' if m['role'] == 'user' else 'I'}: {m['text']}" for m in messages])
        
        prompt = f"""
Analiza la siguiente conversación y extrae SOLO información importante (hechos, preferencias del usuario, datos técnicos, decisiones).
Si no hay nada relevante a largo plazo (solo saludos o charla trivial), responde 'null'.
Resumen conciso (máx 50 palabras):

CONVERSACIÓN:
{conv}
"""
        # Opción 1: Gemini
        if self.ia_habilitada:
            try:
                res = self._call_gemini(prompt)
                if res and res.get("respuesta"):
                    summary = res["respuesta"]
                    if summary.lower() == "null":
                        return None
                    return summary
                
                # Fallback si no devuelve JSON
                if self.client:
                    res = self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.2)
                    )
                    text = res.text.strip()
                    if text.lower() == "null":
                        return None
                    return text
            except Exception as e:
                logger.error(f"Error en summarize_session con Gemini: {e}")

        # Opción 2: NVIDIA DeepSeek (v4 Flash)
        if self.nvidia_habilitado:
            try:
                logger.info("Generando resumen de sesión con NVIDIA DeepSeek...")
                res = self._call_nvidia(prompt)
                if res and res.get("respuesta"):
                    summary = res["respuesta"]
                    if summary.lower() == "null":
                        return None
                    return summary
            except Exception as e:
                logger.error(f"Error en summarize_session con NVIDIA DeepSeek: {e}")

        return None

    def fallback_response(self) -> str:
        return "No pude entender eso, ¿puedes repetirlo?"

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado de salud de todos los subsistemas de IA."""
        return {
            "gemini_cloud": self.ia_habilitada,
            "ollama_local": self.ollama_habilitado,
            "nvidia_deepseek": self.nvidia_habilitado,
            "mcps": {
                "gemini_docs": self.gemini_mcp.enabled if self.gemini_mcp else False,
                "security": self.security_mcp.enabled if self.security_mcp else False,
                "obsidian": self.obsidian_mcp.enabled if self.obsidian_mcp else False,
                "github": self.github_mcp.enabled if self.github_mcp else False
            }
        }

    def disable_ai(self) -> None:
        """Desactiva ambos motores de IA."""
        self.ia_habilitada = False
        self.ollama_habilitado = False
        logger.info("IA desactivada explícitamente.")
