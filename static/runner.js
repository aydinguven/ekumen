/* Ekumen - Real-Time Streaming Ansible Runner & Terminal */

let currentMode = 'adhoc';
let lastOutputRaw = '';
let currentJobId = null;
let currentEventSource = null;
let currentFilter = 'all';
let playbookEditor = null; // CodeMirror instance
let executionStartTime = null;
let executionTimer = null;

/**
 * Switch between Ad-hoc and Playbook modes.
 */
function switchMode(mode) {
    currentMode = mode;

    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    const adhocSection = document.getElementById('adhoc-section');
    const playbookSection = document.getElementById('playbook-section');

    if (adhocSection) adhocSection.classList.toggle('hidden', mode !== 'adhoc');
    if (playbookSection) playbookSection.classList.toggle('hidden', mode !== 'playbook');

    if (mode === 'playbook') {
        refreshCodeMirror();
        loadPlaybookList();
        loadPlaybookTemplatesDropdown();
    }
}

/**
 * Toggle password visibility.
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

    targetEl.style.transition = 'background-color 0.3s ease';
    targetEl.style.backgroundColor = 'rgba(99, 102, 241, 0.25)';
    setTimeout(() => {
        targetEl.style.backgroundColor = '';
    }, 350);
}

/**
 * Load SSH Key content from user-selected local file.
 */
function loadSSHKeyFromFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('private-key').value = e.target.result;
        showToast(`Loaded key: ${file.name}`, 'info');
    };
    reader.readAsText(file);
}

/**
 * Parse ANSI color and style escape codes into safe HTML spans.
 */
function ansiToHtml(text) {
    if (!text) return '';

    let escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    const colorMap = {
        '30': 'color: #64748b;',
        '31': 'color: #ef4444; font-weight: 600;', // red
        '32': 'color: #22c55e; font-weight: 600;', // green
        '33': 'color: #eab308; font-weight: 600;', // yellow
        '34': 'color: #3b82f6;', // blue
        '35': 'color: #a855f7;', // magenta
        '36': 'color: #06b6d4; font-weight: 600;', // cyan
        '37': 'color: #f1f5f9;', // white
        '90': 'color: #94a3b8;',
        '91': 'color: #f87171;',
        '92': 'color: #4ade80;',
        '93': 'color: #fde047;',
        '94': 'color: #60a5fa;',
        '95': 'color: #c084fc;',
        '96': 'color: #22d3ee;',
        '97': 'color: #ffffff;'
    };

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

    escaped = escaped.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    return escaped;
}

/**
 * Filter terminal output by task state (all / changed / failed).
 */
function filterOutput(type) {
    currentFilter = type;

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === type);
    });

    const outputContent = document.getElementById('output-content');
    if (!lastOutputRaw) return;

    if (type === 'all') {
        outputContent.innerHTML = ansiToHtml(lastOutputRaw);
        return;
    }

    const lines = lastOutputRaw.split('\n');
    const filteredLines = [];
    let capturing = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const plain = line.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');

        if (plain.startsWith('TASK [') || plain.startsWith('PLAY [')) {
            capturing = false;
        }

        if (type === 'changed' && (plain.includes('changed: [') || plain.includes('changed='))) {
            capturing = true;
            // Also include previous TASK header if available
            if (i > 0 && lines[i-1].includes('TASK [')) {
                filteredLines.push(lines[i-1]);
            }
        } else if (type === 'failed' && (plain.includes('fatal: [') || plain.includes('failed: [') || plain.includes('failed=') || plain.includes('ERROR'))) {
            capturing = true;
            if (i > 0 && lines[i-1].includes('TASK [')) {
                filteredLines.push(lines[i-1]);
            }
        }

        if (capturing || plain.includes('PLAY RECAP')) {
            filteredLines.push(line);
        }
    }

    outputContent.innerHTML = ansiToHtml(filteredLines.join('\n') || `(No ${type} tasks found in output)`);
}

/**
 * Real-time text search inside terminal output.
 */
