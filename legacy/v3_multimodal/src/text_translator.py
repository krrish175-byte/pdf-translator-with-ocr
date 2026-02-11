from deep_translator import GoogleTranslator
from dataclasses import dataclass
from typing import List, Optional
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from langdetect import detect, LangDetectException

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

@dataclass
class TranslatedText:
    original: str
    translated: str
    x0: float
    top: float
    x1: float
    bottom: float
    page_num: int
    fontname: Optional[str] = None
    size: Optional[float] = None

class TextTranslator:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.source_lang = config['translation']['source_lang']
        self.target_lang = config['translation']['target_lang']
        self.provider = config['translation'].get('api_provider', 'google')
        
        self.logger.info(f"Initializing TextTranslator using provider: {self.provider}")
        
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                self.logger.error("OpenAI library not installed. Falling back to Google.")
                self.provider = "google"
            else:
                api_key = config['translation'].get('api_key') or os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    self.logger.error("OpenAI API key not found in config or environment. Falling back to Google.")
                    self.provider = "google"
                else:
                    self.client = OpenAI(api_key=api_key)
                    self.model = config['translation'].get('model', 'gpt-3.5-turbo')
        
        if self.provider == "google":
            self.google_translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def translate_text(self, text):
        """Translate single text block with retry logic"""
        if not text or not text.strip():
            return text
        
        # Skip translation if already in target language (optimization)
        # Note: langdetect might be inaccurate for short text, but good for blocks
        try:
            detected = detect(text)
            if detected == self.target_lang:
                return text
        except LangDetectException:
            pass
            
        if self.provider == "openai":
            return self._translate_openai(text)
        else:
            return self._translate_google(text)

    def _translate_google(self, text):
        try:
            # Using deep-translator (more robust than googletrans)
            if not hasattr(self, 'google_translator'):
                 self.google_translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
                 
            return self.google_translator.translate(text)
        except Exception as e:
            self.logger.warning(f"Google translation failed for text: {text[:20]}... Error: {e}")
            return text

    def _translate_openai(self, text):
        try:
            # Construct prompt
            system_prompt = f"You are a professional translator. Translate the following text from {self.source_lang} to {self.target_lang}. Return ONLY the translated text, no explanations."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.warning(f"OpenAI translation failed for text: {text[:20]}... Error: {e}")
            return text
    
    def translate_all(self, text_blocks):
        """Translate all text blocks"""
        translated_blocks = []
        total = len(text_blocks)
        
        for idx, block in enumerate(text_blocks):
            if idx % 5 == 0:
                self.logger.info(f"Translating text block {idx}/{total}")
                
            translated_text = self.translate_text(block.text)
            self.logger.debug(f"Block {idx}: '{block.text}' -> '{translated_text}'")
            
            translated_block = TranslatedText(
                original=block.text,
                translated=translated_text,
                x0=block.x0,
                top=block.top,
                x1=block.x1,
                bottom=block.bottom,
                page_num=block.page_num,
                fontname=block.fontname,
                size=block.size
            )
            translated_blocks.append(translated_block)
        
        self.logger.info(f"Translated {len(translated_blocks)} text blocks")
        return translated_blocks
