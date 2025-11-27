import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from lexiforge import language_constants, tts_client


class TestTTSSimple(unittest.TestCase):
    def test_supported_languages_subset(self) -> None:
        for language in language_constants.LANGUAGE_NAMES:
            code = language_constants.get_lang_code(language)
            self.assertTrue(code)

    @patch("lexiforge.tts_client.urllib.request.urlopen")
    def test_download_audio_mocked(self, mock_urlopen) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"audio"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        languages = language_constants.LANGUAGE_NAMES[:3]
        for language in languages:
            with self.subTest(language=language):
                path = f"test_{language}.mp3"
                success = tts_client.download_audio("sample", language, path)
                self.assertTrue(success)
                self.assertTrue(os.path.exists(path))
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
