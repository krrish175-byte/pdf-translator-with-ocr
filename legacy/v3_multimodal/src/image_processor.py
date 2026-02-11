import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr
import io
from dataclasses import dataclass
from typing import List, Tuple
import logging
from pathlib import Path
from src.utils.fonts import get_cjk_font_path
from .text_translator import TextTranslator

@dataclass
class ProcessedImage:
    original_image: bytes
    processed_image: bytes
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    translated_texts: List[Tuple[str, str, Tuple[int, int, int, int]]]

class ImageProcessor:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.text_translator = TextTranslator(config)
        
        # Initialize OCR reader
        self.logger.info("Initializing EasyOCR...")
        try:
            self.reader = easyocr.Reader(
                self.config['ocr']['languages'], 
                gpu=self.config['ocr']['gpu']
            )
        except Exception as e:
            self.logger.warning(f"EasyOCR initialization failed: {e}. OCR features will be disabled.")
            self.reader = None
        

    

    
    def process_image(self, pdf_image):
        """Process a single image: OCR, translate, overlay text"""
        if not self.reader:
            return ProcessedImage(
                original_image=pdf_image.image_data,
                processed_image=pdf_image.image_data,
                x0=pdf_image.x0, y0=pdf_image.y0, x1=pdf_image.x1, y1=pdf_image.y1,
                page_num=pdf_image.page_num, translated_texts=[]
            )

        try:
            # Convert bytes to PIL Image
            pil_image = Image.open(io.BytesIO(pdf_image.image_data))
            # Handle RGBA to RGB convert if needed for opencv
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
                
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Perform OCR
            ocr_results = self.reader.readtext(cv_image)
            
            translated_texts = []
            processed_image = cv_image.copy()
            
            for bbox, text, confidence in ocr_results:
                if confidence < self.config['ocr']['text_threshold']:
                    continue
                
                # Translate text
                translated = self.text_translator.translate_text(text)
                
                # Store for debugging
                translated_texts.append((text, translated, bbox))
                
                # Remove original text (simple white rectangle overlay)
                # For production, use inpainting algorithms like cv2.inpaint
                top_left = tuple(map(int, bbox[0]))
                bottom_right = tuple(map(int, bbox[2]))
                
                # Get mask of text area
                # mask = np.zeros(processed_image.shape[:2], dtype="uint8")
                # cv2.rectangle(mask, top_left, bottom_right, 255, -1)
                # processed_image = cv2.inpaint(processed_image, mask, 3, cv2.INPAINT_TELEA) # Slower but better
                
                # Fast whitespace fill
                cv2.rectangle(processed_image, top_left, bottom_right, (255, 255, 255), -1)
                
                # Add translated text
                # Calculate font size based on bbox size
                bbox_width = bottom_right[0] - top_left[0]
                text_len = len(translated) if translated else 1
                font_scale = bbox_width / (text_len * 10) 
                # This scaling is for cv2.putText. For PIL ImageFont it's different.
                
                # Use PIL for better Japanese text rendering
                pil_processed = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil_processed)
                
                # Position text
                text_position = (top_left[0], top_left[1])
                
                # Approximate font size
                bbox_height = bottom_right[1] - top_left[1]
                font_size = max(10, int(bbox_height * 0.8))
                
                font_path = get_cjk_font_path()
                if font_path:
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    font = ImageFont.load_default()
                
                try:
                    draw.text(text_position, translated, font=font, fill=(0, 0, 0))
                except:
                    # Fallback
                    pass
                
                processed_image = cv2.cvtColor(np.array(pil_processed), cv2.COLOR_RGB2BGR)
            
            # Convert back to bytes
            _, buffer = cv2.imencode('.png', processed_image)
            processed_bytes = buffer.tobytes()
            
            return ProcessedImage(
                original_image=pdf_image.image_data,
                processed_image=processed_bytes,
                x0=pdf_image.x0,
                y0=pdf_image.y0,
                x1=pdf_image.x1,
                y1=pdf_image.y1,
                page_num=pdf_image.page_num,
                translated_texts=translated_texts
            )
            
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            # Return original if failed
            return ProcessedImage(
                original_image=pdf_image.image_data,
                processed_image=pdf_image.image_data,
                x0=pdf_image.x0, y0=pdf_image.y0, x1=pdf_image.x1, y1=pdf_image.y1,
                page_num=pdf_image.page_num, translated_texts=[]
            )
    
    def process_all(self, images):
        """Process all images in the PDF"""
        processed_images = []
        total = len(images)
        
        for idx, image in enumerate(images):
            if idx % 5 == 0:
                self.logger.info(f"Processing image {idx+1}/{total}")
            
            try:
                processed = self.process_image(image)
                processed_images.append(processed)
            except Exception as e:
                self.logger.error(f"Failed to process image: {e}")
                processed_images.append(ProcessedImage(
                    original_image=image.image_data,
                    processed_image=image.image_data,
                    x0=image.x0, y0=image.y0, x1=image.x1, y1=image.y1,
                    page_num=image.page_num, translated_texts=[]
                ))
        
        self.logger.info(f"Processed {len(processed_images)} images")
        return processed_images
