// TAB SWITCHER SCRIPT
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', function() {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    // Update localization tags/texts so language switching works with just-rendered elements
    if (window.setLanguageTags) window.setLanguageTags();
    if (window.updateLocalizedText) window.updateLocalizedText();
    });
});

// DYNAMIC FORM GENERATION SCRIPT
// -- DATA ARRAYS --
const weaponTemplates = [
    { label: "One-Handed Melee-Caster Weapon + Shield",     value: "one-hand-shield" },
    { label: "One-Handed Melee-Caster Weapon + Off-Hand",   value: "one-hand-offhand" },
    { label: "One-Handed Melee-Caster Weapon + One-Handed Melee-Caster Weapon", value: "one-hand-one-hand" },
    { label: "One-Handed Ranged Weapon + Off-Hand",       value: "ranged-offhand" },
    { label: "One-Handed Ranged Weapon + One-Handed Ranged Weapon",  value: "ranged-ranged" },
    { label: "Two-Handed Melee Weapon",              value: "two-hand-melee" },
    { label: "Two-Handed Ranged Weapon",              value: "two-hand-ranged" }
];

const resistances = [
    { label: "Fire",          name: "current-fire",      value: 40 },
    { label: "Cold",          name: "current-cold",      value: 40 },
    { label: "Lightning",     name: "current-lightning", value: 40 },
    { label: "Poison & Acid", name: "current-poison",    value: 40 },
    { label: "Pierce",        name: "current-pierce",    value: 40 },
    { label: "Bleeding",      name: "current-bleeding",  value: 40 },
    { label: "Vitality",      name: "current-vitality",  value: 40 },
    { label: "Aether",        name: "current-aether",    value: 40 },
    { label: "Chaos",         name: "current-chaos",     value: 40 }
];

const targetResistances = [
    { label: "Fire",          name: "target-fire",      value: 80 },
    { label: "Cold",          name: "target-cold",      value: 80 },
    { label: "Lightning",     name: "target-lightning", value: 80 },
    { label: "Poison & Acid", name: "target-poison",    value: 80 },
    { label: "Pierce",        name: "target-pierce",    value: 80 },
    { label: "Bleeding",      name: "target-bleeding",  value: 80 },
    { label: "Vitality",      name: "target-vitality",  value: 80 },
    { label: "Aether",        name: "target-aether",    value: 80 },
    { label: "Chaos",         name: "target-chaos",     value: 80 }
];

const componentSlots = [
    { label: "Helm",      name: "component-head" },
    { label: "Chest",     name: "component-chest" },
    { label: "Shoulders", name: "component-shoulder" },
    { label: "Gloves",    name: "component-hand" },
    { label: "Boots",     name: "component-foot" },
    { label: "Pants",     name: "component-legs" },
    { label: "Belt",      name: "component-belt" },
    { label: "Amulet",    name: "component-amulet" },
    { label: "Ring 1",    name: "component-ring1" },
    { label: "Ring 2",    name: "component-ring2" },
    { label: "Medal",     name: "component-medal" },
    { label: "Weapon",    name: "component-weapon" },
    { label: "Weapon2/Off-Hand/Shield", name: "component-offhand-shield" }
];
const augmentSlots = [
    { label: "Helm",      name: "augment-head" },
    { label: "Chest",     name: "augment-chest" },
    { label: "Shoulders", name: "augment-shoulder" },
    { label: "Gloves",    name: "augment-hand" },
    { label: "Boots",     name: "augment-foot" },
    { label: "Pants",     name: "augment-legs" },
    { label: "Belt",      name: "augment-belt" },
    { label: "Amulet",    name: "augment-amulet" },
    { label: "Ring 1",    name: "augment-ring1" },
    { label: "Ring 2",    name: "augment-ring2" },
    { label: "Medal",     name: "augment-medal" },
    { label: "Weapon",    name: "augment-weapon" },
    { label: "Weapon2/Off-Hand/Shield", name: "augment-offhand-shield" }
];

const factions = [
    { label: "Devil's Crossing", name: "standing-crossing",  },
    { label: "Rovers", name: "standing-rovers" },
    { label: "Homestead", name: "standing-homestead" },
    { label: "Kymon's Chosen", name: "standing-kymon" },
    { label: "Death's Vigil", name: "standing-order" },
    { label: "Black Legion", name: "standing-black-legion" },
    { label: "The Outcast", name: "standing-outcast" },
    { label: "Coven of Ugdenbog", name: "standing-coven" },
    { label: "Barrowholm", name: "standing-barrowholm" },
    { label: "Malmouth", name: "standing-malmouth" },
    { label: "Cult of Bysmiel", name: "standing-bysmiel" },
    { label: "Cult of Dreeg", name: "standing-dreeg" },
    { label: "Cult of Solael", name: "standing-solael" }
];
const factionOptions = [
    { value: "friendly",  label: "Friendly" },
    { value: "respected", label: "Respected" },
    { value: "honored",   label: "Honored" },
    { value: "revered",   label: "Revered" }
];

