import os
import sys

from flask import Flask, render_template, request, send_from_directory

sys.path.append(".")  # Adjust path to import ResistanceOptimizer module
from src.resistance_optimizer import ResistanceOptimizer

app = Flask(__name__)

# Serve CSV files from sibling 'data' folder
@app.route('/data/<path:filename>')
def custom_static(filename):
    # Adjust the path below to the absolute or relative path to your 'data' folder
    data_folder = os.path.abspath(os.path.join(app.root_path, '..', 'data'))
    return send_from_directory(data_folder, filename)

@app.route("/", methods=["GET", "POST"])
def index():
    selected_items_with_urls_and_tags = None
    final_resistances = None
    target_resistances = None
    gap_resistances = None
    input_data = None
    unavailable_component_slots = None
    unavailable_augment_slots = None
    if request.method == "POST":
        weapon_template = request.form.get("template")
        char_level = int(request.form.get("char-level", 100))
        input_resistances = {
            "Fire Resistance": int(request.form.get("current-fire", 40)),
            "Cold Resistance": int(request.form.get("current-cold", 40)),
            "Lightning Resistance": int(request.form.get("current-lightning", 40)),
            "Poison & Acid Resistance": int(request.form.get("current-poison", 40)),
            "Pierce Resistance": int(request.form.get("current-pierce", 40)),
            "Bleeding Resistance": int(request.form.get("current-bleeding", 40)),
            "Vitality Resistance": int(request.form.get("current-vitality", 40)),
            "Aether Resistance": int(request.form.get("current-aether", 40)),
            "Chaos Resistance": int(request.form.get("current-chaos", 40)),
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
            current_resistances=input_resistances,
            target_resistances=target_resistances,
            weapon_template=weapon_template,
            unavailable_component_slots=unavailable_component_slots,
            unavailable_augment_slots=unavailable_augment_slots,
            component_blacklist=component_blacklist,
            augment_blacklist=augment_blacklist,
            player_faction_standings=player_faction_standings,
        )
        selected_items_with_urls_and_tags, final_resistances = optimizer.optimize_resistances()

        # Calculate the resistance gaps if any after optimization
        gap_resistances = {
            res: max(0, target_resistances[res] - final_resistances[res])
            for res in optimizer.resistance_types
        }

    return render_template(
        "index.html",
        data=input_data,
        target_resistances=target_resistances,
        results=selected_items_with_urls_and_tags,
        final_resistances=final_resistances,
        gap_resistances=gap_resistances,
        component_slots=unavailable_component_slots,
        augment_slots=unavailable_augment_slots,
    )


if __name__ == "__main__":
    app.run(debug=True)
