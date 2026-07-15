// Photo lightbox functionality
document.addEventListener('DOMContentLoaded', function() {
    // Create lightbox elements
    const lightbox = document.createElement('div');
    lightbox.className = 'photo-lightbox';
    lightbox.innerHTML = `
        <button class="photo-lightbox-close" aria-label="Close">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
        <img src="" alt="Expanded photo">
    `;
    document.body.appendChild(lightbox);

    const lightboxImg = lightbox.querySelector('img');
    const closeBtn = lightbox.querySelector('.photo-lightbox-close');

    // Open lightbox when photo is clicked
    document.querySelectorAll('.photo-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const photoUrl = this.getAttribute('data-photo-url');
            if (photoUrl) {
                lightboxImg.src = photoUrl;
                lightbox.classList.add('is-active');
                document.body.style.overflow = 'hidden';
            }
        });
    });

    // Close lightbox functions
    function closeLightbox() {
        lightbox.classList.remove('is-active');
        lightboxImg.src = '';
        document.body.style.overflow = '';
    }

    closeBtn.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', function(e) {
        if (e.target === lightbox) {
            closeLightbox();
        }
    });

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && lightbox.classList.contains('is-active')) {
            closeLightbox();
        }
    });
});
