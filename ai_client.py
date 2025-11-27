import json
import re
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_MODEL = "gemini-flash-latest"


def get_default_prompt_template() -> str:
    """Returns the default prompt template with variable placeholders."""
    return """Analyze the word '{{word}}' in {{source_lang}}.

1. Identify the BASE FORM (lemma) of the word.
2. Translate the BASE FORM to {{definition_lang}}.

Rules for the DEFINITION:
1. If the base form is a simple, common word (like 'cat', 'milk', 'run'), provide ONLY the direct one-word translation in {{definition_lang}}.
2. If it is complex, abstract, or ambiguous, provide the translation in {{definition_lang}} followed by a very short definition (4-7 words) in parentheses.

3. Provide 1 example sentence in {{source_lang}} using the word (or its base form).

Format the output exactly like this:
BASE_FORM: [The base form of the word in {{source_lang}}]
DEFINITION: [Translation/definition in {{definition_lang}}]
EXAMPLE: [Sentence in {{source_lang}} using the word]

Do not use markdown formatting."""


def generate_content(
    word: str,
    source_lang: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    definition_lang: str = "English",
    prompt_template: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Generate word definition and example using Gemini API.

    Args:
        word: The word to analyze
        source_lang: Language of the word or "Auto" for auto-detection
        api_key: Gemini API key
        model: Model to use (default: gemini-flash-latest)
        definition_lang: Language for definition (default: "English")
        prompt_template: Custom prompt template (uses default if None)

    Returns:
        Tuple of (definition, example, base_form)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    if prompt_template is None:
        prompt_template = get_default_prompt_template()

    # Handle Auto language detection
    actual_source = source_lang
    if source_lang.lower() == "auto":
        # Modify prompt to detect language first
        prompt_template = f"""First, detect the language of the word '{{{{word}}}}' and use that language as {{{{source_lang}}}}.

{prompt_template}"""
        actual_source = "the detected language"

    # Replace template variables
    prompt = prompt_template.replace("{{word}}", word)
    prompt = prompt.replace("{{source_lang}}", actual_source)
    prompt = prompt.replace("{{definition_lang}}", definition_lang)

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    headers = {"Content-Type": "application/json"}

    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Parse response
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"LexiForge Raw Response: {text}")  # Debug log
            return parse_response(text)
        except (KeyError, IndexError) as e:
            print(f"LexiForge Error parsing response: {e}")
            return (
                "Error parsing AI response",
                "",
                word,
            )  # Return original word as fallback

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"LexiForge HTTP Error {e.code}: {error_body}")

        # If model not found (404), try to list available models to help debug
        if e.code == 404:
            print("LexiForge: Model not found. Listing available models...")
            list_models(api_key)

        return f"API Error: {e.code}", "", word
    except Exception as e:
        print(f"LexiForge General Error: {e}")
        return f"Error: {e!s}", "", word


def parse_response(text: str) -> tuple[str, str, str]:
    """
    Parse the AI response text to extract definition, example, and base form.

    Args:
        text: The raw text response from the AI.

    Returns:
        Tuple of (definition, example, base_form)
    """
    definition = ""
    example = ""
    base_form = ""

    # Remove any markdown formatting if present
    text = text.replace("**", "").replace("*", "")

    # Use regex for more robust parsing
    base_form_match = re.search(r"BASE_FORM:\s*(.+)", text, re.IGNORECASE)
    definition_match = re.search(r"DEFINITION:\s*(.+)", text, re.IGNORECASE)
    example_match = re.search(r"EXAMPLE:\s*(.+)", text, re.IGNORECASE)

    base_form = base_form_match.group(1).strip() if base_form_match else ""
    definition = definition_match.group(1).strip() if definition_match else ""
    example = example_match.group(1).strip() if example_match else ""

    return definition, example, base_form


def list_models(api_key: str) -> list[dict[str, Any]]:
    """
    List available models from the Gemini API.

    Args:
        api_key: The API key to use.

    Returns:
        A list of model dictionaries.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

    try:
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode("utf-8"))
            models = result.get("models", [])
            print("LexiForge Available Models:")
            for m in models:
                print(f"- {m['name']} ({m.get('displayName', '')})")
            return models
    except Exception as e:
        print(f"LexiForge Error listing models: {e}")
        return []
