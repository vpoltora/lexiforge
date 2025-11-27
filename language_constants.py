"""
Language constants for LexiForge plugin.
Contains the 20 most popular world languages supported by both Gemini API and Google Translate TTS.
"""

# Supported languages mapping: Display Name -> ISO Code for Google TTS
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Mandarin Chinese": "zh-CN",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "Arabic": "ar",
    "Bengali": "bn",
    "Russian": "ru",
    "Portuguese": "pt-BR",
    "Urdu": "ur",
    "Indonesian": "id",
    "German": "de",
    "Japanese": "ja",
    "Turkish": "tr",
    "Korean": "ko",
    "Vietnamese": "vi",
    "Italian": "it",
    "Tamil": "ta",
    "Thai": "th",
    "Polish": "pl",
}

# Get sorted list of language names for UI dropdowns
LANGUAGE_NAMES = sorted(SUPPORTED_LANGUAGES.keys())


def get_lang_code(language_name: str) -> str:
    """
    Get the ISO language code for a given language name.

    Args:
        language_name: Display name of the language (e.g., "English")

    Returns:
        ISO language code (e.g., "en"), defaults to "en" if not found
    """
    return SUPPORTED_LANGUAGES.get(language_name, "en")
