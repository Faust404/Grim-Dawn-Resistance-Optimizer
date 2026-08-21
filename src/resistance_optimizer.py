from dataclasses import dataclass
from math import ceil

import pandas as pd
import pulp


def _make_solver() -> pulp.LpSolver:
    """Return the fastest available MILP solver: HiGHS (via the highspy Python
    bindings) when installed, otherwise fall back to PuLP's default CBC binary."""
    try:
        import highspy  # noqa: F401  # bindings present -> use HiGHS

        return pulp.HiGHS(msg=0)
    except ImportError:
        return pulp.PULP_CBC_CMD(msg=0)


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

    def optimize_resistances(
        self,
        secondary_stats: list[str] | list[list[str]] | None = None,
        base_secondary_stat_values: dict[str, float] | float | None = None,
    ):
        # Decision variables: binary variable for each component-slot combination
        component_slot_vars = {}
        for i, item in self.useful_components.iterrows():
            # Initialize the secondary_stat_gain list
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            for slot in allowed_gear_slots:
                component_slot_vars[(i, slot)] = pulp.LpVariable(f"comp_{i}_{slot}", cat="Binary")

        # Decision variables: binary variable for each augment-slot combination
        augment_slot_vars = {}
        for i, item in self.useful_augments.iterrows():
            # Initialize the augment_slot_vars dictionary
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            for slot in allowed_gear_slots:
                augment_slot_vars[(i, slot)] = pulp.LpVariable(f"aug_{i}_{slot}", cat="Binary")

        # Error variables for shortfall in resistances and armor absorption percentage
        resistance_shortfall = {
            res: pulp.LpVariable(f"shortfall_{res}", lowBound=0, cat="Continuous")
            for res in self.resistance_types
        }
        armor_shortfall = pulp.LpVariable("shortfall_armor", lowBound=0, cat="Continuous")

        # Secondary objective: Minimize number of components used
        component_count = []
        for i, item in self.useful_components.iterrows():
            # Count components for optimization
            allowed_gear_slots = [slot for slot in self.available_component_slots if item[slot]]
            if allowed_gear_slots:
                component_count.append(pulp.lpSum(component_slot_vars[(i, slot)] for slot in allowed_gear_slots))

        # Secondary objective: Minimize number of augments used
        augment_count = []
        for i, item in self.useful_augments.iterrows():
            allowed_gear_slots = [slot for slot in self.available_augment_slots if item[slot]]
            if allowed_gear_slots:
                augment_count.append(pulp.lpSum(augment_slot_vars[(i, slot)] for slot in allowed_gear_slots))

        def add_core_constraints(problem):
            # Constraint: Each gear slot can only have one component
            for slot in self.available_component_slots:
                items_for_slot = [
                    (i, slot)
                    for i, item in self.useful_components.iterrows()
                    if item[slot] and (i, slot) in component_slot_vars
                ]
                if items_for_slot:
                    problem += pulp.lpSum(component_slot_vars[idx] for idx in items_for_slot) <= 1

            # Constraint: Each gear slot can only have one augment
            for slot in self.available_augment_slots:
                items_for_slot = [
                    (i, slot)
                    for i, item in self.useful_augments.iterrows()
                    if item[slot] and (i, slot) in augment_slot_vars
                ]
                if items_for_slot:
                    problem += pulp.lpSum(augment_slot_vars[idx] for idx in items_for_slot) <= 1

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

                problem += self.current_resistances[res] + pulp.lpSum(gained) + resistance_shortfall[res] >= self.target_resistances[res]

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

            armor_absorption_percentage_gained_expr = pulp.lpSum(armor_abs_gained)
            problem += armor_absorption_percentage_gained_expr + armor_shortfall >= self.required_armor_abs_percentage

            return armor_absorption_percentage_gained_expr

        # Penalize shortfalls heavily in the objective function to prioritize meeting resistance and armor absorption targets
        res_penalty = 1e4
        armor_penalty = 1e3
        item_penalty = 1

        primary_problem = pulp.LpProblem("Resistance_Optimization", pulp.LpMinimize)
        # Add core constraints to the primary problem
        add_core_constraints(primary_problem)
        primary_problem += (
            (res_penalty * pulp.lpSum(resistance_shortfall.values()))
            + (armor_penalty * armor_shortfall)
            + (item_penalty * (pulp.lpSum(component_count) + pulp.lpSum(augment_count)))
        )

        primary_problem.solve(_make_solver())

        status = pulp.LpStatus[primary_problem.status]
        if status != "Optimal":
            return None, None, None

        optimal_resistance_shortfalls = {
            res: resistance_shortfall[res].varValue or 0
            for res in self.resistance_types
        }
        optimal_armor_shortfall = armor_shortfall.varValue or 0

        # Secondary optimization: priority tiers. `secondary_stats` supports two shapes:
        #   - a flat list ["OA", "DA"]            -> strict priority (OA > DA)
        #   - a list of tiers [["OA", "DA"], ["Health"]]
        #     -> stats inside one tier have EQUAL priority and are balanced together
        #     -> tiers keep strict priority (tier 1 above tier 2, ...)
        # A single weighted sum of raw gains cannot guarantee either behavior: a stat
        # with larger item values dominates regardless of priority (e.g. weight 5 * OA
        # is beaten when DA gains exceed 5x OA gains). So tiers are solved
        # lexicographically, and within a tier every stat's gain is normalized by its
        # own achievable maximum, putting all stats on a comparable 0-1 scale before
        # weighting them equally.
        # None (the default) means no secondary optimization at all: only the primary
        # shortfall/item-count problem is solved, like the production optimizer.
        if secondary_stats is None:
            secondary_stats = []

        # Normalize the input into tiers; a flat list means strict priority
        if secondary_stats and isinstance(secondary_stats[0], list):
            stat_tiers: list[list[str]] = [list(tier) for tier in secondary_stats]
        else:
            stat_tiers = [[stat] for stat in secondary_stats]

        all_secondary_stats = [stat for tier in stat_tiers for stat in tier]

        # Per-stat base values used to linearize percent gains into equivalent flat
        # units: percent of the stat's typical in-game base (OA/DA/Armor ~2500,
        # Health ~10k). Stats without an entry default to 1 (pure % stats like
        # ADCTH/Move/Attack/Cast Speed have no flat items and are just scaled by 1).
        # A plain float is accepted for backwards compatibility (same base for all).
        if base_secondary_stat_values is None:
            base_secondary_stat_values = {}
        elif isinstance(base_secondary_stat_values, (int, float)):
            base_secondary_stat_values = {
                stat: float(base_secondary_stat_values) for stat in all_secondary_stats
            }

        # Build per-stat gain expressions (linearized percent contribution)
        stat_gain_terms: dict[str, list] = {stat: [] for stat in all_secondary_stats}
        for i, item in self.useful_components.iterrows():
            for slot in self.available_component_slots:
                if item[slot] and (i, slot) in component_slot_vars:
                    for stat in all_secondary_stats:
                        flat = item.get(stat, 0)
                        pct = item.get(f"{stat} %", 0)
                        base_value = base_secondary_stat_values.get(stat, 1.0)
                        equiv_flat = flat + (base_value * pct / 100.0)
                        stat_gain_terms[stat].append(component_slot_vars[(i, slot)] * equiv_flat)

        for i, item in self.useful_augments.iterrows():
            for slot in self.available_augment_slots:
                if item[slot] and (i, slot) in augment_slot_vars:
                    for stat in all_secondary_stats:
                        flat = item.get(stat, 0)
                        pct = item.get(f"{stat} %", 0)
                        base_value = base_secondary_stat_values.get(stat, 1.0)
                        equiv_flat = flat + (base_value * pct / 100.0)
                        stat_gain_terms[stat].append(augment_slot_vars[(i, slot)] * equiv_flat)

        total_items_expr = pulp.lpSum(component_count) + pulp.lpSum(augment_count)
        tiny_eps = 1e-4        # slack for preservation constraints and raw-gain tie-breaks
        normalized_eps = 1e-6  # tie-break on normalized (0-1) objectives, below any real gain difference

        # Build a sub-problem that pins the primary shortfalls and preserves every
        # higher-priority stat already optimized.
        def build_secondary_problem(preserved_values: dict[str, float]) -> pulp.LpProblem:
            sub_problem = pulp.LpProblem("Secondary_Stat_Optimization", pulp.LpMaximize)
            add_core_constraints(sub_problem)

            # Pin the primary shortfalls so resists/AA targets stay exactly as before
            for res, shortfall_value in optimal_resistance_shortfalls.items():
                sub_problem += resistance_shortfall[res] == shortfall_value
            sub_problem += armor_shortfall == optimal_armor_shortfall

            # Keep every higher-priority stat at its optimum (tiny slack for solver tolerance)
            for stat, opt_value in preserved_values.items():
                sub_problem += pulp.lpSum(stat_gain_terms[stat]) >= opt_value - tiny_eps

            return sub_problem

        # Achieved values that lower tiers must preserve
        preserved_values: dict[str, float] = {}

        for tier in stat_tiers:
            # 1) Per-stat maxima inside this tier: the normalization scale that makes
            #    equal-priority stats comparable. A stat with no item sources has max 0
            #    and is simply excluded from the balanced objective.
            max_gain: dict[str, float] = {}
            for stat in tier:
                sub_problem = build_secondary_problem(preserved_values)
                sub_problem += pulp.lpSum(stat_gain_terms[stat]) - tiny_eps * total_items_expr
                sub_problem.solve(_make_solver())

                if pulp.LpStatus[sub_problem.status] != "Optimal":
                    return None, None, None

                max_gain[stat] = pulp.lpSum(stat_gain_terms[stat]).value()

            # 2) Balanced solve for equal-priority stats: maximize the sum of normalized
            #    gains so no stat's raw magnitude can dominate the others. For a
            #    single-stat tier the max solve above is already the optimum.
            if len(tier) > 1:
                normalizable_stats = [stat for stat in tier if max_gain[stat] > 0]
                if normalizable_stats:
                    sub_problem = build_secondary_problem(preserved_values)
                    sub_problem += (
                        pulp.lpSum(
                            pulp.lpSum(stat_gain_terms[stat]) / max_gain[stat]
                            for stat in normalizable_stats
                        )
                        - normalized_eps * total_items_expr
                    )
                    sub_problem.solve(_make_solver())

                    if pulp.LpStatus[sub_problem.status] != "Optimal":
                        return None, None, None

            # 3) Record the values achieved in this tier; lower tiers must keep them
            for stat in tier:
                preserved_values[stat] = pulp.lpSum(stat_gain_terms[stat]).value()

        selected_items = self.generated_selected_items_dict()
        final_resistances = self.current_resistances.copy()
        armor_absorption_percentage_gained = 0

        # Raw flat/% gains of the chosen items, per secondary stat the user asked
        # to optimize (empty when no secondary optimization was requested)
        secondary_gains: dict[str, dict[str, float]] = {
            stat: {"flat": 0, "pct": 0} for stat in all_secondary_stats
        }

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
                    for stat in all_secondary_stats:
                        secondary_gains[stat]["flat"] += item.get(stat, 0)
                        secondary_gains[stat]["pct"] += item.get(f"{stat} %", 0)
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
                    for stat in all_secondary_stats:
                        secondary_gains[stat]["flat"] += item.get(stat, 0)
                        secondary_gains[stat]["pct"] += item.get(f"{stat} %", 0)
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
        return (
            selected_items_with_urls_and_tags,
            final_resistances,
            self.final_armor_abs_percentage,
            secondary_gains,
        )
