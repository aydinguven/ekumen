/* Ekumen - Command History Management */

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
