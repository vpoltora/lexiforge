import unittest
import os
import sys
import time

# Add the parent directory of the project to sys.path
# We need to go up 3 levels: tests -> vocabai -> python (root)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import MagicMock

# Mock Anki modules before importing vocabai
sys.modules['aqt'] = MagicMock()
sys.modules['aqt.qt'] = MagicMock()
sys.modules['aqt.utils'] = MagicMock()
sys.modules['anki'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()

from vocabai import ai_client, tts_client, get_config

class TestVocabAIPopular(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = get_config()
        if not cls.config or not cls.config.get("api_key"):
            raise ValueError("Config not found or API Key missing.")
        cls.api_key = cls.config["api_key"]
        cls.model = cls.config.get("model", "gemini-flash-latest")
        
        # 5 Popular Languages to test
        # Format: (Source, Definition, Word to test, Expected Base Form)
        cls.test_cases = [
            ("Spanish", "English", "comiendo", "comer"),
            ("French", "English", "allé", "aller"),
            ("German", "English", "gegangen", "gehen"),
            ("Italian", "English", "mangiato", "mangiare"),
            ("Portuguese", "English", "falando", "falar")
        ]

    def test_popular_languages(self):
        for source, definition_lang, word, expected_base in self.test_cases:
            with self.subTest(source=source, word=word):
                print(f"\nTesting {source}: {word} -> {definition_lang}")
                definition, example, base_form = ai_client.generate_content(word, source, self.api_key, self.model, definition_lang)
                
                print(f"  Base: {base_form}")
                print(f"  Def: {definition}")
                print(f"  Ex: {example}")
                
                # 1. Check Base Form
                self.assertEqual(base_form.lower(), expected_base.lower(), f"Base form for {word} should be {expected_base}")
                
                # 2. Check Definition Language (English)
                # Simple heuristic: check for common English words
                self.assertTrue(any(w in definition.lower() for w in ["to", "the", "a", "an", "eat", "go", "speak"]), f"Definition for {word} should be in English")
                
                # 3. Check Example Language (Source)
                # Heuristic: Check if the example contains the base form or the word itself (often true)
                # Or check for common words in that language if possible, but that's hard.
                # We rely on the prompt being obeyed.
                self.assertTrue(len(example) > 5, "Example should not be empty")
                
                # 4. Check Audio Generation
                safe_word = "".join([c for c in base_form if c.isalnum() or c in (' ', '-', '_')]).strip()
                lang_code = tts_client.get_lang_code(source)
                filename = f"test_{safe_word}_{lang_code}.mp3"
                path = os.path.join("test_audio_samples", filename)
                
                if os.path.exists(path):
                    os.remove(path)
                    
                success = tts_client.download_audio(base_form, source, path)
                self.assertTrue(success, f"Audio generation failed for {source}")
                self.assertTrue(os.path.exists(path), f"Audio file missing for {source}")
                
                time.sleep(1) # Avoid rate limits

if __name__ == '__main__':
    unittest.main()