// -- RENDER FUNCTIONS --
function renderWeaponTemplate(templateArr, selectId, defaultValue) {
    const sel = document.getElementById(selectId);
    sel.innerHTML = '';
    templateArr.forEach(opt => {
    sel.innerHTML += `<option value="${opt.value}"${opt.value === defaultValue ? ' selected' : ''}>${opt.label}</option>`;
    });
}

function renderResistances(list, containerId) {
    const cont = document.getElementById(containerId);
    cont.innerHTML = '';
    list.forEach(r => {
    cont.innerHTML += `
        <div class="resistance-input">
        <label>${r.label}:</label>
        <input type="number" name="${r.name}" value="${r.value}" min="0" max="300">
        </div>
    `;
    });
}

function renderCheckboxGroup(list, containerId) {
    const cont = document.getElementById(containerId);
    cont.innerHTML = '';
    list.forEach(item => {
    cont.innerHTML += `
        <label><input type="checkbox" name="${item.name}">${item.label}</label>
    `;
    });
}

function renderFactionDropdowns(factions, options, containerId) {
    const cont = document.getElementById(containerId);
    cont.innerHTML = '';
    factions.forEach(fac => {
    let optionsHtml = options.map(opt =>
        `<option value="${opt.value}"${opt.value === 'revered' ? ' selected' : ''}>${opt.label}</option>`
    ).join('');
    cont.innerHTML += `
        <div class="dropdown-item">
        <label>${fac.label}</label>
        <select name="${fac.name}">
            ${optionsHtml}
        </select>
        </div>
    `;
    });
}

// Function to render multi-select options
function renderNameMultiSelect(list, selectId) {
    const sel = document.getElementById(selectId);
    sel.innerHTML = '';
    list.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        sel.appendChild(opt);
    });
}

// Store Choices instances for multi-selects
let componentChoices = null;
let augmentChoices = null;

function initItemChoices(selectId) {
    if (selectId === 'component-blacklist' && componentChoices) {
        componentChoices.destroy();
        componentChoices = null;
    }
    if (selectId === 'augment-blacklist' && augmentChoices) {
        augmentChoices.destroy();
        augmentChoices = null;
    }
    
    const instance = new Choices('#' + selectId, {
        removeItemButton: true,
        searchEnabled: true,
        placeholderValue: 'Type an item name...'
    });
    
    if (selectId === 'component-blacklist') {
        componentChoices = instance;
    } else if (selectId === 'augment-blacklist') {
        augmentChoices = instance;
    }
}

// Fetch and parse CSV to extract 'Item' column and populate the dropdown
function loadNamesFromCSV(url, selectId) {
    return fetch(url)
        .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.text();
        })
        .then(csvText => {
        const results = Papa.parse(csvText, { header: true, skipEmptyLines: true });
        const items = results.data.map(row => row.Item).filter(item => !!item);
        renderNameMultiSelect(items, selectId);
        initItemChoices(selectId);
        })
        .catch(error => {
        console.error('Failed to load or parse CSV:', error);
        // Still resolve so Promise.all won't block
        return Promise.resolve();
        });
}

// Save state to localStorage
function saveState() {
    const formData = {};

    // Save weapon template
    formData['template'] = document.getElementById('template').value;

    // Character level
    formData['char-level'] = document.getElementById('char-level').value;

    // Resistances inputs
    [...document.querySelectorAll('#resistances-section input[type="number"]')].forEach(input => {
    formData[input.name] = input.value;
    });
    [...document.querySelectorAll('#target-resistances-section input[type="number"]')].forEach(input => {
    formData[input.name] = input.value;
    });

    // Component & augment checkboxes
    [...document.querySelectorAll('#component-slots-section input[type="checkbox"]')].forEach(input => {
    formData[input.name] = input.checked;
    });
    [...document.querySelectorAll('#augment-slots-section input[type="checkbox"]')].forEach(input => {
    formData[input.name] = input.checked;
    });

    // Faction dropdowns
    [...document.querySelectorAll('#faction-dropdowns-section select')].forEach(select => {
    formData[select.name] = select.value;
    });

    // Save multi-selects via Choices instances
    formData['component_blacklist'] = componentChoices ? componentChoices.getValue(true) : [];
    formData['augment_blacklist'] = augmentChoices ? augmentChoices.getValue(true) : [];

    localStorage.setItem('grimDawnOptimizerForm', JSON.stringify(formData));
    // console.log('State saved to localStorage:', formData);
}

