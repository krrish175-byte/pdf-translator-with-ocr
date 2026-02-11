import base64
import io
from anthropic import Anthropic

def encode_image(image):
    """Encode PIL Image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

class ClaudeService:
    def __init__(self, api_key):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20240620"

    def translate_page(self, image, source_lang="English", target_lang="Japanese"):
        """
        Sends page image to Claude for analysis and translation.
        Returns HTML string representing the translated page.
        """
        base64_image = encode_image(image)
        
        system_prompt = f"""You are an expert translator and document layout specialist. 
Your task is to translate the document from {source_lang} to {target_lang} while PRESERVING the visual layout, formatting, and style as closely as possible.

Return ONLY a complete, valid HTML document with embedded CSS. 
- The HTML should accurately mirror the structure of the original image.
- Use absolute positioning or flexbox/grid to match the layout.
- The output will be converted to PDF, so ensure it fits on a standard A4 page (or match aspect ratio).
- Do not explain your process, just return the HTML code start to finish.
- If there are images/figures, try to preserve their space or describe them in a placeholder if you cannot reproduce them (but prefer reproducing text content).
"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Translate this page to {target_lang}. Preserve the layout using HTML/CSS."
                        }
                    ],
                }
            ],
        )
        
        return message.content[0].text
