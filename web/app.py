from flask import Flask, render_template, request
import pandas as pd
from icecream import ic

import sys
sys.path.append('.')  # Adjust path to import components module
from grim_dawn_resistance_optimizer.components import Components
from grim_dawn_resistance_optimizer.resistance_component_augment_lp_solver import optimize_resistances


app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def index():
    selected_items_with_urls = None
    final_resistances = None
    gap_resistances = None
    input_data = None
    unavailable_component_slots = None
    unavailable_augment_slots = None
    if request.method == 'POST':

        char_level = int(request.form.get('char-level', 100))
        input_resistances = {
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

        # Create a dictionary for unavailable component slots
        unavailable_component_slots = {
            "Helm" : request.form.get('component-head', 'off'),
            "Chest" : request.form.get('component-chest', 'off'),
            "Shoulders" : request.form.get('component-shoulder', 'off'),
            "Gloves" : request.form.get('component-hand', 'off'),
            "Pants" : request.form.get('component-legs', 'off'),
            "Boots" : request.form.get('component-foot', 'off'),
            "Belt" : request.form.get('component-belt', 'off'),
            "Amulet" : request.form.get('component-amulet', 'off'),
            "Ring1" : request.form.get('component-ring1', 'off'),
            "Ring2" : request.form.get('component-ring2', 'off'),
            "Medal" : request.form.get('component-medal', 'off'),
            "Weapon" : request.form.get('component-weapon', 'off'),
            "Shield" : request.form.get('component-shield', 'off'),
            "Off-Hand" : request.form.get('component-offhand', 'off'),
        }
        for slot, status in unavailable_component_slots.items():
            if status == 'on':
                unavailable_component_slots[slot] = True
            elif status == 'off':
                unavailable_component_slots[slot] = False

        # Create a dictionary for unavailable augment slots
        unavailable_augment_slots = {
            "Helm" : request.form.get('augment-head', 'off'),
            "Chest" : request.form.get('augment-chest', 'off'),
            "Shoulders" : request.form.get('augment-shoulder', 'off'),
            "Gloves" : request.form.get('augment-hand', 'off'),
            "Pants" : request.form.get('augment-legs', 'off'),
            "Boots" : request.form.get('augment-foot', 'off'),
            "Belt" : request.form.get('augment-belt', 'off'),
            "Amulet" : request.form.get('augment-amulet', 'off'),
            "Ring1" : request.form.get('augment-ring1', 'off'),
            "Ring2" : request.form.get('augment-ring2', 'off'),
            "Medal" : request.form.get('augment-medal', 'off'),
            "Weapon" : request.form.get('augment-weapon', 'off'),
            "Shield" : request.form.get('augment-shield', 'off'),
            "Off-Hand" : request.form.get('augment-offhand', 'off'),
        }
        for slot, status in unavailable_augment_slots.items():
            if status == 'on':
                unavailable_augment_slots[slot] = True
            elif status == 'off':
                unavailable_augment_slots[slot] = False

        # Consolidate input data for enabling persistance on the frontend
        input_data = {}
        input_data['Character Level'] = char_level
        input_data['weapon_template'] = weapon_template
        input_data.update(input_resistances)

        components_obj = Components(
            character_level=char_level,
            current_resistances=input_resistances,
            weapon_template=weapon_template,
            unavailable_component_slots=unavailable_component_slots,
            unavailable_augment_slots=unavailable_augment_slots
        )

        # Remove components that have no resistance values
        component_df = pd.read_csv(components_obj.component_csv_path)
        useful_components = component_df[
            (component_df[components_obj.resistance_types] != 0).any(axis=1)
            & (component_df['Required Player Level'] <= components_obj.character_level)
            ]
        useful_components = useful_components.reset_index(drop=True)

        # Remove augments that have no resistance values
        augment_df = pd.read_csv(components_obj.augment_csv_path)
        useful_augments = augment_df[
            (augment_df[components_obj.resistance_types] != 0).any(axis=1)
            & (augment_df['Required Player Level'] <= components_obj.character_level)
            ]
        useful_augments = useful_augments.reset_index(drop=True)

        selected_items_with_urls, final_resistances = optimize_resistances(
            current_resistances=components_obj.current_resistances,
            remaining_resistances=components_obj.remaining_resistances,
            resistance_types=components_obj.resistance_types,
            weapon_template=components_obj.weapon_template,
            available_component_slots=components_obj.available_component_slots,
            available_augment_slots=components_obj.available_augment_slots,
            useful_components=useful_components,
            useful_augments=useful_augments,
        )

        # Calculate the resistance gaps if any after optimization
        gap_resistances = {res: max(0, 80 - final_resistances[res]) for res in components_obj.resistance_types}

    return render_template(
        "index.html",
        results=selected_items_with_urls,
        final_resistances=final_resistances,
        gap_resistances=gap_resistances,
        data=input_data,
        component_slots=unavailable_component_slots,
        augment_slots=unavailable_augment_slots
    )

if __name__ == "__main__":
    app.run(debug=True)
