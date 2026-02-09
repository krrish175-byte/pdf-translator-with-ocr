"""
Translation service wrapper for multi-language PDF translation.
Uses deep-translator for better compatibility.
Supports: English (en), Japanese (ja), Chinese (zh)
"""

from deep_translator import GoogleTranslator
import time

# Language codes for deep-translator
LANGUAGE_CODES = {
    'en': 'english',
    'ja': 'japanese', 
    'zh': 'chinese (simplified)'
}


class TranslationService:
    """Handles text translation between languages."""
    
    def __init__(self, source_lang: str = 'en', target_lang: str = 'ja'):
        source = LANGUAGE_CODES.get(source_lang, 'english')
        target = LANGUAGE_CODES.get(target_lang, 'japanese')
        self.translator = GoogleTranslator(source=source, target=target)
        print(f"Translator: {source} → {target}")
    
    def translate_text(self, text: str, max_retries: int = 3) -> str:
        """
        Translate text from English to Japanese.
        
        Args:
            text: The English text to translate
            max_retries: Maximum number of retry attempts
            
        Returns:
            Translated Japanese text
        """
        if not text or not text.strip():
            return text
        
        # Skip if text is too short or just whitespace/numbers
        cleaned = text.strip()
        if len(cleaned) < 2:
            return text
        
        for attempt in range(max_retries):
            try:
                result = self.translator.translate(cleaned)
                return result if result else text
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                print(f"Translation failed after {max_retries} attempts: {e}")
                return text
        
        return text
    
    def batch_translate(self, texts: list[str]) -> list[str]:
        """
        Translate a batch of texts.
        
        Args:
            texts: List of English texts to translate
            
        Returns:
            List of translated Japanese texts
        """
        translated = []
        for text in texts:
            translated.append(self.translate_text(text))
            time.sleep(0.1)  # Rate limiting
        return translated
