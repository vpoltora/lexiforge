import os
import time
import json
import re
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from anki.hooks import addHook

# Anki imports
from aqt import mw
from aqt.qt import (
    QAction,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QTextEdit,
    QVBoxLayout,
)
from aqt.utils import showInfo

if TYPE_CHECKING:
    from concurrent.futures import Future
    from anki.notes import Note
    from aqt.editor import Editor

# Constants
ADDON_NAME = "LexiForge"
ICON_NAME = "lexiforge_icon.svg"
CONFIG_FILENAME = "config.json"
DEFAULT_MODEL = "gemini-flash-latest"
_CONFIG_CACHE: dict[str, Any] | None = None

# --- Language Constants ---

# Supported languages mapping: Display Name -> ISO Code for Google TTS
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Mandarin Chinese": "zh-CN",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "Arabic": "ar",
    "Bengali": "bn",
    "Russian": "ru",
    "Portuguese": "pt-BR",
    "Urdu": "ur",
    "Indonesian": "id",
    "German": "de",
    "Japanese": "ja",
    "Turkish": "tr",
    "Korean": "ko",
    "Vietnamese": "vi",
    "Italian": "it",
    "Tamil": "ta",
    "Thai": "th",
    "Polish": "pl",
}

# Get sorted list of language names for UI dropdowns
LANGUAGE_NAMES = sorted(SUPPORTED_LANGUAGES.keys())


def get_lang_code(language_name: str) -> str:
    """
    Get the ISO language code for a given language name.

    Args:
        language_name: Display name of the language (e.g., "English")

    Returns:
        ISO language code (e.g., "en"), defaults to "en" if not found
    """
    return SUPPORTED_LANGUAGES.get(language_name, "en")


# --- Config ---

def get_config_path() -> str:
    """Get the absolute path to the configuration file."""
    return os.path.join(os.path.dirname(__file__), CONFIG_FILENAME)


def get_config() -> dict[str, Any]:
    """
    Load the configuration from the JSON file.
    Returns an empty dictionary if the file does not exist.
    """
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE.copy()

    config_path = get_config_path()
    data: dict[str, Any] = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    _CONFIG_CACHE = data
    return _CONFIG_CACHE.copy()


def save_config(config: dict[str, Any]) -> None:
    """
    Save the configuration to the JSON file.

    Args:
        config: The configuration dictionary to save.
    """
    global _CONFIG_CACHE
    _CONFIG_CACHE = dict(config)
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(_CONFIG_CACHE, f, indent=4)


# --- AI Client ---

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


# --- TTS Client ---

def download_audio(text: str, language_name: str, output_path: str) -> bool:
    """
    Download TTS audio from Google Translate for the given text.

    Args:
        text: Text to convert to speech
        language_name: Display name of the language (e.g., "English")
        output_path: Path where the audio file will be saved

    Returns:
        True if successful, False otherwise
    """
    text = (text or "").strip()
    if not text:
        print("LexiForge: Skipping TTS download because the text is empty")
        return False

    lang_code = get_lang_code(language_name or "English")

    # Google TTS API (unofficial)
    base_url = "https://translate.google.com/translate_tts"
    params = {"ie": "UTF-8", "q": text, "tl": lang_code, "client": "tw-ob"}

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        # Use a custom User-Agent to avoid 403 errors
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req) as response:
            data = response.read()

        with open(output_path, "wb") as f:
            f.write(data)

        print(
            f"LexiForge: TTS audio downloaded successfully for '{text}' in {language_name} ({lang_code})"
        )
        return True
    except Exception as e:
        print(
            f"LexiForge: Error downloading audio for {language_name} ({lang_code}): {e}"
        )
        return False


# --- GUI ---

