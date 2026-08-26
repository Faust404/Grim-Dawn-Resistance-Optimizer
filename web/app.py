import os
import sys

from flask import Flask, jsonify, render_template, request, send_from_directory

sys.path.append(".")  # Adjust path to import ResistanceOptimizer module
# from src.resistance_optimizer import ResistanceOptimizer
from src.resistance_optimizer_new import ResistanceOptimizer
# from src.resistance_optimizer_test import ResistanceOptimizer

from src.gd_save import connect_db
from src.gd_save.gdc_reader import parse_save
from src.gd_save.process_save import process_save
from src.gd_save.get_character_resists import get_character_resists

app = Flask(__name__)
# Uploaded saves are parsed in memory; 16 MB comfortably covers real player.gdc
# files (typically <= 2 MB) while bounding memory.
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


@app.errorhandler(413)
def _too_large(_e):
    return jsonify({'error': 'Save file too large (max 16 MB).'}), 413

# Serve CSV files from sibling 'data' folder
@app.route('/data/<path:filename>')
def custom_static(filename):
    # Adjust the path below to the absolute or relative path to your 'data' folder
    data_folder = os.path.abspath(os.path.join(app.root_path, '..', 'data'))
    return send_from_directory(data_folder, filename)

@app.route('/upload-save', methods=['POST'])
def upload_save():
    """Parse an uploaded player.gdc through the gd_save pipeline and return
    the values needed to pre-fill the optimizer form: faction standings,
    current resistances, occupied component/augment slots and level.

    Pipeline order: parse_save (bytes -> parsed dict) -> process_save (skill
    bonuses + cleanup, mutates the dict in place) -> get_character_resists
    (KEEP-filtered resist dict). The bytes never touch disk.
    """
    upload = request.files.get('save_file')
    if upload is None or not upload.filename:
        return jsonify({'error': 'No save file uploaded.'}), 400
    data = upload.read()  # capped by MAX_CONTENT_LENGTH
    try:
        save = parse_save(data)  # pure; raises ValueError on bad data
    except ValueError as exc:
        return jsonify({'error': f'Not a valid Grim Dawn save: {exc}'}), 400
    try:
        conn = connect_db()
        try:
            process_save(conn, save)  # mutates save in place
            stats = get_character_resists(conn, save)
            # Elemental resistance is a combined stat in Grim Dawn: the
            # character's true fire/cold/lightning resists are the specific
            # values PLUS the elemental value. Split it equally into the three
            # before the UI pre-fills them.
            elem = stats.get('defensiveElementalResistance') or 0
            for key in ('defensiveFire', 'defensiveCold', 'defensiveLightning'):
                stats[key] = (stats.get(key) or 0) + elem
        finally:
            conn.close()
    except ValueError as exc:  # skill arithmetic mismatch etc.
        return jsonify({'error': f'Could not process save: {exc}'}), 422
    return jsonify({
        'character': save['character'],
        'level': save['level'],
        'weaponMode': save['weaponMode'],
        'factions': save['factions'],
        'stats': stats,      # KEEP dict; defensiveLife is the vitality resist
        'state': save['state'],      # per-slot {comp, aug} — True = slot free
        'summary': save['summary'],  # {free_comp, free_aug}
    })

