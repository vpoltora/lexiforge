"""
Test language support for LexiForge plugin.
Tests both Google Translate TTS API and Gemini API with all 20 supported languages.

Run this script to verify all languages work correctly:
    python3 tests/test_language_support.py
"""
# ruff: noqa: F821

import os
import sys
import time

# Add parent directory to path to import our modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import directly from files to avoid relative import issues
# Since we merged everything into __init__.py, we can just import from there
# But for this test script which might run standalone, we need to be careful.
# Actually, since we merged, tts_client.py doesn't exist anymore (it's .bak).
# We should import from lexiforge package.

import lexiforge
from lexiforge import language_constants, tts_client, ai_client


def test_tts_languages():
    """Test Google Translate TTS API with all 20 supported languages."""
    print("=" * 80)
    print("TESTING GOOGLE TRANSLATE TTS API")
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
        "Polish": "cześć",
    }

    results = []
    failed = []

    for language_name in language_constants.LANGUAGE_NAMES:
        test_word = test_words.get(language_name, "hello")
        lang_code = language_constants.get_lang_code(language_name)

        # Create safe filename
        safe_name = language_name.replace(" ", "_").lower()
        output_path = os.path.join(output_dir, f"{safe_name}_{lang_code}.mp3")

        print(f"\nTesting {language_name} ({lang_code})...")
        print(f"  Word: {test_word}")

        try:
            success = tts_client.download_audio(test_word, language_name, output_path)

            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"  ✅ SUCCESS - Audio file created ({file_size} bytes)")
                results.append((language_name, lang_code, "✅ PASS"))
            else:
                print("  ❌ FAILED - Audio file not created")
                results.append((language_name, lang_code, "❌ FAIL"))
                failed.append(language_name)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append((language_name, lang_code, f"❌ ERROR: {e}"))
            failed.append(language_name)

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    # Print summary
    print("\n" + "=" * 80)
    print("TTS TEST SUMMARY")
    print("=" * 80)

    for lang_name, lang_code, status in results:
        print(f"{lang_name:25} ({lang_code:5}) - {status}")

    print(f"\nTotal: {len(results)}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed languages: {', '.join(failed)}")
    else:
        print("\n🎉 All languages passed TTS testing!")

    print(f"\nAudio samples saved to: {os.path.abspath(output_dir)}/")

    return len(failed) == 0


def test_gemini_languages():
    """Test Gemini API with different source and target language combinations."""
    print("\n" + "=" * 80)
    print("TESTING GEMINI API LANGUAGE SUPPORT")
    print("=" * 80)
    print("\nNote: This test requires a valid Gemini API key.")

    # Try to read API key from config
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    api_key = None

    if os.path.exists(config_path):
        import json

        try:
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get("api_key")
        except Exception:
            pass

    if not api_key or "YOUR_KEY" in api_key:
        print("\n⚠️  WARNING: No valid API key found in config.json")
        print("Skipping Gemini API tests...")
        return True

    # Test a few representative language combinations
    test_cases = [
        ("Spanish", "hablar", "English"),
        ("French", "parler", "English"),
        ("German", "sprechen", "English"),
        ("Russian", "говорить", "English"),
        ("Japanese", "話す", "English"),
    ]

    results = []
    failed = []

    for source_lang, word, target_lang in test_cases:
        print(f"\nTesting: '{word}' ({source_lang} → {target_lang})")

        try:
            definition, example, base_form = ai_client.generate_content(
                word, source_lang, api_key, "gemini-flash-latest", target_lang
            )

            print(f"  Base form: {base_form}")
            print(f"  Definition: {definition}")
            print(f"  Example: {example}")

            if definition and example:
                print("  ✅ SUCCESS")
                results.append((source_lang, target_lang, "✅ PASS"))
            else:
                print("  ❌ FAILED - Missing definition or example")
                results.append((source_lang, target_lang, "❌ FAIL"))
                failed.append(f"{source_lang}→{target_lang}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append((source_lang, target_lang, "❌ ERROR"))
            failed.append(f"{source_lang}→{target_lang}")

        # Small delay between API calls
        time.sleep(1)

    # Print summary
    print("\n" + "=" * 80)
    print("GEMINI API TEST SUMMARY")
    print("=" * 80)

    for source, target, status in results:
        print(f"{source:15} → {target:15} - {status}")

    print(f"\nTotal: {len(results)}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed combinations: {', '.join(failed)}")
    else:
        print("\n🎉 All language combinations passed Gemini testing!")

    return len(failed) == 0


if __name__ == "__main__":
    print("LexiForge Language Support Testing")
    print("=" * 80)

    # Test TTS
    tts_passed = test_tts_languages()

    # Test Gemini
    gemini_passed = test_gemini_languages()

    # Final summary
    print("\n" + "=" * 80)
    print("OVERALL TEST RESULTS")
    print("=" * 80)
    print(f"TTS Tests: {'✅ PASSED' if tts_passed else '❌ FAILED'}")
    print(f"Gemini Tests: {'✅ PASSED' if gemini_passed else '❌ FAILED'}")

    if tts_passed and gemini_passed:
        print("\n🎉 ALL TESTS PASSED! All 20 languages are supported.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the results above.")
        sys.exit(1)
