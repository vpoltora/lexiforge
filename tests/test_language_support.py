import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

sys.modules["aqt"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["aqt.utils"] = MagicMock()
sys.modules["anki"] = MagicMock()
sys.modules["anki.hooks"] = MagicMock()

from lexiforge import ai_client, language_constants, tts_client


class TestLanguageSupport(unittest.TestCase):
    def test_all_languages_have_codes(self) -> None:
        missing = [
            lang
            for lang in language_constants.LANGUAGE_NAMES
            if not language_constants.get_lang_code(lang)
        ]
        self.assertListEqual(missing, [])

    @patch("lexiforge.tts_client.urllib.request.urlopen")
    def test_tts_download_mocked(self, mock_urlopen) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"audio"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        for language in language_constants.LANGUAGE_NAMES[:5]:
            with self.subTest(language=language):
                output_path = f"test_{language}.mp3"
                success = tts_client.download_audio("hello", language, output_path)
                self.assertTrue(success)
                if os.path.exists(output_path):
                    os.remove(output_path)

    @patch("lexiforge.ai_client.urllib.request.urlopen")
    def test_ai_generation_mocked(self, mock_urlopen) -> None:
        mock_response = MagicMock()
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "BASE_FORM: hola\nDEFINITION: hello\nEXAMPLE: Hola, mundo."
                            }
                        ]
                    }
                }
            ]
        }
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        definition, example, base_form = ai_client.generate_content(
            "hola", "Spanish", "fake", definition_lang="English"
        )

        self.assertEqual(base_form, "hola")
        self.assertEqual(definition, "hello")
        self.assertIn("Hola", example)


if __name__ == "__main__":
    unittest.main()
