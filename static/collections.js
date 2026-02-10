/* Ekumen - Collections & Roles Management */

let collectionsData = [];
let rolesData = [];
let currentDetailItem = null;
let currentDetailType = null;
let galaxyAvailable = false;

async function loadCollectionsAndRoles() {
    await Promise.all([loadCollections(), loadRoles()]);
}

async function loadCollections() {
    const listEl = document.getElementById('collections-list');
    const countEl = document.getElementById('collections-count');

    try {
        const response = await fetch('/collections');
        const data = await response.json();

        collectionsData = data.collections || [];
        galaxyAvailable = data.galaxy_available;
        countEl.textContent = collectionsData.length;

        if (collectionsData.length === 0) {
            listEl.innerHTML = '<p class="empty-text">No collections installed</p>';
            return;
        }

        listEl.innerHTML = collectionsData.map(c => `
            <div class="resource-item" onclick="showCollectionDetail('${c.fqcn}')">
                <div class="resource-item-header">
                    <span class="resource-name">${c.fqcn}</span>
                    <span class="resource-version">${c.version}</span>
                </div>
                <div class="resource-item-meta">
                    ${c.modules.length} modules
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load collections:', error);
        listEl.innerHTML = '<p class="error-text">Failed to load</p>';
    }
}

async function loadRoles() {
    const listEl = document.getElementById('roles-list');
    const countEl = document.getElementById('roles-count');

    try {
        const response = await fetch('/roles');
        const data = await response.json();

        rolesData = data.roles || [];
        countEl.textContent = rolesData.length;

        if (rolesData.length === 0) {
            listEl.innerHTML = '<p class="empty-text">No roles installed</p>';
            return;
        }

        listEl.innerHTML = rolesData.map(r => `
            <div class="resource-item" onclick="showRoleDetail('${r.name}')">
                <div class="resource-item-header">
                    <span class="resource-name">${r.name}</span>
                    <span class="resource-version">${r.version}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load roles:', error);
        listEl.innerHTML = '<p class="error-text">Failed to load</p>';
    }
}

function toggleResourceSection(section) {
    const listEl = document.getElementById(`${section}-list`);
    const chevron = document.getElementById(`${section}-chevron`);

    listEl.classList.toggle('collapsed');
    chevron.textContent = listEl.classList.contains('collapsed') ? '▶' : '▼';
}

// ========== INSTALL MODAL ==========

function openInstallModal() {
    if (!galaxyAvailable) {
        showToast('ansible-galaxy is not installed', 'error');
        return;
    }
    document.getElementById('install-modal').classList.remove('hidden');
    document.getElementById('install-name').focus();
}

function closeInstallModal() {
    document.getElementById('install-modal').classList.add('hidden');
    document.getElementById('install-name').value = '';
    document.getElementById('install-version').value = '';
    document.getElementById('install-force').checked = false;
}

async function performInstall() {
    const type = document.querySelector('input[name="install-type"]:checked').value;
    const name = document.getElementById('install-name').value.trim();
    const version = document.getElementById('install-version').value.trim();
    const force = document.getElementById('install-force').checked;

    if (!name) {
        showToast('Please enter a name', 'error');
        return;
    }

    const installBtn = document.getElementById('install-btn');
    installBtn.disabled = true;
    installBtn.innerHTML = '<span class="icon">⏳</span> Installing...';

    try {
        const endpoint = type === 'collection' ? '/collections' : '/roles';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, version: version || null, force })
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Installed: ${name}`, 'success');
            closeInstallModal();
            loadCollectionsAndRoles();
        } else {
            showToast(`Failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        installBtn.disabled = false;
        installBtn.innerHTML = '<span class="icon">📥</span> Install';
    }
}

// ========== DETAIL MODAL ==========

function showCollectionDetail(fqcn) {
    const collection = collectionsData.find(c => c.fqcn === fqcn);
    if (!collection) return;

    currentDetailItem = collection;
    currentDetailType = 'collection';

    document.getElementById('detail-title').textContent = collection.fqcn;

    const modulesHtml = collection.modules.length > 0
        ? `<div class="modules-grid">${collection.modules.map(m => `
            <span class="module-tag" title="Copy FQCN" onclick="copyFqcn('${collection.fqcn}.${m}', event)">${m}</span>
        `).join('')}</div>`
        : '<p class="empty-text">No modules found</p>';

    document.getElementById('detail-body').innerHTML = `
        <div class="detail-info">
            <div class="detail-row">
                <span class="detail-label">Version:</span>
                <span class="detail-value">${collection.version}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Path:</span>
                <span class="detail-value path">${collection.path}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">FQCN:</span>
                <span class="detail-value fqcn-copy" onclick="copyFqcn('${collection.fqcn}', event)">${collection.fqcn} 📋</span>
            </div>
        </div>
        <div class="modules-section">
            <h4>📋 Modules (${collection.modules.length})</h4>
            ${modulesHtml}
        </div>
    `;

    document.getElementById('detail-modal').classList.remove('hidden');
}

