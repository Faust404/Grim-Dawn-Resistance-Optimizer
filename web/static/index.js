// TAB SWITCHER SCRIPT
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', function () {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
});

// DYNAMIC FORM GENERATION SCRIPT
// -- DATA ARRAYS --
const weaponTemplates = [
    { label: "One-Handed Melee-Caster Weapon + Off-Hand", value: "one-hand-offhand" },
    { label: "One-Handed Melee-Caster Weapon + One-Handed Melee-Caster Weapon", value: "one-hand-one-hand" },
    { label: "One-Handed Melee-Caster Weapon + Shield", value: "one-hand-shield" },
    { label: "One-Handed Ranged Weapon + Off-Hand", value: "ranged-offhand" },
    { label: "One-Handed Ranged Weapon + One-Handed Ranged Weapon", value: "ranged-ranged" },
    { label: "One-Handed Ranged Weapon + Shield", value: "ranged-shield" },
    { label: "Two-Handed Melee Weapon", value: "two-hand-melee" },
    { label: "Two-Handed Ranged Weapon", value: "two-hand-ranged" }
];

const resistances = [
    { label: "Fire", name: "current-fire", value: 40 },
    { label: "Cold", name: "current-cold", value: 40 },
    { label: "Lightning", name: "current-lightning", value: 40 },
    { label: "Poison & Acid", name: "current-poison", value: 40 },
    { label: "Pierce", name: "current-pierce", value: 40 },
    { label: "Bleeding", name: "current-bleeding", value: 40 },
    { label: "Vitality", name: "current-vitality", value: 40 },
    { label: "Aether", name: "current-aether", value: 40 },
    { label: "Chaos", name: "current-chaos", value: 40 }
];

const targetResistances = [
    { label: "Fire", name: "target-fire", value: 80 },
    { label: "Cold", name: "target-cold", value: 80 },
    { label: "Lightning", name: "target-lightning", value: 80 },
    { label: "Poison & Acid", name: "target-poison", value: 80 },
    { label: "Pierce", name: "target-pierce", value: 80 },
    { label: "Bleeding", name: "target-bleeding", value: 80 },
    { label: "Vitality", name: "target-vitality", value: 80 },
    { label: "Aether", name: "target-aether", value: 80 },
    { label: "Chaos", name: "target-chaos", value: 80 }
];

const componentSlots = [
    { label: "Helm", name: "component-head" },
    { label: "Chest", name: "component-chest" },
    { label: "Shoulders", name: "component-shoulder" },
    { label: "Gloves", name: "component-hand" },
    { label: "Boots", name: "component-foot" },
    { label: "Pants", name: "component-legs" },
    { label: "Belt", name: "component-belt" },
    { label: "Amulet", name: "component-amulet" },
    { label: "Ring 1", name: "component-ring1" },
    { label: "Ring 2", name: "component-ring2" },
    { label: "Medal", name: "component-medal" },
    { label: "Weapon", name: "component-weapon" },
    { label: "Weapon2/Off-Hand/Shield", name: "component-offhand-shield" }
];

const augmentSlots = [
    { label: "Helm", name: "augment-head" },
    { label: "Chest", name: "augment-chest" },
    { label: "Shoulders", name: "augment-shoulder" },
    { label: "Gloves", name: "augment-hand" },
    { label: "Boots", name: "augment-foot" },
    { label: "Pants", name: "augment-legs" },
    { label: "Belt", name: "augment-belt" },
    { label: "Amulet", name: "augment-amulet" },
    { label: "Ring 1", name: "augment-ring1" },
    { label: "Ring 2", name: "augment-ring2" },
    { label: "Medal", name: "augment-medal" },
    { label: "Weapon", name: "augment-weapon" },
    { label: "Weapon2/Off-Hand/Shield", name: "augment-offhand-shield" }
];

const factions = [
    { label: "Devil's Crossing", name: "standing-crossing" },
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
    { label: "Cult of Solael", name: "standing-solael" },
    { label: "Kurn", name: "standing-kurn" }
];

const factionOptions = [
    { value: "friendly", label: "Friendly" },
    { value: "respected", label: "Respected" },
    { value: "honored", label: "Honored" },
    { value: "revered", label: "Revered" }
];

