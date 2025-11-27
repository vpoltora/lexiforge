import urllib.parse
import urllib.request

# Import language constants
# Use absolute import to avoid relative import issues in some environments
try:
    import lexiforge.language_constants as language_constants
except ImportError:
    # Fallback for tests or direct execution
    try:
        from . import language_constants
    except ImportError:
        import language_constants


def get_lang_code(language_name: str) -> str:
    """
    Get the ISO language code for a given language name.
    Uses the centralized SUPPORTED_LANGUAGES dictionary.

    Args:
        language_name: Display name of the language (e.g., "English")

    Returns:
        ISO language code (e.g., "en"), defaults to "en" if not found
    """
    return language_constants.get_lang_code(language_name)


def download_audio(text: str, language_name: str, output_path: str) -> bool:
    """
    Download TTS audio from Google Translate for the given text.

    Args:
        text: Text to convert to speech
        language_name: Display name of the language (e.g., "English")
        output_path: Path where the audio file will be saved

    Returns:
        True if successful, False otherwise
    """
    lang_code = get_lang_code(language_name)

    # Google TTS API (unofficial)
    base_url = "https://translate.google.com/translate_tts"
    params = {"ie": "UTF-8", "q": text, "tl": lang_code, "client": "tw-ob"}

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        # Use a custom User-Agent to avoid 403 errors
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req) as response:
            data = response.read()

        with open(output_path, "wb") as f:
            f.write(data)

        print(
            f"LexiForge: TTS audio downloaded successfully for '{text}' in {language_name} ({lang_code})"
        )
        return True
    except Exception as e:
        print(
            f"LexiForge: Error downloading audio for {language_name} ({lang_code}): {e}"
        )
        return False