function showRoleDetail(name) {
    const role = rolesData.find(r => r.name === name);
    if (!role) return;

    currentDetailItem = role;
    currentDetailType = 'role';

    document.getElementById('detail-title').textContent = role.name;
    document.getElementById('detail-body').innerHTML = `
        <div class="detail-info">
            <div class="detail-row">
                <span class="detail-label">Version:</span>
                <span class="detail-value">${role.version}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Path:</span>
                <span class="detail-value path">${role.path}</span>
            </div>
        </div>
    `;

    document.getElementById('detail-modal').classList.remove('hidden');
}

function closeDetailModal() {
    document.getElementById('detail-modal').classList.add('hidden');
    currentDetailItem = null;
    currentDetailType = null;
}

async function deleteCurrentItem() {
    if (!currentDetailItem || !currentDetailType) return;

    const itemName = currentDetailType === 'collection' ? currentDetailItem.fqcn : currentDetailItem.name;

    if (!confirm(`Delete ${currentDetailType} "${itemName}"?`)) return;

    const deleteBtn = document.getElementById('detail-delete-btn');
    deleteBtn.disabled = true;
    deleteBtn.textContent = '⏳ Deleting...';

    try {
        const endpoint = currentDetailType === 'collection'
            ? `/collections/${encodeURIComponent(itemName)}`
            : `/roles/${encodeURIComponent(itemName)}`;

        const response = await fetch(endpoint, { method: 'DELETE' });
        const result = await response.json();

        if (result.success) {
            showToast(`Deleted: ${itemName}`, 'success');
            closeDetailModal();
            loadCollectionsAndRoles();
        } else {
            showToast(`Failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        deleteBtn.disabled = false;
        deleteBtn.textContent = '🗑️ Delete';
    }
}

function copyFqcn(text, event) {
    event.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied: ${text}`, 'success');
    }).catch(() => {
        showToast('Failed to copy', 'error');
    });
}

// ========== EXPORT / IMPORT REQUIREMENTS ==========

function exportRequirements() {
    if (collectionsData.length === 0 && rolesData.length === 0) {
        showToast('Nothing to export', 'error');
        return;
    }
    // Trigger download
    window.location.href = '/requirements';
    showToast('Downloading requirements.yml', 'success');
}

function openImportModal() {
    if (!galaxyAvailable) {
        showToast('ansible-galaxy is not installed', 'error');
        return;
    }
    document.getElementById('import-modal').classList.remove('hidden');
    document.getElementById('import-content').focus();
}

function closeImportModal() {
    document.getElementById('import-modal').classList.add('hidden');
    document.getElementById('import-content').value = '';
    document.getElementById('import-force').checked = false;
}

async function performImport() {
    const content = document.getElementById('import-content').value.trim();
    const force = document.getElementById('import-force').checked;

    if (!content) {
        showToast('Please paste requirements.yml content', 'error');
        return;
    }

    const importBtn = document.getElementById('import-btn');
    importBtn.disabled = true;
    importBtn.innerHTML = '<span class="icon">⏳</span> Importing...';

    try {
        const response = await fetch('/requirements', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, force })
        });

        const result = await response.json();

        if (result.success) {
            const count = result.results?.length || 0;
            showToast(`Imported ${count} item(s) successfully`, 'success');
            closeImportModal();
            loadCollectionsAndRoles();
        } else {
            // Show partial results
            const succeeded = result.results?.filter(r => r.success).length || 0;
            const failed = result.results?.filter(r => !r.success).length || 0;

            if (succeeded > 0) {
                showToast(`Imported ${succeeded} item(s), ${failed} failed`, 'error');
                loadCollectionsAndRoles();
            } else {
                showToast(`Import failed: ${result.error}`, 'error');
            }
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        importBtn.disabled = false;
        importBtn.innerHTML = '<span class="icon">📥</span> Import All';
    }
}

function toggleCollectionsSidebar() {
    const sidebar = document.getElementById('collections-sidebar');
    const expandBtn = document.getElementById('collections-expand-btn');

    sidebar.classList.toggle('collapsed');
    const isCollapsed = sidebar.classList.contains('collapsed');

    expandBtn.classList.toggle('hidden', !isCollapsed);
    localStorage.setItem('collections_sidebar_collapsed', isCollapsed ? 'true' : 'false');
}
