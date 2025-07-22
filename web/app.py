from flask import Flask, render_template, request
import pandas as pd
from icecream import ic

import sys
sys.path.append('.')  # Adjust path to import components module
from grim_dawn_resistance_optimizer.components import Components
from grim_dawn_resistance_optimizer.resistance_component_augment_lp_solver import optimize_resistances


app = Flask(__name__)

def filter_augment_db(augment_df: pd.DataFrame, player_faction_standings: dict) -> pd.DataFrame:

    # Mapping
    standing_levels = {
        "Friendly": 1,
        "Respected": 2,
        "Honored": 3,
        "Revered": 4
    }

    # Map player's standings to numeric levels
    player_standings_num = { faction: standing_levels.get(level.title(), 0) 
                            for faction, level in player_faction_standings.items() }


    # Create numeric required standing column
    augment_df['RequiredStandingNum'] = augment_df['Required Faction Level'].str.title().map(standing_levels)

    # Define filter function
    def player_meets_requirement(row):
        player_level = player_standings_num.get(row['Faction'], 0)
        required_level = row['RequiredStandingNum']
        if pd.isna(required_level):
            return False  # or True, as your policy
        return player_level >= required_level

    # Filter dataframe based on player standings
    filtered_augments = augment_df[augment_df.apply(player_meets_requirement, axis=1)]

    return filtered_augments


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

        player_faction_standings = {
            "Devil's Crossing": request.form.get('standing-crossing', 'Revered'),
            'Rovers': request.form.get('standing-rovers', 'Revered'),
            'Homestead': request.form.get('standing-homestead', 'Revered'),
            "Kymon's Chosen": request.form.get('standing-kymon', 'Revered'),
            "Order of Death's Vigil": request.form.get('standing-order', 'Revered'),
            'The Black Legion': request.form.get('standing-black-legion', 'Revered'),
            'The Outcast': request.form.get('standing-outcast', 'Revered'),
            'Coven of Ugdenbog': request.form.get('standing-coven', 'Revered'),
            'Barrowholm': request.form.get('standing-barrowholm', 'Revered'),
            'Malmouth Resistance': request.form.get('standing-malmouth', 'Revered'),
            'Cult of Bysmiel': request.form.get('standing-bysmiel', 'Revered'),
            'Cult of Dreeg': request.form.get('standing-dreeg', 'Revered'),
            'Cult of Solael': request.form.get('standing-solael', 'Revered'),
        }

        # Consolidate input data for enabling persistance on the frontend
        input_data = {}
        input_data['Character Level'] = char_level
        input_data['weapon_template'] = weapon_template
        input_data.update(input_resistances)
        input_data.update(player_faction_standings)

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
        filtered_augment_df = filter_augment_db(augment_df, player_faction_standings)
        useful_augments = filtered_augment_df[
            (filtered_augment_df[components_obj.resistance_types] != 0).any(axis=1)
            & (filtered_augment_df['Required Player Level'] <= components_obj.character_level)
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
