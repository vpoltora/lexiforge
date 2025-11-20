import urllib.request
import urllib.parse
import os

def get_lang_code(language):
    lang_map = {
        "russian": "ru",
        "english": "en",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "italian": "it",
        "portuguese": "pt-BR", # Default to Brazilian Portuguese for better quality
        "brazilian portuguese": "pt-BR",
        "chinese": "zh-CN",
        "japanese": "ja",
        "korean": "ko"
    }
    return lang_map.get(language.lower(), "en")

def download_audio(text, language, output_path):
    lang_code = get_lang_code(language)
    
    # Google TTS API (unofficial)
    base_url = "https://translate.google.com/translate_tts"
    params = {
        "ie": "UTF-8",
        "q": text,
        "tl": lang_code,
        "client": "tw-ob"
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        # Use a custom User-Agent to avoid 403 errors
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            data = response.read()
            
        with open(output_path, "wb") as f:
            f.write(data)
            
        return True
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return False
