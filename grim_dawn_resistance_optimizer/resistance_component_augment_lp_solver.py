import pandas as pd
import pulp
from icecream import ic

from grim_dawn_resistance_optimizer.components import Components

def generate_item_urls(selected_items, component_df, augment_df) -> dict[str, dict[str, str]]:

    combined_df = pd.concat([component_df, augment_df], ignore_index=True)

    def get_item_url(name: str) -> str:
        if not name:
            return ""
        item_info = combined_df[combined_df['Item'] == name]
        if not item_info.empty:
            item_id = int(item_info["ID"].iloc[0])
            return f"https://www.grimtools.com/db/items/{item_id}"
        else:
            return ""

    selected_items_with_urls = {}
    for slot, items in selected_items.items():
        augment_name = items.get('augment', '')
        component_name = items.get('component', '')
        selected_items_with_urls[slot] = {
            'Augment': {
                'Name': augment_name,
                'Url': get_item_url(augment_name)
            },
            'Component': {
                'Name': component_name,
                'Url': get_item_url(component_name)
            }
        }

    return selected_items_with_urls

def generated_selected_items_dict(weapon_template) -> dict[str, dict[str, str]]:

        component_obj = Components()
        final_slots = component_obj.all_gear_slots.copy()
        if weapon_template == "one-hand-shield":
            final_slots.remove("Off-Hand")
            final_slots.remove("Two-Handed")
            final_slots.remove("Ranged")
        elif weapon_template == "one-hand-offhand":
            final_slots.remove("Shield")
            final_slots.remove("Two-Handed")
            final_slots.remove("Ranged")
        elif weapon_template == "two-hand":
            final_slots.remove("One-Handed")
            final_slots.remove("Off-Hand")
            final_slots.remove("Ranged")
            final_slots.remove("Shield")
        elif weapon_template == "ranged-offhand":
            final_slots.remove("Shield")
            final_slots.remove("Two-Handed")
            final_slots.remove("One-Handed")

        selected_items = {key: {"component": "", "augment": ""} for key in final_slots}
        return selected_items


