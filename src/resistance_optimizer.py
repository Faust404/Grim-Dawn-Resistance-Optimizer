from dataclasses import dataclass
from math import ceil

import pandas as pd
import pulp


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
    component_blacklist: list[str] = None
    augment_blacklist: list[str] = None

    player_faction_standings: dict[str, str] = None

    current_resistances: dict[str, int] = None
    target_resistances: dict[str, int] = None
    remaining_resistances: dict[str, int] = None

    component_csv_path: str = "data/component_data.csv"
    augment_csv_path: str = "data/augment_data.csv"
    weapon_template: str = "one-hand-offhand"
    character_level: int = 100
    current_armor_abs_percentage: int = 70
    required_armor_abs_percentage: int = 43
    final_armor_abs_percentage: int = 70

    def __post_init__(self):
        """Post Init function to perform certain operations on object creation."""
        self.set_defaults()
        self.calculate_remaining_resistances()
        self.calculate_required_armor_abs_percentage()
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
            "Ring 1",
            "Ring 2",
            "Medal",
            'Melee-Caster-1h 1',
            'Melee-Caster-1h 2',
            'Ranged-1h 1',
            'Ranged-1h 2',
            'Melee-2h',
            'Ranged-2h',
            'Off-Hand',
            'Shield',
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
            res: max(0, self.target_resistances[res] - self.current_resistances[res])
            for res in self.resistance_types
        }

    def calculate_required_armor_abs_percentage(self) -> None:
        """Calculate the required armor absorption percentage based on current armor absorption value."""
        self.required_armor_abs_percentage = ceil(((100 - self.current_armor_abs_percentage)/self.current_armor_abs_percentage)*100)

    def filter_useful_components_augments(self) -> None:
        """Filter out useful components and augments based on character level and player faction standings."""
        # Load the component and augment databases
        component_df: pd.DataFrame = pd.read_csv(self.component_csv_path)
        augment_df: pd.DataFrame = pd.read_csv(self.augment_csv_path)

        # Filter components based on blacklist
        filtered_component_df: pd.DataFrame = component_df[~component_df['Item'].isin(self.component_blacklist)]
        # Remove components that don't meet required player level
        self.useful_components = filtered_component_df[
            (filtered_component_df["Required Player Level"] <= self.character_level)
        ]
        self.useful_components = self.useful_components.reset_index(drop=True)

        # First filter augments based on player faction standings
        filtered_augment_df: pd.DataFrame = self.filter_augment_db(augment_df)
        # Filter augments based on blacklist
        filtered_augment_df = filtered_augment_df[~filtered_augment_df['Item'].isin(self.augment_blacklist)]
        # Remove augments that don't meet required player level
        self.useful_augments = filtered_augment_df[
            (filtered_augment_df["Required Player Level"] <= self.character_level)
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

        # Remove unavailable gear slots based on weapon template
        available_gear_slots = self.process_weapon_template(available_gear_slots)

        for slot, status in unavailable_gear_slots.items():
            gear_to_remove: list[str] = []
            if (status is True) and (slot == "Weapon"):
                gear_to_remove = ["Melee-Caster-1h 1", "Melee-Caster-1h 2", "Ranged-1h 1", "Ranged-1h 2", "Melee-2h", "Ranged-2h"]
            elif (status is True) and (slot == "Off-Hand/Shield"):
                gear_to_remove = ["Melee-Caster-1h 2", "Ranged-1h 2", "Off-Hand", "Shield"]
            elif status is True:
                gear_to_remove = [slot]
            available_gear_slots = self.remove_multiple_gear_slots(available_gear_slots, gear_to_remove)
        
        return available_gear_slots

    def remove_multiple_gear_slots(self, available_gear_slots: list[str], gear_to_remove: list[str]) -> list[str]:
        """Given a list of slots, remove them from all from the available list

        Args:
            available_gear_slots (list[str]): List of available gear slots
            gear_to_remove (list[str]): List of gear to be removed

        Returns:
            list[str]: List of available gear slots
        """
        for gear in gear_to_remove:
            try:
                available_gear_slots.remove(gear)
            except ValueError:
                pass
        return available_gear_slots

    def process_weapon_template(self, available_gear_slots: list[str]) -> list[str]:
        """Adjust list of available gear slots based on the weapon template

        Args:
            available_gear_slots (list[str]): List of available gear slots

        Returns:
            list[str]: List of available gear slots
        """
        weapon_template_gear_slots: list[str] = [
            'Melee-Caster-1h 1',
            'Melee-Caster-1h 2',
            'Ranged-1h 1',
            'Ranged-1h 2',
            'Melee-2h',
            'Ranged-2h',
            'Off-Hand',
            'Shield',
        ]
        gear_to_remove: list[str] = []
        gear_to_keep: list[str] = []
        if self.weapon_template == "one-hand-shield":
            gear_to_keep = ["Melee-Caster-1h 1", "Shield"]
        elif self.weapon_template == "one-hand-offhand":
            gear_to_keep = ["Melee-Caster-1h 1", "Off-Hand"]
        elif self.weapon_template == "one-hand-one-hand":
            gear_to_keep = ["Melee-Caster-1h 1", "Melee-Caster-1h 2"]
        elif self.weapon_template == "ranged-offhand":
            gear_to_keep = ["Ranged-1h 1", "Off-Hand"]
        elif self.weapon_template == "ranged-ranged":
            gear_to_keep = ["Ranged-1h 1", "Ranged-1h 2"]
        elif self.weapon_template == "two-hand-melee":
            gear_to_keep = ["Melee-2h"]
        elif self.weapon_template == "two-hand-ranged":
            gear_to_keep = ["Ranged-2h"]
        gear_to_remove = [gear_piece for gear_piece in weapon_template_gear_slots if gear_piece not in gear_to_keep]
        available_gear_slots = self.remove_multiple_gear_slots(available_gear_slots, gear_to_remove)
    
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

    def generate_item_urls_and_tags(
        self,
        selected_items: dict[str, dict[str, str]],
        component_df: pd.DataFrame,
        augment_df: pd.DataFrame,
    ) -> dict[str, dict[str, dict[str, str]]]:
        """Generate item URLs and tags based on item name for both components and augments.

        Args:
            selected_items (dict[str, dict[str, str]]): Dictionary containing names of selected components and augments.
            component_df (pd.DataFrame): Dataframe containing info of useful components.
            augment_df (pd.DataFrame): Dataframe containing info of useful augments.

        Returns:
            dict[str, dict[str, dict[str, str]]]: Dictionary containing names, URLs, and tags for selected components and augments.
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
            return ""

        def get_item_tag(name: str) -> str:
            if not name:
                return ""
            item_info: pd.Series = combined_df[combined_df["Item"] == name]
            if not item_info.empty:
                return str(item_info["Item Tag"].iloc[0])
            return ""

        selected_items_with_urls_and_tags: dict[str, dict[str, dict[str, str]]] = {}
        for slot, items in selected_items.items():
            augment_name: str = items.get("augment", "")
            component_name: str = items.get("component", "")
            selected_items_with_urls_and_tags[slot] = {
                "Augment": {
                    "Name": augment_name,
                    "Url": get_item_url(augment_name),
                    "Tag": get_item_tag(augment_name)
                },
                "Component": {
                    "Name": component_name,
                    "Url": get_item_url(component_name),
                    "Tag": get_item_tag(component_name)
                },
            }

        return selected_items_with_urls_and_tags

    def generated_selected_items_dict(self) -> dict[str, dict[str, str]]:
        """Generates an empty dictionary based on the weapon template
        to store information of the items to be selected

        Returns:
            dict[str, dict[str, str]]: Empty dictionary for each remaining item based on weapon template
        """
        final_slots: list[str] = self.all_gear_slots.copy()
        final_slots = self.process_weapon_template(final_slots)

        selected_items: dict[str, dict[str, str]] = {
            key: {"component": "", "augment": ""} for key in final_slots
        }
        return selected_items

    def optimize_resistances(self):
        # Create the problem - now minimizing the total shortfall in resistances and armor absorption percentage
        prob = pulp.LpProblem("Resistance_Optimization", pulp.LpMinimize)

        # Decision variables: binary variable for each component-slot combination
        component_slot_vars = {}
        for i, item in self.useful_components.iterrows():
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            for slot in allowed_gear_slots:
                component_slot_vars[(i, slot)] = pulp.LpVariable(f"comp_{i}_{slot}", cat="Binary")

        # Decision variables: binary variable for each augment-slot combination
        augment_slot_vars = {}
        for i, item in self.useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            for slot in allowed_gear_slots:
                augment_slot_vars[(i, slot)] = pulp.LpVariable(f"aug_{i}_{slot}", cat="Binary")

        # Constraint: Each gear slot can only have one component
        for slot in self.available_component_slots:
            items_for_slot = [
                (i, slot)
                for i, item in self.useful_components.iterrows()
                if item[slot] and (i, slot) in component_slot_vars
            ]
            if items_for_slot:
                prob += pulp.lpSum(component_slot_vars[idx] for idx in items_for_slot) <= 1

        # Constraint: Each gear slot can only have one augment
        for slot in self.available_augment_slots:
            items_for_slot = [
                (i, slot)
                for i, item in self.useful_augments.iterrows()
                if item[slot] and (i, slot) in augment_slot_vars
            ]
            if items_for_slot:
                prob += pulp.lpSum(augment_slot_vars[idx] for idx in items_for_slot) <= 1

        # Error variables for shortfall in resistances and armor absorption percentage
        resistance_shortfall = {
            res: pulp.LpVariable(f"shortfall_{res}", lowBound=0, cat="Continuous")
            for res in self.resistance_types
        }
        armor_shortfall = pulp.LpVariable("shortfall_armor", lowBound=0, cat="Continuous")

        # Secondary objective: Minimize number of components used
        component_count = []
        for i, item in self.useful_components.iterrows():
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            if allowed_gear_slots:
                component_count.append(pulp.lpSum(component_slot_vars[(i, slot)] for slot in allowed_gear_slots))

        # Secondary objective: Minimize number of augments used
        augment_count = []
        for i, item in self.useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            if allowed_gear_slots:
                augment_count.append(pulp.lpSum(augment_slot_vars[(i, slot)] for slot in allowed_gear_slots))

        # Primary objective: Minimize total shortfall in resistances
        for res in self.resistance_types:
            gained = []
            for i, item in self.useful_components.iterrows():
                for slot in self.available_component_slots:
                    if item[slot] and (i, slot) in component_slot_vars:
                        gained.append(component_slot_vars[(i, slot)] * item[res])

            for i, item in self.useful_augments.iterrows():
                for slot in self.available_augment_slots:
                    if item[slot] and (i, slot) in augment_slot_vars:
                        gained.append(augment_slot_vars[(i, slot)] * item[res])

            prob += self.current_resistances[res] + pulp.lpSum(gained) + resistance_shortfall[res] >= self.target_resistances[res]

        # Primary objective: Minimize total shortfall in armor absorption percentage
        armor_abs_gained = []
        for i, item in self.useful_components.iterrows():
            for slot in self.available_component_slots:
                if item[slot] and (i, slot) in component_slot_vars:
                    armor_abs_gained.append(component_slot_vars[(i, slot)] * item.get("Armor Absorption %", 0))

        for i, item in self.useful_augments.iterrows():
            for slot in self.available_augment_slots:
                if item[slot] and (i, slot) in augment_slot_vars:
                    armor_abs_gained.append(augment_slot_vars[(i, slot)] * item.get("Armor Absorption %", 0))

        # Make sure armor abs percentage gained from items is more than the required 43% to hit the cap
        armor_absorption_percentage_gained = pulp.lpSum(armor_abs_gained)
        prob += armor_absorption_percentage_gained + armor_shortfall >= self.required_armor_abs_percentage

        # Penalize shortfalls heavily in the objective function to prioritize meeting resistance and armor absorption targets
        res_penalty = 1e4
        armor_penalty = 1e3
        item_penalty = 1

        prob += (
            (res_penalty * pulp.lpSum(resistance_shortfall.values()))
            + (armor_penalty * armor_shortfall)
            + (item_penalty * (pulp.lpSum(component_count) + pulp.lpSum(augment_count)))
        )

        # Initialize the solver and solve the problem
        prob.solve(pulp.PULP_CBC_CMD(msg=0))

        status = pulp.LpStatus[prob.status]
        if status != "Optimal":
            return None, None, None

        selected_items = self.generated_selected_items_dict()
        final_resistances = self.current_resistances.copy()
        armor_absorption_percentage_gained = 0

        for i, item in self.useful_components.iterrows():
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            for slot in allowed_gear_slots:
                if (
                    (i, slot) in component_slot_vars
                    and component_slot_vars[(i, slot)].varValue is not None
                    and component_slot_vars[(i, slot)].varValue > 0.5
                ):
                    selected_items[slot]["component"] = item["Item"]
                    armor_absorption_percentage_gained += item.get("Armor Absorption %", 0)
                    for res in self.resistance_types:
                        final_resistances[res] += item[res]

        for i, item in self.useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            for slot in allowed_gear_slots:
                if (
                    (i, slot) in augment_slot_vars
                    and augment_slot_vars[(i, slot)].varValue is not None
                    and augment_slot_vars[(i, slot)].varValue > 0.5
                ):
                    selected_items[slot]["augment"] = item["Item"]
                    armor_absorption_percentage_gained += item.get("Armor Absorption %", 0)
                    for res in self.resistance_types:
                        final_resistances[res] += item[res]

        for key in selected_items:
            if key not in self.available_component_slots:
                selected_items[key]["component"] = "Slot Unavailable"
            if key not in self.available_augment_slots:
                selected_items[key]["augment"] = "Slot Unavailable"

        selected_items_with_urls_and_tags = self.generate_item_urls_and_tags(
            selected_items, self.useful_components, self.useful_augments
        )

        self.final_armor_abs_percentage = round(
            self.current_armor_abs_percentage * (1 + (armor_absorption_percentage_gained / 100)), 1
        )
        return selected_items_with_urls_and_tags, final_resistances, self.final_armor_abs_percentage
