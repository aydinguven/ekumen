/* Ekumen - Playbook Library Management */

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
