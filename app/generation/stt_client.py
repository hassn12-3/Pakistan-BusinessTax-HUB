import io
import speech_recognition as sr
from app.config import GOOGLE_API_KEY, GEMINI_MODEL

_recognizer = None


def get_recognizer() -> sr.Recognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = sr.Recognizer()
    return _recognizer


def transcribe_audio(audio_bytes: bytes, language: str = "English") -> str:
    """
    Transcribes spoken voice audio (WAV) into text.
    Uses Google Speech Recognition engine with language codes:
      - Urdu: 'ur-PK'
      - English / Roman Urdu: 'en-US' or 'ur-PK'
    """
    if not audio_bytes:
        return ""

    r = get_recognizer()
    lang_code = "ur-PK" if language == "Urdu (اردو)" else "en-US"

    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language=lang_code)
            return text.strip()
    except sr.UnknownValueError:
        # Try alternate language code if first attempt was unclear
        try:
            alt_lang = "ur-PK" if lang_code == "en-US" else "en-US"
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language=alt_lang)
                return text.strip()
        except Exception:
            return ""
    except Exception as e:
        print(f"STT Error: {e}")
        return ""
