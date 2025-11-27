.PHONY: test-popular test-full clean dev lint fix

# Anki addons directory
ANKI_ADDONS_DIR = $(HOME)/Library/Application Support/Anki2/addons21/lexiforge

# Files to sync to Anki plugin directory (Python files, JSON, SVG)
PLUGIN_FILES = __init__.py ai_client.py tts_client.py config.py language_constants.py manifest.json lexiforge_icon.svg

dev:
	@echo "Syncing plugin files to Anki..."
	@mkdir -p "$(ANKI_ADDONS_DIR)"
	@echo "  Cleaning old files (preserving config.json)..."
	@find "$(ANKI_ADDONS_DIR)" -type f ! -name "config.json" -delete 2>/dev/null || true
	@find "$(ANKI_ADDONS_DIR)" -type d -empty -delete 2>/dev/null || true
	@for file in $(PLUGIN_FILES); do \
		echo "  Copying $$file"; \
		cp -f $$file "$(ANKI_ADDONS_DIR)/" 2>/dev/null || true; \
	done
	@echo "✓ Plugin files synced successfully!"
	@echo "  Restart Anki to load changes"


test-popular:
	python3 -m unittest tests/test_popular.py

test-full:
	python3 -m unittest tests/test_popular.py tests/test_full.py

clean:
	rm -f test_audio_samples/*.mp3
	rm -rf tests/__pycache__

lint:
	python3 -m ruff check .

fix:
	python3 -m ruff check --fix .
	python3 -m ruff format .
