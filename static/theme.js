/* Ekumen - Toast Notifications & Theme Logic */

function showToast(message, type = 'info') {
    // Remove existing toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Theme Logic
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
    refreshCodeMirror();
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    btn.textContent = theme === 'light' ? '🌙' : '☀️';
    btn.title = theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode';
}

function toggleColorTheme() {
    const html = document.documentElement;
    const currentColor = html.getAttribute('data-color-theme');
    const newColor = currentColor === 'purple' ? 'default' : 'purple';

    if (newColor === 'default') {
        html.removeAttribute('data-color-theme');
    } else {
        html.setAttribute('data-color-theme', newColor);
    }

    localStorage.setItem('color-theme', newColor);
    updateColorIcon(newColor);
    refreshCodeMirror();
}

function updateColorIcon(color) {
    const btn = document.getElementById('color-toggle');
    // Visual indicator: purple theme = button lit up
    btn.style.opacity = color === 'purple' ? '1' : '0.5';
    btn.style.filter = color === 'purple' ? 'grayscale(0%)' : 'grayscale(100%)';
}

function refreshCodeMirror() {
    // Force CodeMirror to re-read CSS variables after theme change
    if (playbookEditor) {
        setTimeout(() => {
            playbookEditor.refresh();
        }, 50);
    }
}
