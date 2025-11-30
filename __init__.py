import html
import json
import os
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from anki.hooks import addHook
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)
from aqt.utils import showInfo

from .ai_client import (
    DEFAULT_MODEL,
    generate_content,
    generate_story_with_words,
    get_default_prompt_template,
    get_default_story_prompt_template,
    list_models,
)
from .language_constants import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, get_lang_code
from .tts_client import download_audio

if TYPE_CHECKING:
    from concurrent.futures import Future

    from anki.notes import Note
    from aqt.editor import Editor

# Constants
ADDON_NAME = "LexiForge"
ICON_NAME = "lexiforge_icon.svg"
CONFIG_FILENAME = "config.json"
_CONFIG_CACHE: dict[str, Any] | None = None


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
        main_layout = QVBoxLayout()

        # Create tab widget
        tabs = QTabWidget()

        # Tab 1: Main Settings
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout()

        # API Key
        main_tab_layout.addWidget(QLabel("Gemini API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.config.get("api_key", ""))
        main_tab_layout.addWidget(self.api_key_input)

        # Pricing Link
        pricing_label = QLabel(
            '<a href="https://ai.google.dev/pricing">Check Gemini Pricing</a>'
        )
        pricing_label.setOpenExternalLinks(True)
        main_tab_layout.addWidget(pricing_label)

        # Model Selection
        main_tab_layout.addWidget(QLabel("Model:"))
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # Allow custom models
        current_model = self.config.get("model", DEFAULT_MODEL)
        self.model_combo.addItem(current_model)
        self.model_combo.setCurrentText(current_model)

        self.load_models_btn = QPushButton("Load Models")
        self.load_models_btn.clicked.connect(self.load_models)

        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.load_models_btn)
        main_tab_layout.addLayout(model_layout)

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_tab_layout.addWidget(separator)

        # Source Language (language of the word being learned)
        main_tab_layout.addWidget(QLabel("Source Language (word language):"))
        self.source_lang_combo = QComboBox()
        # Add "Auto" as first option
        languages = ["Auto", *LANGUAGE_NAMES]
        self.source_lang_combo.addItems(languages)
        current_source = self.config.get("source_lang", "Auto")
        index = self.source_lang_combo.findText(current_source)
        if index >= 0:
            self.source_lang_combo.setCurrentIndex(index)
        main_tab_layout.addWidget(self.source_lang_combo)

        # Definition Language (language for definitions)
        main_tab_layout.addWidget(QLabel("Definition Language (definitions):"))
        self.def_lang_combo = QComboBox()
        self.def_lang_combo.addItems(LANGUAGE_NAMES)
        current_def = self.config.get("definition_lang", "English")
        index = self.def_lang_combo.findText(current_def)
        if index >= 0:
            self.def_lang_combo.setCurrentIndex(index)
        main_tab_layout.addWidget(self.def_lang_combo)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        main_tab_layout.addWidget(separator2)

        # Prompt Editor
        main_tab_layout.addWidget(QLabel("Prompt Template (Advanced):"))
        self.prompt_editor = QTextEdit()
        self.prompt_editor.setMaximumHeight(100)
        self.prompt_editor.setPlaceholderText(
            "Variables: {{word}}, {{source_lang}}, {{definition_lang}}"
        )
        default_prompt = get_default_prompt_template()
        current_prompt = self.config.get("prompt_template", "") or default_prompt
        self.prompt_editor.setPlainText(current_prompt)
        main_tab_layout.addWidget(self.prompt_editor)

        # Reset button
        reset_btn = QPushButton("Reset to Default Prompt")
        reset_btn.clicked.connect(
            lambda: self.prompt_editor.setPlainText(
                get_default_prompt_template()
            )
        )
        main_tab_layout.addWidget(reset_btn)

        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        main_tab_layout.addWidget(separator3)

        # Field Mapping
        main_tab_layout.addWidget(QLabel("Field Mapping:"))

        field_mapping = self.config.get("field_mapping", {})

        # Word field
        word_layout = QHBoxLayout()
        word_layout.addWidget(QLabel("Word (base form):"))
        self.word_field_input = QComboBox()
        self.word_field_input.setEditable(True)
        self.word_field_input.addItems(self.all_field_names)
        self.word_field_input.setCurrentText(field_mapping.get("word_field", "Front"))
        word_layout.addWidget(self.word_field_input)
        main_tab_layout.addLayout(word_layout)

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
        main_tab_layout.addLayout(def_field_layout)

        # Example field
        ex_field_layout = QHBoxLayout()
        ex_field_layout.addWidget(QLabel("Example:"))
        self.ex_field_input = QComboBox()
        self.ex_field_input.setEditable(True)
        self.ex_field_input.addItems(self.all_field_names)
        self.ex_field_input.setCurrentText(field_mapping.get("example_field", "Back"))
        ex_field_layout.addWidget(self.ex_field_input)
        main_tab_layout.addLayout(ex_field_layout)

        # Help text
        help_label = QLabel(
            "💡 If Definition and Example use the same field, they will be combined."
        )
        help_label.setStyleSheet("color: gray; font-size: 11px;")
        main_tab_layout.addWidget(help_label)

        main_tab_layout.addStretch()
        main_tab.setLayout(main_tab_layout)

        # Tab 2: Reading Practice Settings
        practice_tab = QWidget()
        practice_tab_layout = QVBoxLayout()

        # CEFR Level
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Language Level:"))
        self.level_combo = QComboBox()
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        self.level_combo.addItems(levels)
        current_level = self.config.get("story_level", "B1")
        index = self.level_combo.findText(current_level)
        if index >= 0:
            self.level_combo.setCurrentIndex(index)
        level_layout.addWidget(self.level_combo)
        practice_tab_layout.addLayout(level_layout)

        # Story Length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Story Length:"))
        self.length_combo = QComboBox()
        self.length_combo.addItem("Short (100-150 words)", "short")
        self.length_combo.addItem("Medium (200-300 words)", "medium")
        self.length_combo.addItem("Long (400-500 words)", "long")
        current_length = self.config.get("story_length", "short")
        for i in range(self.length_combo.count()):
            if self.length_combo.itemData(i) == current_length:
                self.length_combo.setCurrentIndex(i)
                break
        length_layout.addWidget(self.length_combo)
        practice_tab_layout.addLayout(length_layout)

        # Story Prompt Editor
        practice_tab_layout.addWidget(QLabel("Story Prompt Template (Advanced):"))
        self.story_prompt_editor = QTextEdit()
        self.story_prompt_editor.setMaximumHeight(200)
        self.story_prompt_editor.setPlaceholderText(
            "Variables: {{words}}, {{level}}, {{word_count}}"
        )
        default_story_prompt = get_default_story_prompt_template()
        current_story_prompt = self.config.get("story_prompt_template", "") or default_story_prompt
        self.story_prompt_editor.setPlainText(current_story_prompt)
        practice_tab_layout.addWidget(self.story_prompt_editor)

        # Reset button for story prompt
        reset_story_btn = QPushButton("Reset to Default Story Prompt")
        reset_story_btn.clicked.connect(
            lambda: self.story_prompt_editor.setPlainText(
                get_default_story_prompt_template()
            )
        )
        practice_tab_layout.addWidget(reset_story_btn)

        practice_tab_layout.addStretch()
        practice_tab.setLayout(practice_tab_layout)

        # Add tabs
        tabs.addTab(main_tab, "Main Settings")
        tabs.addTab(practice_tab, "Reading Practice")

        main_layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.setLayout(main_layout)

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
            current = self.config.get("model", DEFAULT_MODEL)
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
        # Save Reading Practice settings
        self.config["story_level"] = self.level_combo.currentText()
        self.config["story_length"] = self.length_combo.currentData()
        self.config["story_prompt_template"] = self.story_prompt_editor.toPlainText()
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
    model = conf.get("model", DEFAULT_MODEL)

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

    return [*buttons, editor.addButton(icon=icon_path, cmd="lexiforge_generate", func=lambda e=editor: on_generate_click(e), tip=f"Generate with {ADDON_NAME} (Ctrl+G)", keys="Ctrl+G")]  # noqa: E501


# --- Story Generation from Studied Words ---

def get_studied_words_today(deck_id: int | None = None) -> list[str]:
    """
    Get words from cards studied today with interval >= 1 day.

    Args:
        deck_id: Optional deck ID to filter words. If None, get words from all decks.

    Returns:
        List of words (from the first field of each card)
    """
    if not mw or not mw.col:
        return []

    # Get today's timestamp (start of day in milliseconds)
    today_start = int(time.time() - (time.time() % 86400)) * 1000

    # Query cards reviewed today with interval >= 1 day
    # ivl is in days, so we want ivl >= 1
    if deck_id is not None:
        card_ids = mw.col.db.list(
            """
            SELECT DISTINCT c.id
            FROM cards c
            JOIN revlog r ON c.id = r.cid
            WHERE r.id >= ?
            AND c.ivl >= 1
            AND c.did = ?
            """,
            today_start,
            deck_id
        )
    else:
        card_ids = mw.col.db.list(
            """
            SELECT DISTINCT c.id
            FROM cards c
            JOIN revlog r ON c.id = r.cid
            WHERE r.id >= ?
            AND c.ivl >= 1
            """,
            today_start
        )

    if not card_ids:
        return []

    # Get the words from the first field of each card's note
    words = []
    for card_id in card_ids:
        card = mw.col.get_card(card_id)
        note = card.note()
        if note and note.fields:
            word = note.fields[0].strip()
            # Remove HTML tags and sound tags
            word = re.sub(r'<[^>]+>', '', word)
            word = re.sub(r'\[sound:[^\]]+\]', '', word)
            # Decode HTML entities like &nbsp;, &amp;, etc.
            word = html.unescape(word)
            word = word.strip()
            if word and word not in words:
                words.append(word)

    return words


class StoryDialog(QDialog):
    """Dialog to display generated story from studied words."""

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{ADDON_NAME} - Reading Practice")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        # Deck selection group
        deck_group = QGroupBox("Select Deck")
        deck_layout = QHBoxLayout()
        
        self.deck_combo = QComboBox()
        self.deck_combo.currentIndexChanged.connect(self.on_deck_changed)
        deck_layout.addWidget(self.deck_combo)
        
        self.word_count_label = QLabel()
        deck_layout.addWidget(self.word_count_label)
        
        deck_group.setLayout(deck_layout)
        layout.addWidget(deck_group)

        # Info label
        self.info_label = QLabel("Select a deck to generate a story...")
        layout.addWidget(self.info_label)

        # Story text area
        self.story_text = QTextEdit()
        self.story_text.setReadOnly(True)
        self.story_text.setMinimumHeight(350)
        self.story_text.setAcceptRichText(True)

        # Increase font size for better readability
        font = self.story_text.font()
        font.setPointSize(14)  # Larger font
        self.story_text.setFont(font)

        layout.addWidget(self.story_text)

        # Buttons
        button_box = QDialogButtonBox()

        self.generate_btn = QPushButton("Generate Story")
        self.generate_btn.clicked.connect(self.generate_story)
        button_box.addButton(self.generate_btn, QDialogButtonBox.ButtonRole.ActionRole)

        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.clicked.connect(self.regenerate_story)
        self.regenerate_btn.setEnabled(False)
        button_box.addButton(self.regenerate_btn, QDialogButtonBox.ButtonRole.ActionRole)

        close_btn = button_box.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(self.close)

        layout.addWidget(button_box)

        self.setLayout(layout)

        # Initialize state
        self.words: list[str] = []
        self.current_story_generated = False
        
        # Load decks
        self.load_decks()

    def load_decks(self) -> None:
        """Load all decks with their studied word counts."""
        if not mw or not mw.col:
            return
        
        self.deck_combo.clear()
        
        # Add "All Decks" option
        all_words = get_studied_words_today()
        self.deck_combo.addItem(f"All Decks ({len(all_words)} words)", None)
        
        # Add individual decks
        deck_list = mw.col.decks.all_names_and_ids()
        for deck in deck_list:
            deck_id = deck.id
            deck_name = deck.name
            words = get_studied_words_today(deck_id)
            word_count = len(words)
            
            # Add deck to combo with word count
            self.deck_combo.addItem(f"{deck_name} ({word_count} words)", deck_id)
        
        # Update word count label for initial selection
        self.on_deck_changed(0)

    def on_deck_changed(self, index: int) -> None:
        """Handle deck selection change."""
        if index < 0:
            return
        
        deck_id = self.deck_combo.itemData(index)
        words = get_studied_words_today(deck_id)
        
        self.word_count_label.setText(f"📚 {len(words)} word(s)")
        
        if len(words) == 0:
            self.info_label.setText("⚠️ No studied words found in this deck (interval ≥ 1 day)")
            self.generate_btn.setEnabled(False)
            self.story_text.clear()
        else:
            self.info_label.setText("Ready to generate a story with your studied words!")
            self.generate_btn.setEnabled(True)
        
        # Reset regenerate button when deck changes
        self.regenerate_btn.setEnabled(False)
        self.current_story_generated = False

    def generate_story(self) -> None:
        """Generate and display the story."""
        config = get_config()
        api_key = config.get("api_key")

        if not api_key or "YOUR_KEY" in api_key:
            self.story_text.setText("Please configure your API Key in Tools → LexiForge Settings")
            return

        # Get selected deck
        current_index = self.deck_combo.currentIndex()
        deck_id = self.deck_combo.itemData(current_index)
        
        # Get studied words from selected deck
        self.words = get_studied_words_today(deck_id)

        if not self.words:
            self.story_text.setText("No words found. Study some cards first!\n\nMake sure you have cards with interval ≥ 1 day that were reviewed today.")  # noqa: E501
            self.regenerate_btn.setEnabled(False)
            return

        deck_name = self.deck_combo.currentText()
        self.story_text.setText(f"📚 Using {len(self.words)} words from {deck_name}\n\nWords: {', '.join(self.words[:10])}{'...' if len(self.words) > 10 else ''}\n\nGenerating story...")  # noqa: E501

        self.generate_btn.setEnabled(False)
        self.regenerate_btn.setEnabled(False)

        # Generate story in background
        model = config.get("model", DEFAULT_MODEL)
        source_lang = config.get("source_lang", "Auto")
        level = config.get("story_level", "B1")
        length = config.get("story_length", "short")
        story_prompt = config.get("story_prompt_template", "") or None

        def generate() -> str:
            return generate_story_with_words(
                self.words, api_key, model, source_lang, level, length, story_prompt
            )

        def on_done(future: "Future[str]") -> None:
            try:
                story = future.result()
                # Convert markdown bold (**text**) to HTML (<b>text</b>)
                story_html = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', story)
                # Convert newlines to HTML breaks
                story_html = story_html.replace('\n', '<br>')
                self.story_text.setHtml(story_html)
                self.generate_btn.setEnabled(True)
                self.regenerate_btn.setEnabled(True)
                self.current_story_generated = True
            except Exception as e:
                self.story_text.setText(f"Error: {e!s}")
                self.generate_btn.setEnabled(True)
                self.regenerate_btn.setEnabled(False)

        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(generate)
        future.add_done_callback(lambda f: mw.taskman.run_on_main(lambda: on_done(f)))

    def regenerate_story(self) -> None:
        """Regenerate the story with the same words."""
        self.generate_story()


def open_story_dialog() -> None:
    """Open the story generation dialog."""
    dialog = StoryDialog(mw)
    dialog.exec()


# Initialize - always clean up old menu items before adding new ones
# Remove any existing LexiForge menu items to prevent duplicates
for action in list(mw.form.menuTools.actions()):
    if action.text() in (f"{ADDON_NAME} Settings", f"{ADDON_NAME} Reading Practice"):
        mw.form.menuTools.removeAction(action)

addHook("setupEditorButtons", add_editor_button)

# Add menu items
settings_action = QAction(f"{ADDON_NAME} Settings", mw)
settings_action.triggered.connect(open_settings)
mw.form.menuTools.addAction(settings_action)

story_action = QAction(f"{ADDON_NAME} Reading Practice", mw)
story_action.triggered.connect(open_story_dialog)
mw.form.menuTools.addAction(story_action)
