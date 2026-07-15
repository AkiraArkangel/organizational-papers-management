// Calendar View
document.addEventListener('DOMContentLoaded', function() {
    const calendarContainer = document.getElementById('calendar-view');
    if (!calendarContainer) return;

    let currentDate = new Date();
    let events = [];

    // Parse events from data attribute if available
    const eventsData = calendarContainer.dataset.events;
    if (eventsData) {
        try {
            events = JSON.parse(eventsData);
        } catch (e) {
            console.error('Failed to parse calendar events:', e);
        }
    }

    function renderCalendar(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startingDay = firstDay.getDay();
        const totalDays = lastDay.getDate();
        
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                           'July', 'August', 'September', 'October', 'November', 'December'];
        
        // Update title
        document.getElementById('calendar-title').textContent = `${monthNames[month]} ${year}`;
        
        // Clear grid
        const grid = document.getElementById('calendar-grid');
        grid.innerHTML = '';
        
        // Add day headers
        const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayHeaders.forEach(day => {
            const header = document.createElement('div');
            header.className = 'calendar-day-header';
            header.textContent = day;
            grid.appendChild(header);
        });
        
        // Add empty cells for days before the first day of the month
        for (let i = 0; i < startingDay; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.className = 'calendar-day empty';
            grid.appendChild(emptyDay);
        }
        
        // Add days
        const today = new Date();
        for (let day = 1; day <= totalDays; day++) {
            const dayElement = document.createElement('div');
            dayElement.className = 'calendar-day';
            
            // Check if this is today
            if (day === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                dayElement.classList.add('today');
            }
            
            // Add day number
            const dayNumber = document.createElement('div');
            dayNumber.className = 'calendar-day-number';
            dayNumber.textContent = day;
            dayElement.appendChild(dayNumber);
            
            // Add events for this day
            const dayEvents = document.createElement('div');
            dayEvents.className = 'calendar-day-events';
            
            const currentDateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const dayEventsList = events.filter(event => event.date === currentDateStr);
            
            dayEventsList.forEach(event => {
                const eventElement = document.createElement('div');
                eventElement.className = `calendar-event ${event.status.toLowerCase()}`;
                eventElement.textContent = event.title;
                eventElement.title = event.title;
                dayEvents.appendChild(eventElement);
            });
            
            dayElement.appendChild(dayEvents);
            grid.appendChild(dayElement);
        }
    }

    // Navigation
    document.getElementById('prev-month').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar(currentDate);
    });

    document.getElementById('next-month').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar(currentDate);
    });

    document.getElementById('today-btn').addEventListener('click', function() {
        currentDate = new Date();
        renderCalendar(currentDate);
    });

    // Initial render
    renderCalendar(currentDate);
});
