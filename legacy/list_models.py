import google.generativeai as genai
import os
from config import GEMINI_API_KEY as key

genai.configure(api_key=key)
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
