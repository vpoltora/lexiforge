import re

def parse_deck_language(deck_name, deck_language_map):
    for pattern, language in deck_language_map.items():
        if re.search(pattern, deck_name, re.IGNORECASE):
            return language
    return "en"