class SettingsDialog(QDialog):
    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("LexiForge Settings")
        # Make sure the dialog appears on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.config = get_config()
        self.all_field_names = self.get_all_field_names()
        self.setup_ui()

    def get_all_field_names(self) -> list[str]:
        if not mw.col:
            return []
        fields = set()
        for model in mw.col.models.all():
            for fld in model["flds"]:
                fields.add(fld["name"])
        return sorted(fields)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # API Key
        layout.addWidget(QLabel("Gemini API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.config.get("api_key", ""))
        layout.addWidget(self.api_key_input)

        # Pricing Link
        pricing_label = QLabel(
            '<a href="https://ai.google.dev/pricing">Check Gemini Pricing</a>'
        )
        pricing_label.setOpenExternalLinks(True)
        layout.addWidget(pricing_label)

        # Model Selection
        layout.addWidget(QLabel("Model:"))
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # Allow custom models
        current_model = self.config.get("model", "gemini-flash-latest")
        self.model_combo.addItem(current_model)
        self.model_combo.setCurrentText(current_model)

        self.load_models_btn = QPushButton("Load Models")
        self.load_models_btn.clicked.connect(self.load_models)

        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.load_models_btn)
        layout.addLayout(model_layout)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Source Language (language of the word being learned)
        layout.addWidget(QLabel("Source Language (word language):"))
        self.source_lang_combo = QComboBox()
        # Add "Auto" as first option
        languages = ["Auto", *LANGUAGE_NAMES]
        self.source_lang_combo.addItems(languages)
        current_source = self.config.get("source_lang", "Auto")
        index = self.source_lang_combo.findText(current_source)
        if index >= 0:
            self.source_lang_combo.setCurrentIndex(index)
        layout.addWidget(self.source_lang_combo)

        # Definition Language (language for definitions)
        layout.addWidget(QLabel("Definition Language (definitions):"))
        self.def_lang_combo = QComboBox()
        self.def_lang_combo.addItems(LANGUAGE_NAMES)
        current_def = self.config.get("definition_lang", "English")
        index = self.def_lang_combo.findText(current_def)
        if index >= 0:
            self.def_lang_combo.setCurrentIndex(index)
        layout.addWidget(self.def_lang_combo)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator2)

        # Prompt Editor
        layout.addWidget(QLabel("Prompt Template (Advanced):"))
        self.prompt_editor = QTextEdit()
        self.prompt_editor.setMaximumHeight(120)
        self.prompt_editor.setPlaceholderText(
            "Variables: {{word}}, {{source_lang}}, {{definition_lang}}"
        )
        default_prompt = get_default_prompt_template()
        current_prompt = self.config.get("prompt_template", "") or default_prompt
        self.prompt_editor.setPlainText(current_prompt)
        layout.addWidget(self.prompt_editor)

        # Reset button
        reset_btn = QPushButton("Reset to Default Prompt")
        reset_btn.clicked.connect(
            lambda: self.prompt_editor.setPlainText(
                get_default_prompt_template()
            )
        )
        layout.addWidget(reset_btn)

        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator3)

        # Field Mapping
        layout.addWidget(QLabel("Field Mapping:"))

        field_mapping = self.config.get("field_mapping", {})

        # Word field
        word_layout = QHBoxLayout()
        word_layout.addWidget(QLabel("Word (base form):"))
        self.word_field_input = QComboBox()
        self.word_field_input.setEditable(True)
        self.word_field_input.addItems(self.all_field_names)
        self.word_field_input.setCurrentText(field_mapping.get("word_field", "Front"))
        word_layout.addWidget(self.word_field_input)
        layout.addLayout(word_layout)

        # Definition field
        def_field_layout = QHBoxLayout()
        def_field_layout.addWidget(QLabel("Definition:"))
        self.def_field_input = QComboBox()
        self.def_field_input.setEditable(True)
        self.def_field_input.addItems(self.all_field_names)
        self.def_field_input.setCurrentText(
            field_mapping.get("definition_field", "Back")
        )
        def_field_layout.addWidget(self.def_field_input)
        layout.addLayout(def_field_layout)

        # Example field
        ex_field_layout = QHBoxLayout()
        ex_field_layout.addWidget(QLabel("Example:"))
        self.ex_field_input = QComboBox()
        self.ex_field_input.setEditable(True)
        self.ex_field_input.addItems(self.all_field_names)
        self.ex_field_input.setCurrentText(field_mapping.get("example_field", "Back"))
        ex_field_layout.addWidget(self.ex_field_input)
        layout.addLayout(ex_field_layout)

        # Help text
        help_label = QLabel(
            "💡 If Definition and Example use the same field, they will be combined."
        )
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(help_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_models(self) -> None:
        api_key = self.api_key_input.text()
        if not api_key:
            showInfo("Please enter an API Key first.")
            return

        self.load_models_btn.setEnabled(False)
        self.load_models_btn.setText("Loading...")
        mw.app.processEvents()

        try:
            models = list_models(api_key)
            self.model_combo.clear()

            # Filter and sort models
            # We want to show popular/free models first

            # Sort by name to have some order
            models.sort(key=lambda x: x["name"])

            # Add top models (limit to 6 to avoid huge list)
            for count, m in enumerate(models):
                if count >= 6:
                    break
                model_name = m["name"].replace("models/", "")
                self.model_combo.addItem(model_name)

            # Ensure current model is selected if present, or add it
            current = self.config.get("model", "gemini-flash-latest")
            index = self.model_combo.findText(current)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            else:
                self.model_combo.addItem(current)
                self.model_combo.setCurrentText(current)

            showInfo("Models loaded successfully!")

        except Exception as e:
            showInfo(f"Error loading models: {e}")
        finally:
            self.load_models_btn.setEnabled(True)
            self.load_models_btn.setText("Load Models")

    def accept(self) -> None:
        # Save config
        self.config["api_key"] = self.api_key_input.text()
        self.config["model"] = self.model_combo.currentText()
        self.config["source_lang"] = self.source_lang_combo.currentText()
        self.config["definition_lang"] = self.def_lang_combo.currentText()
        self.config["prompt_template"] = self.prompt_editor.toPlainText()
        self.config["field_mapping"] = {
            "word_field": self.word_field_input.currentText() or "Front",
            "definition_field": self.def_field_input.currentText() or "Back",
            "example_field": self.ex_field_input.currentText() or "Back",
        }
        save_config(self.config)
        super().accept()


def open_settings() -> None:
    """Open settings dialog"""
    dialog = SettingsDialog(mw)
    dialog.exec()


def get_field_mapping(note: "Note", config: dict[str, Any]) -> tuple[str, str, str]:
    """
    Determine the field mapping based on note type and configuration.
    Returns (word_field, def_field, ex_field)
    """
    fields = note.keys()

    # If exactly 2 fields, automatically map to 1st and 2nd field
    if len(fields) == 2:
        return fields[0], fields[1], fields[1]

    # Otherwise use configuration (defaulting to Front/Back)
    field_mapping = config.get("field_mapping", {})
    word_field = field_mapping.get("word_field", "Front")
    def_field = field_mapping.get("definition_field", "Back")
    ex_field = field_mapping.get("example_field", "Back")

    return word_field, def_field, ex_field


def _validate_note_and_config(
    note: "Note | None",
    conf: dict[str, Any] | None,
    word_field: str,
    def_field: str,
    ex_field: str,
) -> bool:
    """Validate note, config, and required fields."""
    if not note:
        showInfo("Please select a note.")
        return False

    if not conf:
        showInfo("Configuration not found. Please check config.json.")
        return False

    missing = []
    if word_field not in note:
        missing.append(word_field)
    if def_field not in note:
        missing.append(def_field)
    if ex_field != def_field and ex_field not in note:
        missing.append(ex_field)

    if missing:
        showInfo(
            f"Error: The following fields are missing in this note type: {', '.join(missing)}\n\n"
            f"Detected fields: {', '.join(note.keys())}"
        )
        return False

    word = note[word_field]
    if not word:
        showInfo(f"Please enter a word in the '{word_field}' field.")
        return False

    return True


def _generate_audio_filename(target_word: str, source_lang: str) -> str:
    """Generate a unique audio filename."""
    safe_word = "".join(
        [c for c in target_word if c.isalnum() or c in (" ", "-", "_")]
    ).strip()
    lang_code = get_lang_code(source_lang)
    return f"lexiforge_{safe_word}_{lang_code}_{int(time.time())}.mp3"


def _generate_content_and_audio(
    word: str,
    source_lang: str,
    definition_lang: str,
    conf: dict[str, Any],
) -> dict[str, Any]:
    """Generate definition, examples, and audio for the word."""
    api_key = conf.get("api_key")
    if not api_key or "YOUR_KEY" in api_key:
        return {"error": "Please configure your API Key in Tools -> LexiForge Settings"}

    model = conf.get("model", "gemini-flash-latest")
    prompt_template = conf.get("prompt_template", "") or None

    print(f"LexiForge: Using model: {model}")
    print(
        f"LexiForge: Source language: {source_lang}, Definition language: {definition_lang}"
    )

    definition, examples, base_form = generate_content(
        word, source_lang, api_key, model, definition_lang, prompt_template
    )

    target_word = base_form if base_form else word
    filename = _generate_audio_filename(target_word, source_lang)
    full_path = Path(mw.col.media.dir()) / filename
    success = download_audio(target_word, source_lang, str(full_path))

    return {
        "definition": definition,
        "examples": examples,
        "base_form": base_form,
        "audio_file": filename if success else None,
        "source_lang": source_lang,
        "definition_lang": definition_lang,
    }


def _update_note_fields(
    note: "Note",
    result: dict[str, Any],
    word_field: str,
    def_field: str,
    ex_field: str,
) -> None:
    """Update note fields with generated content."""
    if result.get("base_form") and word_field in note:
        note[word_field] = result["base_form"]

    if def_field == ex_field:
        combined = f"{result['definition']}<br><br>{result['examples']}"
        if def_field in note:
            note[def_field] = combined
    else:
        if def_field in note:
            note[def_field] = result["definition"]
        if ex_field in note:
            note[ex_field] = result["examples"]

    if result["audio_file"]:
        if "Audio" in note:
            note["Audio"] = f"[sound:{result['audio_file']}]"
        elif word_field in note:
            note[word_field] += f" [sound:{result['audio_file']}]"


def on_generate_click(editor: "Editor") -> None:
    """Handler for the 'Generate' button click in the editor."""
    note = editor.note
    conf = get_config()
    word_field, def_field, ex_field = get_field_mapping(note, conf)

    if not _validate_note_and_config(note, conf, word_field, def_field, ex_field):
        return

    word = note[word_field]
    source_lang = conf.get("source_lang", "English")
    definition_lang = conf.get("definition_lang", "English")
    model = conf.get("model", "gemini-flash-latest")

    mw.progress.start(label=f"Generating with {model}...", immediate=True)

    def background_op() -> dict[str, Any]:
        try:
            return _generate_content_and_audio(word, source_lang, definition_lang, conf)
        except Exception as e:
            return {"error": str(e)}

    def on_success(future: "Future[dict[str, Any]]") -> None:
        mw.progress.finish()

        try:
            result = future.result()
        except Exception as e:
            showInfo(f"Error during generation: {e!s}")
            return

        if "error" in result:
            showInfo(f"Error: {result['error']}")
            return

        word_field, def_field, ex_field = get_field_mapping(note, conf)
        _update_note_fields(note, result, word_field, def_field, ex_field)
        editor.loadNote()

    mw.taskman.run_in_background(background_op, on_success)


def add_editor_button(buttons, editor):
    # Use absolute path for icon to ensure it loads
    addon_path = os.path.dirname(__file__)
    icon_path = os.path.join(addon_path, ICON_NAME)

    return [*buttons, editor.addButton(icon=icon_path, cmd="lexiforge_generate", func=lambda e=editor: on_generate_click(e), tip=f"Generate with {ADDON_NAME} (Ctrl+G)", keys="Ctrl+G")]


# Initialize
addHook("setupEditorButtons", add_editor_button)

# Add menu item
action = QAction(f"{ADDON_NAME} Settings", mw)
action.triggered.connect(open_settings)
mw.form.menuTools.addAction(action)