// Load state from localStorage, if available
function loadState() {
    const saved = localStorage.getItem('grimDawnOptimizerForm');
    if (!saved) return;
    const formData = JSON.parse(saved);

    // Restore weapon template
    if (formData['template'] !== undefined) {
    document.getElementById('template').value = formData['template'];
    }

    // Restore character level
    if (formData['char-level'] !== undefined) {
    document.getElementById('char-level').value = formData['char-level'];
    }

    // Restore resistances
    [...document.querySelectorAll('#resistances-section input[type="number"]')].forEach(input => {
    if (formData[input.name] !== undefined) input.value = formData[input.name];
    });
    [...document.querySelectorAll('#target-resistances-section input[type="number"]')].forEach(input => {
    if (formData[input.name] !== undefined) input.value = formData[input.name];
    });

    // Restore component slots checkboxes
    [...document.querySelectorAll('#component-slots-section input[type="checkbox"]')].forEach(input => {
    if (formData[input.name] !== undefined) input.checked = formData[input.name];
    });

    // Restore augment slots checkboxes
    [...document.querySelectorAll('#augment-slots-section input[type="checkbox"]')].forEach(input => {
    if (formData[input.name] !== undefined) input.checked = formData[input.name];
    });

    // Restore faction dropdowns
    [...document.querySelectorAll('#faction-dropdowns-section select')].forEach(select => {
    if (formData[select.name] !== undefined) select.value = formData[select.name];
    });

    // Restore blacklist multi-selects AFTER they are initialized
    if (componentChoices && Array.isArray(formData['component_blacklist'])) {
        componentChoices.setValue(formData['component_blacklist']);
    }
    if (augmentChoices && Array.isArray(formData['augment_blacklist'])) {
        augmentChoices.setValue(formData['augment_blacklist']);
    }
}

// -- Scroll position persistence --
// Object to store scroll positions per tab
const scrollPositions = {};

// Save scroll position for active tab before form submit
const savePageState = () => {
const activeTab = document.querySelector('.tab.active');
if (activeTab) {
    const tabName = activeTab.dataset.tab;
    scrollPositions[tabName] = window.scrollY;
    localStorage.setItem('scrollPositions', JSON.stringify(scrollPositions));
    localStorage.setItem('activeTab', tabName);
}
};

document.querySelector('form').addEventListener('submit', savePageState);

window.addEventListener('load', () => {
    const savedScrollPositions = JSON.parse(localStorage.getItem('scrollPositions') || '{}');
    const activeTab = localStorage.getItem('activeTab');

    if (activeTab) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        const tabToActivate = document.querySelector(`.tab[data-tab="${activeTab}"]`);
        const contentToActivate = document.getElementById(`tab-${activeTab}`);
        if (tabToActivate && contentToActivate) {
            tabToActivate.classList.add('active');
            contentToActivate.classList.add('active');
        }

    // Restore scroll for the active tab if saved
    if (savedScrollPositions[activeTab] !== undefined) {
        window.scrollTo(0, savedScrollPositions[activeTab]);
        }
    }

  // Clean up stored values
    localStorage.removeItem('activeTab');
    localStorage.removeItem('scrollPositions');
});

// Save scroll position on tab change
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', function() {
        // Save scroll of currently active tab before switching
        const currentActiveTab = document.querySelector('.tab.active');
        if (currentActiveTab) {
            scrollPositions[currentActiveTab.dataset.tab] = window.scrollY;
            localStorage.setItem('scrollPositions', JSON.stringify(scrollPositions));
        }
        // Save new active tab
        localStorage.setItem('activeTab', tab.dataset.tab);
    });
});

// INITIALIZATION
document.addEventListener('DOMContentLoaded', function() {
    renderWeaponTemplate(weaponTemplates, 'template', 'one-hand-shield');
    renderResistances(resistances, 'resistances-section');
    renderResistances(targetResistances, 'target-resistances-section');
    renderCheckboxGroup(componentSlots, 'component-slots-section');
    renderCheckboxGroup(augmentSlots, 'augment-slots-section');
    renderFactionDropdowns(factions, factionOptions, 'faction-dropdowns-section');

    // Load CSVs and initialize both multi-selects before loading the saved state
    Promise.all([
        loadNamesFromCSV('/data/component_data.csv', 'component-blacklist'),
        loadNamesFromCSV('/data/augment_data.csv', 'augment-blacklist')
    ]).then(() => {
        loadState();

        // Attach saveState event listeners after initialization and state restore
        document.getElementById('template').addEventListener('change', saveState);
        document.getElementById('char-level').addEventListener('input', saveState);

        document.querySelectorAll('#resistances-section input[type="number"], #target-resistances-section input[type="number"]').forEach(input => {
            input.addEventListener('input', saveState);
        });

        document.querySelectorAll('#component-slots-section input[type="checkbox"], #augment-slots-section input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', saveState);
        });

        document.querySelectorAll('#faction-dropdowns-section select').forEach(select => {
            select.addEventListener('change', saveState);
        });

        if (componentChoices)
            componentChoices.passedElement.element.addEventListener('change', saveState);
        if (augmentChoices)
            augmentChoices.passedElement.element.addEventListener('change', saveState);
    });

    if (window.setLanguageTags) window.setLanguageTags();
    if (window.updateLocalizedText) window.updateLocalizedText();
});
