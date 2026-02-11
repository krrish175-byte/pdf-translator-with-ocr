import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import io
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

@dataclass
class TextBlock:
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    page_num: int
    fontname: Optional[str] = None
    size: Optional[float] = None

@dataclass
class PDFImage:
    image_data: bytes
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    image_format: str = "JPEG"

class PDFParser:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def parse(self, pdf_path):
        """Extract text and images from PDF"""
        text_blocks = []
        images = []
        
        try:
            # Extract text with pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text blocks
                    words = page.extract_words(keep_blank_chars=True)
                    for word in words:
                        text_block = TextBlock(
                            text=word['text'],
                            x0=float(word['x0']),
                            top=float(word['top']),
                            x1=float(word['x1']),
                            bottom=float(word['bottom']),
                            page_num=page_num,
                            fontname=word.get('fontname'),
                            size=float(word.get('size')) if word.get('size') else None
                        )
                        text_blocks.append(text_block)
                    
                    # Extract images with PyMuPDF for better image extraction quality
                    images.extend(self._extract_images_pymupdf(pdf_path, page_num))
            
            return {
                'text_blocks': text_blocks,
                'images': images,
                'page_count': len(pdf.pages) if 'pdf' in locals() else 0
            }
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {e}")
            raise e
    
    def _extract_images_pymupdf(self, pdf_path, page_num):
        """Extract images using PyMuPDF"""
        images = []
        doc = fitz.open(pdf_path)
        try:
            page = doc.load_page(page_num)
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Get image position (metadata about position is hard in PyMuPDF for raw images)
                    # We often need to iterate through page items to find where the image is drawn.
                    # For now, we'll try to get rects of images on the page.
                    
                    # Rect finding logic:
                    image_rects = [item for item in page.get_images(full=True) if item[0] == xref]
                    # PyMuPDF get_images returns list of (xref, smask, width, height, bpc, colorspace, alt.colorspace, name, filter)
                    # It doesn't give coordinates directly.
                    # We need page.get_image_rects(xref)
                    
                    rects = page.get_image_rects(xref)
                    for rect in rects:
                        pdf_image = PDFImage(
                            image_data=image_bytes,
                            x0=rect.x0,
                            y0=rect.y0,
                            x1=rect.x1,
                            y1=rect.y1,
                            page_num=page_num,
                            image_format=base_image["ext"]
                        )
                        images.append(pdf_image)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to extract image {xref} on page {page_num}: {e}")
                    continue
        finally:
            doc.close()
            
        return images
