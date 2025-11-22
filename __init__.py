import json
import os
import time

# Anki imports
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout,
    QComboBox, QPushButton, QFrame, QDialogButtonBox, QAction,
    Qt, QTextEdit
)
from anki.hooks import addHook

# Local imports
# We need to handle imports carefully for Anki addons
from . import ai_client
from . import tts_client
from . import language_constants

# Constants
ADDON_NAME = "VocabAI"
ICON_NAME = "vocabai_icon.svg"

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return None

def save_config(config):
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VocabAI Settings")
        # Make sure the dialog appears on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.config = get_config() or {}
        self.all_field_names = self.get_all_field_names()
        self.setup_ui()

    def get_all_field_names(self):
        if not mw.col:
            return []
        fields = set()
        for model in mw.col.models.all():
            for fld in model['flds']:
                fields.add(fld['name'])
        return sorted(list(fields))

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # API Key
        layout.addWidget(QLabel("Gemini API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.config.get("api_key", ""))
        layout.addWidget(self.api_key_input)
        
        # Pricing Link
        pricing_label = QLabel('<a href="https://ai.google.dev/pricing">Check Gemini Pricing</a>')
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
        languages = ["Auto"] + language_constants.LANGUAGE_NAMES
        self.source_lang_combo.addItems(languages)
        current_source = self.config.get("source_lang", "Auto")
        index = self.source_lang_combo.findText(current_source)
        if index >= 0:
            self.source_lang_combo.setCurrentIndex(index)
        layout.addWidget(self.source_lang_combo)
        
        # Definition Language (language for definitions)
        layout.addWidget(QLabel("Definition Language (definitions):"))
        self.def_lang_combo = QComboBox()
        self.def_lang_combo.addItems(language_constants.LANGUAGE_NAMES)
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
        self.prompt_editor.setPlaceholderText("Variables: {{word}}, {{source_lang}}, {{definition_lang}}")
        default_prompt = ai_client.get_default_prompt_template()
        current_prompt = self.config.get("prompt_template", "") or default_prompt
        self.prompt_editor.setPlainText(current_prompt)
        layout.addWidget(self.prompt_editor)
        
        # Reset button
        reset_btn = QPushButton("Reset to Default Prompt")
        reset_btn.clicked.connect(lambda: self.prompt_editor.setPlainText(ai_client.get_default_prompt_template()))
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
        self.def_field_input.setCurrentText(field_mapping.get("definition_field", "Back"))
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
        help_label = QLabel("💡 If Definition and Example use the same field, they will be combined.")
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

    def load_models(self):
        api_key = self.api_key_input.text()
        if not api_key:
            showInfo("Please enter an API Key first.")
            return
            
        self.load_models_btn.setEnabled(False)
        self.load_models_btn.setText("Loading...")
        mw.app.processEvents()
        
        try:
            models = ai_client.list_models(api_key)
            self.model_combo.clear()
            
            # Filter and sort models
            # We want to show popular/free models first

            # Sort by name to have some order
            models.sort(key=lambda x: x['name'])
            
            # Add top models (limit to 6 to avoid huge list)
            count = 0
            for m in models:
                model_name = m['name'].replace("models/", "")
                self.model_combo.addItem(model_name)
                count += 1
                if count >= 6:
                    break
            
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

    def accept(self):
        # Save config
        self.config["api_key"] = self.api_key_input.text()
        self.config["model"] = self.model_combo.currentText()
        self.config["source_lang"] = self.source_lang_combo.currentText()
        self.config["definition_lang"] = self.def_lang_combo.currentText()
        self.config["prompt_template"] = self.prompt_editor.toPlainText()
        self.config["field_mapping"] = {
            "word_field": self.word_field_input.currentText() or "Front",
            "definition_field": self.def_field_input.currentText() or "Back",
            "example_field": self.ex_field_input.currentText() or "Back"
        }
        save_config(self.config)
        super().accept()

def open_settings():
    """Open settings dialog"""
    dialog = SettingsDialog(mw)
    dialog.exec()

def get_field_mapping(note, config):
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

def on_generate_click(editor):
    """
    Handler for the 'Generate' button click in the editor.
    """
    note = editor.note
    
    # 1. Validation
    if not note:
        showInfo("Please select a note.")
        return

    # Get Configuration
    config = get_config()
    if not config:
        showInfo("Configuration not found. Please check config.json.")
        return

    # Determine fields
    word_field, def_field, ex_field = get_field_mapping(note, config)

    # Check if required fields exist
    missing = []
    if word_field not in note:
        missing.append(word_field)
    if def_field not in note:
        missing.append(def_field)
    # ex_field might be same as def_field, check if it's different and missing
    if ex_field != def_field and ex_field not in note:
        missing.append(ex_field)

    if missing:
        showInfo(
            f"Error: The following fields are missing in this note type: {', '.join(missing)}\n\n"
            f"Detected fields: {', '.join(note.keys())}"
        )
        return

    word = note[word_field]
    if not word:
        showInfo(f"Please enter a word in the '{word_field}' field.")
        return

    # Get languages from configuration
    source_lang = config.get("source_lang", "English")
    definition_lang = config.get("definition_lang", "English")

    # 3. Run in background to avoid freezing UI
    model = config.get("model", "gemini-flash-latest")
    mw.progress.start(label=f"Generating with {model}...", immediate=True)
    
    def background_op():
        try:
            # Call Gemini
            api_key = config.get("api_key")
            if not api_key or "YOUR_KEY" in api_key:
                return {"error": "Please configure your API Key in Tools -> VocabAI Settings"}

            prompt_template = config.get("prompt_template", "") or None

            print(f"VocabAI: Using model: {model}")
            print(f"VocabAI: Source language: {source_lang}, Definition language: {definition_lang}")
            definition, examples, base_form = ai_client.generate_content(
                word, source_lang, api_key, model, definition_lang, prompt_template
            )

            # Use base_form if available, otherwise fallback to original word
            target_word = base_form if base_form else word

            # Call TTS - use source language for pronunciation
            # Generate a unique filename with language code to avoid caching and ambiguity
            safe_word = "".join([c for c in target_word if c.isalnum() or c in (' ', '-', '_')]).strip()
            lang_code = tts_client.get_lang_code(source_lang)
            filename = f"vocabai_{safe_word}_{lang_code}_{int(time.time())}.mp3"

            media_dir = mw.col.media.dir()
            full_path = os.path.join(media_dir, filename)

            success = tts_client.download_audio(target_word, source_lang, full_path)
            
            return {
                "definition": definition,
                "examples": examples,
                "base_form": base_form,
                "audio_file": filename if success else None,
                "source_lang": source_lang,
                "definition_lang": definition_lang
            }
        except Exception as e:
            return {"error": str(e)}

    def on_success(future):
        mw.progress.finish()

        try:
            result = future.result()
        except Exception as e:
            showInfo(f"Error during generation: {str(e)}")
            return

        if "error" in result:
            showInfo(f"Error: {result['error']}")
            return

        # Get field mapping (re-evaluate to be safe, though config shouldn't change)
        word_field, def_field, ex_field = get_field_mapping(note, config)
        
        # Update word with base form
        if result.get("base_form") and word_field in note:
            note[word_field] = result["base_form"]

        # Write definition and example
        if def_field == ex_field:
            # Same field: combine with double newline (visually 2 empty lines)
            combined = f"{result['definition']}<br><br>{result['examples']}"
            if def_field in note:
                note[def_field] = combined
        else:
            # Different fields: write separately
            if def_field in note:
                note[def_field] = result["definition"]
            if ex_field in note:
                note[ex_field] = result["examples"]

        # Add Audio (fallback to word_field if Audio doesn't exist)
        if result["audio_file"]:
            if "Audio" in note:
                note["Audio"] = f"[sound:{result['audio_file']}]"
            elif word_field in note:
                note[word_field] += f" [sound:{result['audio_file']}]"

        editor.loadNote()

    mw.taskman.run_in_background(background_op, on_success)

def add_editor_button(buttons, editor):
    # Use absolute path for icon to ensure it loads
    addon_path = os.path.dirname(__file__)
    icon_path = os.path.join(addon_path, ICON_NAME)

    return buttons + [editor.addButton(
        icon=icon_path,
        cmd="vocabai_generate",
        func=lambda e=editor: on_generate_click(e),
        tip=f"Generate with {ADDON_NAME} (Ctrl+G)",
        keys="Ctrl+G"
    )]

# Initialize
addHook("setupEditorButtons", add_editor_button)

# Add menu item
action = QAction(f"{ADDON_NAME} Settings", mw)
action.triggered.connect(open_settings)
mw.form.menuTools.addAction(action)
