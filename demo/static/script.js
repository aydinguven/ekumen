/* Ansible Shuttle Frontend Logic */

let currentMode = 'adhoc';
let lastOutput = '';
let playbookEditor = null; // CodeMirror instance

// ========== TOAST NOTIFICATIONS ==========
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

// ========== HISTORY MANAGEMENT ==========
const HISTORY_KEY = 'ekumen_history';
const MAX_HISTORY = 50;

function getHistory() {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
}

function saveHistory(history) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function addToHistory(entry) {
    const history = getHistory();
    // Add new entry at the beginning
    history.unshift({
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        ...entry
    });
    // Limit size
    if (history.length > MAX_HISTORY) {
        history.pop();
    }
    saveHistory(history);
    renderHistory();
}

function deleteHistoryEntry(id, event) {
    event.stopPropagation(); // Don't trigger restore
    const history = getHistory().filter(e => e.id !== id);
    saveHistory(history);
    renderHistory();
}

function clearHistory() {
    if (confirm('Clear all command history?')) {
        localStorage.removeItem(HISTORY_KEY);
        renderHistory();
    }
}

function restoreEntry(id) {
    const history = getHistory();
    const entry = history.find(e => e.id === id);
    if (!entry) return;

    // Switch to correct mode
    switchMode(entry.mode);

    // Restore fields
    document.getElementById('inventory').value = entry.hosts || '';
    document.getElementById('verbosity').value = entry.verbosity || '';

    if (entry.mode === 'adhoc') {
        document.getElementById('module').value = entry.module || 'ping';
        document.getElementById('args').value = entry.args || '';
    } else {
        const playbookContent = entry.playbook || '';
        document.getElementById('playbook').value = playbookContent;
        // Update CodeMirror if available
        if (playbookEditor) {
            playbookEditor.setValue(playbookContent);
        }
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function formatTimeAgo(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    return date.toLocaleDateString();
}

function renderHistory() {
    const listEl = document.getElementById('history-list');
    const clearBtn = document.getElementById('clear-history-btn');
    const history = getHistory();

    if (history.length === 0) {
        listEl.innerHTML = '<div class="history-empty">No commands yet.<br>Run something to see it here.</div>';
        clearBtn.classList.add('hidden');
        return;
    }

    clearBtn.classList.remove('hidden');

    listEl.innerHTML = history.map(entry => {
        const command = entry.mode === 'adhoc'
            ? `${entry.module}${entry.args ? ' ' + entry.args : ''}`
            : 'Playbook';
        const hostCount = (entry.hosts || '').split('\n').filter(h => h.trim()).length;
        const hostsLabel = hostCount === 1 ? '1 host' : `${hostCount} hosts`;

        return `
            <div class="history-entry" onclick="restoreEntry('${entry.id}')">
                <div class="history-entry-header">
                    <span class="history-entry-mode">${entry.mode === 'adhoc' ? '⚡ Ad-hoc' : '📋 Playbook'}</span>
                    <button class="history-entry-delete" onclick="deleteHistoryEntry('${entry.id}', event)" title="Delete">✕</button>
                </div>
                <div class="history-entry-command">${escapeHtml(command)}</div>
                <div class="history-entry-hosts">${hostsLabel}</div>
                <div class="history-entry-time">${formatTimeAgo(entry.timestamp)}</div>
            </div>
        `;
    }).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleSidebar() {
    const sidebar = document.getElementById('history-sidebar');
    const expandBtn = document.getElementById('sidebar-expand-btn');

    sidebar.classList.toggle('collapsed');
    const isCollapsed = sidebar.classList.contains('collapsed');

    expandBtn.classList.toggle('hidden', !isCollapsed);
    localStorage.setItem('sidebar_collapsed', isCollapsed ? 'true' : 'false');
}

function refreshCodeMirror() {
    // Force CodeMirror to re-read CSS variables after theme change
    if (playbookEditor) {
        setTimeout(() => {
            playbookEditor.refresh();
        }, 50);
    }
}

// Initialize Theme and History
document.addEventListener('DOMContentLoaded', () => {
    // Light/Dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Color Theme
    const savedColor = localStorage.getItem('color-theme') || 'default';
    if (savedColor === 'purple') {
        document.documentElement.setAttribute('data-color-theme', 'purple');
    }
    updateColorIcon(savedColor);

    // History Sidebar
    renderHistory();
    const sidebarCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
    if (sidebarCollapsed) {
        document.getElementById('history-sidebar').classList.add('collapsed');
        document.getElementById('sidebar-expand-btn').classList.remove('hidden');
    }

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

// ========== PLAYBOOK LIBRARY ==========
let currentLoadedPlaybook = null;

async function loadPlaybookList() {
    const select = document.getElementById('playbook-library');
    try {
        const response = await fetch('/playbooks');
        const data = await response.json();

        // Keep first option, remove rest
        select.innerHTML = '<option value="">📂 Load...</option>';

        if (data.playbooks && data.playbooks.length > 0) {
            data.playbooks.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load playbook list:', error);
    }
}

async function loadPlaybook(name) {
    if (!name) {
        currentLoadedPlaybook = null;
        document.getElementById('delete-playbook-btn').style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/playbooks/${encodeURIComponent(name)}`);
        const data = await response.json();

        if (data.success) {
            const content = data.content;
            document.getElementById('playbook').value = content;
            if (playbookEditor) {
                playbookEditor.setValue(content);
            }
            currentLoadedPlaybook = data.name;
            document.getElementById('delete-playbook-btn').style.display = 'inline-block';
        } else {
            alert('Failed to load playbook: ' + data.error);
        }
    } catch (error) {
        showToast('Failed to load: ' + error.message, 'error');
    }
}

async function savePlaybook() {
    const content = playbookEditor ? playbookEditor.getValue() : document.getElementById('playbook').value;

    if (!content.trim()) {
        showToast('Playbook content is empty', 'error');
        return;
    }

    const defaultName = currentLoadedPlaybook || '';
    const name = prompt('Enter playbook name:', defaultName.replace('.yml', '').replace('.yaml', ''));

    if (!name) return;

    try {
        const response = await fetch('/playbooks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, content })
        });

        const data = await response.json();

        if (data.success) {
            currentLoadedPlaybook = data.name;
            loadPlaybookList();
            // Select the saved playbook
            setTimeout(() => {
                document.getElementById('playbook-library').value = data.name;
                document.getElementById('delete-playbook-btn').style.display = 'inline-block';
            }, 100);
            showToast('Saved: ' + data.name, 'success');
        } else {
            showToast('Failed to save: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to save: ' + error.message, 'error');
    }
}

async function deletePlaybook() {
    if (!currentLoadedPlaybook) return;

    if (!confirm(`Delete playbook "${currentLoadedPlaybook}"?`)) return;

    try {
        const response = await fetch(`/playbooks/${encodeURIComponent(currentLoadedPlaybook)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            currentLoadedPlaybook = null;
            document.getElementById('playbook-library').value = '';
            document.getElementById('delete-playbook-btn').style.display = 'none';
            loadPlaybookList();
            showToast('Playbook deleted', 'success');
        } else {
            showToast('Failed to delete: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to delete: ' + error.message, 'error');
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
