"""
Configuración centralizada del asistente Ícaro.
Carga variables de entorno, define rutas y parámetros con validaciones.
"""

import logging
import os
import secrets
import sys
from pathlib import Path
from typing import Set, Optional, Final, Dict, Any, List
from dotenv import load_dotenv

_logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Rutas base (absolutas)
# ----------------------------------------------------------------------
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = BASE_DIR / "data"
LOGS_DIR: Final[Path] = BASE_DIR / "logs"

# ----------------------------------------------------------------------
# Carga de variables de entorno (desde raíz del proyecto)
# ----------------------------------------------------------------------
load_dotenv(PROJECT_ROOT / ".env", override=False)

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


# ----------------------------------------------------------------------
# Entorno y logging
# ----------------------------------------------------------------------
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
DEBUG: bool = _env_bool("DEBUG")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: Final[Path] = LOGS_DIR / "icaro.log"

# ----------------------------------------------------------------------
# Seguridad, JWT y secretos
# ----------------------------------------------------------------------
SECRET_KEY: str = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise ValueError("SECRET_KEY must be set in production via environment variable")
    SECRET_KEY = f"dev-temp-{secrets.token_hex(16)}"

JWT_SECRET: str = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION: int = int(os.getenv("JWT_EXPIRATION", "3600"))

# ----------------------------------------------------------------------
# API keys
# ----------------------------------------------------------------------
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
NVIDIA_API_KEY: Optional[str] = os.getenv("NVIDIA_API_KEY")
OPENAI_API_KEY: Optional[str] = os.getenv("API_KEY_OPENAI")
EXTERNAL_API_KEY: Optional[str] = os.getenv("API_KEY_EXTERNAL")
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")

if not GEMINI_API_KEY:
    _logger.warning("GEMINI_API_KEY no definida. Gemini y embeddings RAG estarán desactivados.")

# ----------------------------------------------------------------------
# Perfil y conocimiento externo
# ----------------------------------------------------------------------
OBSIDIAN_VAULT_PATH: Optional[str] = os.getenv("OBSIDIAN_VAULT_PATH")
USER_NAME: str = os.getenv("USER_NAME", "Jesús")

# ----------------------------------------------------------------------
# Palabras de activación (evitar falsos positivos)
# ----------------------------------------------------------------------
WAKE_WORD: Set[str] = {"ícaro", "icaro", "hícaro", "e caro", "y claro", "y creo", "y caro"}

# ----------------------------------------------------------------------
# Modelos de IA
# ----------------------------------------------------------------------
MODELO_LOCAL: str = os.getenv("MODELO_OLLAMA", "qwen2.5:1.5b")
AI_WARMUP: bool = _env_bool("AI_WARMUP")
AI_ENABLE_RAG: bool = _env_bool("AI_ENABLE_RAG", "true")
AI_ENABLE_MCP: bool = _env_bool("AI_ENABLE_MCP", "true")
AI_MAX_MCP_WORKERS: int = max(1, int(os.getenv("AI_MAX_MCP_WORKERS", "2")))

# ----------------------------------------------------------------------
# Base de datos (opcional; reservado para futuras integraciones)
# ----------------------------------------------------------------------
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "asistente_ia")
DB_USER: str = os.getenv("DB_USER", "")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

# ----------------------------------------------------------------------
# Servicios opcionales
# ----------------------------------------------------------------------
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
MAIL_SERVER: str = os.getenv("MAIL_SERVER", "localhost")
MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")

# ----------------------------------------------------------------------
# Micrófono
# ----------------------------------------------------------------------
MIC_INDEX: Optional[int] = None

# ----------------------------------------------------------------------
# Historial de conversación
# ----------------------------------------------------------------------
MAX_HISTORY: Final[int] = 40
HISTORY_FILE: Final[Path] = DATA_DIR / "historial.json"

