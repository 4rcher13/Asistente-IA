import os
import time
import threading
import logging
import queue
from typing import Optional, Callable

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

import pyttsx3
import speech_recognition as sr
import webrtcvad

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False
    logging.warning("sounddevice no está instalado. VAD Real desactivado.")

from ..config.settings import (
    VOICE_RATE,
    TIMEOUT_SILENCIO,
    LIMITE_SEGUNDOS,
    MIC_INDEX,
    AUDIO_RATE,
    VAD_AGGRESSIVENESS,
)

logger = logging.getLogger(__name__)

_POST_SPEECH_DELAY = 0.15

class AudioService:
    """Maneja entrada (micrófono) y salida (voz) optimizado con WebRTC VAD y sounddevice."""

    def __init__(self, microphone=None, on_feedback: Optional[Callable[[str], None]] = None):
        self.recognizer = sr.Recognizer()
        self.microphone = microphone
        self.on_feedback = on_feedback
        
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS) if SD_AVAILABLE else None
        
        # TTS worker
        self._tts_queue: queue.Queue = queue.Queue()
        self._tts_worker_thread = threading.Thread(
            target=self._tts_worker, daemon=True, name="IcaroTTS"
        )
        self._tts_worker_thread.start()

    def _find_voice_id(self) -> Optional[str]:
        """Busca la voz en español UNA sola vez."""
        try:
            engine = pyttsx3.init()
            voces = engine.getProperty("voices")
            voz_es = next(
                (v for v in (voces or []) if any(
                    idioma in v.name.lower() for idioma in ("spanish", "sabina", "helena")
                )), None
            )
            voice_id = voz_es.id if voz_es else (voces[0].id if voces else None)
            engine.stop()
            return voice_id
        except Exception as exc:
            logger.error(f"Error buscando voz TTS: {exc}")
            return None

    def _tts_worker(self) -> None:
        """Worker asíncrono para TTS — el engine pyttsx3 se crea UNA sola vez."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass

        # Buscamos el voice_id UNA sola vez (esto es lo que demoraba 2s).
        voice_id = None
        try:
            voice_id = self._find_voice_id()
        except Exception:
            pass

        engine = None
        while True:
            try:
                item = self._tts_queue.get(timeout=0.5)
                if item is None:
                    break
                texto, evento = item
                evento.clear()
                
                # Inicializar el engine *justo antes* de hablar.
                # SAPI5 cachea el objeto COM, por lo que toma 0.000s después de la 1ra vez.
                # Esto previene cuelgues del hilo y fallos silenciosos.
                engine = None
                try:
                    engine = pyttsx3.init()
                    if voice_id:
                        engine.setProperty("voice", voice_id)
                    engine.setProperty("rate", VOICE_RATE)
                    engine.setProperty("volume", 1.0)
                    
                    engine.say(texto)
                    engine.runAndWait()
                except Exception as exc:
                    logger.error(f"Error reproduciendo TTS: {exc}")
                finally:
                    if engine:
                        try:
                            engine.stop()
                        except Exception:
                            pass
                    evento.set()
            except queue.Empty:
                continue

        # Limpieza final
        if engine:
            try:
                engine.stop()
            except Exception:
                pass
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except ImportError:
            pass

    def hablar(self, texto: str, post_delay: float = _POST_SPEECH_DELAY) -> None:
        """Sintetiza texto a voz usando el queue."""
        if not texto:
            return
        texto_limpio = texto.replace("*", "").replace("#", "").replace("`", "").strip()
        if not texto_limpio:
            return
        
        logger.info(f"Ícaro: {texto_limpio}")
        
        # pyttsx3 (SAPI5) se corta con textos muy largos. Dividimos por oraciones/saltos de línea.
        import re
        frases = [f.strip() for f in re.split(r'(?<=[.!?\n])\s+', texto_limpio) if f.strip()]
        
        for frase in frases:
            evento = threading.Event()
            self._tts_queue.put((frase, evento))
            # Tiempo máximo de espera por cada frase
            evento.wait(timeout=30)
        

        if post_delay > 0:
            time.sleep(post_delay)

    def _notificar_usuario(self, mensaje: str) -> None:
        if self.on_feedback:
            self.on_feedback(mensaje)
        else:
            self.hablar(mensaje)

    def escuchar_vad(self) -> str:
        """
        Escucha usando WebRTC VAD y sounddevice para latencia cero al finalizar.
        """
        frame_duration_ms = 30
        frame_size = int(AUDIO_RATE * (frame_duration_ms / 1000.0))
        
        q = queue.Queue()
        
        def audio_callback(indata, frames, time_info, status):
            # indata es float32 [-1.0, 1.0]. webrtcvad necesita int16 bytes.
            # numpy se importa al nivel del módulo, no aquí (evita overhead por frame)
            if _NUMPY_AVAILABLE:
                audio_data = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            else:
                import array
                samples = [int(s * 32767) for s in indata[:, 0]]
                audio_data = array.array('h', samples).tobytes()
            q.put(audio_data)

        # Buffer para guardar el audio útil
        audio_buffer = []
        triggered = False
        silence_frames = 0
        # Tolerancia: X frames de silencio = cortar escucha
        MAX_SILENCE_FRAMES = int(TIMEOUT_SILENCIO * 1000 / frame_duration_ms) 
        
        logger.debug("Escuchando (VAD Real)...")
        
        try:
            with sd.InputStream(samplerate=AUDIO_RATE, channels=1, dtype='float32', blocksize=frame_size, callback=audio_callback):
                start_time = time.time()
                
                while True:
                    if time.time() - start_time > LIMITE_SEGUNDOS:
                        logger.debug("Timeout de grabación alcanzado.")
                        break
                        
                    frame = q.get()
                    
                    try:
                        is_speech = self.vad.is_speech(frame, AUDIO_RATE)
                    except Exception as e:
                        logger.error(f"VAD Error: {e}")
                        is_speech = False

                    if not triggered:
                        if is_speech:
                            triggered = True
                            audio_buffer.append(frame)
                            logger.debug("Voz detectada.")
                    else:
                        audio_buffer.append(frame)
                        if not is_speech:
                            silence_frames += 1
                            if silence_frames > MAX_SILENCE_FRAMES:
                                logger.debug("Fin de voz detectado.")
                                break
                        else:
                            silence_frames = 0

            if not audio_buffer:
                return ""

            # Reconstruir audio completo
            raw_audio = b''.join(audio_buffer)
            
            # Pasar a speech_recognition
            audio_data = sr.AudioData(raw_audio, AUDIO_RATE, 2) # 2 bytes = 16 bit
            
            comando = self.recognizer.recognize_google(audio_data, language="es-ES")
            comando = comando.lower().strip()
            logger.info(f"Usuario: '{comando}'")
            return comando

        except sr.UnknownValueError:
            return ""
        except Exception as e:
            logger.error(f"Error en VAD escuchar: {e}")
            return ""

    def escuchar_legacy(self, timeout_silencio=TIMEOUT_SILENCIO, limite_segundos=LIMITE_SEGUNDOS) -> str:
        """Fallback a speech_recognition tradicional si VAD/sounddevice falla."""
        try:
            if self.microphone is None:
                self.microphone = sr.Microphone(device_index=MIC_INDEX)

            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.recognizer.pause_threshold = timeout_silencio
                audio = self.recognizer.listen(source, timeout=limite_segundos, phrase_time_limit=15)
                comando = self.recognizer.recognize_google(audio, language="es-ES")
                return comando.lower().strip()
        except Exception:
            return ""

    def escuchar(
        self,
        timeout_silencio: Optional[float] = None,
        limite_segundos: Optional[int] = None,
        phrase_time_limit: int = 15,
        **kwargs,
    ) -> str:
        # Compatibilidad con tests/código antiguo que usaba limite_segundo
        if limite_segundos is None and "limite_segundo" in kwargs:
            limite_segundos = kwargs["limite_segundo"]
        ts = timeout_silencio if timeout_silencio is not None else TIMEOUT_SILENCIO
        ls = limite_segundos if limite_segundos is not None else LIMITE_SEGUNDOS
        if SD_AVAILABLE and self.vad:
            return self.escuchar_vad()
        return self.escuchar_legacy(timeout_silencio=ts, limite_segundos=ls)
    
    def shutdown(self) -> None:
        """Detiene el TTS worker y libera recursos."""
        self._tts_queue.put(None)
        if self._tts_worker_thread.is_alive():
            self._tts_worker_thread.join(timeout=5)
            logger.info("TTS worker detenido")