const secondaryStats = [
    { label: "ADCTH% (Attack Damage Converted to Health)", name: "stat-adcth" },
    { label: "Armor", name: "stat-armor" },
    { label: "Attack Speed%", name: "stat-attack-speed" },
    { label: "Cast Speed%", name: "stat-cast-speed" },
    { label: "Defensive Ability", name: "stat-da" },
    { label: "Health", name: "stat-health" },
    { label: "Move Speed%", name: "stat-move-speed" },
    { label: "Offensive Ability", name: "stat-oa" }
];

// Secondary resists: pure % stats whose CSV column value IS the percent gain.
// Alphabetical by label (they render below the secondary stats with a gap).
const secondaryResists = [
    { label: "Energy Leech Resistance", name: "stat-res-energy-leech" },
    { label: "Entrapment Resistance", name: "stat-res-entrapment" },
    { label: "Freeze Resistance", name: "stat-res-freeze" },
    { label: "Life Leech Resistance", name: "stat-res-life-leech" },
    { label: "Petrify Resistance", name: "stat-res-petrify" },
    { label: "Reflect Resistance", name: "stat-res-reflect" },
    { label: "Skill Disruption Protection", name: "stat-res-disruption" },
    { label: "Slow Resistance", name: "stat-res-slow" },
    { label: "Stun Resistance", name: "stat-res-stun" }
];

// Every stat the panel can optimize; both sub-sections share the priority
// controls, bulk "Set all" links, save/restore, and Reset All.
const allSecondaryStats = secondaryStats.concat(secondaryResists);

const STAT_PRIORITY_OPTIONS = ["ignore", "nice", "priority"];

// Current priority selection per stat, e.g. { "stat-oa": "priority", ... }
const statPriorities = {};
allSecondaryStats.forEach(s => { statPriorities[s.name] = "ignore"; });

function prioControlHtml(name) {
    const current = statPriorities[name];
    return `<div class="prio" data-key="${name}">` +
        STAT_PRIORITY_OPTIONS.map(v => {
            const label = v === "nice" ? "Nice to Have" : v.charAt(0).toUpperCase() + v.slice(1);
            return `<button type="button" data-v="${v}"${v === current ? ' class="on"' : ''}>${label}</button>`;
        }).join('') +
        `</div>`;
}

function prioRowHtml(s) {
    return `
        <div class="prow">
            <span class="plabel">${s.label}</span>
            ${prioControlHtml(s.name)}
            <input type="hidden" name="${s.name}" value="${statPriorities[s.name]}">
        </div>`;
}

function renderSecondaryStats() {
    const cont = document.getElementById('secondary-stats-section');
    if (!cont) return;
    cont.innerHTML = '';
    secondaryStats.forEach(s => { cont.innerHTML += prioRowHtml(s); });
    cont.innerHTML += '<div class="stat-prio-divider"></div>';
    secondaryResists.forEach(s => { cont.innerHTML += prioRowHtml(s); });
    // Freshly created buttons/labels are untagged, so re-tag and re-translate them
    // (bulk "Set all", Reset All, and saved-state restore all go through this render).
    if (typeof setLanguageTags === 'function' && typeof updateWebLocalizedText === 'function') {
        setLanguageTags();
        updateWebLocalizedText();
    }
}

function initSecondaryStats() {
    const cont = document.getElementById('secondary-stats-section');
    if (!cont) return;

    // Toggle a single stat's priority (delegated so re-renders keep working)
    cont.addEventListener('click', (e) => {
        const btn = e.target.closest('.prio button');
        if (!btn) return;
        const name = btn.closest('.prio').dataset.key;
        statPriorities[name] = btn.dataset.v;
        [...btn.parentElement.children].forEach(x => x.classList.toggle('on', x === btn));
        cont.querySelector(`input[name="${name}"]`).value = statPriorities[name];
        saveState();
    });

    // Bulk "Set all" links
    document.querySelectorAll('.pbulk a[data-all]').forEach(a => {
        a.addEventListener('click', () => {
            const v = a.dataset.all;
            allSecondaryStats.forEach(s => { statPriorities[s.name] = v; });
            renderSecondaryStats();
            saveState();
        });
    });
}

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
        <input type="number" name="${r.name}" value="${r.value}" min="-200" max="200">
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

// Store Choices instances for multi-selects
let componentChoices = null;
let augmentChoices = null;

