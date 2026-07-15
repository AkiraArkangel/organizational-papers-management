// Error Handling
document.addEventListener('DOMContentLoaded', function() {
    // Global error handler
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        handleGlobalError(e.error);
    });

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
        handleGlobalError(e.reason);
    });

    function handleGlobalError(error) {
        // Show user-friendly error message
        showErrorMessage('An unexpected error occurred. Please try again or contact support if the problem persists.');
        
        // Log detailed error for debugging
        if (error) {
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                timestamp: new Date().toISOString()
            });
        }
    }

    function showErrorMessage(message, duration = 5000) {
        // Create error toast if it doesn't exist
        let errorToast = document.getElementById('error-toast');
        if (!errorToast) {
            errorToast = document.createElement('div');
            errorToast.id = 'error-toast';
            errorToast.className = 'error-toast';
            document.body.appendChild(errorToast);
        }

        errorToast.textContent = message;
        errorToast.classList.add('is-visible');

        // Auto-hide after duration
        setTimeout(() => {
            errorToast.classList.remove('is-visible');
        }, duration);
    }

    // Form validation and error handling
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                    
                    // Add error message if not exists
                    let errorMsg = field.nextElementSibling;
                    if (!errorMsg || !errorMsg.classList.contains('field-error')) {
                        errorMsg = document.createElement('span');
                        errorMsg.className = 'field-error';
                        errorMsg.textContent = 'This field is required';
                        field.parentNode.insertBefore(errorMsg, field.nextSibling);
                    }
                } else {
                    field.classList.remove('error');
                    const errorMsg = field.nextElementSibling;
                    if (errorMsg && errorMsg.classList.contains('field-error')) {
                        errorMsg.remove();
                    }
                }
            });

            if (!isValid) {
                e.preventDefault();
                showErrorMessage('Please fill in all required fields.');
            }
        });

        // Remove error styling on input
        form.addEventListener('input', function(e) {
            if (e.target.classList.contains('error')) {
                e.target.classList.remove('error');
                const errorMsg = e.target.nextElementSibling;
                if (errorMsg && errorMsg.classList.contains('field-error')) {
                    errorMsg.remove();
                }
            }
        });
    });

    // AJAX error handling for fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.message || `HTTP error! status: ${response.status}`);
                    });
                }
                return response;
            })
            .catch(error => {
                console.error('Fetch error:', error);
                showErrorMessage(error.message || 'Network error. Please check your connection.');
                throw error;
            });
    };

    // Add CSS for error styling
    const style = document.createElement('style');
    style.textContent = `
        .error-toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(239, 68, 68, 0.9);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 3000;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            max-width: 400px;
            font-size: 13px;
        }

        .error-toast.is-visible {
            opacity: 1;
            transform: translateX(0);
        }

        .field-error {
            color: #ef4444;
            font-size: 11px;
            margin-top: 4px;
            display: block;
        }

        input.error,
        textarea.error,
        select.error {
            border-color: #ef4444 !important;
            background: rgba(239, 68, 68, 0.05) !important;
        }
    `;
    document.head.appendChild(style);

    // Make showErrorMessage available globally
    window.showErrorMessage = showErrorMessage;
});