def optimize_resistances(
        current_resistances: dict[str, int],
        remaining_resistances: dict[str, int],
        resistance_types: list[str],
        weapon_template: str,
        available_component_slots: list[str],
        available_augment_slots: list[str],
        useful_components: pd.DataFrame,
        useful_augments: pd.DataFrame,
) -> None:

    # Create the problem - now maximizing resistance achievement
    prob = pulp.LpProblem("Multi_Objective_Resistance_Optimization", pulp.LpMaximize)

    # Decision variables: binary variable for each component-slot combination
    component_slot_vars = {}
    for i, item in useful_components.iterrows():
        allowed_gear_slots = [slot for slot in available_component_slots if item[slot]]
        for slot in allowed_gear_slots:
            var_name = f"Item_{i}_{item['Item']}_in_{slot}"
            component_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat='Binary')

    # Decision variables: binary variable for each augment-slot combination
    augment_slot_vars = {}
    for i, item in useful_augments.iterrows():
        allowed_gear_slots = [slot for slot in available_augment_slots if item[slot]]
        for slot in allowed_gear_slots:
            var_name = f"Item_{i}_{item['Item']}_in_{slot}"
            augment_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat='Binary')

    # Additional variables for resistance achievement tracking
    resistance_achieved = {}
    for resistance in resistance_types:
        resistance_achieved[resistance] = pulp.LpVariable(f"Achieved_{resistance}", lowBound=0)

    # Multi-objective function with weighted priorities
    # Weight for achieving target resistances (primary objective)
    # Penalty for number of items used (secondary objective)
    resistance_weight = 1  # Weight for resistance achievement
    item_penalty_weight = 1 # Penalty for each item used

    # Primary objective: Maximize resistance achievement while minimizing items
    resistance_objectives = []
    for resistance in resistance_types:
        # Reward achieving the full target (60 points needed)
        needed = remaining_resistances[resistance]
        if needed > 0:
            # Use min function to cap at target - this rewards reaching exactly the target
            resistance_objectives.append(resistance_achieved[resistance])
        # ic(resistance_objectives)

    # Secondary objective: Minimize number of components used
    total_components_used = []
    for i, item in useful_components.iterrows():
        allowed_gear_slots = [slot for slot in available_component_slots if item[slot]]
        item_vars_for_this_item = [component_slot_vars[(i, slot)] for slot in allowed_gear_slots]
        if item_vars_for_this_item:
            # This represents whether this item is used (in any slot)
            total_components_used.append(pulp.lpSum(item_vars_for_this_item))

    # Secondary objective: Minimize number of augments used
    total_augments_used = []
    for i, item in useful_augments.iterrows():
        allowed_gear_slots = [slot for slot in available_augment_slots if item[slot]]
        item_vars_for_this_item = [augment_slot_vars[(i, slot)] for slot in allowed_gear_slots]
        if item_vars_for_this_item:
            # This represents whether this item is used (in any slot)
            total_augments_used.append(pulp.lpSum(item_vars_for_this_item))

    prob += (resistance_weight * pulp.lpSum(resistance_objectives) - 
            item_penalty_weight * pulp.lpSum(total_components_used) -
            item_penalty_weight * pulp.lpSum(total_augments_used))

    # prob += (resistance_weight * pulp.lpSum(resistance_objectives) - 
    #          item_penalty_weight * (pulp.lpSum(total_components_used) + pulp.lpSum(total_augments_used)))

    # Constraint: Total components and augments selected must be <= max_items
    prob += pulp.lpSum(total_components_used) <= len(available_component_slots)
    prob += pulp.lpSum(total_augments_used) <= len(available_augment_slots)

    # # Constraint: Each item can be equipped in at most one slot
    # for i, item in useful_items.iterrows():
    #     allowed_gear_slots = [slot for slot in slots if item[slot]]
    #     prob += pulp.lpSum([item_slot_vars[(i, slot)] for slot in allowed_gear_slots]) <= 1
    # # ic(prob)

    # Constraint: Each gear slot can only have one component
    for slot in available_component_slots:
        indices_list = useful_components[useful_components[slot]].index.tolist()
        items_for_slot = [(idx, slot) for idx in indices_list]
        if items_for_slot:
            prob += pulp.lpSum([component_slot_vars[item_slot] for item_slot in items_for_slot]) <= 1

    # Constraint: Each gear slot can only have one augment
    for slot in available_augment_slots:
        indices_list = useful_augments[useful_augments[slot]].index.tolist()
        items_for_slot = [(idx, slot) for idx in indices_list]
        if items_for_slot:
            prob += pulp.lpSum([augment_slot_vars[item_slot] for item_slot in items_for_slot]) <= 1

    # Constraint: Link resistance achieved variables to actual resistance gained
    for resistance in resistance_types:
        needed = remaining_resistances[resistance]
        if needed > 0:
            resistance_sum = []

            for i, item in useful_components.iterrows():
                allowed_gear_slots = [slot for slot in available_component_slots if item[slot]]
                for slot in allowed_gear_slots:
                    if (i, slot) in component_slot_vars:
                        resistance_sum.append(component_slot_vars[(i, slot)] * item[resistance])
            
            for i, item in useful_augments.iterrows():
                allowed_gear_slots = [slot for slot in available_augment_slots if item[slot]]
                for slot in allowed_gear_slots:
                    if (i, slot) in augment_slot_vars:
                        resistance_sum.append(augment_slot_vars[(i, slot)] * item[resistance])
            
            total_resistance_gained = pulp.lpSum(resistance_sum)
            
            # Link the achieved variable to actual resistance gained (capped at needed amount)
            prob += resistance_achieved[resistance] <= total_resistance_gained
            prob += resistance_achieved[resistance] <= needed  # Cap at what we need

    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Extract results
    status = pulp.LpStatus[prob.status]

    if status == 'Optimal' or status == 'Infeasible':
        selected_items = generated_selected_items_dict(weapon_template)
        
        for i, item in useful_components.iterrows():
            allowed_gear_slots = [slot for slot in available_component_slots if item[slot]]
            for slot in allowed_gear_slots:
                if (i, slot) in component_slot_vars and component_slot_vars[(i, slot)].varValue == 1:
                    selected_items[slot]['component'] = item['Item']
                    for res in resistance_types:
                        current_resistances[res] += item[res]

        for i, item in useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in available_augment_slots if item[slot]]
            for slot in allowed_gear_slots:
                if (i, slot) in augment_slot_vars and augment_slot_vars[(i, slot)].varValue == 1:
                    selected_items[slot]['augment'] = item['Item']
                    for res in resistance_types:
                        current_resistances[res] += item[res]

            
        # Set slot as unavailable instead of just empty string to differenciate from free slots
        for key, _ in selected_items.items():
            if key not in available_component_slots:
                selected_items[key]['component'] = 'Slot Unavailable'
            if key not in available_augment_slots:
                selected_items[key]['augment'] = 'Slot Unavailable'

        selected_items_with_urls = generate_item_urls(selected_items, useful_components, useful_augments)

        return selected_items_with_urls, current_resistances

