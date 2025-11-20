# Makefile for VocabAI

# Define virtual environment path
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
FLAKE8 := $(VENV)/bin/flake8

# Anki addons directory
ANKI_ADDONS := $(HOME)/Library/Application Support/Anki2/addons21/vocabai

.PHONY: all lint clean package dev

# Default target
all: lint

# Create virtual environment and install dependencies
$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install flake8

# Run linter (depends on venv)
lint: $(VENV)
	$(FLAKE8) . --exclude=.venv --count --select=E9,F63,F7,F82 --show-source --statistics
	$(FLAKE8) . --exclude=.venv --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Clean up
clean:
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -f *.pyc
	rm -f .DS_Store
	rm -f *.zip

# Sync to Anki for development (excludes dev files)
dev:
	@echo "Syncing VocabAI to Anki..."
	@mkdir -p "$(ANKI_ADDONS)"
	@rsync -av --delete \
		--exclude='.venv/' \
		--exclude='__pycache__/' \
		--exclude='*.pyc' \
		--exclude='.DS_Store' \
		--exclude='Makefile' \
		--exclude='create_icon.py' \
		--exclude='*.zip' \
		./ "$(ANKI_ADDONS)/"
	@echo "✅ VocabAI synced to $(ANKI_ADDONS)"
	@echo "⚠️  Restart Anki to reload changes."

# Package the addon
package: clean
	zip -r vocabai.zip . -x "*.git*" -x "Makefile" -x "*.zip" -x "tests/*" -x ".venv/*"