function initItemChoices(list, selectId) {
    if (selectId === 'component-blacklist' && componentChoices) {
        componentChoices.destroy();
        componentChoices = null;
    }
    if (selectId === 'augment-blacklist' && augmentChoices) {
        augmentChoices.destroy();
        augmentChoices = null;
    }
    //Initialize the selection box using the choices built-in method
    const choiceItems = list.map(obj => ({
        value: String(obj.item),
        label: String(obj.item),
        selected: false,
        customProperties: { tag: String(obj.tag || '') }
    }));

    const instance = new Choices('#' + selectId, {
        removeItemButton: true,
        searchEnabled: true,
        choices: choiceItems,
        placeholderValue: 'Type an item name...',
        allowHTML: true,
        //Customize generated styles and data
        callbackOnCreateTemplates: function (strToEl, escapeForTemplate, getClassNames) {
            return {
                //Selected part
                item: ({ classNames }, data) => {
                    const choice = choiceItems.find((item) => item.id === data.id);
                    const tag = choice?.customProperties?.tag || data.customProperties?.tag || '';
                    const label = data.label || '';
                    const value = data.value || '';
                    return strToEl(`
                <div
                    id="choices--${selectId}-choice-${data.id}"
                    class="${getClassNames(classNames.item).join(' ')} ${getClassNames(data.highlighted ? classNames.highlightedState : classNames.itemSelectable).join(' ')} ${data.placeholder ? classNames.placeholder : ''}"
                    data-item
                    data-id="${data.id}"
                    data-value="${value}"
                    ${data.active ? 'aria-selected="true"' : ''}
                    ${data.disabled ? 'aria-disabled="true"' : ''}
                    data-language-tag="${tag}"
                    data-language-Tag-And-Source-EN="${label}"
                >
                    ${label}
                    <button type="button" class="${getClassNames(classNames.button).join(' ')}" data-button>x</button>
                </div>
                `);
                },
                //To be selected
                choice: ({ classNames }, data) => {
                    const tag = data.customProperties?.tag || '';
                    const label = data.label || '';
                    const value = data.value || '';
                    return strToEl(`
                <div
                    id="choices--${selectId}-item-${data.id}"
                    class="${getClassNames(classNames.item).join(' ')} ${getClassNames(classNames.itemChoice).join(' ')} ${getClassNames(data.disabled ? classNames.itemDisabled : classNames.itemSelectable).join(' ')}"
                    data-select-text="${this.config.itemSelectText}"
                    data-choice
                    data-id="${data.id}"
                    data-value="${value}"
                    ${data.disabled ? 'data-choice-disabled aria-disabled="true"' : 'data-choice-selectable'}
                    data-language-tag="${tag}"
                    data-language-Tag-And-Source-EN="${label}"
                    ${data.groupId > 0 ? 'role="treeitem"' : 'role="option"'}
                >
                    ${label}
                </div>
                `);
                },
            };
        }
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
            const items = results.data
                .map(row => ({ item: row.Item, tag: row['Item Tag'] }))
                .filter(obj => !!obj.item);
            initItemChoices(items, selectId);
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
    formData['template'] = document.getElementById('template').value;
    formData['char-level'] = document.getElementById('char-level').value;
    formData['armor-abs-value'] = document.getElementById('armor-abs-value').value;

    [...document.querySelectorAll('#resistances-section input[type="number"], #target-resistances-section input[type="number"]')]
        .forEach(input => formData[input.name] = input.value === '' ? 0 : input.value);

    [...document.querySelectorAll('#component-slots-section input[type="checkbox"], #augment-slots-section input[type="checkbox"]')]
        .forEach(input => formData[input.name] = input.checked);

    [...document.querySelectorAll('#faction-dropdowns-section select')]
        .forEach(select => formData[select.name] = select.value);

    [...document.querySelectorAll('#secondary-stats-section input[type="hidden"]')]
        .forEach(input => formData[input.name] = input.value);

    formData['component_blacklist'] = componentChoices ? componentChoices.getValue(true) : [];
    formData['augment_blacklist'] = augmentChoices ? augmentChoices.getValue(true) : [];

    localStorage.setItem('grimDawnOptimizerForm', JSON.stringify(formData));
}

function loadState() {
    const saved = localStorage.getItem('grimDawnOptimizerForm');
    if (!saved) return;
    const formData = JSON.parse(saved);

    if (formData['template']) document.getElementById('template').value = formData['template'];
    if (formData['char-level']) document.getElementById('char-level').value = formData['char-level'];
    if (formData['armor-abs-value']) document.getElementById('armor-abs-value').value = formData['armor-abs-value'];

    [...document.querySelectorAll('#resistances-section input[type="number"], #target-resistances-section input[type="number"]')]
        .forEach(input => {
            if (formData[input.name] !== undefined) {
                input.value = formData[input.name] === '' ? 0 : formData[input.name];
            }
        });

    [...document.querySelectorAll('#component-slots-section input[type="checkbox"], #augment-slots-section input[type="checkbox"]')]
        .forEach(input => { if (formData[input.name] !== undefined) input.checked = formData[input.name]; });

    [...document.querySelectorAll('#faction-dropdowns-section select')]
        .forEach(select => { if (formData[select.name] !== undefined) select.value = formData[select.name]; });

    [...document.querySelectorAll('#secondary-stats-section input[type="hidden"]')]
        .forEach(input => {
            if (formData[input.name] !== undefined) statPriorities[input.name] = formData[input.name];
        });
    renderSecondaryStats();

    if (componentChoices && Array.isArray(formData['component_blacklist'])) {
        componentChoices.setChoiceByValue(formData['component_blacklist']);
    }
    if (augmentChoices && Array.isArray(formData['augment_blacklist'])) {
        augmentChoices.setChoiceByValue(formData['augment_blacklist']);
    }
}

// SAVE UPLOAD — backend keys -> UI names (parse_save -> form pre-fill)
const SAVE_SLOT_TO_UI = {
    head: 'head', chest: 'chest', shoulders: 'shoulder', hands: 'hand',
    feet: 'foot', legs: 'legs', waist: 'belt', amulet: 'amulet',
    ring1: 'ring1', ring2: 'ring2', medal: 'medal',
    mainhand: 'weapon', offhand: 'offhand-shield'   // relic: no UI slot
};
const SAVE_RESIST_TO_INPUT = {
    defensiveFire: 'current-fire', defensiveCold: 'current-cold',
    defensiveLightning: 'current-lightning', defensivePoison: 'current-poison',
    defensivePierce: 'current-pierce', defensiveBleeding: 'current-bleeding',
    defensiveLife: 'current-vitality',   // defensiveLife IS the vitality resist
    defensiveAether: 'current-aether', defensiveChaos: 'current-chaos'
};
// Explicit backend-name -> select map: the UI's display labels differ from the
// parser's names for three factions (Death's Vigil / Black Legion / Malmouth),
// so a label-based lookup would silently skip them.
const SAVE_FACTION_TO_SELECT = {
    "Devil's Crossing": 'standing-crossing',
    'Rovers': 'standing-rovers',
    'Homestead': 'standing-homestead',
    "Kymon's Chosen": 'standing-kymon',
    "Order of Death's Vigil": 'standing-order',
    'The Black Legion': 'standing-black-legion',
    'The Outcast': 'standing-outcast',
    'Coven of Ugdenbog': 'standing-coven',
    'Barrowholm': 'standing-barrowholm',
    'Malmouth Resistance': 'standing-malmouth',
    'Cult of Bysmiel': 'standing-bysmiel',
    'Cult of Dreeg': 'standing-dreeg',
    'Cult of Solael': 'standing-solael',
    'Kurn': 'standing-kurn'
};
const SAVE_TIER_OPTIONS = ['friendly', 'respected', 'honored', 'revered'];

function applySaveToForm(data) {
    const levelEl = document.getElementById('char-level');
    if (levelEl && data.level) levelEl.value = data.level;

    for (const [saveStat, inputName] of Object.entries(SAVE_RESIST_TO_INPUT)) {
        const input = document.querySelector(`#resistances-section input[name="${inputName}"]`);
        if (input && data.stats[saveStat] !== undefined)
            input.value = Number(data.stats[saveStat]) || 0;
    }

    // Armor absorption: the save carries the raw defensiveAbsorptionModifier
    // (% bonus on the 70% base), so the field shows 70 * (1 + mod/100),
    // clamped to the field's 50-100 range.
    const absEl = document.getElementById('armor-abs-value');
    if (absEl && data.stats.defensiveAbsorptionModifier !== undefined) {
        const pct = 70 * (1 + (Number(data.stats.defensiveAbsorptionModifier) || 0) / 100);
        absEl.value = Math.min(100, Math.max(50, Math.round(pct)));
    }

    for (const [facName, slug] of Object.entries(SAVE_FACTION_TO_SELECT)) {
        const tier = (data.factions[facName] || '').toLowerCase();
        // Hostile/Neutral standings have no dropdown option — default them to Friendly
        const sel = document.querySelector(`#faction-dropdowns-section select[name="${slug}"]`);
        if (!sel) continue;
        const value = SAVE_TIER_OPTIONS.includes(tier) ? tier : 'friendly';
        if ([...sel.options].some(o => o.value === value)) sel.value = value;
    }

    for (const [slot, ui] of Object.entries(SAVE_SLOT_TO_UI)) {
        const st = data.state[slot];
        if (!st) continue;
        const comp = document.querySelector(`#component-slots-section input[name="component-${ui}"]`);
        const aug = document.querySelector(`#augment-slots-section input[name="augment-${ui}"]`);
        if (comp) comp.checked = !st.comp;   // checked = blocked = slot not free
        if (aug) aug.checked = !st.aug;
    }
    saveState();   // persist like every other change on the page
}


// RESET ALL
function resetAllFields() {
    const form = document.querySelector('form');
    if (!form) return;

    form.reset();
    localStorage.removeItem('grimDawnOptimizerForm');
    localStorage.removeItem('activeTab');
    localStorage.removeItem('scrollPositions');

    // Clear the save-upload status banner (hidden while empty via :empty).
    // Drop the i18n tag too, or the next re-translation pass resurrects it.
    const uploadStatus = document.getElementById('upload-status');
    if (uploadStatus) {
        uploadStatus.textContent = '';
        uploadStatus.removeAttribute('data-language-Tag-And-Source-EN');
    }

    if (componentChoices) {
        componentChoices.removeActiveItems();
        componentChoices.clearInput();
    }

    if (augmentChoices) {
        augmentChoices.removeActiveItems();
        augmentChoices.clearInput();
    }

    document.querySelectorAll('#resistances-section input[type="number"], #target-resistances-section input[type="number"]').forEach(input => {
        input.value = input.defaultValue;
    });

    document.querySelectorAll('#component-slots-section input[type="checkbox"], #augment-slots-section input[type="checkbox"]').forEach(input => {
        input.checked = input.defaultChecked;
    });

    document.querySelectorAll('#faction-dropdowns-section select').forEach(select => {
        // Default to the last option, which is "Revered"
        select.selectedIndex = 3;
    });

    allSecondaryStats.forEach(s => { statPriorities[s.name] = "ignore"; });
    renderSecondaryStats();

    const resultsSection = document.getElementById('results-section');
    const finalResistancesSection = document.getElementById('final-resistances-section');
    const secondaryGainsSection = document.getElementById('secondary-gains-section');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
    if (finalResistancesSection) {
        finalResistancesSection.style.display = 'none';
    }
    if (secondaryGainsSection) {
        secondaryGainsSection.style.display = 'none';
    }

    const defaultTab = document.querySelector('.tab[data-tab="basic"]');
    const defaultContent = document.getElementById('tab-basic');
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    if (defaultTab && defaultContent) {
        defaultTab.classList.add('active');
        defaultContent.classList.add('active');
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
    tab.addEventListener('click', function () {
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
document.addEventListener('DOMContentLoaded', function () {
    renderWeaponTemplate(weaponTemplates, 'template', 'one-hand-shield');
    renderResistances(resistances, 'resistances-section');
    renderResistances(targetResistances, 'target-resistances-section');
    renderCheckboxGroup(componentSlots, 'component-slots-section');
    renderCheckboxGroup(augmentSlots, 'augment-slots-section');
    renderFactionDropdowns(factions, factionOptions, 'faction-dropdowns-section');
    renderSecondaryStats();
    initSecondaryStats();

    // Load CSVs and initialize both multi-selects before loading the saved state
    Promise.all([
        loadNamesFromCSV('/data/component_data.csv', 'component-blacklist'),
        loadNamesFromCSV('/data/augment_data.csv', 'augment-blacklist')
    ]).then(() => {
        loadState();

        //After executing the loading state, set the language
        const language = localStorage.getItem('language') || 'en';
        firstUpdateLanguage(language);

        //Listen for selection click events and handle the language display of enchantments and inlays separately
        const selectIds = ['component-blacklist', 'augment-blacklist'];
        selectIds.forEach(selectId => {
            const element = document.getElementById(selectId);
            if (element) {
                element.addEventListener('addItem', (event) => {
                    const language = localStorage.getItem('language') || 'en';
                    setTimeout(() => {
                        loadDBLanguageFilesAndUpdate(language);
                    }, 0);
                });
                element.addEventListener('removeItem', (event) => {
                    const language = localStorage.getItem('language') || 'en';
                    setTimeout(() => {
                        loadDBLanguageFilesAndUpdate(language);
                    }, 0);
                });
            } else {
                console.error(`Element with id "${selectId}" not found`);
            }
        });

        // Attach saveState event listeners after initialization and state restore
        document.getElementById('template').addEventListener('change', saveState);
        document.getElementById('char-level').addEventListener('input', saveState);
        document.getElementById('armor-abs-value').addEventListener('input', saveState);

        document.querySelectorAll('#resistances-section input[type="number"], #target-resistances-section input[type="number"]').forEach(input => {
            input.addEventListener('input', saveState);
        });

        document.querySelectorAll('#component-slots-section input[type="checkbox"], #augment-slots-section input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', saveState);
        });

        document.querySelectorAll('#faction-dropdowns-section select').forEach(select => {
            select.addEventListener('change', saveState);
        });

        // Add event listener for the target master input to update all target resistances
        const targetMasterSelect = document.getElementById('target-master-select');
        if (targetMasterSelect) {
            targetMasterSelect.addEventListener('input', (event) => {
                const value = event.target.value;
                if (value === '') return;
                document.querySelectorAll('#target-resistances-section input[type="number"]').forEach(input => {
                    input.value = value;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                });
                saveState();
            });
        }

        // Add event listener for the master faction select to update all faction dropdowns
        const factionMasterSelect = document.getElementById('faction-master-select');
        if (factionMasterSelect) {
            factionMasterSelect.addEventListener('change', (event) => {
                const value = event.target.value;
                if (!value) return;
                document.querySelectorAll('#faction-dropdowns-section select').forEach(select => {
                    if ([...select.options].some(opt => opt.value === value)) {
                        select.value = value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            });
        }

        if (componentChoices)
            componentChoices.passedElement.element.addEventListener('change', saveState);
        if (augmentChoices)
            augmentChoices.passedElement.element.addEventListener('change', saveState);

        const resetBtn = document.getElementById('reset-all-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetAllFields);
        } else {
            console.error('Reset All button not found');
        }

        // UPLOAD SAVE — read player.gdc, pre-fill the whole form from it
        const uploadBtn = document.getElementById('upload-save-btn');
        const fileInput = document.getElementById('save-file-input');
        const statusEl = document.getElementById('upload-status');

        function setUploadStatus(text, isError) {
            if (!statusEl) return;
            statusEl.textContent = text;
            statusEl.style.color = isError ? '#ff6b6b' : '#8fd47e';
            statusEl.setAttribute('data-language-Tag-And-Source-EN', text);
            if (typeof updateWebLocalizedText === 'function') updateWebLocalizedText();
        }

        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', () => {
                const file = fileInput.files[0];
                if (!file) return;
                const fd = new FormData();
                fd.append('save_file', file);
                fileInput.value = '';   // allow re-selecting the same file
                setUploadStatus('Uploading save...', false);
                fetch('/upload-save', { method: 'POST', body: fd })
                    .then(resp => resp.json().catch(() => ({})).then(body => ({ resp, body })))
                    .then(({ resp, body }) => {
                        if (!resp.ok) {
                            throw new Error(body.error || ('Upload failed (' + resp.status + ')'));
                        }
                        applySaveToForm(body);
                        setUploadStatus(
                            `Imported ${body.character} (Lv ${body.level}) — ${body.summary.free_comp} comp / ${body.summary.free_aug} aug slots free`,
                            false
                        );
                    })
                    .catch(err => setUploadStatus(err.message, true));
            });
        } else {
            console.error('Upload Save elements not found');
        }
    });
});
