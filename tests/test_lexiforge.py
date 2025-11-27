import os
import sys
import unittest

# Add the parent directory to sys.path to import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch
sys.modules["aqt"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["anki"] = MagicMock()
sys.modules["anki.hooks"] = MagicMock()

from lexiforge import ai_client, tts_client


class TestLexiForge(unittest.TestCase):
    @patch('lexiforge.ai_client.urllib.request.urlopen')
    def test_generate_content_spanish_to_english(self, mock_urlopen) -> None:
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = b'''{
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "BASE_FORM: gato\\nDEFINITION: cat\\nEXAMPLE: El gato es muy lindo."
                    }]
                }
            }]
        }'''
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        word = "gato"
        source_lang = "Spanish"
        definition_lang = "English"

        definition, example, base_form = ai_client.generate_content(
            word, source_lang, "fake_api_key", "gemini-flash-latest", definition_lang
        )

        # Checks
        self.assertEqual(base_form, "gato")
        self.assertEqual(definition, "cat")
        self.assertIn("gato", example.lower())

    @patch('lexiforge.ai_client.urllib.request.urlopen')
    def test_generate_content_english_to_russian(self, mock_urlopen) -> None:
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = b'''{
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "BASE_FORM: run\\nDEFINITION: \\u0431\\u0435\\u0436\\u0430\\u0442\\u044c\\nEXAMPLE: He ran to the store."
                    }]
                }
            }]
        }'''
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        word = "ran"
        source_lang = "English"
        definition_lang = "Russian"

        definition, example, base_form = ai_client.generate_content(
            word, source_lang, "fake_api_key", "gemini-flash-latest", definition_lang
        )

        self.assertEqual(base_form, "run")
        # Check for Cyrillic characters in definition
        self.assertTrue(
            any("\u0400" <= c <= "\u04ff" for c in definition),
            "Definition should contain Cyrillic characters",
        )
        self.assertIn("ran", example.lower())

    @patch('lexiforge.tts_client.urllib.request.urlopen')
    def test_audio_generation(self, mock_urlopen) -> None:
        # Mock TTS download
        mock_response = MagicMock()
        mock_response.read.return_value = b"audio-bytes"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        word = "test"
        source_lang = "English"
        lang_code = tts_client.get_lang_code(source_lang)

        self.assertEqual(lang_code, "en")

        # Test audio download with mock
        output_path = "test_audio.mp3"
        success = tts_client.download_audio(word, source_lang, output_path)
        self.assertTrue(success, "Audio download should succeed")
        mock_urlopen.assert_called_once()
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
