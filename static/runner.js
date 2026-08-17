/* Ekumen - Ansible Runner & Main Application Logic */

let currentMode = 'adhoc';
let lastOutputRaw = '';
let currentRunId = '';
let playbookEditor = null; // CodeMirror instance

/**
 * Switch between Ad-hoc and Playbook modes.
 */
function switchMode(mode) {
    currentMode = mode;

    // Update button states
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Show/hide sections
    const adhocSection = document.getElementById('adhoc-section');
    const playbookSection = document.getElementById('playbook-section');

    if (adhocSection) adhocSection.classList.toggle('hidden', mode !== 'adhoc');
    if (playbookSection) playbookSection.classList.toggle('hidden', mode !== 'playbook');

    // Refresh CodeMirror when switching to playbook
    if (mode === 'playbook') {
        refreshCodeMirror();
        loadPlaybookList();
    }
}

/**
 * Toggle visibility of password fields.
 */
function togglePassword(inputId, iconId) {
    const passwordInput = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (!passwordInput || !icon) return;

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.textContent = '🙈';
    } else {
        passwordInput.type = 'password';
        icon.textContent = '👁️';
    }
}

/**
 * Toggle become credentials section.
 */
function toggleBecomeCredentials() {
    const checkbox = document.getElementById('different-become');
    const becomeSection = document.getElementById('become-credentials');
    if (checkbox && becomeSection) {
        becomeSection.classList.toggle('hidden', !checkbox.checked);
    }
}

/**
 * Copy field values between regular and become credentials.
 */
function copyFromRegular(sourceId, targetId) {
    const sourceEl = document.getElementById(sourceId);
    const targetEl = document.getElementById(targetId);
    if (!sourceEl || !targetEl) return;

    targetEl.value = sourceEl.value;

    // Visual feedback
    targetEl.style.transition = 'background-color 0.3s ease';
    targetEl.style.backgroundColor = 'rgba(99, 102, 241, 0.25)';
    setTimeout(() => {
        targetEl.style.backgroundColor = '';
    }, 350);
}

/**
 * Parse ANSI color and style escape codes into safe HTML spans.
 */
function ansiToHtml(text) {
    if (!text) return '';

    // First escape HTML entities
    let escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // ANSI color map
    const colorMap = {
        '30': 'color: #64748b;',
        '31': 'color: #ef4444; font-weight: 600;', // red (failures)
        '32': 'color: #22c55e; font-weight: 600;', // green (ok/success)
        '33': 'color: #eab308; font-weight: 600;', // yellow (changed)
        '34': 'color: #3b82f6;', // blue
        '35': 'color: #a855f7;', // magenta
        '36': 'color: #06b6d4; font-weight: 600;', // cyan (skipping/item)
        '37': 'color: #f1f5f9;', // white
        '90': 'color: #94a3b8;', // bright black/gray
        '91': 'color: #f87171;', // bright red
        '92': 'color: #4ade80;', // bright green
        '93': 'color: #fde047;', // bright yellow
        '94': 'color: #60a5fa;', // bright blue
        '95': 'color: #c084fc;', // bright magenta
        '96': 'color: #22d3ee;', // bright cyan
        '97': 'color: #ffffff;'  // bright white
    };

    // Replace ANSI color codes
    escaped = escaped.replace(/\x1b\[(\d+(?:;\d+)*)m/g, (match, codeStr) => {
        const codes = codeStr.split(';');
        if (codes.includes('0') || codes.includes('00')) {
            return '</span>';
        }
        let styles = [];
        codes.forEach(c => {
            if (colorMap[c]) styles.push(colorMap[c]);
            if (c === '1') styles.push('font-weight: 700;');
            if (c === '4') styles.push('text-decoration: underline;');
        });
        if (styles.length > 0) {
            return `<span style="${styles.join(' ')}">`;
        }
        return '';
    });

    // Remove any leftover non-color ANSI escape sequences
    escaped = escaped.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');

    return escaped;
}

/**
 * Download last output as a text file.
 */
function downloadOutput() {
    if (!lastOutputRaw) {
        showToast('No output available to download', 'error');
        return;
    }
    const url = currentRunId ? `/download?id=${encodeURIComponent(currentRunId)}` : '/download';
    window.location.href = url;
}

/**
 * Copy terminal output to clipboard.
 */
function copyOutput() {
    if (!lastOutputRaw) {
        showToast('No output to copy', 'error');
        return;
    }
    navigator.clipboard.writeText(lastOutputRaw).then(() => {
        showToast('Output copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy output', 'error');
    });
}

/**
 * Execute Ansible command or playbook.
 */
async function runAnsible() {
    const runBtn = document.getElementById('run-btn');
    const downloadBtn = document.getElementById('download-btn');
    const copyBtn = document.getElementById('copy-btn');
    const outputSection = document.getElementById('output-section');
    const outputStatus = document.getElementById('output-status');
    const outputContent = document.getElementById('output-content');

    const inventoryVal = document.getElementById('inventory').value.trim();
    if (!inventoryVal) {
        showToast('Please specify at least one host in Inventory', 'error');
        document.getElementById('inventory').focus();
        return;
    }

    // Build payload
    const payload = {
        mode: currentMode,
        verbosity: document.getElementById('verbosity').value,
        inventory: inventoryVal,
        limit: document.getElementById('limit').value.trim(),
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value,
        become: true,
        become_method: 'sudo',
        become_user: 'root',
        become_password: document.getElementById('password').value
    };

    if (document.getElementById('different-become').checked) {
        payload.become_method = document.getElementById('become-method').value;
        payload.become_user = document.getElementById('become-user').value.trim() || 'root';
        payload.become_password = document.getElementById('become-password').value;
    }

    if (currentMode === 'adhoc') {
        payload.module = document.getElementById('module').value;
        payload.args = document.getElementById('args').value;
    } else {
        const playbookVal = playbookEditor ? playbookEditor.getValue() : document.getElementById('playbook').value;
        if (!playbookVal.trim()) {
            showToast('Please provide playbook content', 'error');
            return;
        }
        payload.playbook = playbookVal;
    }

    // UI Loading State
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="icon">⏳</span> Running...';
    if (downloadBtn) downloadBtn.classList.add('hidden');
    if (copyBtn) copyBtn.classList.add('hidden');
    outputSection.classList.remove('hidden');
    outputStatus.className = 'output-status running';
    outputStatus.textContent = '⏳ Executing Ansible...';
    outputContent.innerHTML = 'Connecting and executing...';

    // Smooth scroll to output
    outputSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        currentRunId = result.run_id || '';

        if (result.success) {
            outputStatus.className = 'output-status success';
            outputStatus.textContent = '✅ Execution Succeeded';
        } else {
            outputStatus.className = 'output-status error';
            outputStatus.textContent = '❌ Execution Failed';
        }

        let fullOutput = '';
        if (result.output) fullOutput += result.output;
        if (result.error) {
            if (fullOutput) fullOutput += '\n\n--- STDERR / ERROR ---\n';
            fullOutput += result.error;
        }

        lastOutputRaw = fullOutput || 'No output received.';
        outputContent.innerHTML = ansiToHtml(lastOutputRaw);

        if (lastOutputRaw) {
            if (downloadBtn) downloadBtn.classList.remove('hidden');
            if (copyBtn) copyBtn.classList.remove('hidden');
        }

        // Save entry to history
        addToHistory({
            mode: currentMode,
            module: currentMode === 'adhoc' ? document.getElementById('module').value : null,
            args: currentMode === 'adhoc' ? document.getElementById('args').value : null,
            playbook: currentMode === 'playbook' ? (playbookEditor ? playbookEditor.getValue() : document.getElementById('playbook').value) : null,
            hosts: inventoryVal,
            verbosity: document.getElementById('verbosity').value
        });

    } catch (error) {
        outputStatus.className = 'output-status error';
        outputStatus.textContent = '❌ Network / Server Error';
        outputContent.textContent = 'Request failed: ' + error.message;
        lastOutputRaw = '';
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = '<span class="icon">▶️</span> Run';
    }
}

