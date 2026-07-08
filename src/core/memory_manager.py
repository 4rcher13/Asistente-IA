import json
import logging
import re
import threading
import atexit
import time
from pathlib import Path
from typing import Any, Dict, List

from ..config.settings import HISTORY_FILE, MAX_HISTORY
from .vector_memory import VectorMemory

logger = logging.getLogger(__name__)

class MemoryManager:
    """Maneja la persistencia del historial de conversación de Ícaro."""

    def __init__(self, buffer_size: int = 5, flush_timeout: int = 30):
        self.archivo = Path(HISTORY_FILE)
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        self.max_items = MAX_HISTORY
        self.lock = threading.Lock()
        
        # Configuración de batching
        self.buffer_size = buffer_size
        self.flush_timeout = flush_timeout
        self.pending_changes = 0
        self.last_flush_time = time.time()
        
        self.historial: List[Dict[str, Any]] = self._leer_archivo()
        
        # Registrar guardado al salir
        atexit.register(self.flush)
        atexit.register(self._shutdown_vector)
        
        # Hilo daemon de flush periódico (sin timers recursivos)
        threading.Thread(target=self._flush_worker, daemon=True).start()

        # Memoria Vectorial
        try:
            self.vector_db = VectorMemory()
        except Exception as e:
            logger.error(f"No se pudo iniciar VectorMemory: {e}")
            self.vector_db = None

    def _leer_archivo(self) -> List[Dict[str, Any]]:
        """Lee el historial del disco de forma segura en la inicialización."""
        try:
            if not self.archivo.exists():
                return []
            with open(self.archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Historial corrupto, reiniciando")
            return []
        except OSError:
            logger.error("Error de I/O leyendo historial.")
            return []

    def cargar(self) -> List[Dict[str, Any]]:
        """Devuelve la caché del historial en memoria."""
        with self.lock:
            return list(self.historial)

    def _redactar_sensible(self, texto: str) -> str:
        """Filtra información sensible del texto antes de persistir."""
        if not texto: 
            return texto
        
        # Patrones de seguridad críticos
        patrones = [
            # JWT (JSON Web Tokens) - Primero por ser más específico
            (r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', '[JWT-REDACTADO]'),
            # Passwords, tokens, api keys en formatos comunes (evita re-redactar si ya empieza por '[')
            (r'(?i)(password|passwd|contraseña|token|api_key|secret|bearer|authorization)\s*[=:]\s*(?!\[)[^\s,;]+', r'\1: [REDACTADO]'),
            # Emails
            (r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL-REDACTADO]'),
            # Tarjetas de crédito/débito (13-16 dígitos)
            (r'\b(?:\d[ -]*?){13,16}\b', '[TARJETA-REDACTADA]'),
            # URLs con credenciales embebidas (user:pass@host)
            (r'https?://[^:\s]+:[^@\s]+@[^\s/]+', '[URL-PROTEGIDA]')
        ]
        
        resultado = texto
        for patron, remplazo in patrones:
            resultado = re.sub(patron, remplazo, resultado)
        return resultado

    def _flush_worker(self):
        """Hilo daemon que hace flush periódico sin crear timers recursivos."""
        while True:
            time.sleep(self.flush_timeout)
            if self.pending_changes > 0:
                logger.debug("Flush periódico del historial.")
                self.flush()

    def flush(self):
        """Escribe el historial al disco inmediatamente."""
        with self.lock:
            if self.pending_changes == 0:
                return
                
            try:
                temp = self.archivo.with_suffix(".tmp")
                with open(temp, "w", encoding="utf-8") as f:
                    json.dump(self.historial, f, ensure_ascii=False, indent=2)
                temp.replace(self.archivo)
                self.pending_changes = 0
                self.last_flush_time = time.time()
                logger.debug("Historial persistido correctamente.")
            except Exception as e:
                logger.error(f"Error en flush de historial: {e}")

    def guardar(self, rol: str, texto: str) -> None:
        """Guarda un nuevo mensaje en el buffer con filtrado de seguridad."""
        texto_seguro = self._redactar_sensible(texto)
        texto_final = f"[Largo omitido: {texto_seguro[:50]}...]" if len(texto_seguro) > 1000 else texto_seguro
        
        should_flush = False
        with self.lock:
            self.historial.append({"role": "user" if rol == "user" else "model", "text": texto_final})
            
            if len(self.historial) > self.max_items:
                self.historial = self.historial[-self.max_items:]
            
            self.pending_changes += 1
            # Decidir si hacer flush dentro del lock para evitar race condition
            should_flush = self.pending_changes >= self.buffer_size
        
        if should_flush:
            self.flush()

        # Guardar en memoria vectorial (fuera del lock principal)
        if self.vector_db:
            try:
                # No bloqueamos el path crítico, pero VectorMemory suele ser rápido
                self.vector_db.add_memory(rol, texto_final)
            except Exception as e:
                logger.debug(f"Error asíncrono en VectorMemory: {e}")

    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        """Retorna las últimas n interacciones del historial."""
        with self.lock:
            return list(self.historial[-n:])

    def guardar_evento(self, source: str, event_type: str, content: str) -> None:
        """
        Guarda un evento del sistema en memoria compartida.
        
        Los eventos se distinguen de user/model usando role="system" para poder
        filtrar después. Se guardan también en VectorMemory para recuperación RAG.
        
        Args:
            source: Componente que genera el evento (ej: "ActionService")
            event_type: Tipo de evento (ej: "action_executed")
            content: Mensaje del evento (puede ser texto largo)
        """
        content_seguro = self._redactar_sensible(content)
        content_final = (
            f"[Largo omitido: {content_seguro[:50]}...]"
            if len(content_seguro) > 1000
            else content_seguro
        )
        
        should_flush = False
        with self.lock:
            self.historial.append({
                "role": "system",
                "source": source,
                "event_type": event_type,
                "text": content_final
            })
            
            if len(self.historial) > self.max_items:
                self.historial = self.historial[-self.max_items:]
            
            self.pending_changes += 1
            should_flush = self.pending_changes >= self.buffer_size
        
        if should_flush:
            self.flush()
        
        # Guardar en memoria vectorial con metadata (fuera del lock)
        if self.vector_db:
            try:
                # Incluir source y event_type en el texto para búsqueda semántica
                contexto = f"[{source}|{event_type}] {content_final}"
                self.vector_db.add_memory("system", contexto)
            except Exception as e:
                logger.debug(f"Error asíncrono en VectorMemory guardar_evento: {e}")

    def _shutdown_vector(self) -> None:
        """Detiene VectorMemory antes del shutdown del intérprete (evita errores atexit)."""
        if self.vector_db and hasattr(self.vector_db, "shutdown"):
            try:
                self.vector_db.shutdown(wait=False)
            except Exception as e:
                logger.debug(f"Shutdown VectorMemory: {e}")
