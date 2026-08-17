/* Ekumen - Inventory Management & Structure Explorer */

let currentSelectedInventory = null;
let inventoryExplorerOpen = false;

/**
 * Toggle visibility of Inventory Hierarchy Explorer.
 */
function toggleInventoryExplorer() {
    const explorerEl = document.getElementById('inventory-explorer');
    const toggleBtn = document.getElementById('toggle-explorer-btn');
    if (!explorerEl) return;

    inventoryExplorerOpen = !inventoryExplorerOpen;
    explorerEl.classList.toggle('hidden', !inventoryExplorerOpen);

    if (toggleBtn) {
        toggleBtn.classList.toggle('active', inventoryExplorerOpen);
    }

    if (inventoryExplorerOpen) {
        refreshInventoryExplorer();
    }
}

/**
 * Event handler when inventory text changes.
 */
function onInventoryChanged() {
    if (inventoryExplorerOpen) {
        // Debounced refresh
        clearTimeout(window._invDebounce);
        window._invDebounce = setTimeout(refreshInventoryExplorer, 400);
    }
}

/**
 * Request server to parse current inventory content and display tree.
 */
async function refreshInventoryExplorer() {
    const content = document.getElementById('inventory').value;
    const treeEl = document.getElementById('explorer-tree');
    const countEl = document.getElementById('explorer-host-count');
    if (!treeEl) return;

    try {
        const response = await fetch('/inventories/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        const res = await response.json();
        if (res.success && res.data) {
            const data = res.data;
            if (countEl) countEl.textContent = data.total_hosts || 0;

            const groups = data.groups || {};
            const groupNames = Object.keys(groups);

            if (groupNames.length === 0) {
                treeEl.innerHTML = '<p class="empty-text">No hosts or groups detected</p>';
                return;
            }

            treeEl.innerHTML = groupNames.map(gname => {
                const group = groups[gname];
                const hosts = group.hosts || [];
                const vars = group.vars || {};
                const children = group.children || [];

                const hostsHtml = hosts.map(h => {
                    const hostName = typeof h === 'string' ? h : h.name;
                    const hvars = typeof h === 'object' && h.vars ? h.vars : {};
                    const varsStr = Object.keys(hvars).length > 0
                        ? Object.entries(hvars).map(([k, v]) => `${k}=${v}`).join(' ')
                        : '';

                    return `
                        <div class="tree-host-item">
                            🖥️ <strong>${escapeHtml(hostName)}</strong>
                            ${varsStr ? `<span class="tree-host-vars">[${escapeHtml(varsStr)}]</span>` : ''}
                        </div>
                    `;
                }).join('');

                const childrenHtml = children.length > 0
                    ? `<div class="tree-children"><em>Subgroups:</em> ${children.join(', ')}</div>`
                    : '';

                return `
                    <div class="tree-group">
                        <div class="tree-group-name">📁 [${escapeHtml(gname)}] (${hosts.length} hosts)</div>
                        ${childrenHtml}
                        <div class="tree-hosts-list">
                            ${hostsHtml || '<span class="tree-host-vars">(no direct hosts)</span>'}
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        console.error('Failed to parse inventory:', e);
    }
}

/**
 * Migrate legacy inventories from localStorage to server on initial load.
 */
async function migrateLocalStorageInventories() {
    const raw = localStorage.getItem('ekumen_inventories');
    if (!raw) return;

    try {
        const localInventories = JSON.parse(raw);
        const names = Object.keys(localInventories);
        if (names.length === 0) return;

        for (const name of names) {
            const content = localInventories[name];
            if (content && typeof content === 'string') {
                await fetch('/inventories', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, content })
                });
            }
        }
        localStorage.removeItem('ekumen_inventories');
    } catch (e) {
        console.warn('Could not migrate legacy local inventories:', e);
    }
}

/**
 * Fetch and render saved inventories from the server.
 */
async function renderInventoryDropdown() {
    const select = document.getElementById('inventory-select');
    const deleteBtn = document.getElementById('delete-inventory-btn');

    if (!select) return;

    try {
        const response = await fetch('/inventories');
        const data = await response.json();
        const inventories = data.inventories || [];

        select.innerHTML = '<option value="">📂 Load saved...</option>';
        inventories.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        });

        if (currentSelectedInventory && inventories.includes(currentSelectedInventory)) {
            select.value = currentSelectedInventory;
            if (deleteBtn) deleteBtn.style.display = 'inline-block';
        } else {
            currentSelectedInventory = null;
            if (deleteBtn) deleteBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to load inventories from server:', error);
    }
}

/**
 * Load selected inventory content from server into textarea.
 */
async function loadInventoryFromSelect() {
    const select = document.getElementById('inventory-select');
    const deleteBtn = document.getElementById('delete-inventory-btn');
    const name = select.value;

    if (!name) {
        currentSelectedInventory = null;
        if (deleteBtn) deleteBtn.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/inventories/${encodeURIComponent(name)}`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('inventory').value = data.content;
            currentSelectedInventory = data.name;
            if (deleteBtn) deleteBtn.style.display = 'inline-block';
            showToast(`Loaded inventory: ${data.name}`, 'success');
            if (inventoryExplorerOpen) refreshInventoryExplorer();
        } else {
            showToast('Failed to load inventory: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to load inventory: ' + error.message, 'error');
    }
}

/**
 * Save current inventory textarea content to server.
 */
async function saveCurrentInventory() {
    const content = document.getElementById('inventory').value.trim();
    if (!content) {
        showToast('Inventory is empty', 'error');
        return;
    }

    const defaultName = currentSelectedInventory ? currentSelectedInventory.replace(/\.(ini|yaml|yml|hosts|txt)$/i, '') : '';
    const name = prompt('Enter inventory name:', defaultName);
    if (!name || !name.trim()) return;

    try {
        const response = await fetch('/inventories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim(), content })
        });

        const data = await response.json();

        if (data.success) {
            currentSelectedInventory = data.name;
            await renderInventoryDropdown();
            showToast(`Saved inventory: ${data.name}`, 'success');
        } else {
            showToast('Failed to save inventory: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to save inventory: ' + error.message, 'error');
    }
}

/**
 * Delete currently selected inventory from server.
 */
async function deleteCurrentInventory() {
    if (!currentSelectedInventory) return;
    if (!confirm(`Delete inventory "${currentSelectedInventory}"?`)) return;

    try {
        const response = await fetch(`/inventories/${encodeURIComponent(currentSelectedInventory)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Deleted inventory: ${currentSelectedInventory}`, 'success');
            currentSelectedInventory = null;
            document.getElementById('inventory-select').value = '';
            const deleteBtn = document.getElementById('delete-inventory-btn');
            if (deleteBtn) deleteBtn.style.display = 'none';
            await renderInventoryDropdown();
            if (inventoryExplorerOpen) refreshInventoryExplorer();
        } else {
            showToast('Failed to delete inventory: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to delete inventory: ' + error.message, 'error');
    }
}

// ====================================================
// Live Connectivity & Fact Discovery Functions
// ====================================================

let lastFetchedFactsJson = '';

/**
 * Execute ping connectivity test against all inventory hosts.
 */
async function testHostConnectivity() {
    const pingBtn = document.getElementById('ping-hosts-btn');
    const panel = document.getElementById('connectivity-panel');
    const grid = document.getElementById('connectivity-hosts-grid');
    const connTotal = document.getElementById('conn-total');
    const connOnline = document.getElementById('conn-online');
    const connOffline = document.getElementById('conn-offline');
    const connLatency = document.getElementById('conn-latency');

    const inventoryVal = document.getElementById('inventory').value.trim();
    if (!inventoryVal) {
        showToast('Please specify hosts in Inventory to test connectivity', 'error');
        return;
    }

    if (pingBtn) {
        pingBtn.disabled = true;
        pingBtn.innerHTML = '⏳ Testing...';
    }

    panel.classList.remove('hidden');
    grid.innerHTML = '<div class="loading-text" style="grid-column: 1/-1;">⚡ Pinging hosts concurrently...</div>';

    const payload = {
        inventory: inventoryVal,
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value,
        private_key: document.getElementById('private-key').value.trim()
    };

    try {
        const response = await fetch('/connectivity/ping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success && data.summary) {
            const sum = data.summary;
            if (connTotal) connTotal.textContent = `Total: ${sum.total}`;
            if (connOnline) connOnline.textContent = `🟢 ${sum.online + sum.slow} Online`;
            if (connOffline) connOffline.textContent = `🔴 ${sum.offline} Offline`;
            if (connLatency) connLatency.textContent = `⏱️ ${sum.avg_latency_ms}ms avg`;

            const hosts = data.hosts || {};
            const hostList = Object.keys(hosts);

            if (hostList.length === 0) {
                grid.innerHTML = '<p class="empty-text">No hosts responded</p>';
                return;
            }

            grid.innerHTML = hostList.map(hname => {
                const hdata = hosts[hname];
                const isOnline = hdata.status === 'online' || hdata.status === 'slow';
                const cardClass = hdata.status === 'online' ? 'conn-online' :
                    (hdata.status === 'slow' ? 'conn-slow' : 'conn-offline');
                const pillClass = hdata.status === 'online' ? 'pill-online' :
                    (hdata.status === 'slow' ? 'pill-slow' : 'pill-offline');
                const pillText = hdata.status === 'online' ? '🟢 Online' :
                    (hdata.status === 'slow' ? '🟡 Slow' : '🔴 Unreachable');

                const latencyStr = hdata.latency_ms > 0 ? `${hdata.latency_ms}ms` : (hdata.error || 'Timed out');

                return `
                    <div class="host-conn-card ${cardClass}">
                        <div class="host-conn-top">
                            <span class="host-conn-name" title="${escapeHtml(hname)}">🖥️ ${escapeHtml(hname)}</span>
                            <span class="host-conn-status-pill ${pillClass}">${pillText}</span>
                        </div>
                        <div class="host-conn-meta">
                            <span title="${escapeHtml(hdata.error || '')}">${escapeHtml(latencyStr)}</span>
                            ${isOnline ? `<button class="host-facts-btn" onclick="showHostFacts('${escapeHtml(hname)}')">🔍 Facts</button>` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            showToast(`Connectivity test complete (${sum.online + sum.slow}/${sum.total} online)`, 'info');
        } else {
            showToast('Ping failed: ' + (data.error || 'Unknown error'), 'error');
            grid.innerHTML = `<p class="error-text">${escapeHtml(data.error || 'Failed to ping hosts')}</p>`;
        }
    } catch (e) {
        showToast('Connectivity test error: ' + e.message, 'error');
        grid.innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
    } finally {
        if (pingBtn) {
            pingBtn.disabled = false;
            pingBtn.innerHTML = '⚡ Ping';
        }
    }
}

/**
 * Open host facts preview modal and fetch facts via Ansible setup module.
 */
async function showHostFacts(hostname) {
    const modal = document.getElementById('host-facts-modal');
    const hostTitle = document.getElementById('facts-modal-host');
    const osBadge = document.getElementById('facts-modal-os-badge');
    const loadingEl = document.getElementById('facts-loading');
    const contentEl = document.getElementById('facts-content');

    if (!modal) return;

    modal.classList.remove('hidden');
    hostTitle.textContent = `🖥️ ${hostname}`;
    osBadge.textContent = 'Gathering facts...';
    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');

    const payload = {
        host: hostname,
        inventory: document.getElementById('inventory').value.trim(),
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value,
        private_key: document.getElementById('private-key').value.trim()
    };

    try {
        const response = await fetch('/connectivity/facts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success && data.facts) {
            const facts = data.facts;
            osBadge.textContent = facts.os_name || 'Linux';

            // Fill spec values
            document.getElementById('spec-os').textContent = facts.os_name || '-';
            document.getElementById('spec-kernel').textContent = facts.kernel || '-';
            document.getElementById('spec-cpu').textContent = `${facts.cpus || 1} vCPUs`;
            document.getElementById('spec-arch').textContent = facts.architecture || '-';

            // Memory
            if (facts.memory) {
                const mem = facts.memory;
                document.getElementById('spec-mem-text').textContent =
                    `${mem.used_mb} MB / ${mem.total_mb} MB (${mem.used_pct}%)`;
                document.getElementById('spec-mem-fill').style.width = `${Math.min(100, mem.used_pct)}%`;
            }

            // Network
            if (facts.network) {
                const net = facts.network;
                document.getElementById('spec-ip').textContent = net.ip || '-';
                document.getElementById('spec-net-if').textContent = net.interface || '-';
                document.getElementById('spec-mac').textContent = net.mac || '-';
                document.getElementById('spec-gw').textContent = net.gateway || '-';
            }

            // Storage Mounts
            const mountsList = document.getElementById('storage-mounts-list');
            if (mountsList) {
                const mounts = facts.mounts || [];
                if (mounts.length === 0) {
                    mountsList.innerHTML = '<span class="text-muted">No partition facts available</span>';
                } else {
                    mountsList.innerHTML = mounts.map(m => `
                        <div class="mount-item">
                            <span><strong>${escapeHtml(m.mount)}</strong> (${m.fstype})</span>
                            <span>${m.used_gb} GB / ${m.total_gb} GB (${m.used_pct}%)</span>
                        </div>
                    `).join('');
                }
            }

            // Raw JSON
            lastFetchedFactsJson = JSON.stringify(data.raw || facts, null, 2);
            document.getElementById('raw-facts-json').textContent = lastFetchedFactsJson;

            loadingEl.classList.add('hidden');
            contentEl.classList.remove('hidden');
        } else {
            loadingEl.textContent = '❌ Failed: ' + (data.error || 'Could not retrieve facts');
        }
    } catch (e) {
        loadingEl.textContent = '❌ Error: ' + e.message;
    }
}

/**
 * Close host facts modal.
 */
function closeHostFactsModal() {
    const modal = document.getElementById('host-facts-modal');
    if (modal) modal.classList.add('hidden');
}

/**
 * Copy raw facts JSON to clipboard.
 */
function copyRawFacts() {
    if (!lastFetchedFactsJson) return;
    navigator.clipboard.writeText(lastFetchedFactsJson).then(() => {
        showToast('Raw facts JSON copied to clipboard', 'success');
    });
}