# ----------------------------------------------------------------------
# Audio y síntesis de voz
# ----------------------------------------------------------------------
VOICE_RATE: int = 130
AUDIO_RATE: Final[int] = 16000
AUDIO_CHANNELS: Final[int] = 1
AUDIO_FRAME_DURATION_MS: Final[int] = 20
AUDIO_FRAME_SIZE: Final[int] = int(AUDIO_RATE * AUDIO_FRAME_DURATION_MS / 1000)

VAD_AGGRESSIVENESS: int = 2
VAD_SILENCE_TIMEOUT_MS: int = 1000
VAD_PRE_RECORD_MS: int = 300
TIMEOUT_SILENCIO: float = 1.5
LIMITE_SEGUNDOS: int = 15


def database_url() -> str:
    """Construye URL de conexión a PostgreSQL."""
    if DB_USER and DB_PASSWORD:
        return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return f"postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"


def validate_config() -> None:
    """Valida configuración crítica (útil en startup o despliegue)."""
    errors: List[str] = []

    if ENVIRONMENT == "production":
        if not SECRET_KEY or SECRET_KEY.startswith("dev-"):
            errors.append("SECRET_KEY debe ser segura en producción")
        if DEBUG:
            errors.append("DEBUG debe ser False en producción")
        if not DB_PASSWORD:
            errors.append("DB_PASSWORD es requerido en producción")

    if errors:
        raise ValueError("Errores de configuración:\n" + "\n".join(f"  - {e}" for e in errors))


def config_to_dict(*, exclude_secrets: bool = True) -> Dict[str, Any]:
    """Resumen de configuración para logs o diagnóstico."""
    summary: Dict[str, Any] = {
        "ENVIRONMENT": ENVIRONMENT,
        "DEBUG": DEBUG,
        "LOG_LEVEL": LOG_LEVEL,
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
        "DB_NAME": DB_NAME,
        "AI_WARMUP": AI_WARMUP,
        "AI_ENABLE_RAG": AI_ENABLE_RAG,
        "AI_ENABLE_MCP": AI_ENABLE_MCP,
    }

    if not exclude_secrets:
        summary.update({
            "SECRET_KEY": "***" if SECRET_KEY else None,
            "JWT_SECRET": "***" if JWT_SECRET else None,
            "DB_PASSWORD": "***" if DB_PASSWORD else None,
            "OPENAI_API_KEY": "***" if OPENAI_API_KEY else None,
            "GEMINI_API_KEY": "***" if GEMINI_API_KEY else None,
        })

    return summary


class ConfigView:
    """Vista de compatibilidad para código que usa `from src.config import config`."""

    ENVIRONMENT = ENVIRONMENT
    DEBUG = DEBUG
    LOG_LEVEL = LOG_LEVEL
    SECRET_KEY = SECRET_KEY
    JWT_SECRET = JWT_SECRET
    JWT_ALGORITHM = JWT_ALGORITHM
    JWT_EXPIRATION = JWT_EXPIRATION
    DB_HOST = DB_HOST
    DB_PORT = DB_PORT
    DB_NAME = DB_NAME
    DB_USER = DB_USER
    DB_PASSWORD = DB_PASSWORD
    OPENAI_API_KEY = OPENAI_API_KEY
    EXTERNAL_API_KEY = EXTERNAL_API_KEY
    REDIS_URL = REDIS_URL
    MAIL_SERVER = MAIL_SERVER
    MAIL_PORT = MAIL_PORT
    MAIL_USERNAME = MAIL_USERNAME
    MAIL_PASSWORD = MAIL_PASSWORD

    @property
    def DATABASE_URL(self) -> str:
        return database_url()

    @classmethod
    def validate(cls) -> None:
        validate_config()

    @classmethod
    def to_dict(cls, exclude_secrets: bool = True) -> Dict[str, Any]:
        return config_to_dict(exclude_secrets=exclude_secrets)


config = ConfigView()


def check_dependencies() -> None:
    """Verifica que las librerías necesarias estén instaladas."""
    try:
        import pyaudio
        import webrtcvad
        import speech_recognition
        import ollama
        import google.genai
    except ImportError as e:
        print(f"Falta una dependencia: {e}")
        sys.exit(1)
