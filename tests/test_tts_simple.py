"""
Test Google Translate TTS API support for all 20 languages.
This is a standalone test script.

Run this script to verify TTS works for all languages:
    python3 tests/test_tts_simple.py
"""

import os
import sys
import time
import urllib.request
import urllib.parse

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
    "Polish": "pl"
}

LANGUAGE_NAMES = sorted(SUPPORTED_LANGUAGES.keys())

def download_audio(text, language_name, output_path):
    """Download TTS audio from Google Translate for the given text."""
    lang_code = SUPPORTED_LANGUAGES.get(language_name, "en")
    
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
        print(f"    Error: {e}")
        return False

def test_tts_languages():
    """Test Google Translate TTS API with all 20 supported languages."""
    print("=" * 80)
    print("TESTING GOOGLE TRANSLATE TTS API - 20 LANGUAGES")
    print("=" * 80)
    
    # Create output directory for test audio files
    output_dir = "test_audio_samples"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test words for each language (simple common words)
    test_words = {
        "English": "hello",
        "Mandarin Chinese": "你好",
        "Hindi": "नमस्ते",
        "Spanish": "hola",
        "French": "bonjour",
        "Arabic": "مرحبا",
        "Bengali": "হ্যালো",
        "Russian": "привет",
        "Portuguese": "olá",
        "Urdu": "ہیلو",
        "Indonesian": "halo",
        "German": "hallo",
        "Japanese": "こんにちは",
        "Turkish": "merhaba",
        "Korean": "안녕하세요",
        "Vietnamese": "xin chào",
        "Italian": "ciao",
        "Tamil": "வணக்கம்",
        "Thai": "สวัสดี",
        "Polish": "cześć"
    }
    
    results = []
    failed = []
    
    for i, language_name in enumerate(LANGUAGE_NAMES, 1):
        test_word = test_words.get(language_name, "hello")
        lang_code = SUPPORTED_LANGUAGES[language_name]
        
        # Create safe filename
        safe_name = language_name.replace(" ", "_").lower()
        output_path = os.path.join(output_dir, f"{safe_name}_{lang_code}.mp3")
        
        print(f"\n[{i}/20] Testing {language_name} ({lang_code})...")
        print(f"    Word: {test_word}")
        
        try:
            success = download_audio(test_word, language_name, output_path)
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"    ✅ SUCCESS - Audio file created ({file_size} bytes)")
                results.append((language_name, lang_code, "✅ PASS", file_size))
            else:
                print(f"    ❌ FAILED - Audio file not created")
                results.append((language_name, lang_code, "❌ FAIL", 0))
                failed.append(language_name)
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            results.append((language_name, lang_code, f"❌ ERROR", 0))
            failed.append(language_name)
        
        # Small delay to avoid rate limiting
        time.sleep(0.3)
    
    # Print summary table
    print("\n" + "=" * 80)
    print("TTS TEST SUMMARY")
    print("=" * 80)
    print(f"{'Language':<25} {'Code':<8} {'Status':<15} {'Size (bytes)'}")
    print("-" * 80)
    
    for lang_name, lang_code, status, size in results:
        size_str = str(size) if size > 0 else "-"
        print(f"{lang_name:<25} {lang_code:<8} {status:<15} {size_str}")
    
    print("=" * 80)
    print(f"Total: {len(results)}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\n❌ Failed languages: {', '.join(failed)}")
        return False
    else:
        print(f"\n🎉 ALL 20 LANGUAGES PASSED TTS TESTING!")
        print(f"\nAudio samples saved to: {os.path.abspath(output_dir)}/")
        return True

if __name__ == "__main__":
    success = test_tts_languages()
    sys.exit(0 if success else 1)
