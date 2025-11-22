"""
Test Gemini API support for multiple language combinations.
This is a standalone test script.

Run this script to verify Gemini API works with different languages:
    python3 tests/test_gemini_simple.py
"""

import os
import sys
import json
import urllib.request

# Test a few representative language combinations
TEST_CASES = [
    ("Spanish", "hablar", "English"),
    ("French", "parler", "English"),
    ("German", "sprechen", "English"),
    ("Russian", "говорить", "English"),
    ("Japanese", "話す", "English"),
    ("English", "speak", "Spanish"),
    ("English", "hello", "French"),
]

DEFAULT_MODEL = "gemini-flash-latest"

def generate_content(word, source_language, api_key, model, target_language):
    """Generate word definition and example using Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = f"""
    Analyze the word '{word}' in {source_language}.
    
    1. Identify the BASE FORM (lemma) of the word.
    2. Translate the BASE FORM to {target_language}.
    
    Rules for the DEFINITION:
    1. If the base form is a simple, common word (like 'cat', 'milk', 'run'), provide ONLY the direct one-word translation in {target_language}.
    2. If it is complex, abstract, or ambiguous, provide the translation in {target_language} followed by a very short definition (4-7 words) in parentheses.
    
    3. Provide 1 example sentence in {target_language} using the translated word.
    
    Format the output exactly like this:
    BASE_FORM: [The base form of the word in {source_language}]
    DEFINITION: [Translation/definition in {target_language}]
    EXAMPLE: [Sentence in {target_language} using the translated word]
    
    Do not use markdown formatting.
    """
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            
        # Parse response
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return parse_response(text)
        except (KeyError, IndexError) as e:
            return "Error parsing response", "", word
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return f"API Error: {e.code}", "", word
    except Exception as e:
        return f"Error: {str(e)}", "", word

def parse_response(text):
    """Parse Gemini response to extract base form, definition, and example."""
    definition = ""
    example = ""
    base_form = ""
    
    # Remove any markdown formatting if present
    text = text.replace("**", "").replace("*", "")
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.upper().startswith("BASE_FORM:"):
            base_form = line[10:].strip()
        elif line.upper().startswith("DEFINITION:"):
            definition = line[11:].strip()
        elif line.upper().startswith("EXAMPLE:"):
            example = line[8:].strip()
            
    return definition, example, base_form

def test_gemini_languages():
    """Test Gemini API with different source and target language combinations."""
    print("=" * 80)
    print("TESTING GEMINI API LANGUAGE SUPPORT")
    print("=" * 80)
    print("\nNote: This test requires a valid Gemini API key.")
    
    # Try to read API key from config
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    api_key = None
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                api_key = config.get("api_key")
        except:
            pass
    
    if not api_key or "YOUR_KEY" in api_key:
        print("\n⚠️  WARNING: No valid API key found in config.json")
        print("Skipping Gemini API tests...")
        return True
    
    results = []
    failed = []
    
    for i, (source_lang, word, target_lang) in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] Testing: '{word}' ({source_lang} → {target_lang})")
        
        try:
            definition, example, base_form = generate_content(
                word, 
                source_lang, 
                api_key, 
                DEFAULT_MODEL,
                target_lang
            )
            
            print(f"    Base form: {base_form}")
            print(f"    Definition: {definition}")
            print(f"    Example: {example}")
            
            if definition and example and "Error" not in definition:
                print(f"    ✅ SUCCESS")
                results.append((source_lang, target_lang, "✅ PASS"))
            else:
                print(f"    ❌ FAILED - Missing or invalid response")
                results.append((source_lang, target_lang, "❌ FAIL"))
                failed.append(f"{source_lang}→{target_lang}")
        except Exception as e:
            print(f"    ❌ ERROR: {e}")
            results.append((source_lang, target_lang, "❌ ERROR"))
            failed.append(f"{source_lang}→{target_lang}")
        
        # Small delay between API calls
        import time
        time.sleep(1)
    
    # Print summary
    print("\n" + "=" * 80)
    print("GEMINI API TEST SUMMARY")
    print("=" * 80)
    print(f"{'Source Language':<20} {'Target Language':<20} {'Status'}")
    print("-" * 80)
    
    for source, target, status in results:
        print(f"{source:<20} {target:<20} {status}")
    
    print("=" * 80)
    print(f"Total: {len(results)}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\n❌ Failed combinations: {', '.join(failed)}")
        return False
    else:
        print(f"\n🎉 ALL LANGUAGE COMBINATIONS PASSED GEMINI TESTING!")
        return True

if __name__ == "__main__":
    success = test_gemini_languages()
    sys.exit(0 if success else 1)
