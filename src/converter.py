import io
import fitz  # PyMuPDF
from services.pdf_service import convert_pdf_to_images, convert_html_to_pdf
from services.gemini_service import GeminiService

class PDFTranslator:
    def __init__(self, api_key):
        self.gemini_service = GeminiService(api_key)

    def translate_pdf(self, pdf_bytes, source_lang="English", target_lang="Japanese", progress_callback=None):
        """
        Orchestrates the PDF translation process using OpenAI.
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
                
            # 2. Translate image to HTML using Gemini
            try:
                width, height = image.size
                html_content = self.gemini_service.translate_page(image, width, height, source_lang, target_lang)
                
                # Debug: Save HTML
                with open(f"debug_page_{i+1}.html", "w") as f:
                    f.write(html_content)
                
                # 3. Convert HTML to PDF page (in memory)
                pdf_page_bytes = convert_html_to_pdf(html_content)
                
                # 4. Merge into output PDF
                page_doc = fitz.open(stream=pdf_page_bytes, filetype="pdf")
                output_pdf.insert_pdf(page_doc)
                
            except Exception as e:
                import traceback
                print(f"Error processing page {i+1}: {e}")
                # formatting for Tenacity RetryError to show cause
                if hasattr(e, 'last_attempt') and e.last_attempt.exception():
                    print(f"Original error: {e.last_attempt.exception()}")
                pass
            
        if progress_callback: progress_callback("Finalizing PDF...", 0.95)
        
        if output_pdf.page_count == 0:
            output_pdf.close()
            raise Exception("No pages were successfully translated. Check API Key or logs.")

        output_bytes = output_pdf.tobytes()
        output_pdf.close()
        
        return output_bytes
