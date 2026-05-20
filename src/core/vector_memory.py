import json
import logging
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_DEBUG_LOG = Path(__file__).resolve().parent.parent.parent / "debug-7ec0d9.log"


def _dbg(location: str, message: str, data: dict | None = None, hypothesis_id: str = "?") -> None:
    # region agent log
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "7ec0d9",
                "location": location,
                "message": message,
                "data": data or {},
                "hypothesisId": hypothesis_id,
                "timestamp": int(time.time() * 1000),
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # endregion


def _interpreter_shutting_down() -> bool:
    return getattr(sys, "is_finalizing", lambda: False)()

# ─── ChromaDB (import ligero, ~0.1s) ──────────────────────────────────────
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB no disponible. La memoria RAG estará desactivada.")

# ─── sentence_transformers NO se importa aquí ─────────────────────────────
# Su import tarda ~78s porque ejecuta código pesado de PyTorch.
# Se carga de forma diferida (lazy) en un hilo de background para que
# Ícaro pueda arrancar de inmediato y el modelo esté listo cuando se
# necesite por primera vez.

_embedding_model = None
_embedding_lock  = threading.Lock()
_embedding_ready = threading.Event()   # se pone en "set" cuando el modelo está listo
_embedding_failed = False              # bandera para no reintentar si falló
_active_instances: list["VectorMemory"] = []
_instances_lock = threading.Lock()


def _load_embedding_model_background() -> None:
    """
    Carga el modelo de embeddings en un hilo daemon.
    Llamar UNA sola vez al arranque; el Event notifica cuando termina.
    """
    global _embedding_model, _embedding_failed

    if _embedding_ready.is_set():
        return

    if not CHROMADB_AVAILABLE or _interpreter_shutting_down():
        _dbg("vector_memory.py:_load_embedding_model_background", "skip load", {"shutting_down": _interpreter_shutting_down()}, "A")
        _embedding_ready.set()
        return

    try:
        from chromadb.utils import embedding_functions  # import ligero
        t0 = time.perf_counter()

        # Intentar SentenceTransformer (mejor calidad semántica)
        try:
            import sentence_transformers  # noqa — importado aquí, en background
            _embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            _dbg("vector_memory.py:_load_embedding_model_background", "ST loaded", {"elapsed_s": round(time.perf_counter() - t0, 2)}, "A")
            logger.info(f"Modelo SentenceTransformer listo ({time.perf_counter()-t0:.1f}s).")
        except Exception as e:
            _dbg("vector_memory.py:_load_embedding_model_background", "ST failed", {"error": str(e)[:120]}, "A")
            err = str(e).lower()
            if any(x in err for x in ("atexit", "shutdown", "interpreter")):
                _embedding_failed = True
                logger.debug(f"Carga de embeddings omitida (apagado del intérprete): {e}")
            else:
                logger.warning(f"SentenceTransformer no disponible, usando fallback ChromaDB: {e}")
                try:
                    _embedding_model = embedding_functions.DefaultEmbeddingFunction()
                    logger.info("DefaultEmbeddingFunction de ChromaDB lista.")
                except Exception as e2:
                    logger.error(f"No se pudo cargar ningún modelo de embeddings: {e2}")
                    _embedding_failed = True

    except Exception as e:
        logger.error(f"Error crítico cargando embeddings: {e}")
        _embedding_failed = True
    finally:
        _embedding_ready.set()   # siempre notificar, aunque haya fallado


def get_embedding_model(timeout: float = 90.0):
    """
    Devuelve el modelo de embeddings cuando esté disponible.
    Bloquea como máximo `timeout` segundos (solo en la primera query).
    Si el modelo aún no está listo, espera; si falló, retorna None.
    """
    if _embedding_failed:
        return None
    if not _embedding_ready.is_set():
        logger.debug("Esperando que el modelo de embeddings termine de cargar...")
        _embedding_ready.wait(timeout=timeout)
    return _embedding_model


