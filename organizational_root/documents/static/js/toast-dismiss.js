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
                    // Get the target href and tab before dismissing
                    const targetHref = toast.getAttribute('href');
                    const targetTab = toast.getAttribute('data-target-tab');
                    
                    // Dismiss the notification
                    dismiss();
                    
                    // Navigate to target after dismissal animation
                    if (targetTab) {
                        setTimeout(() => {
                            // Switch to the correct tab
                            const targetTabButton = document.querySelector(`[data-tab-target="${targetTab}"]`);
                            const targetTabPanel = document.querySelector(`[data-tab-panel="${targetTab}"]`);
                            
                            if (targetTabButton && targetTabPanel) {
                                // Remove active class from all tabs
                                document.querySelectorAll('.bottom-tab').forEach(tab => tab.classList.remove('is-active'));
                                document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('is-active'));
                                
                                // Add active class to target tab
                                targetTabButton.classList.add('is-active');
                                targetTabPanel.classList.add('is-active');
                                
                                // Scroll to target element if href exists
                                if (targetHref && targetHref !== '#') {
                                    const targetElement = document.querySelector(targetHref);
                                    if (targetElement) {
                                        setTimeout(() => {
                                            // Scroll to the bottom of the target section to show the latest submission
                                            const rect = targetElement.getBoundingClientRect();
                                            const scrollTop = window.pageYOffset + rect.bottom - window.innerHeight + 100;
                                            window.scrollTo({ top: scrollTop, behavior: 'smooth' });
                                        }, 100);
                                    }
                                }
                            }
                        }, 250);
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
