.PHONY: test-popular test-full clean dev

# Anki addons directory
ANKI_ADDONS_DIR = $(HOME)/Library/Application Support/Anki2/addons21/vocabai

# Files to sync to Anki plugin directory (all git-tracked files except tests and Makefile)
PLUGIN_FILES = $(shell git ls-files | grep -v '^tests/' | grep -v '^Makefile$$' | grep -v '^\.gitignore$$')

dev:
	@echo "Syncing plugin files to Anki..."
	@mkdir -p "$(ANKI_ADDONS_DIR)"
	@echo "  Cleaning old files (preserving config.json)..."
	@find "$(ANKI_ADDONS_DIR)" -type f ! -name "config.json" -delete
	@find "$(ANKI_ADDONS_DIR)" -type d -empty -delete
	@for file in $(PLUGIN_FILES); do \
		echo "  Copying $$file"; \
		cp -f $$file "$(ANKI_ADDONS_DIR)/"; \
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
