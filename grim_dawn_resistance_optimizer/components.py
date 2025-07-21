from dataclasses import dataclass, field
from icecream import ic


@dataclass
class Components:
    gear_slots: list[str]
    resistances: list[str]
    current_resistances: dict[str, int] = field(default_factory=dict)
    needed_resistances: dict[str, int] = field(default_factory=dict)
    component_csv_path: str = "data/component_data.csv"
    augment_csv_path: str = "data/augment_data.csv"
    character_level: int = 70

    def __init__(self):
        self.gear_slots = [
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
            "Off-Hand",
            # "Two-Handed",
            # "Shield",
        ]

        self.resistances = [
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

        self.current_resistances = {resistance: 0 for resistance in self.resistances}

        # self.current_resistances = {
        #     'Fire Resistance': 20,
        #     'Cold Resistance': 10,
        #     'Lightning Resistance': 10,
        #     'Poison & Acid Resistance': 30,
        #     'Pierce Resistance': 40,
        #     'Bleeding Resistance': 30,
        #     'Vitality Resistance': 50,
        #     'Aether Resistance': 60,
        #     'Chaos Resistance': 40
        # }

        self.needed_resistances = {res: 80 - self.current_resistances[res] for res in self.resistances}

    def show_slot_allocation(self, slot_status) -> None:
        # Allocated items
        allocated_slots = {slot: item for slot, item in slot_status.items() if item is not None}
        # Free slots
        free_slots = [slot for slot, item in slot_status.items() if item is None]
        print(f"{len(allocated_slots.keys())} out of {len(slot_status.keys())} slots allocated")
        ic(allocated_slots)
        ic(free_slots)

    def calculate_penalty(self, current_resistances: dict[str, int]) -> None:
        penalty = 0
        for res in self.resistances:
            penalty += max(0, 80 - current_resistances[res])
        ic(penalty)
