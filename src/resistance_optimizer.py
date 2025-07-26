from dataclasses import dataclass

import pandas as pd
import pulp
from icecream import ic


@dataclass
class ResistanceOptimizer:
    all_gear_slots: list[str] = None
    resistance_types: list[str] = None

    useful_components: pd.DataFrame = None
    useful_augments: pd.DataFrame = None

    unavailable_component_slots: dict[str, bool] = None
    available_component_slots: list[str] = None
    unavailable_augment_slots: dict[str, bool] = None
    available_augment_slots: list[str] = None

    player_faction_standings: dict[str, str] = None

    current_resistances: dict[str, int] = None
    remaining_resistances: dict[str, int] = None

    component_csv_path: str = "data/component_data.csv"
    augment_csv_path: str = "data/augment_data.csv"
    weapon_template: str = "one-hand-offhand"
    character_level: int = 100

    def __post_init__(self):
        """Post Init function to perform certain operations on object creation."""
        self.set_defaults()
        self.calculate_remaining_resistances()
        self.filter_useful_components_augments()
        self.available_component_slots = self.check_available_slots(self.unavailable_component_slots)
        self.available_augment_slots = self.check_available_slots(self.unavailable_augment_slots)

    def set_defaults(self) -> None:
        self.all_gear_slots: list[str] = [
            "Helm",
            "Chest",
            "Shoulders",
            "Gloves",
            "Pants",
            "Boots",
            "Belt",
            "Amulet",
            "Ring1",
            "Ring2",
            "Medal",
            "One-Handed",
            "Two-Handed",
            "Ranged",
            "Off-Hand",
            "Shield",
        ]

        self.resistance_types: list[str] = [
            "Fire Resistance",
            "Cold Resistance",
            "Lightning Resistance",
            "Poison & Acid Resistance",
            "Pierce Resistance",
            "Bleeding Resistance",
            "Vitality Resistance",
            "Aether Resistance",
            "Chaos Resistance",
        ]

        if self.current_resistances is None:
            self.current_resistances = {res: 40 for res in self.resistance_types}

        if self.unavailable_component_slots is None:
            self.unavailable_component_slots = {slot: False for slot in self.all_gear_slots}

        if self.unavailable_augment_slots is None:
            self.unavailable_augment_slots = {slot: False for slot in self.all_gear_slots}

    def calculate_remaining_resistances(self) -> None:
        """Calculate the remaining resistances based on current resistances."""
        self.remaining_resistances = {
            res: max(0, 80 - self.current_resistances[res])
            for res in self.resistance_types
        }

    def filter_useful_components_augments(self) -> None:
        """Filter out useful components and augments based on character level and player faction standings."""
        # Load the component and augment databases
        component_df: pd.DataFrame = pd.read_csv(self.component_csv_path)
        augment_df: pd.DataFrame = pd.read_csv(self.augment_csv_path)

        # Remove components that have no resistance values
        self.useful_components = component_df[
            (component_df[self.resistance_types] != 0).any(axis=1)
            & (component_df["Required Player Level"] <= self.character_level)
        ]
        self.useful_components = self.useful_components.reset_index(drop=True)

        # First filter augments based on player faction standings
        filtered_augment_df = self.filter_augment_db(augment_df)
        # Remove augments that have no resistances values
        self.useful_augments = filtered_augment_df[
            (filtered_augment_df[self.resistance_types] != 0).any(axis=1)
            & (filtered_augment_df["Required Player Level"] <= self.character_level)
        ]
        self.useful_augments = self.useful_augments.reset_index(drop=True)

    def check_available_slots(
        self, unavailable_gear_slots: dict[str, bool]
    ) -> list[str]:
        """Calculate available gear slots based on the weapon template and blocked slots.

        Args:
            unavailable_gear_slots (dict[str, bool]): Dictionary containing availability info
                                                        of each gear slot denoted by True/False.

        Returns:
            list[str]: List of available gear slots based on weapon template as well as given unavailability.
        """
        available_gear_slots: list[str] = self.all_gear_slots.copy()
        if self.weapon_template == "one-hand-shield":
            available_gear_slots.remove("Off-Hand")
            available_gear_slots.remove("Two-Handed")
            available_gear_slots.remove("Ranged")
        elif self.weapon_template == "one-hand-offhand":
            available_gear_slots.remove("Shield")
            available_gear_slots.remove("Two-Handed")
            available_gear_slots.remove("Ranged")
        elif self.weapon_template == "two-hand":
            available_gear_slots.remove("One-Handed")
            available_gear_slots.remove("Off-Hand")
            available_gear_slots.remove("Ranged")
            available_gear_slots.remove("Shield")
        elif self.weapon_template == "ranged-offhand":
            available_gear_slots.remove("Shield")
            available_gear_slots.remove("Two-Handed")
            available_gear_slots.remove("One-Handed")

        def remove_gear(available_gear_slots: list[str], gear: str) -> list[str]:
            try:
                available_gear_slots.remove(gear)
            except ValueError:
                pass
            return available_gear_slots

        for slot, status in unavailable_gear_slots.items():
            if (status is True) and (slot == "Weapon"):
                for gear in ["One-Handed", "Two-Handed", "Ranged"]:
                    available_gear_slots = remove_gear(available_gear_slots, gear)
            elif (status is True) and (slot == "Off-Hand/Shield"):
                available_gear_slots = remove_gear(available_gear_slots, "Off-Hand")
                available_gear_slots = remove_gear(available_gear_slots, "Shield")
            elif status is True:
                available_gear_slots = remove_gear(available_gear_slots, slot)

        return available_gear_slots

    def filter_augment_db(self, augment_df: pd.DataFrame) -> pd.DataFrame:
        """Filter augment database based on player faction standings.

        Args:
            augment_df (pd.DataFrame): Dataframe containing all augment info.

        Returns:
            pd.DataFrame: Augment db dataframe filtered by player faction standings.
        """
        # Mapping of faction standings from str to int
        standing_levels: dict[str, int] = {
            "Friendly": 1,
            "Respected": 2,
            "Honored": 3,
            "Revered": 4,
        }

        # Map player's standings to numeric levels
        player_standings_num: dict[str, int] = {
            faction: standing_levels.get(level.title(), 0)
            for faction, level in self.player_faction_standings.items()
        }

        # Create numeric required standing column
        augment_df["RequiredStandingNum"] = (
            augment_df["Required Faction Level"].str.title().map(standing_levels)
        )

        # Define filter function
        def player_meets_requirement(row):
            player_level: int = player_standings_num.get(row["Faction"], 0)
            required_level: int = row["RequiredStandingNum"]
            if pd.isna(required_level):
                return False  # or True, as your policy
            return player_level >= required_level

        # Filter dataframe based on player standings
        filtered_augments = augment_df[
            augment_df.apply(player_meets_requirement, axis=1)
        ]

        return filtered_augments

    def generate_item_urls(
        self,
        selected_items: dict[str, dict[str, str]],
        component_df: pd.DataFrame,
        augment_df: pd.DataFrame,
    ) -> dict[str, dict[str, dict[str, str]]]:
        """Grab item URLs based on item name for both components and augments.

        Args:
            selected_items (dict[str, dict[str, str]]): Dictionary containing names of selected components and augments.
            component_df (pd.DataFrame): Dataframe containing info of useful components.
            augment_df (pd.DataFrame): Dataframe containing info of useful augments.

        Returns:
            dict[str, dict[str, dict[str, str]]]: Dictionary containing names and urls for selected components and augments.
        """
        combined_df: pd.DataFrame = pd.concat(
            [component_df, augment_df], ignore_index=True
        )

        def get_item_url(name: str) -> str:
            if not name:
                return ""
            item_info: pd.Series = combined_df[combined_df["Item"] == name]
            if not item_info.empty:
                item_id: int = int(item_info["ID"].iloc[0])
                return f"https://www.grimtools.com/db/items/{item_id}"
            else:
                return ""

        selected_items_with_urls: dict[str, dict[str, dict[str, str]]] = {}
        for slot, items in selected_items.items():
            augment_name: str = items.get("augment", "")
            component_name: str = items.get("component", "")
            selected_items_with_urls[slot] = {
                "Augment": {"Name": augment_name, "Url": get_item_url(augment_name)},
                "Component": {
                    "Name": component_name,
                    "Url": get_item_url(component_name),
                },
            }

        return selected_items_with_urls

    def generated_selected_items_dict(self) -> dict[str, dict[str, str]]:
        """Generates an empty dictionary based on the weapon template
        to store information of the items to be selected

        Returns:
            dict[str, dict[str, str]]: Empty dictionary for each remaining item based on weapon template
        """
        final_slots: list[str] = self.all_gear_slots.copy()
        if self.weapon_template == "one-hand-shield":
            final_slots.remove("Off-Hand")
            final_slots.remove("Two-Handed")
            final_slots.remove("Ranged")
        elif self.weapon_template == "one-hand-offhand":
            final_slots.remove("Shield")
            final_slots.remove("Two-Handed")
            final_slots.remove("Ranged")
        elif self.weapon_template == "two-hand":
            final_slots.remove("One-Handed")
            final_slots.remove("Off-Hand")
            final_slots.remove("Ranged")
            final_slots.remove("Shield")
        elif self.weapon_template == "ranged-offhand":
            final_slots.remove("Shield")
            final_slots.remove("Two-Handed")
            final_slots.remove("One-Handed")

        selected_items: dict[str, dict[str, str]] = {
            key: {"component": "", "augment": ""} for key in final_slots
        }
        return selected_items

    def optimize_resistances(
        self,
    ) -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, int]]:
        """Generate optimal combination of components and augments for each slot based on given info.

        Returns:
            dict[str, dict[str, dict[str, str]]]: Dictionary containing names and urls for selected components and augments.
            dict[str, int]: Dictionary containing final resistance values after updating
                                current resistances with values from chosen components and augments.
        """
        # Create the problem - now maximizing resistance achievement
        prob = pulp.LpProblem(
            "Multi_Objective_Resistance_Optimization", pulp.LpMaximize
        )

        # Decision variables: binary variable for each component-slot combination
        component_slot_vars = {}
        for i, item in self.useful_components.iterrows():
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            for slot in allowed_gear_slots:
                var_name = f"Item_{i}_{item['Item']}_in_{slot}"
                component_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat="Binary")

        # Decision variables: binary variable for each augment-slot combination
        augment_slot_vars = {}
        for i, item in self.useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            for slot in allowed_gear_slots:
                var_name = f"Item_{i}_{item['Item']}_in_{slot}"
                augment_slot_vars[(i, slot)] = pulp.LpVariable(var_name, cat="Binary")

        # Additional variables for resistance achievement tracking
        resistance_achieved = {}
        for resistance in self.resistance_types:
            resistance_achieved[resistance] = pulp.LpVariable(
                f"Achieved_{resistance}", lowBound=0
            )

        # Multi-objective function with weighted priorities
        # Weight for achieving target resistances (primary objective)
        # Penalty for number of items used (secondary objective)
        resistance_weight = 1  # Weight for resistance achievement
        item_penalty_weight = 1  # Penalty for each item used

        # Primary objective: Maximize resistance achievement while minimizing items
        resistance_objectives = []
        for resistance in self.resistance_types:
            # Reward achieving the full target (60 points needed)
            needed = self.remaining_resistances[resistance]
            if needed > 0:
                # Use min function to cap at target - this rewards reaching exactly the target
                resistance_objectives.append(resistance_achieved[resistance])

        # Secondary objective: Minimize number of components used
        total_components_used = []
        for i, item in self.useful_components.iterrows():
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            item_vars_for_this_item = [component_slot_vars[(i, slot)] for slot in allowed_gear_slots]
            if item_vars_for_this_item:
                # This represents whether this item is used (in any slot)
                total_components_used.append(pulp.lpSum(item_vars_for_this_item))

        # Secondary objective: Minimize number of augments used
        total_augments_used = []
        for i, item in self.useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            item_vars_for_this_item = [augment_slot_vars[(i, slot)] for slot in allowed_gear_slots]
            if item_vars_for_this_item:
                # This represents whether this item is used (in any slot)
                total_augments_used.append(pulp.lpSum(item_vars_for_this_item))

        prob += (
            resistance_weight * pulp.lpSum(resistance_objectives)
            - item_penalty_weight * pulp.lpSum(total_components_used)
            - item_penalty_weight * pulp.lpSum(total_augments_used)
        )

        # Constraint: Total components and augments selected must be <= max_items
        prob += pulp.lpSum(total_components_used) <= len(self.available_component_slots)
        prob += pulp.lpSum(total_augments_used) <= len(self.available_augment_slots)

        # Constraint: Each gear slot can only have one component
        for slot in self.available_component_slots:
            indices_list = self.useful_components[self.useful_components[slot]].index.tolist()
            items_for_slot = [(idx, slot) for idx in indices_list]
            if items_for_slot:
                prob += (
                    pulp.lpSum([component_slot_vars[item_slot] for item_slot in items_for_slot])
                    <= 1
                )

        # Constraint: Each gear slot can only have one augment
        for slot in self.available_augment_slots:
            indices_list = self.useful_augments[
                self.useful_augments[slot]
            ].index.tolist()
            items_for_slot = [(idx, slot) for idx in indices_list]
            if items_for_slot:
                prob += (
                    pulp.lpSum([augment_slot_vars[item_slot] for item_slot in items_for_slot])
                    <= 1
                )

        # Constraint: Link resistance achieved variables to actual resistance gained
        for resistance in self.resistance_types:
            needed = self.remaining_resistances[resistance]
            if needed > 0:
                resistance_sum = []

                for i, item in self.useful_components.iterrows():
                    allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
                    for slot in allowed_gear_slots:
                        if (i, slot) in component_slot_vars:
                            resistance_sum.append(component_slot_vars[(i, slot)] * item[resistance])

                for i, item in self.useful_augments.iterrows():
                    allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
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

        if status == "Optimal" or status == "Infeasible":
            selected_items = self.generated_selected_items_dict()
            final_resistances = self.current_resistances.copy()

            for i, item in self.useful_components.iterrows():
                allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
                for slot in allowed_gear_slots:
                    if (i, slot) in component_slot_vars and component_slot_vars[(i, slot)].varValue == 1:
                        selected_items[slot]["component"] = item["Item"]
                        for res in self.resistance_types:
                            final_resistances[res] += item[res]

            for i, item in self.useful_augments.iterrows():
                allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
                for slot in allowed_gear_slots:
                    if (i, slot) in augment_slot_vars and augment_slot_vars[(i, slot)].varValue == 1:
                        selected_items[slot]["augment"] = item["Item"]
                        for res in self.resistance_types:
                            final_resistances[res] += item[res]

            # Set slot as unavailable instead of just empty string to differenciate from free slots
            for key, _ in selected_items.items():
                if key not in self.available_component_slots:
                    selected_items[key]["component"] = "Slot Unavailable"
                if key not in self.available_augment_slots:
                    selected_items[key]["augment"] = "Slot Unavailable"

            selected_items_with_urls = self.generate_item_urls(
                selected_items, self.useful_components, self.useful_augments
            )

            return selected_items_with_urls, final_resistances
