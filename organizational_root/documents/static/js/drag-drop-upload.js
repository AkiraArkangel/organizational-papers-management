// Drag and Drop Upload
document.addEventListener('DOMContentLoaded', function() {
    const dragDropZone = document.getElementById('drag-drop-zone');
    const fileInput = document.getElementById('file-input');

    if (!dragDropZone || !fileInput) return;

    // Click to browse
    dragDropZone.addEventListener('click', function(e) {
        if (e.target.closest('.drag-drop-zone-remove') || e.target.closest('.drag-drop-zone-file-info')) {
            return;
        }
        const currentFileInput = document.getElementById('file-input');
        if (currentFileInput) {
            currentFileInput.click();
        }
    });

    // Handle file selection
    fileInput.addEventListener('change', function(e) {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    // Drag events
    dragDropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        dragDropZone.classList.add('drag-over');
    });

    dragDropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        dragDropZone.classList.remove('drag-over');
    });

    dragDropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        dragDropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const currentFileInput = document.getElementById('file-input');
            if (currentFileInput) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                currentFileInput.files = dataTransfer.files;
                handleFileSelect(files[0]);
            }
        }
    });

    function handleFileSelect(file) {
        if (!file) return;

        const validTypes = ['.pdf', '.doc', '.docx'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!validTypes.includes(fileExtension)) {
            alert('Please upload a PDF, DOC, or DOCX file.');
            const currentFileInput = document.getElementById('file-input');
            if (currentFileInput) {
                currentFileInput.value = '';
            }
            return;
        }

        dragDropZone.classList.add('has-file');
        
        const icon = dragDropZone.querySelector('.drag-drop-zone-icon');
        const text = dragDropZone.querySelector('.drag-drop-zone-text');
        const subtext = dragDropZone.querySelector('.drag-drop-zone-subtext');
        
        if (icon) icon.style.display = 'none';
        if (text) text.style.display = 'none';
        if (subtext) subtext.style.display = 'none';
        
        const existingFileInfo = dragDropZone.querySelector('.drag-drop-zone-file-info');
        if (existingFileInfo) {
            existingFileInfo.remove();
        }
        
        const fileInfoDiv = document.createElement('div');
        fileInfoDiv.className = 'drag-drop-zone-file-info';
        fileInfoDiv.innerHTML = `
            <svg class="drag-drop-zone-file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <div class="drag-drop-zone-file-name">${file.name}</div>
            <div class="drag-drop-zone-file-size">${formatFileSize(file.size)}</div>
            <button type="button" class="drag-drop-zone-remove" id="remove-file">Remove</button>
        `;
        
        dragDropZone.appendChild(fileInfoDiv);

        const removeButton = document.getElementById('remove-file');
        if (removeButton) {
            removeButton.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                resetDragDropZone();
            });
        }
    }

    function resetDragDropZone() {
        dragDropZone.classList.remove('has-file');
        
        const icon = dragDropZone.querySelector('.drag-drop-zone-icon');
        const text = dragDropZone.querySelector('.drag-drop-zone-text');
        const subtext = dragDropZone.querySelector('.drag-drop-zone-subtext');
        
        if (icon) icon.style.display = '';
        if (text) text.style.display = '';
        if (subtext) subtext.style.display = '';
        
        const existingFileInfo = dragDropZone.querySelector('.drag-drop-zone-file-info');
        if (existingFileInfo) {
            existingFileInfo.remove();
        }
        
        const currentFileInput = document.getElementById('file-input');
        if (currentFileInput) {
            currentFileInput.value = '';
        }
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
});
