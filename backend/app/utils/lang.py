"""
Language detection and voice/WPM mapping.
Phase 1: keyword-based heuristic. Phase 2: LLM or langdetect.
"""
import re

# BCP-47 tag → default edge-tts voice name
VOICE_MAP: dict[str, str] = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-AriaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural",
}

# Words-per-minute (or mora/min for JA) per language — used by Script Agent
WPM_MAP: dict[str, int] = {
    "vi": 150,
    "en": 160,
    "ja": 280,  # mora per minute
    "ko": 230,
    "zh": 180,
    "fr": 155,
    "de": 145,
    "es": 160,
}

# Unicode ranges for script detection
_CJK_RE = re.compile(r"[一-鿿㐀-䶿぀-ヿ가-힯]")
_VIETNAMESE_RE = re.compile(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]", re.IGNORECASE)


def detect_language(text: str) -> str:
    """
    Simple heuristic language detection from keyword text.
    Returns BCP-47 tag. Phase 2 replaces with LLM node.
    """
    if _CJK_RE.search(text):
        # CJK block heuristics
        if re.search(r"[぀-ヿ]", text):
            return "ja"
        if re.search(r"[가-힯]", text):
            return "ko"
        return "zh"
    if _VIETNAMESE_RE.search(text):
        return "vi"
    return "en"


def get_voice(language: str) -> str:
    return VOICE_MAP.get(language, VOICE_MAP["en"])


def get_wpm(language: str) -> int:
    return WPM_MAP.get(language, 160)
