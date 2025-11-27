import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-flash-latest"


def get_default_prompt_template() -> str:
    return """Analyze the word ‘{{word}}’ in {{source_lang}}.
	1.	Find its base form (lemma).
	2.	Translate this base form into {{definition_lang}}:
	•	If it is a simple common word (e.g. ‘cat’, ‘milk’, ‘run’), give only a one-word translation in {{definition_lang}}.
	•	Otherwise give the translation in {{definition_lang}} plus a very short 4-7 word definition in parentheses.
	3.	Give 1 example sentence in {{source_lang}} using the base form.

Format the answer exactly as:
BASE_FORM: [base form in {{source_lang}}]
DEFINITION: [translation/definition in {{definition_lang}}]
EXAMPLE: [sentence in {{source_lang}} using the base form]

Do not use markdown formatting."""  # noqa: E501


def get_default_story_prompt_template() -> str:
    """Returns the default story prompt template with variable placeholders."""
    return """Analyze the following words and detect their language: {{words}}

Then create an engaging and educational short story ({{word_count}}) IN THE EXACT SAME LANGUAGE as these words.

IMPORTANT: The story MUST be written in the same language as the input words. Do not translate or use any other language.

Requirements:
- Detect the language of the words first
- Write the ENTIRE story in that detected language
- Use all or most of the provided words naturally in context
- Highlight the studied words by wrapping them in **bold** (using **word** format)
- Make the story interesting and memorable
- Keep the language level appropriate for {{level}} learners (CEFR {{level}})
- The story should be approximately {{word_count}}
- Add a title to the story in the same language

Format your response as:
Title: [Story Title in the detected language]

[Story text with **highlighted** words in the detected language]"""  # noqa: E501


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

    Raises:
        ValueError: If api_key is empty or None
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key is required and cannot be empty")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    if prompt_template is None:
        prompt_template = get_default_prompt_template()

    actual_source = source_lang
    if source_lang.lower() == "auto":
        prompt_template = f"""First, detect the language of the word '{{{{word}}}}' and use that language as {{{{source_lang}}}}.
{prompt_template}"""
        actual_source = "the detected language"

    # Replace template variables
    prompt = prompt_template.replace("{{word}}", word)
    prompt = prompt.replace("{{source_lang}}", actual_source)
    prompt = prompt.replace("{{definition_lang}}", definition_lang)

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Parse response
        try:
            # Safely extract nested values with checks
            candidates = result.get("candidates")
            if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
                raise KeyError("Missing or empty 'candidates' in result")
            candidate = candidates[0]
            content = candidate.get("content")
            if not content or not isinstance(content, dict):
                raise KeyError("Missing or invalid 'content' in candidate")
            parts = content.get("parts")
            if not parts or not isinstance(parts, list) or len(parts) == 0:
                raise KeyError("Missing or empty 'parts' in content")
            part = parts[0]
            text = part.get("text")
            if text is None:
                raise KeyError("Missing 'text' in part")
            logger.debug(f"Raw Response: {text}")
            return parse_response(text)
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing response: {e}")
            return (
                "Error parsing AI response",
                "",
                word,
            )


    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"HTTP Error {e.code}: {error_body}")

        if e.code == 404:
            logger.info("Model not found. Listing available models...")
            list_models(api_key)

        return f"API Error: {e.code}", "", word
    except urllib.error.URLError as e:
        logger.error(f"Network Error: {e}")
        return f"Network Error: {e.reason}", "", word
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
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
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {"x-goog-api-key": api_key}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            models = result.get("models", [])
            logger.info("Available Models:")
            for m in models:
                logger.info(f"- {m['name']} ({m.get('displayName', '')})")
            return models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []


