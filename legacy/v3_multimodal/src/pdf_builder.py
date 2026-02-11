import fitz  # PyMuPDF
from PIL import Image
import io
import logging
from pathlib import Path
from src.utils.fonts import get_cjk_font_path

class PDFBuilder:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def build(self, original_pdf, translated_text, processed_images, output_path):
        """Rebuild PDF with translated content"""
        # Open original PDF
        doc = fitz.open(original_pdf)
        
        # Load CJK font for PDF text insertion
        cjk_font_path = get_cjk_font_path()
        fontname = "helv"
        if cjk_font_path:
            self.logger.info(f"Using CJK font: {cjk_font_path}")
            fontname = "cjk_font"
            # We will use 'fontfile' argument in insert_textbox
        else:
            self.logger.warning("CJK font not found. Japanese text may not render correctly (?????).")
        
        # Group text and images by page
        text_by_page = {}
        images_by_page = {}
        
        for text_block in translated_text:
            page_num = text_block.page_num
            if page_num not in text_by_page:
                text_by_page[page_num] = []
            text_by_page[page_num].append(text_block)
        
        for image in processed_images:
            page_num = image.page_num
            if page_num not in images_by_page:
                images_by_page[page_num] = []
            images_by_page[page_num].append(image)
        
        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # --- 1. Redact Original Text ---
            if page_num in text_by_page:
                for text_block in text_by_page[page_num]:
                    # Create redaction annotation
                    rect = fitz.Rect(
                        text_block.x0, text_block.top,
                        text_block.x1, text_block.bottom
                    )
                    
                    # Fill with white (simplest)
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                
                page.apply_redactions()
            
            # --- 2. Replace Images ---
            if page_num in images_by_page:
                for image in images_by_page[page_num]:
                    # Build rect
                    rect = fitz.Rect(image.x0, image.y0, image.x1, image.y1)
                    
                    # We can't easily "replace" an image in-place without potentially distinct logic,
                    # but since we are rebuilding, we can overlay the new image.
                    # Or we can redact the old image area first?
                    # Images in PDF are distinct objects.
                    # Redaction removes underlying content including images.
                    
                    # Redact image area first to clear it
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    page.apply_redactions()
                    
                    # Insert new processed image
                    page.insert_image(rect, stream=image.processed_image)
            
            # --- 3. Insert Translated Text ---
            if page_num in text_by_page:
                for text_block in text_by_page[page_num]:
                    if not text_block.translated:
                        self.logger.warning(f"Skipping empty translation for block at {text_block.top}")
                        continue
                        
                    rect = fitz.Rect(
                        text_block.x0, text_block.top,
                        text_block.x1, text_block.bottom
                    )
                    
                    # Estimate font size
                    height = text_block.bottom - text_block.top
                    font_size = max(6, height * 0.8)
                    
                    self.logger.debug(f"Inserting text: '{text_block.translated}' at {rect} with font {fontname}")
                    
                    # Attempt to insert text, reducing font size if necessary
                    inserted = False
                    current_fontsize = font_size
                    min_fontsize = 6
                    
                    while current_fontsize >= min_fontsize:
                        try:
                            rc = -1
                            if cjk_font_path:
                                rc = page.insert_textbox(
                                    rect,
                                    text_block.translated,
                                    fontsize=current_fontsize,
                                    fontname=fontname,
                                    fontfile=cjk_font_path,
                                    color=(0, 0, 0)
                                )
                            else:
                                rc = page.insert_textbox(
                                    rect,
                                    text_block.translated,
                                    fontsize=current_fontsize,
                                    fontname="helv",
                                    color=(0, 0, 0)
                                )
                                
                            if rc >= 0:
                                self.logger.debug(f"Inserted text successfully with fontsize {current_fontsize}")
                                inserted = True
                                break
                            else:
                                self.logger.debug(f"Text did not fit with fontsize {current_fontsize}, retrying smaller...")
                                current_fontsize -= 2
                                
                        except Exception as e:
                            self.logger.warning(f"Failed to insert text: {e}")
                            break
                            
                    if not inserted:
                         self.logger.warning(f"Could not fit text '{text_block.translated}' into {rect}. Using simple insertion.")
                         # Fallback to insert_text at top-left of rect
                         try:
                             # Use a small font for fallback
                             fallback_fontsize = max(6, height * 0.6)
                             if cjk_font_path:
                                 page.insert_text(
                                     (rect.x0, rect.y0 + fallback_fontsize),
                                     text_block.translated,
                                     fontsize=fallback_fontsize,
                                     fontname=fontname,
                                     fontfile=cjk_font_path,
                                     color=(0, 0, 0)
                                 )
                             else:
                                 page.insert_text(
                                     (rect.x0, rect.y0 + fallback_fontsize),
                                     text_block.translated,
                                     fontsize=fallback_fontsize,
                                     fontname="helv",
                                     color=(0, 0, 0)
                                 )
                         except Exception as e:
                             self.logger.error(f"Fallback insertion failed: {e}")
        
        # Save the document
        doc.save(output_path)
        doc.close()
        
        self.logger.info(f"PDF rebuilt and saved to {output_path}")
