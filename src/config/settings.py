import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base del proyecto de forma absoluta
BASE_DIR = Path(__file__).resolve().parent.parent

# Seguridad
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# IA
# ==========================================
# Solo variaciones fonéticas reales del nombre Ícaro
WAKE_WORD = {"icaro", "ícaro", "vicaro", "vícaro", "pícaro", "hícaro", "e caro", "ikáro"}
MODELO_LOCAL = "qwen2.5:3b"
MIC_INDEX = 7  # Intel Smart Sound detectado en diagnóstico

# Historial
# ==========================================
MAX_HISTORY = 40
HISTORY_FILE = BASE_DIR / "data" / "historial.json"

# Audio / UI
# ==========================================
VOICE_RATE = 155
TIMEOUT_SILENCIO = 1.5
LIMITE_SEGUNDOS = 15

# Sistema & Logging
# ==========================================
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "icaro.log"
