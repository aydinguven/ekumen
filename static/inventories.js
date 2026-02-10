/* Ekumen - Inventory Management (localStorage) */

const INVENTORY_KEY = 'ekumen_inventories';
let currentSelectedInventory = null;

function getInventories() {
    const raw = localStorage.getItem(INVENTORY_KEY);
    return raw ? JSON.parse(raw) : {};
}

function saveInventories(inventories) {
    localStorage.setItem(INVENTORY_KEY, JSON.stringify(inventories));
}

function renderInventoryDropdown() {
    const select = document.getElementById('inventory-select');
    const deleteBtn = document.getElementById('delete-inventory-btn');
    const inventories = getInventories();
    const names = Object.keys(inventories).sort();

    // Keep first option, rebuild rest
    select.innerHTML = '<option value="">📂 Load saved...</option>';
    names.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
    });

    // Show/hide delete button based on selection
    if (currentSelectedInventory && inventories[currentSelectedInventory]) {
        select.value = currentSelectedInventory;
        deleteBtn.style.display = 'inline-block';
    } else {
        currentSelectedInventory = null;
        deleteBtn.style.display = 'none';
    }
}

function loadInventoryFromSelect() {
    const select = document.getElementById('inventory-select');
    const deleteBtn = document.getElementById('delete-inventory-btn');
    const name = select.value;

    if (!name) {
        currentSelectedInventory = null;
        deleteBtn.style.display = 'none';
        return;
    }

    const inventories = getInventories();
    if (inventories[name]) {
        document.getElementById('inventory').value = inventories[name];
        currentSelectedInventory = name;
        deleteBtn.style.display = 'inline-block';
        showToast(`Loaded: ${name}`, 'success');
    }
}

function saveCurrentInventory() {
    const content = document.getElementById('inventory').value.trim();
    if (!content) {
        showToast('Inventory is empty', 'error');
        return;
    }

    const defaultName = currentSelectedInventory || '';
    const name = prompt('Enter inventory name:', defaultName);
    if (!name || !name.trim()) return;

    const inventories = getInventories();
    inventories[name.trim()] = content;
    saveInventories(inventories);

    currentSelectedInventory = name.trim();
    renderInventoryDropdown();
    showToast(`Saved: ${name.trim()}`, 'success');
}

function deleteCurrentInventory() {
    if (!currentSelectedInventory) return;
    if (!confirm(`Delete inventory "${currentSelectedInventory}"?`)) return;

    const inventories = getInventories();
    delete inventories[currentSelectedInventory];
    saveInventories(inventories);

    currentSelectedInventory = null;
    document.getElementById('inventory-select').value = '';
    document.getElementById('delete-inventory-btn').style.display = 'none';
    renderInventoryDropdown();
    showToast('Inventory deleted', 'success');
}
