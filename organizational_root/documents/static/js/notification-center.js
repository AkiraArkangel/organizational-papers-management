// Notification Center
document.addEventListener('DOMContentLoaded', function() {
    const notificationToggle = document.getElementById('notification-center-toggle');
    const notificationCenter = document.getElementById('notification-center');
    const notificationList = document.getElementById('notification-list');
    const notificationBadge = document.getElementById('notification-badge');
    const markAllReadBtn = document.getElementById('mark-all-read');
    const clearAllBtn = document.getElementById('clear-all-notifications');

    // Get notifications from backend data
    let notifications = window.notifications || [];

    // Toggle notification center
    if (notificationToggle) {
        notificationToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationCenter.classList.toggle('is-active');
        });
    }

    // Close notification center when clicking outside
    document.addEventListener('click', function(e) {
        if (notificationCenter && !notificationCenter.contains(e.target) && !notificationToggle.contains(e.target)) {
            notificationCenter.classList.remove('is-active');
        }
    });

    // Update notification badge
    function updateBadge() {
        const unreadCount = notifications.filter(n => !n.is_read).length;
        if (notificationBadge) {
            if (unreadCount > 0) {
                notificationBadge.textContent = unreadCount > 9 ? '9+' : unreadCount;
                notificationBadge.style.display = 'flex';
            } else {
                notificationBadge.style.display = 'none';
            }
        }
    }

    // Format time
    function formatTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString();
    }

    // Render notifications
    function renderNotifications() {
        if (!notificationList) return;

        if (notifications.length === 0) {
            notificationList.innerHTML = `
                <div class="notification-center-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                        <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                    </svg>
                    <p>No notifications</p>
                </div>
            `;
            return;
        }

        notificationList.innerHTML = notifications.map(notification => `
            <div class="notification-center-item ${notification.is_read ? '' : 'unread'}" data-id="${notification.id}">
                <div class="notification-center-item-header">
                    <span class="notification-center-item-title">${notification.title}</span>
                    <span class="notification-center-item-time">${formatTime(notification.created_at)}</span>
                </div>
                <div class="notification-center-item-message">${notification.message}</div>
            </div>
        `).join('');

        // Add click handlers to notification items
        notificationList.querySelectorAll('.notification-center-item').forEach(item => {
            item.addEventListener('click', function() {
                const id = this.dataset.id;
                markAsRead(id);
            });
        });
    }

    // Mark notification as read
    function markAsRead(id) {
        const notification = notifications.find(n => n.id === id);
        if (notification) {
            notification.is_read = true;
            updateBadge();
            renderNotifications();

            // Send to backend to mark as read
            fetch(`/notifications/${id}/read/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ id: id })
            }).catch(err => console.error('Failed to mark notification as read:', err));
        }
    }

    // Get CSRF token
    function getCsrfToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    // Mark all as read
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function() {
            notifications.forEach(n => n.is_read = true);
            updateBadge();
            renderNotifications();

            // Send to backend to mark all as read
            fetch('/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            }).catch(err => console.error('Failed to mark all notifications as read:', err));
        });
    }

    // Clear all notifications
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            notifications = [];
            updateBadge();
            renderNotifications();

            // Send to backend to clear all
            fetch('/notifications/clear-all/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            }).catch(err => console.error('Failed to clear notifications:', err));
        });
    }

    // Initialize
    updateBadge();
    renderNotifications();
});
