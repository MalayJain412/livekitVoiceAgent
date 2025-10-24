import requests
import json 

# --- CONFIGURATION ---
API_KEY = ""  # <--- PASTE YOUR API KEY HERE
TARGET_MODEL = "eleven_multilingual_v2" 
TARGET_GENDER = "female"
TARGET_ACCENT = "british" # Use lowercase for matching
# --- END CONFIGURATION ---

URL = "https://api.elevenlabs.io/v1/voices"

headers = {
  "Accept": "application/json",
  "xi-api-key": API_KEY
}

try:
    response = requests.get(URL, headers=headers)
    response.raise_for_status() # Check for HTTP errors

    data = response.json()

    print(f"--- Finding '{TARGET_GENDER}' voices with '{TARGET_ACCENT}' accent supporting '{TARGET_MODEL}' ---")
    
    matching_voices = []
    
    for voice in data['voices']:
        # 1. Check Model Compatibility
        supported_models = voice.get("high_quality_base_model_ids", [])
        if TARGET_MODEL not in supported_models:
            continue # Skip if model doesn't match

        # 2. Check Labels for Gender and Accent
        labels = voice.get('labels', {})
        gender = labels.get('gender', '').lower()
        accent = labels.get('accent', '').lower()

        if gender == TARGET_GENDER and accent == TARGET_ACCENT:
            matching_voices.append(voice)

    if matching_voices:
        print(f"\nFound {len(matching_voices)} matching voices:")
        for voice in matching_voices:
            voice_id = voice.get('voice_id', 'N/A')
            name = voice.get('name', 'N/A')
            
            labels = voice.get('labels', {})
            accent_display = labels.get('accent', 'Unknown Accent') # Keep original case for display
            age = labels.get('age', 'Unknown Age')
            gender_display = labels.get('gender', 'Unknown Gender') # Keep original case for display
            description_label = labels.get('description', 'No Description Label')
            
            verified_langs_data = voice.get('verified_languages', [])
            languages = []
            if verified_langs_data:
                languages = [lang_info.get('language', 'unknown') for lang_info in verified_langs_data]
            elif TARGET_MODEL == "eleven_multilingual_v2":
                 languages = ["Multiple (based on model)"]
            else:
                 languages = ["Unknown"]

            print(f"\n- Name: {name}")
            print(f"  ID: {voice_id}")
            print(f"  Accent: {accent_display}")
            print(f"  Gender: {gender_display}")
            print(f"  Age: {age}")
            print(f"  Description Label: {description_label}")
            print(f"  Supported Languages: {', '.join(languages)}")
            
    else:
        print(f"No voices were found matching all criteria (Model: '{TARGET_MODEL}', Gender: '{TARGET_GENDER}', Accent: '{TARGET_ACCENT}').")


except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
    if "401" in str(e):
        print("Hint: Make sure you have pasted your API_KEY into the script.")