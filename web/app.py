from flask import Flask, render_template, request
import pandas as pd
from icecream import ic

import sys
sys.path.append('.')  # Adjust path to import components module
from grim_dawn_resistance_optimizer.components import Components
from grim_dawn_resistance_optimizer.resistance_component_lp_solver import optimize_resistances


app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    selected_items_with_urls = None
    final_resistances = None
    if request.method == 'POST':

        char_level = int(request.form.get('char-level', 100))
        current_resistances = {
            'Fire Resistance': int(request.form.get('current-fire', 20)),
            'Cold Resistance': int(request.form.get('current-cold', 20)),
            'Lightning Resistance': int(request.form.get('current-lightning', 20)),
            'Poison & Acid Resistance': int(request.form.get('current-poison', 20)),
            'Pierce Resistance': int(request.form.get('current-pierce', 20)),
            'Bleeding Resistance': int(request.form.get('current-bleeding', 20)),
            'Vitality Resistance': int(request.form.get('current-vitality', 20)),
            'Aether Resistance': int(request.form.get('current-aether', 20)),
            'Chaos Resistance': int(request.form.get('current-chaos', 20))
        }
        weapon_template = request.form.get('template')

        # Create a dictionary for unavailable gear slots
        unavailable_gear_slots = {
            "Helm" : request.form.get('lock-head', 'off'),
            "Chest" : request.form.get('lock-chest', 'off'),
            "Shoulders" : request.form.get('lock-shoulder', 'off'),
            "Gloves" : request.form.get('lock-hand', 'off'),
            "Pants" : request.form.get('lock-legs', 'off'),
            "Boots" : request.form.get('lock-foot', 'off'),
            "Belt" : request.form.get('lock-belt', 'off'),
            "Amulet" : request.form.get('lock-amulet', 'off'),
            "Ring1" : request.form.get('lock-ring1', 'off'),
            "Ring2" : request.form.get('lock-ring2', 'off'),
            "Medal" : request.form.get('lock-medal', 'off'),
            "Weapon" : request.form.get('lock-weapon', 'off'),
            "Shield" : request.form.get('lock-shield', 'off'),
            "Off-Hand" : request.form.get('lock-offhand', 'off'),
        }
        for slot, status in unavailable_gear_slots.items():
            if status == 'on':
                unavailable_gear_slots[slot] = True
            elif status == 'off':
                unavailable_gear_slots[slot] = False

        components_obj = Components(
            character_level=char_level,
            current_resistances=current_resistances,
            weapon_template=weapon_template,
            unavailable_gear_slots=unavailable_gear_slots
        )

        component_df = pd.read_csv(components_obj.component_csv_path)
        # Remove items that have no resistance values
        useful_items = component_df[
            (component_df[components_obj.resistance_types] != 0).any(axis=1)
            & (component_df['Required Player Level'] <= char_level)
            ]
        useful_items = useful_items.reset_index(drop=True)

        selected_items_with_urls, final_resistances = optimize_resistances(
            current_resistances=components_obj.current_resistances,
            remaining_resistances=components_obj.remaining_resistances,
            resistance_types=components_obj.resistance_types,
            slots=components_obj.available_gear_slots,
            useful_items=useful_items,
        )

    return render_template("index.html", results=selected_items_with_urls, final_resistances=final_resistances)

if __name__ == "__main__":
    app.run(debug=True)
