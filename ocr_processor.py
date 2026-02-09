"""
OCR processor for extracting and replacing text in images.
"""

import pytesseract
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from io import BytesIO
from translator import TranslationService

# Tesseract language codes
TESSERACT_LANGS = {
    'en': 'eng',
    'ja': 'jpn',
    'zh': 'chi_sim'
}


class OCRProcessor:
    """Handles OCR text extraction and image text overlay."""
    
    def __init__(self, source_lang: str = 'en', target_lang: str = 'ja'):
        self.translator = TranslationService(source_lang, target_lang)
        # Configure Tesseract for source language
        tess_lang = TESSERACT_LANGS.get(source_lang, 'eng')
        self.tesseract_config = f'--oem 3 --psm 6 -l {tess_lang}'
    
    def extract_text_from_image(self, image: Image.Image) -> list[dict]:
        """
        Extract text and bounding boxes from an image using Tesseract OCR.
        
        Args:
            image: PIL Image object
            
        Returns:
            List of dicts with 'text', 'bbox', 'conf' keys
        """
        # Convert to OpenCV format for preprocessing
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Apply preprocessing to improve OCR accuracy
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Get detailed OCR data
        try:
            data = pytesseract.image_to_data(
                gray,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            return []
        
        # Extract text blocks with bounding boxes
        text_blocks = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            # Only include text with reasonable confidence
            if text and conf > 30:
                text_blocks.append({
                    'text': text,
                    'bbox': (
                        data['left'][i],
                        data['top'][i],
                        data['width'][i],
                        data['height'][i]
                    ),
                    'conf': conf
                })
        
        return text_blocks
    
    def group_text_blocks(self, text_blocks: list[dict], line_threshold: int = 10) -> list[dict]:
        """
        Group text blocks that are on the same line.
        
        Args:
            text_blocks: List of individual text blocks
            line_threshold: Vertical distance threshold for same-line grouping
            
        Returns:
            List of grouped text blocks
        """
        if not text_blocks:
            return []
        
        # Sort by vertical position
        sorted_blocks = sorted(text_blocks, key=lambda x: (x['bbox'][1], x['bbox'][0]))
        
        # Group blocks on same line
        lines = []
        current_line = [sorted_blocks[0]]
        
        for block in sorted_blocks[1:]:
            prev_y = current_line[-1]['bbox'][1]
            curr_y = block['bbox'][1]
            
            if abs(curr_y - prev_y) <= line_threshold:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
        
        lines.append(current_line)
        
        # Combine each line into a single block
        grouped = []
        for line in lines:
            if not line:
                continue
            
            # Sort by x position
            line = sorted(line, key=lambda x: x['bbox'][0])
            
            # Combine text
            combined_text = ' '.join([b['text'] for b in line])
            
            # Calculate bounding box for entire line
            min_x = min(b['bbox'][0] for b in line)
            min_y = min(b['bbox'][1] for b in line)
            max_x = max(b['bbox'][0] + b['bbox'][2] for b in line)
            max_y = max(b['bbox'][1] + b['bbox'][3] for b in line)
            
            grouped.append({
                'text': combined_text,
                'bbox': (min_x, min_y, max_x - min_x, max_y - min_y),
                'conf': sum(b['conf'] for b in line) // len(line)
            })
        
        return grouped
    
    def overlay_translation(self, image: Image.Image, text_blocks: list[dict]) -> Image.Image:
        """
        Replace English text with Japanese translation in the image.
        
        Args:
            image: Original PIL Image
            text_blocks: List of text blocks with translations
            
        Returns:
            Modified PIL Image with Japanese text overlay
        """
        # Create a copy to modify
        img = image.copy()
        draw = ImageDraw.Draw(img)
        
        # Try to use a Japanese font
        font_size = 14
        try:
            # Try common Japanese fonts on macOS
            font_paths = [
                '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
                '/Library/Fonts/Arial Unicode.ttf',
                '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
            ]
            font = None
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        for block in text_blocks:
            if 'translated' not in block:
                continue
            
            x, y, w, h = block['bbox']
            
            # Draw white background to cover original text
            draw.rectangle([x, y, x + w, y + h], fill='white')
            
            # Draw translated text
            translated = block['translated']
            draw.text((x, y), translated, fill='black', font=font)
        
        return img
    
    def process_image(self, image_bytes: bytes) -> tuple[bytes, bool]:
        """
        Full pipeline: extract text, translate, and overlay.
        
        Args:
            image_bytes: Original image as bytes
            
        Returns:
            Tuple of (processed image bytes, whether text was found)
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text
            text_blocks = self.extract_text_from_image(image)
            
            if not text_blocks:
                return image_bytes, False
            
            # Group into lines
            grouped_blocks = self.group_text_blocks(text_blocks)
            
            # Translate each block
            for block in grouped_blocks:
                block['translated'] = self.translator.translate_text(block['text'])
            
            # Overlay translations
            processed_image = self.overlay_translation(image, grouped_blocks)
            
            # Convert back to bytes
            output = BytesIO()
            processed_image.save(output, format='PNG', quality=95)
            output.seek(0)
            
            return output.getvalue(), True
            
        except Exception as e:
            print(f"Image processing error: {e}")
            return image_bytes, False