class VectorMemory:
    """
    Memoria semántica persistente usando ChromaDB.
    El modelo de embeddings se carga en background; el cliente ChromaDB
    se inicializa de forma lazy en la primera operación real.
    """

    def __init__(self, db_path: str = "data/chroma_db"):
        self.enabled = CHROMADB_AVAILABLE
        self.collection = None
        self.client = None
        self._db_path = db_path

        # Worker para guardar memorias sin bloquear la respuesta
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="VecMemWorker")

        with _instances_lock:
            _active_instances.append(self)

        if self.enabled:
            # El cliente ChromaDB es rápido de iniciar (~1s); lo hacemos aquí.
            try:
                self.client = chromadb.PersistentClient(path=db_path)
                logger.info(f"VectorMemory: cliente ChromaDB listo en '{db_path}'.")
            except Exception as e:
                logger.error(f"No se pudo abrir ChromaDB en '{db_path}': {e}")
                self.enabled = False

    def _ensure_collection(self) -> bool:
        """Crea/obtiene la colección cuando el modelo de embeddings esté disponible."""
        if not self.enabled or self.client is None or _interpreter_shutting_down():
            _dbg("vector_memory.py:_ensure_collection", "blocked", {"enabled": self.enabled, "shutting_down": _interpreter_shutting_down()}, "A")
            return False
        if self.collection is not None:
            return True

        embed_fn = get_embedding_model()
        if not embed_fn:
            _dbg("vector_memory.py:_ensure_collection", "no embed_fn", {}, "D")
            return False

        try:
            self.collection = self.client.get_or_create_collection(
                name="icaro_memories",
                embedding_function=embed_fn,
                metadata={"hnsw:space": "cosine"},
            )
            return True
        except Exception as e:
            err = str(e)
            _dbg("vector_memory.py:_ensure_collection", "collection error", {"error": err[:160]}, "D")
            if any(x in err.lower() for x in ("atexit", "shutdown", "interpreter")):
                self.enabled = False
            logger.error(f"Error creando colección ChromaDB: {e}")
            return False

    def _add_memory_task(self, role: str, text: str, intent: Optional[str] = None) -> None:
        """Tarea real de guardado (se ejecuta en el worker thread)."""
        if not self._ensure_collection():
            return

        timestamp = time.time()
        memory_id = f"mem_{int(timestamp * 1000)}"
        metadata = {
            "role": role,
            "timestamp": timestamp,
            "intent": intent or "none",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[memory_id],
            )
            logger.debug(f"Memoria guardada en background: {memory_id}")
        except Exception as e:
            err = str(e)
            if any(x in err.lower() for x in ("atexit", "shutdown", "interpreter")):
                self.enabled = False
                logger.debug(f"Escritura VectorMemory omitida (apagado): {e}")
            else:
                logger.error(f"Error guardando en VectorMemory: {e}")

    def add_memory(self, role: str, text: str, intent: Optional[str] = None) -> None:
        """Encola el guardado de una memoria (no bloquea)."""
        if not self.enabled or not text or len(text.strip()) < 5 or _interpreter_shutting_down():
            return
        self.executor.submit(self._add_memory_task, role, text, intent)

    def shutdown(self, wait: bool = True) -> None:
        """Detiene el worker y evita escrituras durante el apagado del intérprete."""
        self.enabled = False
        self.executor.shutdown(wait=wait, cancel_futures=True)
        with _instances_lock:
            try:
                _active_instances.remove(self)
            except ValueError:
                pass


    def query_memories(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Busca las memorias semánticamente más similares a la consulta."""
        if not self.enabled or not query:
            return []
        if not self._ensure_collection():
            return []

        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]
            return [
                {"text": docs[i], "metadata": metas[i], "distance": dists[i] if dists else None}
                for i in range(len(docs))
            ]
        except Exception as e:
            logger.error(f"Error consultando VectorMemory: {e}")
            return []

    def get_context_string(self, query: str, max_results: int = 3) -> str:
        """Retorna fragmentos relevantes formateados para inyectar en el prompt."""
        memories = self.query_memories(query, n_results=max_results)
        if not memories:
            return ""
        lines = ["Fragmentos relevantes de conversaciones pasadas:"]
        for mem in memories:
            role = "Usuario" if mem["metadata"]["role"] == "user" else "Ícaro"
            lines.append(f"- {role}: {mem['text']}")
        return "\n".join(lines) + "\n"


def shutdown_all_instances(wait: bool = False) -> None:
    """Cierra todos los VectorMemory activos (p. ej. al terminar pytest)."""
    with _instances_lock:
        instances = list(_active_instances)
    for vm in instances:
        try:
            vm.shutdown(wait=wait)
        except Exception:
            pass
