import argparse
import sys
import logging
from pathlib import Path
from src.pdf_parser import PDFParser
from src.text_translator import TextTranslator
from src.image_processor import ImageProcessor
from src.pdf_builder import PDFBuilder
from src.utils.config import load_config
# from src.utils.progress import ProgressTracker # Skipping progress tracker for now to keep it simple

def main():
    parser = argparse.ArgumentParser(description="Multimodal PDF Translator EN→JA")
    parser.add_argument("input", help="Input PDF file path")
    parser.add_argument("output", help="Output PDF file path")
    parser.add_argument("--source", "-s", default="en", help="Source language code")
    parser.add_argument("--target", "-t", default="ja", help="Target language code")
    parser.add_argument("--mode", "-m", choices=["fast", "standard", "premium"], 
                       default="standard", help="Translation mode (affects OCR quality)")
    parser.add_argument("--config", "-c", default="config.yaml", help="Config file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Load configuration
    config = load_config(args.config)
    
    # Update config with CLI arguments
    config['translation']['source_lang'] = args.source
    config['translation']['target_lang'] = args.target
    
    if args.mode == "fast":
        config['ocr']['gpu'] = False
    elif args.mode == "premium":
        config['ocr']['gpu'] = True # Try to use GPU if available
        
    try:
        # Initialize components
        logging.info("Initializing components...")
        
        # Parse PDF
        logging.info(f"Parsing PDF: {args.input}")
        pdf_parser = PDFParser(config)
        document_data = pdf_parser.parse(args.input)
        
        # Translate text
        logging.info("Translating text blocks...")
        translator = TextTranslator(config)
        translated_text = translator.translate_all(document_data['text_blocks'])
        
        # Process images
        logging.info("Processing images with OCR...")
        image_processor = ImageProcessor(config)
        processed_images = image_processor.process_all(document_data['images'])
        
        # Build translated PDF
        logging.info("Building translated PDF...")
        pdf_builder = PDFBuilder(config)
        pdf_builder.build(
            original_pdf=args.input,
            translated_text=translated_text,
            processed_images=processed_images,
            output_path=args.output
        )
        
        logging.info(f"Translation complete! Output saved to: {args.output}")
        
    except Exception as e:
        logging.error(f"Translation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
