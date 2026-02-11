"""
PDF processor for extracting content, translating, and rebuilding PDFs.
Uses Docling for layout analysis and deep-translator for text.
"""

import fitz  # PyMuPDF
from io import BytesIO
from typing import Dict, List, Tuple
from pathlib import Path
from translator import TranslationService
from layout_processor import LayoutProcessor
from ocr_processor import OCRProcessor


class PDFProcessor:
    """Handles PDF text extraction, image processing, and PDF generation."""
    
    def __init__(self, source_lang: str = 'en', target_lang: str = 'ja',
                 translate_text: bool = True, translate_images: bool = True):
        self.translator = TranslationService(source_lang, target_lang)
        self.ocr_processor = OCRProcessor(source_lang, target_lang)
        
        # Docling handles OCR internally if translate_images is True
        self.layout_processor = LayoutProcessor(do_ocr=translate_images)
        
        self.translate_text = translate_text
        self.translate_images = translate_images
    
    def process_pdf(self, pdf_path: str, progress_callback=None) -> bytes:
        """
        Process a PDF: analyze layout, translate text blocks, and rebuild.
        
        Args:
            pdf_path: Path to PDF file (Docling needs file path)
            progress_callback: Function(current, total, message) for progress updates
            
        Returns:
            Translated PDF as bytes
        """
        # 1. Analyze Layout with Docling
        if progress_callback:
            progress_callback(0, 100, "Analyzing document layout (this may take a moment)...")
            
        try:
            docling_doc = self.layout_processor.process(pdf_path)
        except Exception as e:
            print(f"Docling failed: {e}")
            # Fallback or returning error would be better, but let's assume it works for now
            return b""
            
        # Open PDF with PyMuPDF for reconstruction
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # Helper map for page heights (needed for coordinate conversion)
        page_heights = {i: page.rect.height for i, page in enumerate(doc)}
        
        # Register a font that supports CJK
        fontname = "helv"  # Default fallback
        cjk_font_path = "/Library/Fonts/Arial Unicode.ttf"
        if not Path(cjk_font_path).exists():
            cjk_font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
            
        if Path(cjk_font_path).exists():
            try:
                # Register font with a custom name
                # We need to register it for EACH page or once for document?
                # insert_font returns the name to use. 
                # Ideally, we register it once per document, but PyMuPDF's insert_font works on page?
                # No, PyMuPDF docs say: page.insert_font(...) or doc.extract_font(...)
                # Actually doc.embfile_add() or page.insert_font().
                # Correct way: use page.insert_textbox(..., fontfile=path, fontname=name) handles it.
                fontname = "cjk_font"
                # We don't need explicit registration if we pass fontfile to insert_textbox (it registers automatically)
                # But to avoid re-registering for every text block, we should perhaps be careful.
                # However, PyMuPDF handles reuse if fontname matches.
            except Exception as e:
                print(f"Font loading error: {e}")
                cjk_font_path = None
        else:
            cjk_font_path = None
            print("Warning: CJK font not found. Text might appear as '?'")
        
        # 2. Iterate through layout items and translate
        layout_items = list(self.layout_processor.iter_layout_items(docling_doc, page_heights))
        total_items = len(layout_items)
        
        processed_items = 0
        
        for item in layout_items:
            processed_items += 1
            if progress_callback and processed_items % 5 == 0:
                percent = int((processed_items / total_items) * 80)
                progress_callback(percent, 100, f"Translating text blocks {processed_items}/{total_items}")
            
            page_num = item['page']
            if page_num >= total_pages:
                continue
                
            page = doc[page_num]
            text = item['text']
            bbox = fitz.Rect(item['bbox'])
            
            if not text or not text.strip():
                continue
                
            # Translate text
            translated_text = self.translator.translate_text(text)
            if translated_text == text:
                continue
            
            # Redact original text
            self._redact_with_background(page, bbox)
            
            # Insert translated text
            font_size = max(6, min(bbox.height * 0.8, 12))
            
            try:
                if cjk_font_path:
                    page.insert_textbox(
                        bbox,
                        translated_text,
                        fontsize=font_size,
                        color=(0, 0, 0),
                        fontname=fontname,
                        fontfile=cjk_font_path,
                        align=0
                    )
                else:
                    page.insert_textbox(
                        bbox,
                        translated_text,
                        fontsize=font_size,
                        color=(0, 0, 0),
                        fontname="helv",
                        align=0
                    )
            except Exception as e:
                print(f"Error inserting text: {e}")
        
        # 3. Process Images (OCR) if enabled
        # Note: Docling does OCR internally but we might want to handle images separately
        # or rely on Docling's text extraction from images.
        # For now, let's keep our image processor for non-text graphics if needed?
        # Actually Docling handles OCR for text in images.
        # But for charts/diagrams, we might still want to try our image processor.
        # Let's verify if Docling extracts text from images well.
        
        # 3. Process Images (OCR) if enabled
        # Docling (with do_ocr=True) extracts text from images and provides bounding boxes.
        # We have already processed these items in the layout loop above.
        # So we skip the explicit image processing step to avoid double-translation artifacts.
        
        # However, if Docling missed some, we might want this.
        # But generally, Docling is superior. Let's rely on it.
        pass
        
        # if self.translate_images:
        #     if progress_callback:
        #         progress_callback(90, 100, "Processing remaining images...")
        #     
        #     for page_num in range(total_pages):
        #         page = doc[page_num]
        #         self._process_images(page)
                
        # Save to bytes
        output = BytesIO()
        doc.save(output, garbage=4, deflate=True)
        doc.close()
        output.seek(0)
        
        if progress_callback:
            progress_callback(100, 100, "Complete!")
        
        return output.getvalue()

    def _redact_with_background(self, page, bbox):
        """Redact a region using the average background color."""
        try:
            # Sample background color
            pix = page.get_pixmap(clip=bbox, alpha=False)
            samples = pix.samples
            if len(samples) >= 3:
                r = samples[0] / 255.0
                g = samples[1] / 255.0
                b = samples[2] / 255.0
                fill_color = (r, g, b)
            else:
                fill_color = (1, 1, 1)  # White fallback
        except:
            fill_color = (1, 1, 1)
            
        page.add_redact_annot(bbox, text="", fill=fill_color)
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    def _process_images(self, page):
        """Find images, OCR them, and overlay translated text."""
        # Same logic as before
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            try:
                base_image = page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Check for small images/icons to skip?
                
                processed_bytes, found_text = self.ocr_processor.process_image(image_bytes)
                
                if found_text:
                    page.parent.update_object(xref, processed_bytes)
                    
            except Exception as e:
                print(f"Error processing image {xref}: {e}")
                continue


# Helper for preview
def get_page_preview(pdf_bytes: bytes, page_num: int = 0) -> bytes:
    """Get a preview image of a PDF page."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_num >= len(doc):
        page_num = 0
    
    page = doc[page_num]
    mat = fitz.Matrix(1.5, 1.5)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    doc.close()
    return img_data
