const notesField = document.getElementById('id_correction_notes');
const preview = document.querySelector('[data-checklist-preview]');

function renderChecklistPreview() {
    if (!notesField || !preview) {
        return;
    }

    const items = preview.querySelector('.live-checklist-items');
    const lines = notesField.value
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);

    items.innerHTML = '';

    if (!lines.length) {
        preview.classList.add('is-empty');
        return;
    }

    preview.classList.remove('is-empty');
    lines.forEach((line) => {
        const label = document.createElement('label');
        label.className = 'checklist-item preview-checklist-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.disabled = true;

        const text = document.createElement('span');
        text.textContent = line;

        label.append(checkbox, text);
        items.appendChild(label);
    });
}

if (notesField && preview) {
    notesField.addEventListener('input', renderChecklistPreview);
    notesField.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            renderChecklistPreview();
        }
    });
    renderChecklistPreview();
}
