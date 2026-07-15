// Auto-Save Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Auto-save configuration
    const AUTO_SAVE_INTERVAL = 30000; // 30 seconds
    const STORAGE_PREFIX = 'autosave_';
    
    // Get all forms that should have auto-save
    const forms = document.querySelectorAll('form[data-autosave="true"]');
    
    forms.forEach(form => {
        const formId = form.id || `form_${Date.now()}`;
        const storageKey = `${STORAGE_PREFIX}${formId}`;
        
        // Restore saved data
        restoreFormData(form, storageKey);
        
        // Auto-save on input changes
        let saveTimeout;
        form.addEventListener('input', function(e) {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                saveFormData(form, storageKey);
            }, 1000); // Save 1 second after last input
        });
        
        // Save on form submit
        form.addEventListener('submit', function() {
            clearSavedData(storageKey);
        });
        
        // Show auto-save indicator
        addAutoSaveIndicator(form, storageKey);
    });
    
    // Periodic auto-save for all forms
    setInterval(() => {
        forms.forEach(form => {
            const formId = form.id || `form_${Date.now()}`;
            const storageKey = `${STORAGE_PREFIX}${formId}`;
            saveFormData(form, storageKey);
        });
    }, AUTO_SAVE_INTERVAL);
    
    function saveFormData(form, storageKey) {
        const formData = {};
        
        // Collect form data
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            if (input.type === 'checkbox' || input.type === 'radio') {
                formData[input.name] = input.checked;
            } else if (input.type !== 'file') {
                formData[input.name] = input.value;
            }
        });
        
        // Save to localStorage
        try {
            localStorage.setItem(storageKey, JSON.stringify({
                data: formData,
                timestamp: new Date().toISOString()
            }));
            
            // Update indicator
            updateAutoSaveIndicator(form, true);
        } catch (e) {
            console.error('Failed to auto-save:', e);
        }
    }
    
    function restoreFormData(form, storageKey) {
        try {
            const saved = localStorage.getItem(storageKey);
            if (!saved) return;
            
            const parsed = JSON.parse(saved);
            const formData = parsed.data;
            const timestamp = new Date(parsed.timestamp);
            
            // Check if data is recent (within 24 hours)
            const hoursSinceSave = (Date.now() - timestamp.getTime()) / (1000 * 60 * 60);
            if (hoursSinceSave > 24) {
                clearSavedData(storageKey);
                return;
            }
            
            // Restore form data
            Object.keys(formData).forEach(name => {
                const input = form.querySelector(`[name="${name}"]`);
                if (input) {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        input.checked = formData[name];
                    } else {
                        input.value = formData[name];
                    }
                }
            });
            
            // Show restore notification
            showRestoreNotification(form, timestamp);
            
        } catch (e) {
            console.error('Failed to restore form data:', e);
        }
    }
    
    function clearSavedData(storageKey) {
        try {
            localStorage.removeItem(storageKey);
        } catch (e) {
            console.error('Failed to clear saved data:', e);
        }
    }
    
    function addAutoSaveIndicator(form, storageKey) {
        let indicator = form.querySelector('.autosave-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'autosave-indicator';
            form.insertBefore(indicator, form.firstChild);
        }
        
        indicator.innerHTML = `
            <span class="autosave-status">Auto-save enabled</span>
            <button class="autosave-clear" data-storage-key="${storageKey}">Clear saved data</button>
        `;
        
        // Clear button functionality
        indicator.querySelector('.autosave-clear').addEventListener('click', function(e) {
            e.preventDefault();
            const key = this.getAttribute('data-storage-key');
            clearSavedData(key);
            updateAutoSaveIndicator(form, false);
        });
    }
    
    function updateAutoSaveIndicator(form, justSaved) {
        const indicator = form.querySelector('.autosave-indicator');
        if (!indicator) return;
        
        const status = indicator.querySelector('.autosave-status');
        if (justSaved) {
            status.textContent = 'Saved just now';
            setTimeout(() => {
                status.textContent = 'Auto-save enabled';
            }, 2000);
        }
    }
    
    function showRestoreNotification(form, timestamp) {
        const notification = document.createElement('div');
        notification.className = 'autosave-notification';
        notification.innerHTML = `
            <p>Form data restored from ${timestamp.toLocaleString()}</p>
            <button class="autosave-dismiss">Dismiss</button>
        `;
        
        form.insertBefore(notification, form.firstChild);
        
        // Dismiss button
        notification.querySelector('.autosave-dismiss').addEventListener('click', function() {
            notification.remove();
        });
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
    
    // Add CSS for auto-save UI
    const style = document.createElement('style');
    style.textContent = `
        .autosave-indicator {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: rgba(76, 175, 80, 0.1);
            border: 1px solid rgba(76, 175, 80, 0.3);
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 12px;
        }
        
        .autosave-status {
            color: #4caf50;
            font-weight: 500;
        }
        
        .autosave-clear {
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
            background: transparent;
            border: 1px solid var(--line);
            border-radius: 4px;
            color: var(--muted);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .autosave-clear:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text);
        }
        
        .autosave-notification {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 13px;
        }
        
        .autosave-notification p {
            margin: 0;
            color: #3b82f6;
        }
        
        .autosave-dismiss {
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
            background: transparent;
            border: 1px solid var(--line);
            border-radius: 4px;
            color: var(--muted);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .autosave-dismiss:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text);
        }
    `;
    document.head.appendChild(style);
});
