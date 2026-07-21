(function () {
    const dismissDistance = 90;

    document.querySelectorAll(".toast-notification").forEach((toast) => {
        let startX = 0;
        let currentX = 0;
        let pointerId = null;

        const setOffset = (distance) => {
            currentX = distance;
            toast.style.transform = `translateX(${distance}px)`;
            toast.style.opacity = String(Math.max(0.35, 1 - Math.abs(distance) / 280));
        };

        const dismiss = () => {
            const direction = currentX < 0 ? -1 : 1;
            toast.classList.remove("is-dragging");
            toast.style.setProperty("--dismiss-x", `${direction * (window.innerWidth + toast.offsetWidth)}px`);
            toast.classList.add("is-dismissing");
            toast.style.opacity = "";
            
            // Store dismissed notification ID in session storage and sync with server
            const notificationId = toast.getAttribute('data-notification-id');
            if (notificationId) {
                const dismissedNotifications = JSON.parse(sessionStorage.getItem('dismissedNotifications') || '[]');
                if (!dismissedNotifications.includes(notificationId)) {
                    dismissedNotifications.push(notificationId);
                    sessionStorage.setItem('dismissedNotifications', JSON.stringify(dismissedNotifications));
                    
                    // Sync with server session via fetch
                    fetch('/dismiss-notification/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                        },
                        body: JSON.stringify({ notification_id: notificationId })
                    }).catch(err => console.error('Failed to dismiss notification:', err));
                }
            }
            
            window.setTimeout(() => toast.remove(), 240);
        };

        const reset = () => {
            toast.classList.remove("is-dragging");
            toast.style.transform = "";
            toast.style.opacity = "";
            currentX = 0;
            pointerId = null;
        };

        // Handle click to dismiss for clickable notifications
        if (toast.classList.contains('clickable-notification')) {
            toast.addEventListener('click', (event) => {
                // Prevent default navigation
                event.preventDefault();
                
                // Don't dismiss if it was a drag
                if (Math.abs(currentX) < dismissDistance) {
                    // Get the target data attributes
                    const targetTab = toast.getAttribute('data-target-tab');
                    const documentId = toast.getAttribute('data-document-id');
                    const section = toast.getAttribute('data-section');
                    
                    console.log('Notification clicked:', { targetTab, documentId, section });
                    
                    // Dismiss the notification
                    dismiss();
                    
                    // Navigate to target after dismissal animation
                    if (targetTab) {
                        setTimeout(() => {
                            // Switch to the correct tab
                            const targetTabButton = document.querySelector(`[data-tab-target="${targetTab}"]`);
                            const targetTabPanel = document.querySelector(`[data-tab-panel="${targetTab}"]`);
                            
                            console.log('Tab elements found:', { targetTabButton: !!targetTabButton, targetTabPanel: !!targetTabPanel });
                            
                            if (targetTabButton && targetTabPanel) {
                                // Remove active class from all tabs
                                document.querySelectorAll('.bottom-tab').forEach(tab => tab.classList.remove('is-active'));
                                document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('is-active'));
                                
                                // Add active class to target tab
                                targetTabButton.classList.add('is-active');
                                targetTabPanel.classList.add('is-active');
                                
                                // Scroll to specific document if documentId is provided
                                if (documentId) {
                                    // Try multiple selectors to find the document
                                    const documentElement = 
                                        document.querySelector(`[data-document-id="${documentId}"]`) ||
                                        document.querySelector(`.document-item[data-document-id="${documentId}"]`) ||
                                        document.querySelector(`.document-row[data-document-id="${documentId}"]`);
                                    
                                    console.log('Document element found:', !!documentElement, 'Selector used:', `[data-document-id="${documentId}"]`);
                                    
                                    if (documentElement) {
                                        setTimeout(() => {
                                            const rect = documentElement.getBoundingClientRect();
                                            const scrollTop = window.pageYOffset + rect.top - (window.innerHeight / 2) + (rect.height / 2);
                                            window.scrollTo({ top: scrollTop, behavior: 'smooth' });
                                            
                                            // Highlight the document briefly
                                            documentElement.style.transition = 'background-color 0.3s ease';
                                            documentElement.style.backgroundColor = 'rgba(59, 130, 246, 0.15)';
                                            documentElement.style.boxShadow = '0 0 0 2px rgba(59, 130, 246, 0.3)';
                                            
                                            setTimeout(() => {
                                                documentElement.style.backgroundColor = '';
                                                documentElement.style.boxShadow = '';
                                            }, 2500);
                                        }, 150);
                                    } else {
                                        console.warn('Document element not found, falling back to tab panel');
                                        targetTabPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                    }
                                } else if (section) {
                                    // Scroll to section if no specific document
                                    const sectionElement = document.querySelector(`[data-section="${section}"]`);
                                    console.log('Section element found:', !!sectionElement);
                                    if (sectionElement) {
                                        setTimeout(() => {
                                            sectionElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                        }, 150);
                                    } else {
                                        targetTabPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                    }
                                } else {
                                    // Default scroll to tab panel
                                    setTimeout(() => {
                                        targetTabPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                    }, 150);
                                }
                            }
                        }, 300);
                    }
                }
            });
        }

        toast.addEventListener("pointerdown", (event) => {
            if (event.button !== undefined && event.button !== 0) {
                return;
            }

            startX = event.clientX;
            currentX = 0;
            pointerId = event.pointerId;
            toast.classList.add("is-dragging");
            toast.setPointerCapture(pointerId);
        });

        toast.addEventListener("pointermove", (event) => {
            if (event.pointerId !== pointerId) {
                return;
            }

            setOffset(event.clientX - startX);
        });

        toast.addEventListener("pointerup", (event) => {
            if (event.pointerId !== pointerId) {
                return;
            }

            if (Math.abs(currentX) >= dismissDistance) {
                dismiss();
            } else {
                reset();
            }
        });

        toast.addEventListener("pointercancel", reset);
    });
})();
