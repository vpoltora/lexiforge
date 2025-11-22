import unittest
import os
import sys
from unittest.mock import MagicMock

# Add the parent directory to sys.path to import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vocabai import ai_client, tts_client
from vocabai import get_config

class TestVocabAI(unittest.TestCase):
    def setUp(self):
        self.config = get_config()
        if not self.config or not self.config.get("api_key"):
            self.fail("Config not found or API Key missing. Please restore config.json with a valid key.")
        self.api_key = self.config["api_key"]
        self.model = self.config.get("model", "gemini-flash-latest")

    def test_generate_content_spanish_to_english(self):
        # Test case: Spanish word "gato" -> English definition
        word = "gato"
        source_lang = "Spanish"
        definition_lang = "English"
        
        print(f"\nTesting: {word} ({source_lang}) -> {definition_lang}")
        definition, example, base_form = ai_client.generate_content(word, source_lang, self.api_key, self.model, definition_lang)
        
        print(f"Base Form: {base_form}")
        print(f"Definition: {definition}")
        print(f"Example: {example}")

        # Checks
        self.assertTrue(base_form.lower() == "gato", f"Base form should be 'gato', got '{base_form}'")
        # Definition should be in English (contains English words)
        self.assertTrue(any(w in definition.lower() for w in ["cat", "animal", "feline"]), "Definition should contain English translation")
        
        # Example should be in Spanish (source language)
        # Simple check: should contain common Spanish words or the word itself
        self.assertTrue("gato" in example.lower() or "el" in example.lower() or "un" in example.lower(), "Example should be in Spanish")

    def test_generate_content_english_to_russian(self):
        # Test case: English word "run" -> Russian definition
        word = "ran" # Past tense to check base form
        source_lang = "English"
        definition_lang = "Russian"
        
        print(f"\nTesting: {word} ({source_lang}) -> {definition_lang}")
        definition, example, base_form = ai_client.generate_content(word, source_lang, self.api_key, self.model, definition_lang)
        
        print(f"Base Form: {base_form}")
        print(f"Definition: {definition}")
        print(f"Example: {example}")

        self.assertEqual(base_form.lower(), "run", f"Base form should be 'run', got '{base_form}'")
        # Definition should be in Russian
        # Check for cyrillic characters
        self.assertTrue(any("\u0400" <= c <= "\u04FF" for c in definition), "Definition should contain Cyrillic characters")
        
        # Example should be in English
        self.assertTrue(any(w in example.lower() for w in ["run", "running", "ran", "he", "she", "it"]), "Example should be in English")

    def test_audio_generation(self):
        # Test TTS generation
        word = "test"
        source_lang = "English"
        lang_code = tts_client.get_lang_code(source_lang)
        filename = f"test_audio_{lang_code}.mp3"
        path = os.path.join("test_audio_samples", filename)
        
        if os.path.exists(path):
            os.remove(path)
            
        success = tts_client.download_audio(word, source_lang, path)
        self.assertTrue(success, "Audio download should succeed")
        self.assertTrue(os.path.exists(path), "Audio file should exist")
        self.assertGreater(os.path.getsize(path), 0, "Audio file should not be empty")

if __name__ == '__main__':
    unittest.main()