def generate_story_with_words(
    words: list[str],
    api_key: str,
    model: str,
    language: str = "English",
    level: str = "B1",
    length: str = "short",
    prompt_template: Optional[str] = None
) -> str:
    """
    Generate a story using the given words via Gemini API.

    Args:
        words: List of words to include in the story
        api_key: Gemini API key
        model: Model name to use
        language: Target language for the story (source language of the words)
        level: CEFR level (A1, A2, B1, B2, C1, C2)
        length: Story length (short, medium, long)
        prompt_template: Custom prompt template (uses default if None)

    Returns:
        Generated story text
    """
    if not words:
        return "No words available to generate a story."

    words_list = ", ".join(words[:30])  # Limit to 30 words for reasonable story

    # Map length to word count and token limit
    length_config = {
        "short": {"words": "100-150 words", "tokens": 1500},
        "medium": {"words": "200-300 words", "tokens": 2500},
        "long": {"words": "400-500 words", "tokens": 4000},
    }

    config = length_config.get(length, length_config["short"])
    word_count = config["words"]
    max_tokens = config["tokens"]

    if prompt_template is None:
        prompt_template = get_default_story_prompt_template()

    # Replace template variables
    prompt = prompt_template.replace("{{words}}", words_list)
    prompt = prompt.replace("{{level}}", level)
    prompt = prompt.replace("{{word_count}}", word_count)

    # Handle Auto language detection - modify prompt if needed
    if language.lower() != "auto":
        # If specific language is set, ensure prompt uses it
        prompt = prompt.replace(
            "Analyze the following words and detect their language",
            f"Use the following words in {language}"
        )
        prompt = prompt.replace(
            "IN THE EXACT SAME LANGUAGE as these words",
            f"in {language}"
        )
        prompt = prompt.replace("Detect the language of the words first", "")
        prompt = prompt.replace("Write the ENTIRE story in that detected language", f"Write the ENTIRE story in {language}")
        prompt = prompt.replace("in the detected language", f"in {language}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": max_tokens,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers=headers,
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Parse response with error handling
        try:
            story = result["candidates"][0]["content"]["parts"][0]["text"]

            # Clean up the story - remove language detection lines if present
            lines = story.split('\n')
            cleaned_lines = []
            skip_next = False

            for line in lines:
                # Skip language detection headers
                if 'linguagem detectada' in line.lower() or 'detected language' in line.lower():
                    skip_next = True
                    continue
                # Skip separator lines after detection
                if skip_next and (line.strip() == '***' or line.strip() == '---' or line.strip() == ''):
                    if line.strip() in ('***', '---'):
                        skip_next = False
                    continue
                skip_next = False
                cleaned_lines.append(line)

            story = '\n'.join(cleaned_lines).strip()
            return story
        except (KeyError, IndexError) as e:
            # Create detailed error message for user
            error_details = f"Parsing Error: {e!s}\n\n"
            error_details += "API Response Keys: " + str(list(result.keys())) + "\n\n"

            if "candidates" in result:
                error_details += f"Candidates count: {len(result.get('candidates', []))}\n"
                if result.get('candidates'):
                    candidate = result['candidates'][0]
                    error_details += f"Candidate keys: {list(candidate.keys())}\n"
                    if 'content' in candidate:
                        error_details += f"Content keys: {list(candidate['content'].keys())}\n"

            # Also write to a log file for debugging
            log_path = os.path.expanduser("~/Library/Application Support/Anki2/lexiforge_error.log")
            with open(log_path, "a") as f:
                f.write(f"\n=== {datetime.datetime.now()} ===\n")
                f.write(error_details)
                f.write("\nFull response:\n")
                f.write(json.dumps(result, indent=2))
                f.write("\n")

            return f"❌ Parsing Error\n\n{error_details}\n\nFull log saved to:\n{log_path}"

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"LexiForge Story HTTP Error {e.code}: {error_body}")
        return f"API Error: {e.code}\n\n{error_body}"
    except Exception as e:
        logger.error(f"LexiForge Story Error: {e}")
        return f"Error generating story: {e!s}"


