import json
import os
import time


# Anki imports
from aqt import mw
from aqt.utils import showInfo, tooltip
from aqt.qt import *
from anki.hooks import addHook

# Local imports
# We need to handle imports carefully for Anki addons
from . import ai_client
from . import tts_client
from . import utils

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
        from aqt.qt import Qt
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.config = get_config() or {}
        self.setup_ui()

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
        self.model_combo.setEditable(True) # Allow custom models
        current_model = self.config.get("model", "gemini-flash-latest")
        self.model_combo.addItem(current_model)
        self.model_combo.setCurrentText(current_model)
        
        self.load_models_btn = QPushButton("Load Models")
        self.load_models_btn.clicked.connect(self.load_models)
        
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(self.load_models_btn)
        layout.addLayout(model_layout)
        
        # Language Map (Simplified for now, just a label)
        # layout.addWidget(QLabel("Deck Language Map (Edit in config.json for now)"))
        # self.lang_map_info = QLabel(str(self.config.get("deck_language_map", {})))
        # self.lang_map_info.setWordWrap(True)
        # layout.addWidget(self.lang_map_info)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
        save_config(self.config)
        super().accept()

def open_settings():
    """Open settings dialog"""
    dialog = SettingsDialog(mw)
    dialog.exec()

def on_generate_click(editor):
    """
    Handler for the 'Generate' button click in the editor.
    """
    note = editor.note
    
    # 1. Validation
    if not note:
        showInfo("Please select a note.")
        return
        
    if "Front" not in note or "Back" not in note:
        # Check if fields exist, if not try to find similar ones or warn
        missing = []
        for f in ["Front", "Back", "Example"]:
            if f not in note:
                missing.append(f)
        
        if missing:
            showInfo(f"Error: The following fields are missing in this note type: {', '.join(missing)}")
            return

    word = note["Front"]
    if not word:
        showInfo("Please enter a word in the 'Front' field.")
        return

    # 2. Get Configuration
    config = get_config()
    if not config:
        showInfo("Configuration not found. Please check config.json.")
        return
    
    # Determine Language
    deck_id = note.mid
    # We need to find the deck name. Note.mid is actually model ID. 
    # To get deck name we need the card, but in editor we might not have a card yet if it's a new note.
    # However, editor.parentWindow is usually the AddCards dialog or Browser.
    
    # Best effort to get deck name
    deck_name = ""
    if hasattr(editor, 'parentWindow') and hasattr(editor.parentWindow, 'deckChooser'):
        deck_name = editor.parentWindow.deckChooser.deckName()
    
    language = utils.parse_deck_language(deck_name, config.get("deck_language_map", {}))
    
    # Get Note Type
    note_type = note.model()['name']
    
    # 3. Run in background to avoid freezing UI
    model = config.get("model", "gemini-flash-latest")
    mw.progress.start(label=f"Generating with {model}...", immediate=True)
    
    def background_op():
        try:
            # Call Gemini
            api_key = config.get("api_key")
            if not api_key or "YOUR_KEY" in api_key:
                return {"error": "Please configure your API Key in Tools -> VocabAI Settings"}
                
            print(f"VocabAI: Using model: {model}")
            definition, examples, base_form = ai_client.generate_content(word, language, api_key, model)
            
            # Use base_form if available, otherwise fallback to original word
            target_word = base_form if base_form else word
            
            # Call TTS
            # Generate a unique filename with language code to avoid caching and ambiguity
            safe_word = "".join([c for c in target_word if c.isalnum() or c in (' ', '-', '_')]).strip()
            lang_code = tts_client.get_lang_code(language)
            filename = f"vocabai_{safe_word}_{lang_code}_{int(time.time())}.mp3"
            
            media_dir = mw.col.media.dir()
            full_path = os.path.join(media_dir, filename)
            
            success = tts_client.download_audio(target_word, language, full_path)
            
            return {
                "definition": definition,
                "examples": examples,
                "base_form": base_form,
                "audio_file": filename if success else None,
                "detected_lang": language,
                "detected_deck": deck_name
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
            
        # Update fields
        note["Back"] = result["definition"]
        if "Example" in note:
            note["Example"] = result["examples"]
            
        # Update Front field with base form if found
        if result.get("base_form"):
            # Preserve audio tag if it was there (though we usually append it)
            # But here we are replacing the word.
            # Let's just set it to the base form. Audio will be appended next.
            note["Front"] = result["base_form"]
            
        # Add Audio
        if result["audio_file"]:
            # Check if Audio field exists, otherwise append to Front
            if "Audio" in note:
                note["Audio"] = f"[sound:{result['audio_file']}]"
            else:
                note["Front"] += f" [sound:{result['audio_file']}]"
                
        editor.loadNote()
        # tooltip("Content generated successfully!")

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
