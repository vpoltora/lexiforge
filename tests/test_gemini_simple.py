import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from lexiforge import ai_client


class TestGeminiSimple(unittest.TestCase):
    def setUp(self) -> None:
        self.test_cases = [
            ("Spanish", "hablar", "English", "to speak"),
            ("French", "parler", "English", "to speak"),
            ("German", "sprechen", "English", "to speak"),
            ("Russian", "говорить", "English", "to speak"),
            ("Japanese", "話す", "English", "to speak"),
            ("English", "hello", "French", "bonjour"),
        ]

    @patch("lexiforge.ai_client.urllib.request.urlopen")
    def test_generate_content_with_mocked_responses(self, mock_urlopen) -> None:
        for source, word, target, definition in self.test_cases:
            with self.subTest(source=source, word=word, target=target):
                mock_response = MagicMock()
                payload = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": f"BASE_FORM: {word}\nDEFINITION: {definition}\nEXAMPLE: Example sentence for {word}."
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

                result_definition, example, base_form = ai_client.generate_content(
                    word, source, "fake_api", definition_lang=target
                )

                self.assertEqual(base_form, word)
                self.assertEqual(result_definition, definition)
                self.assertIn(word, example)

    def test_parse_response_handles_missing_fields(self) -> None:
        text = "BASE_FORM: test"
        definition, example, base_form = ai_client.parse_response(text)
        self.assertEqual(base_form, "test")
        self.assertEqual(definition, "")
        self.assertEqual(example, "")


if __name__ == "__main__":
    unittest.main()
