.PHONY: test clean dev lint fix install help

ANKI_ADDONS_DIR = $(HOME)/Library/Application Support/Anki2/addons21/lexiforge

PLUGIN_FILES = __init__.py ai_client.py tts_client.py config.py language_constants.py manifest.json lexiforge_icon.svg

install:
	pip install ruff

dev:
	@echo "Syncing plugin files to Anki..."
	@mkdir -p "$(ANKI_ADDONS_DIR)"
	@echo "  Cleaning old files (preserving config.json)..."
	@find "$(ANKI_ADDONS_DIR)" -type f ! -name "config.json" -delete 2>/dev/null || true
	@rm -rf "$(ANKI_ADDONS_DIR)/__pycache__" 2>/dev/null || true
	@for file in $(PLUGIN_FILES); do \
		echo "  Copying $$file"; \
		cp -f "$(CURDIR)/$$file" "$(ANKI_ADDONS_DIR)/" || exit 1; \
	done
	@echo "✓ Plugin files synced successfully!"
	@echo "  Restart Anki to load changes"

test:
	python3 -m unittest discover -s tests -p "test_*.py"

clean:
	rm -f test_audio_samples/*.mp3
	rm -rf tests/__pycache__
	rm -rf __pycache__
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

lint:
	python3 -m ruff check .

fix:
	python3 -m ruff check --fix .
	python3 -m ruff format .
