import pandas as pd
import pulp
from icecream import ic

from components import Components

components_obj = Components()
component_df = pd.read_csv(components_obj.component_csv_path)
augment_df = pd.read_csv(components_obj.augment_csv_path)

current_resistances = components_obj.current_resistances
res_types = components_obj.resistances
slots = components_obj.gear_slots
remaining_needed = components_obj.needed_resistances

blocked_slots = ['Ring1', 'Ring2']  # Slots that should not be used in the optimization
for blocked_slot in blocked_slots:
    slots.remove(blocked_slot)
# ic(slots)

# Remove components that have no resistance values
useful_components = component_df[
    (component_df[res_types] != 0).any(axis=1)
    & (component_df['Required Player Level'] <= components_obj.character_level)
    ]
useful_components = useful_components.reset_index(drop=True)

# Remove augments that have no resistance values
useful_augments = augment_df[
    (augment_df[res_types] != 0).any(axis=1)
    & (augment_df['Required Player Level'] <= components_obj.character_level)
    ]
useful_augments = useful_augments.reset_index(drop=True)

ic(useful_components.shape[0])
ic(useful_augments.shape[0])

# Create the problem - now maximizing resistance achievement
prob = pulp.LpProblem("Multi_Objective_Resistance_Optimization", pulp.LpMaximize)

# Decision variables: binary variable for each component-slot combination
component_slot_vars = {}
for i, item in useful_components.iterrows():
    allowed_gear_slots = [slot for slot in slots if item[slot]]
    for slot in allowed_gear_slots:
        var_name = f"Item_{i}_{item['Item']}_in_{slot}"
        component_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat='Binary')

# Decision variables: binary variable for each augment-slot combination
augment_slot_vars = {}
for i, item in useful_augments.iterrows():
    allowed_gear_slots = [slot for slot in slots if item[slot]]
    for slot in allowed_gear_slots:
        var_name = f"Item_{i}_{item['Item']}_in_{slot}"
        augment_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat='Binary')

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

# Secondary objective: Minimize number of components used
total_components_used = []
for i, item in useful_components.iterrows():
    allowed_gear_slots = [slot for slot in slots if item[slot]]
    item_vars_for_this_item = [component_slot_vars[(i, slot)] for slot in allowed_gear_slots]
    if item_vars_for_this_item:
        # This represents whether this item is used (in any slot)
        total_components_used.append(pulp.lpSum(item_vars_for_this_item))

# Secondary objective: Minimize number of augments used
total_augments_used = []
for i, item in useful_augments.iterrows():
    allowed_gear_slots = [slot for slot in slots if item[slot]]
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
prob += pulp.lpSum(total_components_used) <= len(slots)
prob += pulp.lpSum(total_augments_used) <= len(slots)

# # Constraint: Each item can be equipped in at most one slot
# for i, item in useful_items.iterrows():
#     allowed_gear_slots = [slot for slot in slots if item[slot]]
#     prob += pulp.lpSum([item_slot_vars[(i, slot)] for slot in allowed_gear_slots]) <= 1
# # ic(prob)

# Constraint: Each gear slot can only have one component
for slot in slots:
    indices_list = useful_components[useful_components[slot]].index.tolist()
    items_for_slot = [(idx, slot) for idx in indices_list]
    if items_for_slot:
        prob += pulp.lpSum([component_slot_vars[item_slot] for item_slot in items_for_slot]) <= 1

# Constraint: Each gear slot can only have one augment
for slot in slots:
    indices_list = useful_augments[useful_augments[slot]].index.tolist()
    items_for_slot = [(idx, slot) for idx in indices_list]
    if items_for_slot:
        prob += pulp.lpSum([augment_slot_vars[item_slot] for item_slot in items_for_slot]) <= 1

# Constraint: Link resistance achieved variables to actual resistance gained
for resistance in res_types:
    needed = remaining_needed[resistance]
    if needed > 0:
        resistance_sum = []

        for i, item in useful_components.iterrows():
            allowed_gear_slots = [slot for slot in slots if item[slot]]
            for slot in allowed_gear_slots:
                if (i, slot) in component_slot_vars:
                    resistance_sum.append(component_slot_vars[(i, slot)] * item[resistance])
        
        for i, item in useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in slots if item[slot]]
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

def show_selected_components_augments(selected_items):
    selected_components = 0
    selected_augments = 0
    for slot, item in selected_items.items():
        if item['component']:
            selected_components += 1
        if item['augment']:
            selected_augments += 1
    print(f"{selected_components} out of {len(selected_items.keys())} slots allocated for components")
    print(f"{selected_augments} out of {len(selected_items.keys())} slots allocated for augments")

selected_items = {key: {"component": "", "augment": ""} for key in slots}

if status == 'Optimal' or status == 'Infeasible':
    gear_resistances = {r: 0 for r in res_types}
    final_resistances = current_resistances.copy()
    
    for i, item in useful_components.iterrows():
        allowed_gear_slots = [slot for slot in slots if item[slot]]
        for slot in allowed_gear_slots:
            if (i, slot) in component_slot_vars and component_slot_vars[(i, slot)].varValue == 1:
                selected_items[slot]['component'] = item['Item']
                for res in res_types:
                    current_resistances[res] += item[res]

    for i, item in useful_augments.iterrows():
        allowed_gear_slots = [slot for slot in slots if item[slot]]
        for slot in allowed_gear_slots:
            if (i, slot) in augment_slot_vars and augment_slot_vars[(i, slot)].varValue == 1:
                selected_items[slot]['augment'] = item['Item']
                for res in res_types:
                    current_resistances[res] += item[res]

    # components_obj.show_slot_allocation(selected_items)
    show_selected_components_augments(selected_items)
    ic(selected_items)
    ic(current_resistances)
    components_obj.calculate_penalty(current_resistances)
