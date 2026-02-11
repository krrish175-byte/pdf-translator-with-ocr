from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from pathlib import Path
import json
import fitz

def test_docling():
    # Use a dummy PDF or create one
    pdf_path = "test.pdf"
    
    # Create dummy PDF if not exists
    if not Path(pdf_path).exists():
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Hello Docling!", fontsize=20)
        page.insert_text((50, 100), "This is a test paragraph.", fontsize=12)
        doc.save(pdf_path)
        doc.close()

    # Configure pipeline options
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    
    # Try to reproduce error
    try:
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print("Converter initialized successfully")
    except Exception as e:
        print(f"Converter initialization failed: {e}")
        # Try the correct way if known, or just fail
        return

    result = converter.convert(pdf_path)
    
    # Inspection
    print(f"Pages type: {type(result.document.pages)}")
    
    # Handle dict (page_no -> Page) or list
    pages = result.document.pages
    if isinstance(pages, dict):
        iterator = pages.values()
    else:
        iterator = pages
        
    for page in iterator:
        print(f"Page {page.page_no} Size: {page.size}")
        # text items are usually under 'texts' or 'items' depending on version
        # Let's inspect available attributes
        print(f"Attributes: {dir(page)}")

        
    
    # Inspect document root
    print(f"Document attributes: {dir(result.document)}")
    
    if hasattr(result.document, 'texts'):
        print(f"Document texts: {len(result.document.texts)}")
        for item in result.document.texts[:5]:
            print(f" - Text: {item.text[:20]}... Page: {item.prov[0].page_no} BBox: {item.prov[0].bbox}")
            
    if hasattr(result.document, 'tables'):
        print(f"Document tables: {len(result.document.tables)}")


if __name__ == "__main__":
    test_docling()
