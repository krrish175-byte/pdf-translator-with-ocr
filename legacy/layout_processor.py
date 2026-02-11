"""
Layout processor using Docling for advanced document structure analysis.
Extracts text blocks and tables with coordinate conversion.
"""

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions, TableFormerMode
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LayoutProcessor:
    """Handles PDF layout analysis using Docling."""
    
    def __init__(self, do_ocr: bool = True, do_table_structure: bool = True):
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = do_ocr
        pipeline_options.do_table_structure = do_table_structure
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        logger.info(f"Docling LayoutProcessor initialized (OCR: {do_ocr})")
        
    def process(self, pdf_path: str):
        """Process PDF and return Docling document."""
        logger.info(f"Processing PDF with Docling: {pdf_path}")
        try:
            result = self.converter.convert(Path(pdf_path))
            return result.document
        except Exception as e:
            logger.error(f"Docling processing failed: {e}")
            raise e
            
    def iter_layout_items(self, doc, page_heights: dict):
        """
        Iterate through layout items (text and tables).
        
        Args:
            doc: Docling document
            page_heights: Dict mapping page_num (0-indexed) to height
            
        Yields:
            Dict with text, bbox (PyMuPDF format), page_num (0-indexed), type
        """
        # Process Text Items
        if hasattr(doc, 'texts'):
            for item in doc.texts:
                if not item.prov:
                    continue
                
                prov = item.prov[0]
                page_num = prov.page_no - 1  # Convert 1-indexed to 0-indexed
                bbox = prov.bbox
                
                # Get page height for coordinate conversion
                h = page_heights.get(page_num, 842.0) # Default A4 height if missing
                
                # Convert Docling (Bottom-Left origin) to PyMuPDF (Top-Left origin)
                # Docling bbox: (left, top, right, bottom) where y increases upwards
                # PyMuPDF rect: (x0, y0, x1, y1) where (x0,y0) is top-left
                
                x0 = bbox.l
                # Visual top (high Y in Docling) -> low Y in PyMuPDF
                y0 = h - bbox.t
                
                x1 = bbox.r
                # Visual bottom (low Y in Docling) -> high Y in PyMuPDF
                y1 = h - bbox.b
                
                # Ensure y0 < y1 for PyMuPDF
                if y0 > y1:
                    y0, y1 = y1, y0
                
                yield {
                    'text': item.text,
                    'bbox': (x0, y0, x1, y1),
                    'page': page_num,
                    'type': 'text'
                }

