// File Preview Modal
document.addEventListener('DOMContentLoaded', function() {
    // Create preview modal if it doesn't exist
    if (!document.getElementById('file-preview-modal')) {
        const modalHTML = `
            <div id="file-preview-modal" class="file-preview-modal">
                <div class="file-preview-content">
                    <div class="file-preview-header">
                        <span class="file-preview-title" id="preview-title">File Preview</span>
                        <button class="file-preview-close" id="preview-close">Close</button>
                    </div>
                    <div class="file-preview-body" id="preview-body">
                        <div class="file-preview-loading">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"></circle>
                                <path d="M12 6v6l4 2"></path>
                            </svg>
                            <span>Loading preview...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    const modal = document.getElementById('file-preview-modal');
    const modalTitle = document.getElementById('preview-title');
    const modalBody = document.getElementById('preview-body');
    const closeBtn = document.getElementById('preview-close');

    // Close modal
    closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModal();
    });

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('is-active')) {
            closeModal();
        }
    });

    function closeModal() {
        modal.classList.remove('is-active');
        modalBody.innerHTML = `
            <div class="file-preview-loading">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2"></path>
                </svg>
                <span>Loading preview...</span>
            </div>
        `;
    }

    // Add preview functionality to file links
    const fileLinks = document.querySelectorAll('.file-link');
    fileLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const url = this.getAttribute('href');
            
            // Only intercept PDF files for preview
            if (url && url.toLowerCase().endsWith('.pdf')) {
                e.preventDefault();
                openPreview(url, this.textContent);
            }
        });
    });

    function openPreview(url, title) {
        modalTitle.textContent = title || 'File Preview';
        modal.classList.add('is-active');

        const iframe = document.createElement('iframe');
        iframe.className = 'file-preview-iframe';
        iframe.src = url;
        
        iframe.onload = function() {
            modalBody.innerHTML = '';
            modalBody.appendChild(iframe);
        };

        iframe.onerror = function() {
            modalBody.innerHTML = `
                <div class="file-preview-error">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <span>Unable to preview file. Please download to view.</span>
                    <a href="${url}" target="_blank" class="action-btn" style="margin-top: 16px;">Download File</a>
                </div>
            `;
        };

        // Fallback after timeout
        setTimeout(() => {
            if (modalBody.querySelector('.file-preview-loading')) {
                modalBody.innerHTML = `
                    <div class="file-preview-error">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <span>Preview taking too long. Please download to view.</span>
                        <a href="${url}" target="_blank" class="action-btn" style="margin-top: 16px;">Download File</a>
                    </div>
                `;
            }
        }, 5000);
    }
});
