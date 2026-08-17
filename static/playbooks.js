/* Ekumen - Playbook Library & Templates Management */

let currentLoadedPlaybook = null;

/**
 * Load list of built-in templates into dropdown.
 */
async function loadPlaybookTemplatesDropdown() {
    const select = document.getElementById('playbook-templates');
    if (!select) return;

    try {
        const response = await fetch('/templates');
        const data = await response.json();
        const templates = data.templates || [];

        select.innerHTML = '<option value="">📋 Templates...</option>';
        templates.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = `${t.icon || '📄'} ${t.name}`;
            opt.title = t.description || '';
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load playbook templates:', e);
    }
}

/**
 * Insert selected template into editor.
 */
async function loadPlaybookTemplate(templateId) {
    if (!templateId) return;

    try {
        const response = await fetch(`/templates/${encodeURIComponent(templateId)}`);
        const data = await response.json();

        if (data.success && data.template) {
            const content = data.template.content;
            const textarea = document.getElementById('playbook');
            if (textarea) textarea.value = content;
            if (playbookEditor) playbookEditor.setValue(content);

            showToast(`Loaded template: ${data.template.name}`, 'info');
            document.getElementById('playbook-templates').value = '';
        }
    } catch (e) {
        showToast('Failed to load template: ' + e.message, 'error');
    }
}

/**
 * Load list of saved playbooks into dropdown.
 */
async function loadPlaybookList() {
    const select = document.getElementById('playbook-library');
    if (!select) return;

    try {
        const response = await fetch('/playbooks');
        const data = await response.json();
        const playbooks = data.playbooks || [];

        select.innerHTML = '<option value="">📂 Load...</option>';

        playbooks.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        });

        if (currentLoadedPlaybook && playbooks.includes(currentLoadedPlaybook)) {
            select.value = currentLoadedPlaybook;
            const delBtn = document.getElementById('delete-playbook-btn');
            if (delBtn) delBtn.style.display = 'inline-block';
        }
    } catch (error) {
        console.error('Failed to load playbook list:', error);
    }
}

/**
 * Load selected playbook into editor.
 */
async function loadPlaybook(name) {
    const delBtn = document.getElementById('delete-playbook-btn');

    if (!name) {
        currentLoadedPlaybook = null;
        if (delBtn) delBtn.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`/playbooks/${encodeURIComponent(name)}`);
        const data = await response.json();

        if (data.success) {
            const content = data.content;
            const textarea = document.getElementById('playbook');
            if (textarea) textarea.value = content;

            if (playbookEditor) {
                playbookEditor.setValue(content);
            }
            currentLoadedPlaybook = data.name;
            if (delBtn) delBtn.style.display = 'inline-block';
            showToast(`Loaded playbook: ${data.name}`, 'success');
        } else {
            showToast('Failed to load playbook: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to load playbook: ' + error.message, 'error');
    }
}

/**
 * Save current playbook content to server.
 */
async function savePlaybook() {
    const content = playbookEditor ? playbookEditor.getValue() : document.getElementById('playbook').value;

    if (!content || !content.trim()) {
        showToast('Playbook content cannot be empty', 'error');
        return;
    }

    const defaultName = currentLoadedPlaybook ? currentLoadedPlaybook.replace(/\.(yml|yaml)$/i, '') : '';
    const name = prompt('Enter playbook name:', defaultName);

    if (!name || !name.trim()) return;

    try {
        const response = await fetch('/playbooks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim(), content })
        });

        const data = await response.json();

        if (data.success) {
            currentLoadedPlaybook = data.name;
            await loadPlaybookList();
            const select = document.getElementById('playbook-library');
            if (select) select.value = data.name;
            const delBtn = document.getElementById('delete-playbook-btn');
            if (delBtn) delBtn.style.display = 'inline-block';
            showToast(`Saved playbook: ${data.name}`, 'success');
        } else {
            showToast('Failed to save playbook: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to save playbook: ' + error.message, 'error');
    }
}

/**
 * Delete currently loaded playbook.
 */
async function deletePlaybook() {
    if (!currentLoadedPlaybook) return;

    if (!confirm(`Delete playbook "${currentLoadedPlaybook}"?`)) return;

    try {
        const response = await fetch(`/playbooks/${encodeURIComponent(currentLoadedPlaybook)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Deleted playbook: ${currentLoadedPlaybook}`, 'success');
            currentLoadedPlaybook = null;
            const select = document.getElementById('playbook-library');
            if (select) select.value = '';
            const delBtn = document.getElementById('delete-playbook-btn');
            if (delBtn) delBtn.style.display = 'none';
            await loadPlaybookList();
        } else {
            showToast('Failed to delete playbook: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('Failed to delete playbook: ' + error.message, 'error');
    }
}