@app.route("/", methods=["GET", "POST"])
def index():
    selected_items_with_urls_and_tags = None
    final_resistances = None
    target_resistances = None
    gap_resistances = None
    input_data = None
    unavailable_component_slots = None
    unavailable_augment_slots = None
    final_armor_abs_percentage: int = 0
    gap_armor_abs_percentage: int = 0
    secondary_gains = None
    if request.method == "POST":
        weapon_template = request.form.get("template")
        char_level = int(request.form.get("char-level", 100))
        current_armor_abs_percentage = int(request.form.get("armor-abs-value", 70))

        input_resistances = {
            "Fire Resistance": int(request.form.get("current-fire") or 0),
            "Cold Resistance": int(request.form.get("current-cold") or 0),
            "Lightning Resistance": int(request.form.get("current-lightning") or 0),
            "Poison & Acid Resistance": int(request.form.get("current-poison") or 0),
            "Pierce Resistance": int(request.form.get("current-pierce") or 0),
            "Bleeding Resistance": int(request.form.get("current-bleeding") or 0),
            "Vitality Resistance": int(request.form.get("current-vitality") or 0),
            "Aether Resistance": int(request.form.get("current-aether") or 0),
            "Chaos Resistance": int(request.form.get("current-chaos") or 0),
        }

        target_resistances = {
            "Fire Resistance": int(request.form.get("target-fire", 80)),
            "Cold Resistance": int(request.form.get("target-cold", 80)),
            "Lightning Resistance": int(request.form.get("target-lightning", 80)),
            "Poison & Acid Resistance": int(request.form.get("target-poison", 80)),
            "Pierce Resistance": int(request.form.get("target-pierce", 80)),
            "Bleeding Resistance": int(request.form.get("target-bleeding", 80)),
            "Vitality Resistance": int(request.form.get("target-vitality", 80)),
            "Aether Resistance": int(request.form.get("target-aether", 80)),
            "Chaos Resistance": int(request.form.get("target-chaos", 80)),
        }

        # Create a dictionary for unavailable component slots
        unavailable_component_slots = {
            "Helm": request.form.get("component-head", "off"),
            "Chest": request.form.get("component-chest", "off"),
            "Shoulders": request.form.get("component-shoulder", "off"),
            "Gloves": request.form.get("component-hand", "off"),
            "Pants": request.form.get("component-legs", "off"),
            "Boots": request.form.get("component-foot", "off"),
            "Belt": request.form.get("component-belt", "off"),
            "Amulet": request.form.get("component-amulet", "off"),
            "Ring 1": request.form.get("component-ring1", "off"),
            "Ring 2": request.form.get("component-ring2", "off"),
            "Medal": request.form.get("component-medal", "off"),
            "Weapon": request.form.get("component-weapon", "off"),
            "Off-Hand/Shield": request.form.get("component-offhand-shield", "off"),
        }
        for slot, status in unavailable_component_slots.items():
            if status == "on":
                unavailable_component_slots[slot] = True
            elif status == "off":
                unavailable_component_slots[slot] = False

        # Create a dictionary for unavailable augment slots
        unavailable_augment_slots = {
            "Helm": request.form.get("augment-head", "off"),
            "Chest": request.form.get("augment-chest", "off"),
            "Shoulders": request.form.get("augment-shoulder", "off"),
            "Gloves": request.form.get("augment-hand", "off"),
            "Pants": request.form.get("augment-legs", "off"),
            "Boots": request.form.get("augment-foot", "off"),
            "Belt": request.form.get("augment-belt", "off"),
            "Amulet": request.form.get("augment-amulet", "off"),
            "Ring 1": request.form.get("augment-ring1", "off"),
            "Ring 2": request.form.get("augment-ring2", "off"),
            "Medal": request.form.get("augment-medal", "off"),
            "Weapon": request.form.get("augment-weapon", "off"),
            "Off-Hand/Shield": request.form.get("augment-offhand-shield", "off"),
        }
        for slot, status in unavailable_augment_slots.items():
            if status == "on":
                unavailable_augment_slots[slot] = True
            elif status == "off":
                unavailable_augment_slots[slot] = False

        player_faction_standings = {
            "Devil's Crossing": request.form.get("standing-crossing", "Revered"),
            "Rovers": request.form.get("standing-rovers", "Revered"),
            "Homestead": request.form.get("standing-homestead", "Revered"),
            "Kymon's Chosen": request.form.get("standing-kymon", "Revered"),
            "Order of Death's Vigil": request.form.get("standing-order", "Revered"),
            "The Black Legion": request.form.get("standing-black-legion", "Revered"),
            "The Outcast": request.form.get("standing-outcast", "Revered"),
            "Coven of Ugdenbog": request.form.get("standing-coven", "Revered"),
            "Barrowholm": request.form.get("standing-barrowholm", "Revered"),
            "Malmouth Resistance": request.form.get("standing-malmouth", "Revered"),
            "Cult of Bysmiel": request.form.get("standing-bysmiel", "Revered"),
            "Cult of Dreeg": request.form.get("standing-dreeg", "Revered"),
            "Cult of Solael": request.form.get("standing-solael", "Revered"),
            "Kurn": request.form.get("standing-kurn", "Revered"),
        }

        component_blacklist = request.form.getlist('component_blacklist[]')
        augment_blacklist = request.form.getlist('augment_blacklist[]')

        # Consolidate input data for enabling persistance on the frontend
        input_data = {}
        input_data["Character Level"] = char_level
        input_data["weapon_template"] = weapon_template
        input_data.update(input_resistances)
        input_data.update(player_faction_standings)

        optimizer = ResistanceOptimizer(
            character_level=char_level,
            current_armor_abs_percentage=current_armor_abs_percentage,
            current_resistances=input_resistances,
            target_resistances=target_resistances,
            weapon_template=weapon_template,
            unavailable_component_slots=unavailable_component_slots,
            unavailable_augment_slots=unavailable_augment_slots,
            component_blacklist=component_blacklist,
            augment_blacklist=augment_blacklist,
            player_faction_standings=player_faction_standings,
        )
        # Build the secondary-stat priority tiers from the advanced tab:
        #   Priority stats -> first tier, Nice to Have stats -> second tier,
        #   Ignore stats -> excluded entirely.
        # E.g. 2 priority + 2 nice-to-have stats becomes [["A", "B"], ["C", "D"]].
        stat_tier_map = [
            ("ADCTH", "stat-adcth"),
            ("Armor", "stat-armor"),
            ("Attack Speed", "stat-attack-speed"),
            ("Cast Speed", "stat-cast-speed"),
            ("DA", "stat-da"),
            ("Health", "stat-health"),
            ("Move Speed", "stat-move-speed"),
            ("OA", "stat-oa"),
            # Secondary resists: pure % stats; the CSV column value IS the percent.
            ("Stun Resistance", "stat-res-stun"),
            ("Freeze Resistance", "stat-res-freeze"),
            ("Slow Resistance", "stat-res-slow"),
            ("Petrify Resistance", "stat-res-petrify"),
            ("Entrapment Resistance", "stat-res-entrapment"),
            ("Skill Disruption Protection", "stat-res-disruption"),
            ("Reflect Resistance", "stat-res-reflect"),
            ("Life Leech Resistance", "stat-res-life-leech"),
            ("Energy Leech Resistance", "stat-res-energy-leech"),
        ]
        priority_stats = [stat for stat, field in stat_tier_map if request.form.get(field) == "priority"]
        nice_to_have_stats = [stat for stat, field in stat_tier_map if request.form.get(field) == "nice"]
        if priority_stats and nice_to_have_stats:
            secondary_stats = [priority_stats, nice_to_have_stats]
        elif priority_stats:
            secondary_stats = [priority_stats]
        elif nice_to_have_stats:
            secondary_stats = [nice_to_have_stats]
        else:
            secondary_stats = []

        # Base value used to linearize % stat gains into equivalent flat units
        # (typical in-game base value of the stat; %-only stats just use 1).
        secondary_stat_base_values = {
            "OA": 2500,
            "DA": 2500,
            "Armor": 2500,
            "Health": 10000,
        }

        selected_items_with_urls_and_tags, final_resistances, final_armor_abs_percentage, secondary_gains = optimizer.optimize_resistances(secondary_stats, secondary_stat_base_values)

        # Backend stat keys -> display labels (same labels as the UI selection rows,
        # so the i18n translations apply to the gains table too)
        secondary_stat_labels = {
            "ADCTH": "ADCTH%",
            "Armor": "Armor",
            "Attack Speed": "Attack Speed%",
            "Cast Speed": "Cast Speed%",
            "DA": "Defensive Ability",
            "Health": "Health",
            "Move Speed": "Move Speed%",
            "OA": "Offensive Ability",
        }
        secondary_gains = {
            secondary_stat_labels.get(stat, stat): gains
            for stat, gains in secondary_gains.items()
        }
        # Sort alphabetically by display label so the gains table is stable
        # regardless of which order the optimizer's tiers returned.
        secondary_gains = dict(sorted(secondary_gains.items()))

        # Calculate the resistance gaps if any after optimization
        gap_resistances = {
            res: max(0, target_resistances[res] - final_resistances[res])
            for res in optimizer.resistance_types
        }
        gap_armor_abs_percentage=int(max(100 - final_armor_abs_percentage, 0))

    return render_template(
        "index.html",
        target_resistances=target_resistances,
        results=selected_items_with_urls_and_tags,
        final_resistances=final_resistances,
        gap_resistances=gap_resistances,
        final_armor_abs_percentage=int(final_armor_abs_percentage),
        gap_armor_abs_percentage=gap_armor_abs_percentage,
        secondary_gains=secondary_gains,
    )


if __name__ == "__main__":
    app.run(debug=True)
