"""Unit tests for LexiForge core functionality."""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Add parent directory to path (go up from tests/ to python/ directory)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock Anki modules before importing
sys.modules["aqt"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["aqt.utils"] = MagicMock()
sys.modules["anki"] = MagicMock()
sys.modules["anki.hooks"] = MagicMock()

from lexiforge import ai_client
from lexiforge import language_constants


class TestLanguageConstants(unittest.TestCase):
    """Test language code mappings."""

    def test_get_lang_code_known_language(self) -> None:
        """Test known language codes."""
        self.assertEqual(language_constants.get_lang_code("English"), "en")
        self.assertEqual(language_constants.get_lang_code("Spanish"), "es")
        self.assertEqual(language_constants.get_lang_code("Mandarin Chinese"), "zh-CN")
        self.assertEqual(language_constants.get_lang_code("Portuguese"), "pt-BR")

    def test_get_lang_code_unknown_language(self) -> None:
        """Test fallback for unknown languages."""
        self.assertEqual(language_constants.get_lang_code("Unknown"), "en")
        self.assertEqual(language_constants.get_lang_code(""), "en")


class TestResponseParsing(unittest.TestCase):
    """Test AI response parsing."""

    def test_parse_response_complete(self) -> None:
        """Test parsing a complete response."""
        text = """BASE_FORM: run
DEFINITION: to move quickly on foot
EXAMPLE: She runs every morning."""

        definition, example, base_form = ai_client.parse_response(text)

        self.assertEqual(base_form, "run")
        self.assertEqual(definition, "to move quickly on foot")
        self.assertEqual(example, "She runs every morning.")

    def test_parse_response_with_markdown(self) -> None:
        """Test parsing response with markdown formatting."""
        text = """**BASE_FORM:** run
**DEFINITION:** to move quickly on foot
**EXAMPLE:** She runs every morning."""

        definition, _example, base_form = ai_client.parse_response(text)

        self.assertEqual(base_form, "run")
        self.assertIn("move quickly", definition)

    def test_parse_response_missing_fields(self) -> None:
        """Test parsing incomplete response."""
        text = """BASE_FORM: run"""

        definition, example, base_form = ai_client.parse_response(text)

        self.assertEqual(base_form, "run")
        self.assertEqual(definition, "")
        self.assertEqual(example, "")


class TestPromptTemplates(unittest.TestCase):
    """Test prompt templates."""

    def test_default_prompt_template_has_variables(self) -> None:
        """Test that default prompt contains expected variables."""
        template = ai_client.get_default_prompt_template()

        self.assertIn("{{word}}", template)
        self.assertIn("{{source_lang}}", template)
        self.assertIn("{{definition_lang}}", template)

    def test_story_prompt_template_has_variables(self) -> None:
        """Test that story prompt contains expected variables."""
        template = ai_client.get_default_story_prompt_template()

        self.assertIn("{{words}}", template)
        self.assertIn("{{level}}", template)
        self.assertIn("{{word_count}}", template)


if __name__ == "__main__":
    unittest.main()
