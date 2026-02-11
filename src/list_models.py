import google.generativeai as genai
import sys

def list_models(api_key):
    genai.configure(api_key=api_key)
    print("Available models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python src/list_models.py <api_key>")
    else:
        list_models(sys.argv[1])