function searchOutput(query) {
    const searchCountEl = document.getElementById('search-count');
    const outputContent = document.getElementById('output-content');
    if (!lastOutputRaw || !outputContent) return;

    if (!query || !query.trim()) {
        if (searchCountEl) searchCountEl.classList.add('hidden');
        filterOutput(currentFilter);
        return;
    }

    const cleanQuery = query.trim();
    const cleanRaw = lastOutputRaw;
    const regex = new RegExp(`(${cleanQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const matches = cleanRaw.match(regex) || [];

    if (searchCountEl) {
        searchCountEl.textContent = `${matches.length} match${matches.length === 1 ? '' : 'es'}`;
        searchCountEl.classList.remove('hidden');
    }

    // Render with highlighted spans
    let html = ansiToHtml(cleanRaw);
    html = html.replace(regex, '<span class="search-highlight">$1</span>');
    outputContent.innerHTML = html;
}

/**
 * Render structured play recap badges.
 */
function renderRecapBadges(recap) {
    const recapBar = document.getElementById('recap-bar');
    if (!recapBar || !recap) return;

    const okCount = document.getElementById('recap-ok-count');
    const changedCount = document.getElementById('recap-changed-count');
    const unreachableCount = document.getElementById('recap-unreachable-count');
    const failedCount = document.getElementById('recap-failed-count');
    const skippedCount = document.getElementById('recap-skipped-count');

    if (okCount) okCount.textContent = recap.ok || 0;
    if (changedCount) changedCount.textContent = recap.changed || 0;
    if (unreachableCount) unreachableCount.textContent = recap.unreachable || 0;
    if (failedCount) failedCount.textContent = recap.failed || 0;
    if (skippedCount) skippedCount.textContent = recap.skipped || 0;

    const total = (recap.ok || 0) + (recap.changed || 0) + (recap.unreachable || 0) + (recap.failed || 0) + (recap.skipped || 0);
    if (total > 0) {
        recapBar.classList.remove('hidden');
    } else {
        recapBar.classList.add('hidden');
    }
}

/**
 * Display completed job output and stats from historical record.
 */
function displayJobOutput(job) {
    const outputSection = document.getElementById('output-section');
    const outputStatus = document.getElementById('output-status');
    const outputContent = document.getElementById('output-content');
    const durationBadge = document.getElementById('output-duration');
    const downloadBtn = document.getElementById('download-btn');
    const copyBtn = document.getElementById('copy-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    if (cancelBtn) cancelBtn.classList.add('hidden');
    outputSection.classList.remove('hidden');

    if (job.status === 'success') {
        outputStatus.className = 'output-status success';
        outputStatus.textContent = '✅ Execution Succeeded';
    } else if (job.status === 'cancelled') {
        outputStatus.className = 'output-status error';
        outputStatus.textContent = '🛑 Execution Cancelled';
    } else {
        outputStatus.className = 'output-status error';
        outputStatus.textContent = '❌ Execution Failed';
    }

    if (durationBadge && job.duration) {
        durationBadge.textContent = `${job.duration}s`;
        durationBadge.classList.remove('hidden');
    }

    lastOutputRaw = job.output || '';
    outputContent.innerHTML = ansiToHtml(lastOutputRaw);

    if (lastOutputRaw) {
        if (downloadBtn) downloadBtn.classList.remove('hidden');
        if (copyBtn) copyBtn.classList.remove('hidden');
    }

    renderRecapBadges(job.recap);
}

/**
 * Cancel currently running active job.
 */
async function cancelCurrentJob() {
    if (!currentJobId) return;

    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.disabled = true;
        cancelBtn.innerHTML = '<span class="icon">⏳</span> Stopping...';
    }

    try {
        const response = await fetch(`/jobs/${encodeURIComponent(currentJobId)}/cancel`, { method: 'POST' });
        const res = await response.json();
        if (res.success) {
            showToast('Sent cancellation signal to job', 'info');
        }
    } catch (e) {
        showToast('Cancel failed: ' + e.message, 'error');
    }
}

/**
 * Download last output.
 */
function downloadOutput() {
    if (!lastOutputRaw) {
        showToast('No output to download', 'error');
        return;
    }
    const cleanText = lastOutputRaw.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    const blob = new Blob([cleanText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ekumen_output_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Copy terminal output.
 */
function copyOutput() {
    if (!lastOutputRaw) {
        showToast('No output to copy', 'error');
        return;
    }
    const cleanText = lastOutputRaw.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    navigator.clipboard.writeText(cleanText).then(() => {
        showToast('Output copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy output', 'error');
    });
}

/**
 * Execute Ansible command or playbook with real-time SSE streaming.
 */
async function runAnsible() {
    const runBtn = document.getElementById('run-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const downloadBtn = document.getElementById('download-btn');
    const copyBtn = document.getElementById('copy-btn');
    const outputSection = document.getElementById('output-section');
    const outputStatus = document.getElementById('output-status');
    const outputContent = document.getElementById('output-content');
    const durationBadge = document.getElementById('output-duration');
    const recapBar = document.getElementById('recap-bar');

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
        become_password: document.getElementById('password').value,
        // Advanced options
        forks: document.getElementById('forks').value.trim(),
        tags: document.getElementById('tags').value.trim(),
        skip_tags: document.getElementById('skip-tags').value.trim(),
        extra_vars: document.getElementById('extra-vars').value.trim(),
        private_key: document.getElementById('private-key').value.trim(),
        check_mode: document.getElementById('check-mode').checked,
        diff_mode: document.getElementById('diff-mode').checked
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
        payload.playbook_name = currentLoadedPlaybook || 'Playbook';
    }

    // Reset UI state
    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="icon">⏳</span> Running...';
    if (cancelBtn) {
        cancelBtn.disabled = false;
        cancelBtn.innerHTML = '<span class="icon">🛑</span> Stop';
        cancelBtn.classList.remove('hidden');
    }
    if (downloadBtn) downloadBtn.classList.add('hidden');
    if (copyBtn) copyBtn.classList.add('hidden');
    if (recapBar) recapBar.classList.add('hidden');
    if (durationBadge) durationBadge.classList.add('hidden');

    outputSection.classList.remove('hidden');
    outputStatus.className = 'output-status running';
    outputStatus.textContent = '⏳ Starting Ansible execution...';
    outputContent.textContent = 'Initializing execution...';
    lastOutputRaw = '';

    outputSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Start duration counter
    executionStartTime = Date.now();
    clearInterval(executionTimer);
    executionTimer = setInterval(() => {
        const elapsed = ((Date.now() - executionStartTime) / 1000).toFixed(1);
        if (durationBadge) {
            durationBadge.textContent = `${elapsed}s`;
            durationBadge.classList.remove('hidden');
        }
    }, 200);

    try {
        // Start async job
        const postResp = await fetch('/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const postData = await postResp.json();
        if (!postData.success) {
            throw new Error(postData.error || 'Failed to start job');
        }

        currentJobId = postData.job_id;
        outputStatus.textContent = '⏳ Executing tasks in real time...';
        outputContent.textContent = '';

        // Close any previous SSE
        if (currentEventSource) {
            currentEventSource.close();
        }

        // Open SSE Stream
        currentEventSource = new EventSource(postData.stream_url);

        currentEventSource.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);

                if (msg.type === 'chunk') {
                    lastOutputRaw += msg.text;
                    outputContent.innerHTML = ansiToHtml(lastOutputRaw);

                    const autoscroll = document.getElementById('autoscroll-chk');
                    if (autoscroll && autoscroll.checked) {
                        outputContent.scrollTop = outputContent.scrollHeight;
                    }
                } else if (msg.type === 'done') {
                    clearInterval(executionTimer);
                    currentEventSource.close();
                    currentEventSource = null;

                    if (cancelBtn) cancelBtn.classList.add('hidden');
                    runBtn.disabled = false;
                    runBtn.innerHTML = '<span class="icon">▶️</span> Run';

                    if (msg.status === 'success') {
                        outputStatus.className = 'output-status success';
                        outputStatus.textContent = '✅ Execution Succeeded';
                    } else if (msg.status === 'cancelled') {
                        outputStatus.className = 'output-status error';
                        outputStatus.textContent = '🛑 Execution Cancelled';
                    } else {
                        outputStatus.className = 'output-status error';
                        outputStatus.textContent = '❌ Execution Failed';
                    }

                    if (durationBadge && msg.duration) {
                        durationBadge.textContent = `${msg.duration}s`;
                    }

                    if (lastOutputRaw) {
                        if (downloadBtn) downloadBtn.classList.remove('hidden');
                        if (copyBtn) copyBtn.classList.remove('hidden');
                    }

                    if (msg.recap) {
                        renderRecapBadges(msg.recap);
                    }

                    // Refresh history sidebar from server
                    renderHistory();
                } else if (msg.type === 'error') {
                    clearInterval(executionTimer);
                    currentEventSource.close();
                    outputStatus.className = 'output-status error';
                    outputStatus.textContent = '❌ ' + msg.message;
                    runBtn.disabled = false;
                    runBtn.innerHTML = '<span class="icon">▶️</span> Run';
                    if (cancelBtn) cancelBtn.classList.add('hidden');
                }
            } catch (err) {
                console.error('SSE JSON error:', err);
            }
        };

        currentEventSource.onerror = () => {
            clearInterval(executionTimer);
            if (currentEventSource) {
                currentEventSource.close();
                currentEventSource = null;
            }
            runBtn.disabled = false;
            runBtn.innerHTML = '<span class="icon">▶️</span> Run';
            if (cancelBtn) cancelBtn.classList.add('hidden');
            renderHistory();
        };

    } catch (error) {
        clearInterval(executionTimer);
        outputStatus.className = 'output-status error';
        outputStatus.textContent = '❌ Error: ' + error.message;
        outputContent.textContent = 'Request failed: ' + error.message;
        runBtn.disabled = false;
        runBtn.innerHTML = '<span class="icon">▶️</span> Run';
        if (cancelBtn) cancelBtn.classList.add('hidden');
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
    // Ctrl+F or Cmd+F to focus search input if output is visible
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
        const searchInput = document.getElementById('output-search-input');
        const outputSection = document.getElementById('output-section');
        if (searchInput && outputSection && !outputSection.classList.contains('hidden')) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }
    }
});

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', async () => {
    // Light/Dark Theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    // Color Theme (Red Hat / Purple)
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

    // Render inventories, templates, and collections
    await Promise.all([
        renderInventoryDropdown(),
        loadPlaybookTemplatesDropdown(),
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
