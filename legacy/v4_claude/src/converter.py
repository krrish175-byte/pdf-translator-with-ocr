import io
import fitz  # PyMuPDF
from services.pdf_service import convert_pdf_to_images, convert_html_to_pdf
from services.claude_service import ClaudeService

class PDFTranslator:
    def __init__(self, api_key):
        self.claude_service = ClaudeService(api_key)

    def translate_pdf(self, pdf_bytes, source_lang="English", target_lang="Japanese", progress_callback=None):
        """
        Orchestrates the PDF translation process.
        """
        # 1. Convert PDF to images
        if progress_callback: progress_callback("Converting PDF to images...", 0.1)
        images = convert_pdf_to_images(pdf_bytes)
        
        output_pdf = fitz.open()
        
        total_pages = len(images)
        for i, image in enumerate(images):
            if progress_callback: 
                progress = 0.1 + (0.8 * (i / total_pages))
                progress_callback(f"Translating page {i+1}/{total_pages}...", progress)
                
            # 2. Translate image to HTML using Claude
            # Note: This can be slow. In production, we'd parallelize this.
            html_content = self.claude_service.translate_page(image, source_lang, target_lang)
            
            # 3. Convert HTML to PDF page (in memory)
            pdf_page_bytes = convert_html_to_pdf(html_content)
            
            # 4. Merge into output PDF
            page_doc = fitz.open(stream=pdf_page_bytes, filetype="pdf")
            output_pdf.insert_pdf(page_doc)
            
        if progress_callback: progress_callback("Finalizing PDF...", 0.95)
        
        output_bytes = output_pdf.tobytes()
        output_pdf.close()
        
        return output_bytes
