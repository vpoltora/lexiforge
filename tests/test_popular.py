import os
import sys
import unittest

# Add the parent directory of the project to sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from unittest.mock import MagicMock, patch

# Mock Anki modules before importing lexiforge
sys.modules["aqt"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["aqt.utils"] = MagicMock()
sys.modules["anki"] = MagicMock()
sys.modules["anki.hooks"] = MagicMock()

from lexiforge import ai_client, tts_client


class TestLexiForgePopular(unittest.TestCase):
    def setUp(self) -> None:
        # Test cases: (Source, Definition Lang, Word, Expected Base, Expected Definition, Expected Example)
        self.test_cases = [
            ("Spanish", "English", "comiendo", "comer", "to eat", "Estoy comiendo una manzana."),
            ("French", "English", "allé", "aller", "to go", "Je suis allé au marché."),
            ("German", "English", "gegangen", "gehen", "to go", "Ich bin nach Hause gegangen."),
            ("Italian", "English", "mangiato", "mangiare", "to eat", "Ho mangiato la pizza."),
            ("Portuguese", "English", "falando", "falar", "to speak", "Estou falando português."),
        ]

    @patch('lexiforge.ai_client.urllib.request.urlopen')
    @patch('lexiforge.tts_client.urllib.request.urlopen')
    def test_popular_languages(self, mock_tts_urlopen, mock_urlopen) -> None:
        for source, definition_lang, word, expected_base, expected_def, expected_ex in self.test_cases:
            with self.subTest(source=source, word=word):
                # Mock AI response
                mock_response = MagicMock()
                mock_response.read.return_value = f'''{{
                    "candidates": [{{
                        "content": {{
                            "parts": [{{
                                "text": "BASE_FORM: {expected_base}\\nDEFINITION: {expected_def}\\nEXAMPLE: {expected_ex}"
                            }}]
                        }}
                    }}]
                }}'''.encode('utf-8')
                mock_response.__enter__.return_value = mock_response
                mock_response.__exit__.return_value = None
                mock_urlopen.return_value = mock_response

                # Mock TTS download
                tts_response = MagicMock()
                tts_response.read.return_value = b"fake-bytes"
                tts_response.__enter__.return_value = tts_response
                tts_response.__exit__.return_value = None
                mock_tts_urlopen.return_value = tts_response

                definition, example, base_form = ai_client.generate_content(
                    word, source, "fake_api_key", "gemini-flash-latest", definition_lang
                )

                # Verify results
                self.assertEqual(base_form, expected_base)
                self.assertEqual(definition, expected_def)
                self.assertEqual(example, expected_ex)

                # Test TTS client
                lang_code = tts_client.get_lang_code(source)
                self.assertIsNotNone(lang_code)

                # Test audio download (mocked)
                output_path = "test.mp3"
                success = tts_client.download_audio(base_form, source, output_path)
                self.assertTrue(success)
                if os.path.exists(output_path):
                    os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
