// Undo Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Create undo toast if it doesn't exist
    if (!document.getElementById('undo-toast')) {
        const toastHTML = `
            <div id="undo-toast" class="undo-toast">
                <span class="undo-toast-message" id="undo-message">Action completed</span>
                <div class="undo-toast-actions">
                    <button class="undo-btn" id="undo-action-btn">Undo</button>
                    <button class="undo-dismiss" id="undo-dismiss-btn">Dismiss</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', toastHTML);
    }

    const undoToast = document.getElementById('undo-toast');
    const undoMessage = document.getElementById('undo-message');
    const undoActionBtn = document.getElementById('undo-action-btn');
    const undoDismissBtn = document.getElementById('undo-dismiss-btn');

    let undoTimeout = null;
    let currentUndoAction = null;

    // Show undo toast
    function showUndoToast(message, undoCallback) {
        undoMessage.textContent = message;
        currentUndoAction = undoCallback;
        undoToast.classList.add('is-visible');

        // Clear existing timeout
        if (undoTimeout) {
            clearTimeout(undoTimeout);
        }

        // Auto-dismiss after 5 seconds
        undoTimeout = setTimeout(() => {
            hideUndoToast();
        }, 5000);
    }

    function hideUndoToast() {
        undoToast.classList.remove('is-visible');
        currentUndoAction = null;
        if (undoTimeout) {
            clearTimeout(undoTimeout);
            undoTimeout = null;
        }
    }

    // Undo button click
    undoActionBtn.addEventListener('click', function() {
        if (currentUndoAction) {
            currentUndoAction();
        }
        hideUndoToast();
    });

    // Dismiss button click
    undoDismissBtn.addEventListener('click', function() {
        hideUndoToast();
    });

    // Make showUndoToast available globally for other scripts
    window.showUndoToast = showUndoToast;

    // Example: Intercept form submissions to enable undo
    const forms = document.querySelectorAll('form[action*="delete"], form[action*="forward"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const action = form.getAttribute('action');
            const isDelete = action.includes('delete');
            const isForward = action.includes('forward');

            if (isDelete || isForward) {
                // Store the action details for potential undo
                const formData = new FormData(form);
                const actionUrl = form.getAttribute('action');
                const actionType = isDelete ? 'delete' : 'forward';

                // Note: This is a simplified example. In a real implementation,
                // you would need to store the necessary data to perform the undo
                // and implement the actual undo logic on the server side.
            }
        });
    });
});
