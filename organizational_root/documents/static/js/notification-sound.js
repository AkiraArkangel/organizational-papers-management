// Notification Sound
document.addEventListener('DOMContentLoaded', function() {
    // Check if notification sound is enabled
    const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
    
    // Create audio context for notification sound
    let audioContext = null;
    
    function playNotificationSound() {
        if (!soundEnabled) return;
        
        try {
            // Create audio context if not exists
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)();
            }
            
            // Create oscillator for notification sound
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Set sound properties
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
            
        } catch (e) {
            console.error('Failed to play notification sound:', e);
        }
    }
    
    // Toggle notification sound
    function toggleNotificationSound() {
        const currentSetting = localStorage.getItem('notificationSoundEnabled') !== 'false';
        const newSetting = !currentSetting;
        localStorage.setItem('notificationSoundEnabled', newSetting);
        
        // Update UI if toggle button exists
        const toggleBtn = document.getElementById('notification-sound-toggle');
        if (toggleBtn) {
            toggleBtn.textContent = newSetting ? 'Sound On' : 'Sound Off';
            toggleBtn.classList.toggle('active', newSetting);
        }
        
        // Play sound if enabling
        if (newSetting) {
            playNotificationSound();
        }
        
        return newSetting;
    }
    
    // Add sound toggle to notification center
    const notificationCenterHeader = document.querySelector('.notification-center-header');
    if (notificationCenterHeader) {
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'notification-sound-toggle';
        toggleBtn.className = 'notification-sound-toggle';
        toggleBtn.textContent = soundEnabled ? 'Sound On' : 'Sound Off';
        toggleBtn.classList.toggle('active', soundEnabled);
        toggleBtn.addEventListener('click', toggleNotificationSound);
        
        notificationCenterHeader.appendChild(toggleBtn);
    }
    
    // Add CSS for sound toggle button
    const style = document.createElement('style');
    style.textContent = `
        .notification-sound-toggle {
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--line);
            border-radius: 4px;
            color: var(--muted);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .notification-sound-toggle:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text);
        }
        
        .notification-sound-toggle.active {
            background: rgba(76, 175, 80, 0.1);
            border-color: #4caf50;
            color: #4caf50;
        }
    `;
    document.head.appendChild(style);
    
    // Make playNotificationSound available globally
    window.playNotificationSound = playNotificationSound;
    
    // Play sound when new notification arrives
    // This would typically be triggered by server-sent events or polling
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                const notificationList = document.getElementById('notification-list');
                if (notificationList) {
                    const newItems = notificationList.querySelectorAll('.notification-item:not(:first-child)');
                    if (newItems.length > 0) {
                        playNotificationSound();
                    }
                }
            }
        });
    });
    
    const notificationList = document.getElementById('notification-list');
    if (notificationList) {
        observer.observe(notificationList, { childList: true, subtree: true });
    }
});
