/**
 * PDF Translator - Frontend Application Logic
 */

class PDFTranslator {
    constructor() {
        // State
        this.selectedFile = null;
        this.taskId = null;
        this.currentPage = 0;
        this.totalPages = 1;

        // DOM Elements
        this.uploadSection = document.getElementById('upload-section');
        this.progressSection = document.getElementById('progress-section');
        this.resultSection = document.getElementById('result-section');
        this.errorSection = document.getElementById('error-section');

        this.uploadZone = document.getElementById('upload-zone');
        this.fileInput = document.getElementById('file-input');
        this.fileInfo = document.getElementById('file-info');
        this.fileName = document.getElementById('file-name');
        this.fileSize = document.getElementById('file-size');
        this.btnRemove = document.getElementById('btn-remove');
        this.btnTranslate = document.getElementById('btn-translate');

        this.optText = document.getElementById('opt-text');
        this.optImages = document.getElementById('opt-images');

        this.progressBar = document.getElementById('progress-bar');
        this.progressPercent = document.getElementById('progress-percent');
        this.progressMessage = document.getElementById('progress-message');

        this.previewImage = document.getElementById('preview-image');
        this.previewLoading = document.getElementById('preview-loading');
        this.currentPageSpan = document.getElementById('current-page');
        this.totalPagesSpan = document.getElementById('total-pages');
        this.btnPrev = document.getElementById('btn-prev');
        this.btnNext = document.getElementById('btn-next');
        this.btnDownload = document.getElementById('btn-download');
        this.btnNew = document.getElementById('btn-new');

        this.errorMessage = document.getElementById('error-message');
        this.btnRetry = document.getElementById('btn-retry');

        this.init();
    }

    init() {
        // File input handlers
        this.uploadZone.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Drag and drop
        this.uploadZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadZone.addEventListener('drop', (e) => this.handleDrop(e));

        // Buttons
        this.btnRemove.addEventListener('click', () => this.removeFile());
        this.btnTranslate.addEventListener('click', () => this.startTranslation());
        this.btnDownload.addEventListener('click', () => this.downloadPDF());
        this.btnNew.addEventListener('click', () => this.reset());
        this.btnRetry.addEventListener('click', () => this.reset());

        // Preview navigation
        this.btnPrev.addEventListener('click', () => this.navigatePage(-1));
        this.btnNext.addEventListener('click', () => this.navigatePage(1));
    }

    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.uploadZone.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.uploadZone.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.uploadZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.selectFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.selectFile(files[0]);
        }
    }

    selectFile(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            this.showError('Please select a PDF file');
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            this.showError('File size must be less than 50MB');
            return;
        }

        this.selectedFile = file;

        // Update UI
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        this.uploadZone.classList.add('hidden');
        this.fileInfo.classList.remove('hidden');
        this.btnTranslate.disabled = false;
    }

    removeFile() {
        this.selectedFile = null;
        this.fileInput.value = '';
        this.uploadZone.classList.remove('hidden');
        this.fileInfo.classList.add('hidden');
        this.btnTranslate.disabled = true;
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    async startTranslation() {
        if (!this.selectedFile) return;

        // Show progress section
        this.showSection('progress');
        this.updateProgress(0, 'Uploading file...');

        try {
            // Upload file
            const formData = new FormData();
            formData.append('file', this.selectedFile);
            formData.append('translate_text', this.optText.checked);
            formData.append('translate_images', this.optImages.checked);

            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                const error = await uploadResponse.json();
                throw new Error(error.error || 'Upload failed');
            }

            const uploadData = await uploadResponse.json();
            this.taskId = uploadData.task_id;

            // Start translation with SSE
            await this.streamTranslation();

        } catch (error) {
            this.showError(error.message);
        }
    }

    async streamTranslation() {
        return new Promise((resolve, reject) => {
            const eventSource = new EventSource(`/api/translate/${this.taskId}`);

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.error) {
                        eventSource.close();
                        reject(new Error(data.error));
                        return;
                    }

                    this.updateProgress(data.progress, data.message);

                    if (data.completed) {
                        eventSource.close();
                        this.onTranslationComplete();
                        resolve();
                    }
                } catch (e) {
                    console.error('Parse error:', e);
                }
            };

            eventSource.onerror = (error) => {
                eventSource.close();
                reject(new Error('Connection lost. Please try again.'));
            };
        });
    }

    updateProgress(percent, message) {
        this.progressBar.style.width = `${percent}%`;
        this.progressPercent.textContent = `${percent}%`;
        this.progressMessage.textContent = message;
    }

    async onTranslationComplete() {
        // Get page count
        try {
            const response = await fetch(`/api/page-count/${this.taskId}`);
            if (response.ok) {
                const data = await response.json();
                this.totalPages = data.page_count;
            }
        } catch (e) {
            console.error('Failed to get page count:', e);
        }

        this.currentPage = 0;
        this.showSection('result');
        this.updatePageInfo();
        this.loadPreview();
    }

    async loadPreview() {
        this.previewLoading.classList.remove('hidden');

        try {
            const response = await fetch(`/api/preview/${this.taskId}?page=${this.currentPage}`);
            if (response.ok) {
                const blob = await response.blob();
                this.previewImage.src = URL.createObjectURL(blob);
            }
        } catch (e) {
            console.error('Preview load failed:', e);
        }

        this.previewImage.onload = () => {
            this.previewLoading.classList.add('hidden');
        };
    }

    navigatePage(direction) {
        const newPage = this.currentPage + direction;
        if (newPage >= 0 && newPage < this.totalPages) {
            this.currentPage = newPage;
            this.updatePageInfo();
            this.loadPreview();
        }
    }

    updatePageInfo() {
        this.currentPageSpan.textContent = this.currentPage + 1;
        this.totalPagesSpan.textContent = this.totalPages;
        this.btnPrev.disabled = this.currentPage === 0;
        this.btnNext.disabled = this.currentPage >= this.totalPages - 1;
    }

    downloadPDF() {
        if (!this.taskId) return;
        window.location.href = `/api/download/${this.taskId}`;
    }

    showSection(section) {
        this.uploadSection.classList.add('hidden');
        this.progressSection.classList.add('hidden');
        this.resultSection.classList.add('hidden');
        this.errorSection.classList.add('hidden');

        switch (section) {
            case 'upload':
                this.uploadSection.classList.remove('hidden');
                break;
            case 'progress':
                this.progressSection.classList.remove('hidden');
                break;
            case 'result':
                this.resultSection.classList.remove('hidden');
                break;
            case 'error':
                this.errorSection.classList.remove('hidden');
                break;
        }
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.showSection('error');
    }

    reset() {
        this.selectedFile = null;
        this.taskId = null;
        this.currentPage = 0;
        this.totalPages = 1;

        this.fileInput.value = '';
        this.uploadZone.classList.remove('hidden');
        this.fileInfo.classList.add('hidden');
        this.btnTranslate.disabled = true;
        this.progressBar.style.width = '0%';

        this.showSection('upload');
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PDFTranslator();
});
