import pandas as pd
import pulp
from icecream import ic

from components import Components

if __name__ == "__main__":
    components_obj = Components()
    df = pd.read_csv(components_obj.component_csv_path)
    # df = pd.read_csv("augment_data.csv")

    current_resistances = components_obj.current_resistances
    res_types = components_obj.resistances
    slots = components_obj.gear_slots
    remaining_needed = components_obj.needed_resistances

    blocked_slots = ['Ring1', 'Ring2']  # Slots that should not be used in the optimization
    for blocked_slot in blocked_slots:
        slots.remove(blocked_slot)

    # Remove items that have no resistance values
    useful_items = df[
        (df[res_types] != 0).any(axis=1)
        & (df['Required Player Level'] <= components_obj.character_level)
        ]
    useful_items = useful_items.reset_index(drop=True)

    ic(useful_items.shape[0])

    # Create the problem - now maximizing resistance achievement
    prob = pulp.LpProblem("Multi_Objective_Resistance_Optimization", pulp.LpMaximize)

    # Decision variables: binary variable for each item-slot combination
    item_slot_vars = {}
    for i, item in useful_items.iterrows():
        allowed_gear_slots = [slot for slot in slots if item[slot]]
        for slot in allowed_gear_slots:
            var_name = f"Item_{i}_{item['Item']}_in_{slot}"
            item_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat='Binary')

    # Additional variables for resistance achievement tracking
    resistance_achieved = {}
    for resistance in res_types:
        resistance_achieved[resistance] = pulp.LpVariable(f"Achieved_{resistance}", lowBound=0)

    # Multi-objective function with weighted priorities
    # Weight for achieving target resistances (primary objective)
    # Penalty for number of items used (secondary objective)
    resistance_weight = 1  # Weight for resistance achievement
    item_penalty_weight = 1 # Penalty for each item used

    # Primary objective: Maximize resistance achievement while minimizing items
    resistance_objectives = []
    for resistance in res_types:
        # Reward achieving the full target (60 points needed)
        needed = remaining_needed[resistance]
        if needed > 0:
            # Use min function to cap at target - this rewards reaching exactly the target
            resistance_objectives.append(resistance_achieved[resistance])
        # ic(resistance_objectives)

    # Secondary objective: Minimize number of items used
    total_items_used = []
    for i, item in useful_items.iterrows():
        allowed_gear_slots = [slot for slot in slots if item[slot]]
        item_vars_for_this_item = [item_slot_vars[(i, slot)] for slot in allowed_gear_slots]
        if item_vars_for_this_item:
            # This represents whether this item is used (in any slot)
            total_items_used.append(pulp.lpSum(item_vars_for_this_item))

    prob += (resistance_weight * pulp.lpSum(resistance_objectives) - 
            item_penalty_weight * pulp.lpSum(total_items_used))

    # Constraint: Total items selected must be <= max_items
    prob += pulp.lpSum(total_items_used) <= len(slots)

    # # Constraint: Each item can be equipped in at most one slot
    # for i, item in useful_items.iterrows():
    #     allowed_gear_slots = [slot for slot in slots if item[slot]]
    #     prob += pulp.lpSum([item_slot_vars[(i, slot)] for slot in allowed_gear_slots]) <= 1
    # # ic(prob)

    # Constraint: Each gear slot can only have one item
    for slot in slots:
        indices_list = useful_items[useful_items[slot]].index.tolist()
        items_for_slot = [(idx, slot) for idx in indices_list]
        if items_for_slot:
            prob += pulp.lpSum([item_slot_vars[item_slot] for item_slot in items_for_slot]) <= 1

    # Constraint: Link resistance achieved variables to actual resistance gained
    for resistance in res_types:
        needed = remaining_needed[resistance]
        if needed > 0:
            resistance_sum = []
            for i, item in useful_items.iterrows():
                allowed_gear_slots = [slot for slot in slots if item[slot]]
                for slot in allowed_gear_slots:
                    if (i, slot) in item_slot_vars:
                        resistance_sum.append(item_slot_vars[(i, slot)] * item[resistance])
            
            total_resistance_gained = pulp.lpSum(resistance_sum)
            
            # Link the achieved variable to actual resistance gained (capped at needed amount)
            prob += resistance_achieved[resistance] <= total_resistance_gained
            prob += resistance_achieved[resistance] <= needed  # Cap at what we need

    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Extract results
    status = pulp.LpStatus[prob.status]

    if status == 'Optimal' or status == 'Infeasible':
        selected_items = {slot: None for slot in slots}
        gear_resistances = {r: 0 for r in res_types}
        final_resistances = current_resistances.copy()
        
        for i, item in useful_items.iterrows():
            allowed_gear_slots = [slot for slot in slots if item[slot]]
            # for i, slot in enumerate(allowed_gear_slots):
            for slot in allowed_gear_slots:
                if (i, slot) in item_slot_vars and item_slot_vars[(i, slot)].varValue == 1:
                    # selected_items[gear_slots[i]] = item['Item']
                    selected_items[slot] = item['Item']
                    for res in res_types:
                        current_resistances[res] += item[res]

        components_obj.show_slot_allocation(selected_items)
        ic(current_resistances)
        components_obj.calculate_penalty(current_resistances)
