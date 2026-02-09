"""
PDF processor for extracting content, translating, and rebuilding PDFs.
"""

import fitz  # PyMuPDF
from io import BytesIO
from pathlib import Path
from translator import TranslationService
from ocr_processor import OCRProcessor


class PDFProcessor:
    """Handles PDF text extraction, image processing, and PDF generation."""
    
    def __init__(self, source_lang: str = 'en', target_lang: str = 'ja',
                 translate_text: bool = True, translate_images: bool = True):
        self.translator = TranslationService(source_lang, target_lang)
        self.ocr_processor = OCRProcessor(source_lang, target_lang)
        self.translate_text = translate_text
        self.translate_images = translate_images
    
    def extract_content(self, pdf_bytes: bytes) -> dict:
        """
        Extract all content from a PDF.
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Dict with 'pages' containing text blocks and images
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        content = {
            'page_count': len(doc),
            'pages': []
        }
        
        for page_num, page in enumerate(doc):
            page_content = {
                'number': page_num,
                'width': page.rect.width,
                'height': page.rect.height,
                'text_blocks': [],
                'images': []
            }
            
            # Extract text blocks with positions
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            if span.get("text", "").strip():
                                page_content['text_blocks'].append({
                                    'text': span['text'],
                                    'bbox': span['bbox'],
                                    'font': span.get('font', 'Helvetica'),
                                    'size': span.get('size', 12),
                                    'color': span.get('color', 0),
                                    'flags': span.get('flags', 0)
                                })
            
            # Extract images
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        # Get image position on page
                        img_rects = page.get_image_rects(xref)
                        rect = img_rects[0] if img_rects else None
                        
                        page_content['images'].append({
                            'xref': xref,
                            'data': base_image['image'],
                            'ext': base_image['ext'],
                            'rect': rect,
                            'width': base_image.get('width', 0),
                            'height': base_image.get('height', 0)
                        })
                except Exception as e:
                    print(f"Error extracting image {xref}: {e}")
            
            content['pages'].append(page_content)
        
        doc.close()
        return content
    
    def translate_content(self, content: dict, progress_callback=None) -> dict:
        """
        Translate all content in the extracted PDF.
        
        Args:
            content: Extracted PDF content
            progress_callback: Optional callback(current, total, message)
            
        Returns:
            Same structure with translated content
        """
        total_items = sum(
            len(page['text_blocks']) + len(page['images'])
            for page in content['pages']
        )
        current_item = 0
        
        for page in content['pages']:
            page_num = page['number'] + 1
            
            # Translate text blocks
            if self.translate_text:
                for block in page['text_blocks']:
                    block['translated'] = self.translator.translate_text(block['text'])
                    current_item += 1
                    if progress_callback:
                        progress_callback(
                            current_item,
                            total_items,
                            f"Translating text on page {page_num}..."
                        )
            
            # Process images with OCR
            if self.translate_images:
                for img in page['images']:
                    processed_data, had_text = self.ocr_processor.process_image(img['data'])
                    img['processed_data'] = processed_data
                    img['had_text'] = had_text
                    current_item += 1
                    if progress_callback:
                        progress_callback(
                            current_item,
                            total_items,
                            f"Processing images on page {page_num}..."
                        )
        
        return content
    
    def rebuild_pdf(self, original_bytes: bytes, translated_content: dict) -> bytes:
        """
        Rebuild PDF with translated content using redaction for clean text replacement.
        
        Args:
            original_bytes: Original PDF bytes
            translated_content: Content with translations
            
        Returns:
            New PDF as bytes
        """
        # Open original document
        doc = fitz.open(stream=original_bytes, filetype="pdf")
        
        for page_data in translated_content['pages']:
            page_num = page_data['number']
            page = doc[page_num]
            
            # Collect translations grouped by their approximate line position
            if self.translate_text:
                # First pass: Add redaction annotations to remove original text
                for block in page_data['text_blocks']:
                    if 'translated' in block and block['translated'] != block['text']:
                        bbox = fitz.Rect(block['bbox'])
                        
                        # Sample background color from near the text area
                        try:
                            pix = page.get_pixmap(clip=bbox, alpha=False)
                            samples = pix.samples
                            if len(samples) >= 3:
                                # Get average color from the pixmap
                                r = samples[0] / 255.0
                                g = samples[1] / 255.0
                                b = samples[2] / 255.0
                                fill_color = (r, g, b)
                            else:
                                fill_color = (1, 1, 1)  # White fallback
                        except:
                            fill_color = (1, 1, 1)  # White fallback
                        
                        # Add redaction annotation with sampled background color
                        page.add_redact_annot(
                            bbox,
                            text="",  # No replacement text in redaction
                            fill=fill_color  # Use sampled background color
                        )
                
                # Apply all redactions (removes the original text)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                
                # Second pass: Insert translated text
                for block in page_data['text_blocks']:
                    if 'translated' in block and block['translated'] != block['text']:
                        bbox = fitz.Rect(block['bbox'])
                        
                        # Calculate appropriate font size
                        original_size = block.get('size', 12)
                        # Adjust font size for Japanese (typically needs smaller size)
                        font_size = max(6, min(original_size * 0.85, 24))
                        
                        # Get original text color
                        color = block.get('color', 0)
                        if isinstance(color, int):
                            # Convert integer color to RGB tuple
                            r = ((color >> 16) & 255) / 255.0
                            g = ((color >> 8) & 255) / 255.0
                            b = (color & 255) / 255.0
                            text_color = (r, g, b)
                        else:
                            text_color = (0, 0, 0)  # Default to black
                        
                        # Insert translated text at the original position
                        try:
                            # Try inserting with Japanese font
                            text_point = fitz.Point(bbox.x0, bbox.y0 + font_size)
                            page.insert_text(
                                text_point,
                                block['translated'],
                                fontsize=font_size,
                                fontname="japan",
                                color=text_color
                            )
                        except Exception:
                            try:
                                # Fallback: try with CJK font
                                page.insert_text(
                                    text_point,
                                    block['translated'],
                                    fontsize=font_size,
                                    fontname="china-s",
                                    color=text_color
                                )
                            except Exception:
                                try:
                                    # Final fallback: default font
                                    page.insert_text(
                                        text_point,
                                        block['translated'],
                                        fontsize=font_size,
                                        color=text_color
                                    )
                                except Exception:
                                    pass  # Skip if all attempts fail
            
            # Replace images with processed versions
            if self.translate_images:
                for img in page_data['images']:
                    if img.get('had_text') and img.get('processed_data') and img.get('rect'):
                        try:
                            rect = fitz.Rect(img['rect'])
                            
                            # Remove original image
                            page.delete_image(img['xref'])
                            
                            # Insert processed image
                            page.insert_image(
                                rect,
                                stream=img['processed_data'],
                                keep_proportion=True
                            )
                        except Exception as e:
                            print(f"Error replacing image: {e}")
        
        # Save to bytes with cleanup
        output = BytesIO()
        doc.save(output, garbage=4, deflate=True, clean=True)
        doc.close()
        
        output.seek(0)
        return output.getvalue()
    
    def process_pdf(self, pdf_bytes: bytes, progress_callback=None) -> bytes:
        """
        Full pipeline: extract, translate, and rebuild PDF.
        
        Args:
            pdf_bytes: Input PDF as bytes
            progress_callback: Optional progress callback
            
        Returns:
            Translated PDF as bytes
        """
        # Extract content
        if progress_callback:
            progress_callback(0, 100, "Extracting PDF content...")
        
        content = self.extract_content(pdf_bytes)
        
        # Translate content
        translated_content = self.translate_content(content, progress_callback)
        
        # Rebuild PDF
        if progress_callback:
            progress_callback(95, 100, "Generating translated PDF...")
        
        result = self.rebuild_pdf(pdf_bytes, translated_content)
        
        if progress_callback:
            progress_callback(100, 100, "Complete!")
        
        return result
    
    def generate_preview(self, pdf_bytes: bytes, page_num: int = 0, dpi: int = 150) -> bytes:
        """
        Generate a preview image of a PDF page.
        
        Args:
            pdf_bytes: PDF as bytes
            page_num: Page number to preview
            dpi: Resolution for preview
            
        Returns:
            PNG image as bytes
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if page_num >= len(doc):
            page_num = 0
        
        page = doc[page_num]
        
        # Render page to image
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return img_bytes
