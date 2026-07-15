// Dark Mode Toggle
document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');

    // Check for saved preference or system preference
    const savedTheme = localStorage.getItem('darkMode');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Apply saved theme or system preference
    if (savedTheme === 'true' || (!savedTheme && systemPrefersDark)) {
        document.body.classList.add('dark-mode');
        if (sunIcon) sunIcon.style.display = 'none';
        if (moonIcon) moonIcon.style.display = 'block';
    }

    // Toggle dark mode
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            const isDarkMode = document.body.classList.contains('dark-mode');

            // Toggle icons
            if (sunIcon && moonIcon) {
                sunIcon.style.display = isDarkMode ? 'none' : 'block';
                moonIcon.style.display = isDarkMode ? 'block' : 'none';
            }

            // Save preference
            localStorage.setItem('darkMode', isDarkMode);
        });
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!localStorage.getItem('darkMode')) {
            document.body.classList.toggle('dark-mode', e.matches);
            if (sunIcon && moonIcon) {
                sunIcon.style.display = e.matches ? 'none' : 'block';
                moonIcon.style.display = e.matches ? 'block' : 'none';
            }
        }
    });
});