def generate_story_with_words(
    words: list[str],
    api_key: str,
    model: str,
    language: str = "English",
    level: str = "B1",
    length: str = "short",
    prompt_template: Optional[str] = None
) -> str:
    """
    Generate a story using the given words via Gemini API.

    Args:
        words: List of words to include in the story
        api_key: Gemini API key
        model: Model name to use
        language: Target language for the story (source language of the words)
        level: CEFR level (A1, A2, B1, B2, C1, C2)
        length: Story length (short, medium, long)
        prompt_template: Custom prompt template (uses default if None)

    Returns:
        Generated story text
    """
    if not words:
        return "No words available to generate a story."

    words_list = ", ".join(words[:30])  # Limit to 30 words for reasonable story

    # Map length to word count and token limit
    length_config = {
        "short": {"words": "100-150 words", "tokens": 1500},
        "medium": {"words": "200-300 words", "tokens": 2500},
        "long": {"words": "400-500 words", "tokens": 4000},
    }

    config = length_config.get(length, length_config["short"])
    word_count = config["words"]
    max_tokens = config["tokens"]

    if prompt_template is None:
        prompt_template = get_default_story_prompt_template()

    # Replace template variables
    prompt = prompt_template.replace("{{words}}", words_list)
    prompt = prompt.replace("{{level}}", level)
    prompt = prompt.replace("{{word_count}}", word_count)

    # Handle Auto language detection - modify prompt if needed
    if language.lower() != "auto":
        # If specific language is set, ensure prompt uses it
        prompt = prompt.replace(
            "Analyze the following words and detect their language",
            f"Use the following words in {language}"
        )
        prompt = prompt.replace(
            "IN THE EXACT SAME LANGUAGE as these words",
            f"in {language}"
        )
        prompt = prompt.replace("Detect the language of the words first", "")
        prompt = prompt.replace("Write the ENTIRE story in that detected language", f"Write the ENTIRE story in {language}")
        prompt = prompt.replace("in the detected language", f"in {language}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": max_tokens,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers=headers,
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Parse response with error handling
        try:
            story = result["candidates"][0]["content"]["parts"][0]["text"]

            # Clean up the story - remove language detection lines if present
            lines = story.split('\n')
            cleaned_lines = []
            skip_next = False

            for line in lines:
                # Skip language detection headers
                if 'linguagem detectada' in line.lower() or 'detected language' in line.lower():
                    skip_next = True
                    continue
                # Skip separator lines after detection
                if skip_next and (line.strip() == '***' or line.strip() == '---' or line.strip() == ''):
                    if line.strip() in ('***', '---'):
                        skip_next = False
                    continue
                skip_next = False
                cleaned_lines.append(line)

            story = '\n'.join(cleaned_lines).strip()
            return story
        except (KeyError, IndexError) as e:
            # Create detailed error message for user
            error_details = f"Parsing Error: {e!s}\n\n"
            error_details += "API Response Keys: " + str(list(result.keys())) + "\n\n"

            if "candidates" in result:
                error_details += f"Candidates count: {len(result.get('candidates', []))}\n"
                if result.get('candidates'):
                    candidate = result['candidates'][0]
                    error_details += f"Candidate keys: {list(candidate.keys())}\n"
                    if 'content' in candidate:
                        error_details += f"Content keys: {list(candidate['content'].keys())}\n"

            # Also write to a log file for debugging
            log_path = os.path.expanduser("~/Library/Application Support/Anki2/lexiforge_error.log")
            with open(log_path, "a") as f:
                f.write(f"\n=== {datetime.datetime.now()} ===\n")
                f.write(error_details)
                f.write("\nFull response:\n")
                f.write(json.dumps(result, indent=2))
                f.write("\n")

            return f"❌ Parsing Error\n\n{error_details}\n\nFull log saved to:\n{log_path}"

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"LexiForge Story HTTP Error {e.code}: {error_body}")
        return f"API Error: {e.code}\n\n{error_body}"
    except Exception as e:
        logger.error(f"LexiForge Story Error: {e}")
        return f"Error generating story: {e!s}"
