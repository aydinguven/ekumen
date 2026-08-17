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
