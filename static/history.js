/* Ekumen - Execution History Management (SQLite Backend) */

let jobsHistoryData = [];

/**
 * Fetch and render job execution history from the server.
 */
async function renderHistory() {
    const listEl = document.getElementById('history-list');
    const clearBtn = document.getElementById('clear-history-btn');
    if (!listEl) return;

    try {
        const response = await fetch('/jobs?limit=50');
        const data = await response.json();
        jobsHistoryData = data.jobs || [];

        if (jobsHistoryData.length === 0) {
            listEl.innerHTML = '<div class="history-empty">No commands yet.<br>Run something to see it here.</div>';
            if (clearBtn) clearBtn.classList.add('hidden');
            return;
        }

        if (clearBtn) clearBtn.classList.remove('hidden');

        listEl.innerHTML = jobsHistoryData.map(job => {
            const isAdhoc = job.mode === 'adhoc';
            const modeLabel = isAdhoc ? '⚡ Ad-hoc' : '📋 Playbook';
            const target = job.target_name || (isAdhoc ? 'ping' : 'Playbook');
            const duration = job.duration ? `${job.duration}s` : '';
            const statusClass = `status-${job.status}`;
            const statusIcon = job.status === 'success' ? '✅' :
                (job.status === 'failed' ? '❌' :
                    (job.status === 'cancelled' ? '🛑' : '⏳'));

            const hostCount = job.host_count || 1;
            const hostsLabel = hostCount === 1 ? '1 host' : `${hostCount} hosts`;

            return `
                <div class="history-entry" onclick="restoreJob('${job.id}')">
                    <div class="history-entry-top">
                        <span class="history-entry-mode">${modeLabel}</span>
                        <div style="display: flex; gap: 4px; align-items: center;">
                            <span class="history-status-badge ${statusClass}">${statusIcon} ${job.status}</span>
                            <button class="history-entry-delete" onclick="deleteHistoryEntry('${job.id}', event)" title="Delete">✕</button>
                        </div>
                    </div>
                    <div class="history-entry-command">${escapeHtml(target)}</div>
                    <div class="history-meta">
                        <span>${hostsLabel}</span>
                        ${duration ? `<span>⏱️ ${duration}</span>` : ''}
                        <span>${formatTimeAgo(job.start_time)}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load history from server:', error);
    }
}

/**
 * Restore an execution job's parameters and view output.
 */
async function restoreJob(jobId) {
    try {
        const response = await fetch(`/jobs/${encodeURIComponent(jobId)}`);
        const data = await response.json();
        if (!data.success || !data.job) return;

        const job = data.job;
        const params = job.params || {};

        // Switch to correct mode
        switchMode(job.mode);

        // Restore inventory & verbosity
        if (params.inventory) {
            document.getElementById('inventory').value = params.inventory;
        }
        if (params.verbosity !== undefined) {
            document.getElementById('verbosity').value = params.verbosity;
        }
        if (params.limit) {
            document.getElementById('limit').value = params.limit;
        }

        // Restore mode specific fields
        if (job.mode === 'adhoc') {
            if (params.module) document.getElementById('module').value = params.module;
            if (params.args) document.getElementById('args').value = params.args;
        } else {
            if (params.playbook) {
                document.getElementById('playbook').value = params.playbook;
                if (playbookEditor) playbookEditor.setValue(params.playbook);
            }
        }

        // Restore advanced options if present
        if (params.forks) document.getElementById('forks').value = params.forks;
        if (params.tags) document.getElementById('tags').value = params.tags;
        if (params.skip_tags) document.getElementById('skip-tags').value = params.skip_tags;
        if (params.extra_vars) document.getElementById('extra-vars').value = params.extra_vars;
        if (params.check_mode) document.getElementById('check-mode').checked = true;
        if (params.diff_mode) document.getElementById('diff-mode').checked = true;

        // Display historical output
        if (job.output) {
            displayJobOutput({
                output: job.output,
                status: job.status,
                duration: job.duration,
                recap: {
                    ok: job.recap_ok,
                    changed: job.recap_changed,
                    unreachable: job.recap_unreachable,
                    failed: job.recap_failed,
                    skipped: job.recap_skipped
                }
            });
        }

        showToast(`Restored run: ${job.target_name || job.id}`, 'info');
        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (error) {
        showToast('Failed to restore job: ' + error.message, 'error');
    }
}

/**
 * Delete a specific job record.
 */
async function deleteHistoryEntry(jobId, event) {
    event.stopPropagation();

    try {
        const response = await fetch(`/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            renderHistory();
        }
    } catch (error) {
        console.error('Failed to delete history item:', error);
    }
}

/**
 * Clear all history from database.
 */
async function clearHistory() {
    if (!confirm('Clear all command execution history?')) return;

    try {
        const response = await fetch('/jobs', { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            renderHistory();
            showToast('Execution history cleared', 'success');
        }
    } catch (error) {
        showToast('Failed to clear history: ' + error.message, 'error');
    }
}

function formatTimeAgo(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function toggleSidebar() {
    const sidebar = document.getElementById('history-sidebar');
    const expandBtn = document.getElementById('sidebar-expand-btn');
    if (!sidebar || !expandBtn) return;

    sidebar.classList.toggle('collapsed');
    const isCollapsed = sidebar.classList.contains('collapsed');

    expandBtn.classList.toggle('hidden', !isCollapsed);
    localStorage.setItem('sidebar_collapsed', isCollapsed ? 'true' : 'false');
}
