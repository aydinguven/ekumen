/* Ansible Shuttle Frontend Logic */

let currentMode = 'adhoc';
let lastOutput = '';

// Theme Logic
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    btn.textContent = theme === 'light' ? '🌙' : '☀️';
    btn.title = theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode';
}

// Initialize Theme
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
});

function switchMode(mode) {
    currentMode = mode;

    // Update button states
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Show/hide sections
    document.getElementById('adhoc-section').classList.toggle('hidden', mode !== 'adhoc');
    document.getElementById('playbook-section').classList.toggle('hidden', mode !== 'playbook');
}

function togglePassword(inputId, iconId) {
    const passwordInput = document.getElementById(inputId);
    const icon = document.getElementById(iconId);

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.textContent = '🙈';
    } else {
        passwordInput.type = 'password';
        icon.textContent = '👁️';
    }
}

function toggleBecomeCredentials() {
    const checkbox = document.getElementById('different-become');
    const becomeSection = document.getElementById('become-credentials');
    becomeSection.classList.toggle('hidden', !checkbox.checked);
}

function copyFromRegular(sourceId, targetId) {
    const sourceValue = document.getElementById(sourceId).value;
    document.getElementById(targetId).value = sourceValue;

    // Visual feedback
    const targetInput = document.getElementById(targetId);
    targetInput.style.backgroundColor = 'rgba(99, 102, 241, 0.2)';
    setTimeout(() => {
        targetInput.style.backgroundColor = '';
    }, 300);
}

function downloadOutput() {
    if (!lastOutput) {
        alert('No output to download');
        return;
    }
    window.location.href = '/download';
}

async function runAnsible() {
    const runBtn = document.getElementById('run-btn');
    const downloadBtn = document.getElementById('download-btn');
    const outputSection = document.getElementById('output-section');
    const outputStatus = document.getElementById('output-status');
    const outputContent = document.getElementById('output-content');

    // Prepare payload
    const payload = {
        mode: currentMode,
        verbosity: document.getElementById('verbosity').value,
        inventory: document.getElementById('inventory').value,
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
        // Default: use sudo with same credentials
        become: true,
        become_method: 'sudo',
        become_user: 'root',
        become_password: document.getElementById('password').value
    };

    // Check if using different escalation credentials
    if (document.getElementById('different-become').checked) {
        payload.become_method = document.getElementById('become-method').value;
        payload.become_user = document.getElementById('become-user').value || 'root';
        payload.become_password = document.getElementById('become-password').value;
    }

    if (currentMode === 'adhoc') {
        payload.module = document.getElementById('module').value;
        payload.args = document.getElementById('args').value;
    } else {
        payload.playbook = document.getElementById('playbook').value;
    }

    // Update UI state
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="icon">⏳</span> Running...';
    downloadBtn.classList.add('hidden');
    outputSection.classList.remove('hidden');
    outputStatus.className = 'output-status running';
    outputStatus.textContent = '⏳ Running...';
    outputContent.textContent = '';

    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.success) {
            outputStatus.className = 'output-status success';
            outputStatus.textContent = '✅ Success';
        } else {
            outputStatus.className = 'output-status error';
            outputStatus.textContent = '❌ Failed';
        }

        let output = '';
        if (result.output) {
            output += result.output;
        }
        if (result.error) {
            if (output) output += '\n\n--- STDERR ---\n';
            output += result.error;
        }
        outputContent.textContent = output || 'No output';
        lastOutput = output;

        // Show download button if there's output
        if (output) {
            downloadBtn.classList.remove('hidden');
        }

    } catch (error) {
        outputStatus.className = 'output-status error';
        outputStatus.textContent = '❌ Error';
        outputContent.textContent = 'Request failed: ' + error.message;
        lastOutput = '';
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = '<span class="icon">▶️</span> Run';
    }
}
