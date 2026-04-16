from src.core.cerebro_legacy import CerebroIcaro
from src.services.audio_legacy import AudioManager


class IcaroAdapter:
    """Adaptador temporal para mantener compatibilidad con código legado."""

    def __init__(self):
        self.cerebro = CerebroIcaro()
        self.audio = AudioManager()

    def arrancar(self):
        self.audio.hablar("Sistema fusionado correctamente.")