// ========== KEYBOARD SHORTCUTS ==========

document.addEventListener('keydown', (e) => {
    // Ctrl+Enter or Cmd+Enter to Run
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runAnsible();
    }
    // Ctrl+S or Cmd+S to Save active item
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        if (currentMode === 'playbook') {
            savePlaybook();
        } else {
            saveCurrentInventory();
        }
    }
});

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', async () => {
    // Light/Dark Theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Color Theme (Red Hat / Default)
    const savedColor = localStorage.getItem('color-theme') || 'default';
    if (savedColor === 'purple') {
        document.documentElement.setAttribute('data-color-theme', 'purple');
    }
    updateColorIcon(savedColor);

    // History Sidebar
    renderHistory();
    const sidebarCollapsed = localStorage.getItem('sidebar_collapsed');
    if (sidebarCollapsed !== 'false') {
        const hSidebar = document.getElementById('history-sidebar');
        const hExpand = document.getElementById('sidebar-expand-btn');
        if (hSidebar) hSidebar.classList.add('collapsed');
        if (hExpand) hExpand.classList.remove('hidden');
    }

    // Collections Sidebar
    const collectionsCollapsed = localStorage.getItem('collections_sidebar_collapsed');
    if (collectionsCollapsed !== 'false') {
        const cSidebar = document.getElementById('collections-sidebar');
        const cExpand = document.getElementById('collections-expand-btn');
        if (cSidebar) cSidebar.classList.add('collapsed');
        if (cExpand) cExpand.classList.remove('hidden');
    }

    // Migrate any legacy local inventories to server
    await migrateLocalStorageInventories();

    // Render inventories and collections
    await Promise.all([
        renderInventoryDropdown(),
        loadCollectionsAndRoles()
    ]);

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
            autofocus: false,
            extraKeys: {
                "Ctrl-Enter": () => runAnsible(),
                "Cmd-Enter": () => runAnsible(),
                "Ctrl-S": () => savePlaybook(),
                "Cmd-S": () => savePlaybook()
            }
        });

        playbookEditor.on('change', () => {
            textarea.value = playbookEditor.getValue();
        });
    }
});
