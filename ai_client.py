import urllib.request
import json
import re

DEFAULT_MODEL = "gemini-flash-latest"

def generate_content(word, language, api_key, model=DEFAULT_MODEL):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = f"""
    Analyze the word '{word}' in {language}.
    
    1. Identify the BASE FORM (lemma) of the word.
    2. Translate the BASE FORM to English.
    
    Rules for the DEFINITION:
    1. If the base form is a simple, common word (like 'cat', 'milk', 'run'), provide ONLY the direct one-word translation.
    2. If it is complex, abstract, or ambiguous, provide the translation followed by a very short definition (4-7 words) in parentheses.
    
    3. Provide 1 example sentence in {language} using the BASE FORM.
    
    Format the output exactly like this:
    BASE_FORM: [The base form of the word]
    DEFINITION: [English translation/definition of the base form]
    EXAMPLE: [Sentence in {language} using the base form]
    
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
            print(f"VocabAI Raw Response: {text}") # Debug log
            return parse_response(text)
        except (KeyError, IndexError) as e:
            print(f"VocabAI Error parsing response: {e}")
            return "Error parsing AI response", "", word # Return original word as fallback
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"VocabAI HTTP Error {e.code}: {error_body}")
        
        # If model not found (404), try to list available models to help debug
        if e.code == 404:
            print("VocabAI: Model not found. Listing available models...")
            list_models(api_key)
            
        return f"API Error: {e.code}", "", word
    except Exception as e:
        print(f"VocabAI General Error: {e}")
        return f"Error: {str(e)}", "", word

def parse_response(text):
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

def list_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        with urllib.request.urlopen(url) as response:
            result = json.loads(response.read().decode("utf-8"))
            models = result.get("models", [])
            print("VocabAI Available Models:")
            for m in models:
                print(f"- {m['name']} ({m.get('displayName', '')})")
            return models
    except Exception as e:
        print(f"VocabAI Error listing models: {e}")
        return []
