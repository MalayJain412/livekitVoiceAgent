import requests
import json 
# --- CONFIGURATION ---
API_KEY = ""
# --- END CONFIGURATION ---

URL = "https://api.elevenlabs.io/v1/voices"
TARGET_MODEL = "eleven_multilingual_v2" # Change this to test other models like eleven_flash_v2_5

headers = {
  "Accept": "application/json",
  "xi-api-key": API_KEY
}

try:
    response = requests.get(URL, headers=headers)
    response.raise_for_status() # Check for HTTP errors

    data = response.json()

    print(f"--- Finding voices that support '{TARGET_MODEL}' ---")
    
    matching_voices = []
    
    for voice in data['voices']:
        # Get the list of models this voice supports. Default to an empty list.
        supported_models = voice.get("high_quality_base_model_ids", [])
        
        # Check if your target model is in the supported list
        if TARGET_MODEL in supported_models:
            matching_voices.append(voice)

    if matching_voices:
        print(f"\nFound {len(matching_voices)} voices for '{TARGET_MODEL}':")
        for voice in matching_voices:
            # --- Extract additional details ---
            voice_id = voice.get('voice_id', 'N/A')
            name = voice.get('name', 'N/A')
            
            # Get labels like accent, age, gender (if available)
            labels = voice.get('labels', {})
            accent = labels.get('accent', 'Unknown Accent')
            age = labels.get('age', 'Unknown Age')
            gender = labels.get('gender', 'Unknown Gender')
            description_label = labels.get('description', 'No Description Label') # e.g., 'calm', 'raspy'
            
            # Get verified languages (if available)
            verified_langs_data = voice.get('verified_languages', [])
            languages = []
            if verified_langs_data: # Check if the list is not None and not empty
                languages = [lang_info.get('language', 'unknown') for lang_info in verified_langs_data]
            else:
                 # Fallback: Sometimes basic voices don't list verified_languages,
                 # but might have a language hint in labels. Check 'accent' or description?
                 # This is less reliable, the API is the source of truth.
                 # For multilingual_v2, it generally supports many languages.
                 if TARGET_MODEL == "eleven_multilingual_v2":
                     languages = ["Multiple (based on model)"] # Indicate model capability
                 else:
                     languages = ["Unknown"]

            # --- Print the details ---
            print(f"\n- Name: {name}")
            print(f"  ID: {voice_id}")
            print(f"  Accent: {accent}")
            print(f"  Gender: {gender}")
            print(f"  Age: {age}")
            print(f"  Description Label: {description_label}")
            print(f"  Supported Languages: {', '.join(languages)}")
            
    else:
        print(f"No voices were found that explicitly support '{TARGET_MODEL}'.")


except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    if "401" in str(e):
        print("Hint: Make sure you have pasted your API_KEY into the script.")