/* Ekumen - Ansible Runner & Main Application Logic */

let currentMode = 'adhoc';
let lastOutput = '';
let playbookEditor = null; // CodeMirror instance

function switchMode(mode) {
    currentMode = mode;

    // Update button states
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Show/hide sections
    document.getElementById('adhoc-section').classList.toggle('hidden', mode !== 'adhoc');
    document.getElementById('playbook-section').classList.toggle('hidden', mode !== 'playbook');

    // Refresh CodeMirror when switching to playbook (fixes layout on first view)
    if (mode === 'playbook') {
        refreshCodeMirror();
        loadPlaybookList();
    }
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
        limit: document.getElementById('limit').value.trim(), // --limit option
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

        // Save to history (regardless of success/fail, as long as command ran)
        addToHistory({
            mode: currentMode,
            module: currentMode === 'adhoc' ? document.getElementById('module').value : null,
            args: currentMode === 'adhoc' ? document.getElementById('args').value : null,
            playbook: currentMode === 'playbook' ? document.getElementById('playbook').value : null,
            hosts: document.getElementById('inventory').value,
            verbosity: document.getElementById('verbosity').value
        });

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

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', () => {
    // Light/Dark theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Color Theme
    const savedColor = localStorage.getItem('color-theme') || 'default';
    if (savedColor === 'purple') {
        document.documentElement.setAttribute('data-color-theme', 'purple');
    }
    updateColorIcon(savedColor);

    // History Sidebar - default to collapsed
    renderHistory();
    const sidebarCollapsed = localStorage.getItem('sidebar_collapsed');
    if (sidebarCollapsed !== 'false') {
        document.getElementById('history-sidebar').classList.add('collapsed');
        document.getElementById('sidebar-expand-btn').classList.remove('hidden');
    }

    // Collections Sidebar - default to collapsed
    const collectionsCollapsed = localStorage.getItem('collections_sidebar_collapsed');
    if (collectionsCollapsed !== 'false') {
        document.getElementById('collections-sidebar').classList.add('collapsed');
        document.getElementById('collections-expand-btn').classList.remove('hidden');
    }

    // Load saved inventories dropdown
    renderInventoryDropdown();

    // Load collections and roles
    loadCollectionsAndRoles();

    // Initialize CodeMirror for Playbook Editor
    const editorContainer = document.getElementById('playbook-editor');
    const textarea = document.getElementById('playbook');
    if (editorContainer && typeof CodeMirror !== 'undefined') {
        playbookEditor = CodeMirror(editorContainer, {
            value: textarea.value,
            mode: 'yaml',
            lineNumbers: true,
            lineWrapping: true,
            tabSize: 2,
            indentWithTabs: false,
            autofocus: false
        });
        // Sync editor content to hidden textarea
        playbookEditor.on('change', () => {
            textarea.value = playbookEditor.getValue();
        });
    }
});
