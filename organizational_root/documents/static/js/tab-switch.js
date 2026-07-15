document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelector('.bottom-tabs');
    if (!tabs) {
        return;
    }

    const panels = document.querySelectorAll('[data-tab-panel]');

    const activateTab = (targetName) => {
        const targetPanel = document.querySelector(`[data-tab-panel="${targetName}"]`);
        const targetTab = tabs.querySelector(`[data-tab-target="${targetName}"]`);
        if (!targetPanel || !targetTab) {
            return false;
        }

        tabs.querySelectorAll('.bottom-tab').forEach((tab) => {
            tab.classList.toggle('is-active', tab === targetTab);
            tab.classList.remove('is-entering', 'is-leaving');
        });

        panels.forEach((panel) => {
            const isActive = panel === targetPanel;
            panel.classList.toggle('is-active', isActive);
            panel.hidden = !isActive;
        });

        targetTab.classList.add('is-entering');
        window.setTimeout(() => {
            targetTab.classList.remove('is-entering');
            tabs.classList.remove('is-switching');
        }, 180);

        return true;
    };

    panels.forEach((panel) => {
        panel.hidden = !panel.classList.contains('is-active');
    });

    if (window.location.hash) {
        activateTab(window.location.hash.slice(1));
    }

    tabs.querySelectorAll('.bottom-tab').forEach((tab) => {
        tab.addEventListener('click', (event) => {
            const url = tab.getAttribute('href');
            const targetName = tab.dataset.tabTarget;

            if (!url || tab.classList.contains('is-active')) {
                return;
            }

            event.preventDefault();
            tabs.classList.add('is-switching');
            tabs.querySelector('.is-active')?.classList.add('is-leaving');

            if (targetName) {
                window.setTimeout(() => {
                    activateTab(targetName);
                    history.replaceState(null, '', `#${targetName}`);
                }, 120);
                return;
            }

            window.setTimeout(() => {
                window.location.href = url;
            }, 160);
        });
    });
});
