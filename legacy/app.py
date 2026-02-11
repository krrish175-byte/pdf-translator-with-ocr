"""
Flask application for PDF translation with OCR.
"""

import os
import uuid
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pdf_processor import PDFProcessor
import threading

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('outputs')
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Task storage
tasks = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload a PDF file for translation."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    # Save uploaded file
    file_path = UPLOAD_FOLDER / f"{task_id}_{filename}"
    file.save(file_path)
    
    # Get options
    translate_text = request.form.get('translate_text', 'true').lower() == 'true'
    translate_images = request.form.get('translate_images', 'true').lower() == 'true'
    source_lang = request.form.get('source_lang', 'en')
    target_lang = request.form.get('target_lang', 'ja')
    print(f"UPLOAD: source={source_lang}, target={target_lang}")
    
    # Store task info
    tasks[task_id] = {
        'status': 'uploaded',
        'progress': 0,
        'message': 'File uploaded',
        'filename': filename,
        'file_path': str(file_path),
        'translate_text': translate_text,
        'translate_images': translate_images,
        'source_lang': source_lang,
        'target_lang': target_lang,
        'output_path': None,
        'error': None
    }
    
    return jsonify({
        'task_id': task_id,
        'filename': filename,
        'message': 'File uploaded successfully'
    })


@app.route('/api/translate/<task_id>', methods=['GET'])
def translate(task_id):
    """Start translation and stream progress via SSE."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    if task['status'] not in ['uploaded', 'error']:
        return jsonify({'error': 'Translation already in progress or completed'}), 400
    
    def generate():
        try:
            task['status'] = 'processing'
            
            # Read input file
            with open(task['file_path'], 'rb') as f:
                pdf_bytes = f.read()
            
            def progress_callback(current, total, message):
                progress = int((current / total) * 100) if total > 0 else 0
                task['progress'] = progress
                task['message'] = message
            
            # Process PDF
            processor = PDFProcessor(
                source_lang=task.get('source_lang', 'en'),
                target_lang=task.get('target_lang', 'ja'),
                translate_text=task['translate_text'],
                translate_images=task['translate_images']
            )
            
            # Send initial progress
            yield f"data: {json.dumps({'progress': 0, 'message': 'Starting translation...'})}\n\n"
            
            # Create a wrapper that yields progress
            result_holder = {'result': None, 'error': None}
            
            def process():
                try:
                    result_holder['result'] = processor.process_pdf(task['file_path'], progress_callback)
                except Exception as e:
                    result_holder['error'] = str(e)
            
            # Run processing in thread
            thread = threading.Thread(target=process)
            thread.start()
            
            # Stream progress updates
            last_progress = -1
            while thread.is_alive():
                if task['progress'] != last_progress:
                    last_progress = task['progress']
                    yield f"data: {json.dumps({'progress': task['progress'], 'message': task['message']})}\n\n"
                thread.join(timeout=0.5)
            
            if result_holder['error']:
                task['status'] = 'error'
                task['error'] = result_holder['error']
                yield f"data: {json.dumps({'error': result_holder['error']})}\n\n"
                return
            
            # Save output
            output_filename = f"translated_{task['filename']}"
            output_path = OUTPUT_FOLDER / f"{task_id}_{output_filename}"
            
            with open(output_path, 'wb') as f:
                f.write(result_holder['result'])
            
            task['output_path'] = str(output_path)
            task['status'] = 'completed'
            task['progress'] = 100
            task['message'] = 'Translation complete!'
            
            yield f"data: {json.dumps({'progress': 100, 'message': 'Translation complete!', 'completed': True})}\n\n"
            
        except Exception as e:
            task['status'] = 'error'
            task['error'] = str(e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Get the current status of a translation task."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    return jsonify({
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message'],
        'error': task['error']
    })


@app.route('/api/preview/<task_id>', methods=['GET'])
def preview(task_id):
    """Get a preview image of the translated PDF."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    if task['status'] != 'completed' or not task['output_path']:
        return jsonify({'error': 'Translation not complete'}), 400
    
    page = request.args.get('page', 0, type=int)
    
    try:
        with open(task['output_path'], 'rb') as f:
            pdf_bytes = f.read()
        
        processor = PDFProcessor()
        preview_bytes = processor.generate_preview(pdf_bytes, page)
        
        return Response(preview_bytes, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<task_id>', methods=['GET'])
def download(task_id):
    """Download the translated PDF."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    if task['status'] != 'completed' or not task['output_path']:
        return jsonify({'error': 'Translation not complete'}), 400
    
    # Ensure filename ends with .pdf
    original_filename = task['filename']
    if not original_filename.lower().endswith('.pdf'):
        original_filename += '.pdf'
    
    download_filename = f"translated_{original_filename}"
    
    # Read file and return with proper headers
    with open(task['output_path'], 'rb') as f:
        pdf_data = f.read()
    
    response = Response(
        pdf_data,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{download_filename}"',
            'Content-Type': 'application/pdf',
            'Content-Length': str(len(pdf_data))
        }
    )
    return response


@app.route('/api/page-count/<task_id>', methods=['GET'])
def page_count(task_id):
    """Get the page count of the translated PDF."""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = tasks[task_id]
    
    if task['status'] != 'completed' or not task['output_path']:
        return jsonify({'error': 'Translation not complete'}), 400
    
    try:
        import fitz
        with open(task['output_path'], 'rb') as f:
            doc = fitz.open(stream=f.read(), filetype="pdf")
            count = len(doc)
            doc.close()
        
        return jsonify({'page_count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
