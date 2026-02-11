import google.generativeai as genai
import os
import base64
from io import BytesIO

from tenacity import retry, stop_after_attempt, wait_exponential

class GeminiService:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    def translate_page(self, image, width, height, source_lang="English", target_lang="Japanese"):
        """
        Sends page image to Gemini for analysis and translation.
        Returns HTML string representing the translated page with original image as background.
        """
        
        # Convert PIL Image to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        bg_placeholder = "{{BG_IMAGE_PLACEHOLDER}}"

        system_prompt = f"""You are an expert translator and document layout specialist. 
Your task is to translate the document from {source_lang} to {target_lang} while PRESERVING the visual layout.

The original image size is {width}x{height} pixels.

Return ONLY a complete, valid HTML document with embedded CSS. 
1. The HTML must include this CSS to match the page size exactly and use the original image as BACKGROUND:
   <style>
     @page {{ size: {width}px {height}px; margin: 0; }}
     body {{ 
        width: {width}px; 
        height: {height}px; 
        margin: 0; 
        padding: 0; 
        overflow: hidden; 
        position: relative;
        background-image: url('{bg_placeholder}');
        background-size: contain;
        background-repeat: no-repeat;
     }}
     .page-container {{ width: 100%; height: 100%; position: relative; }}
     .text-block {{ 
        position: absolute; 
        white-space: pre-wrap; 
        word-wrap: break-word; 
        overflow: visible;
        background-color: rgba(255, 255, 255, 0.9); /* High contrast background to cover original text */
        color: black;
        padding: 2px;
        z-index: 10;
     }}
   </style>

2. Translate all {source_lang} text to {target_lang}. 
3. Use absolute positioning to place text blocks EXACTLY over the original text locations.
4. **CRITICAL: Prevent Text Overlap & Visual Fidelity**
   - DO NOT recreate images, charts, or diagrams. They are already in the background.
   - ONLY generate div elements for the translated TEXT.
   - Ensure text blocks have a white/light background to obscure the original text underneath.
   - Ensure text blocks do NOT overlap with each other.
   - If translated text is longer, reduce font size or adjust line height.
   
5. Do not omit any text, headlines, or captions.
6. Do not wrap the output in markdown code blocks, just return the raw HTML code.
"""
        
        try:
            response = self.model.generate_content([system_prompt, image])
            text = response.text
            
            # Simple cleanup if Gemini returns markdown block
            if text.startswith("```html"):
                text = text.replace("```html", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            
            text = text.strip()
            
            # Replace placeholder with actual base64 image
            final_html = text.replace(bg_placeholder, f"data:image/jpeg;base64,{img_str}")
            
            return final_html
            
        except Exception as e:
            # Re-raise for tenacity to handle
            raise Exception(f"Gemini API Error: {str(e)}")
