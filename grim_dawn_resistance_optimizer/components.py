from dataclasses import dataclass, field
from icecream import ic


@dataclass
class Components:
    all_gear_slots: list[str] = None
    resistance_types: list[str] = None
    free_slots: list[str] = None
    unavailable_component_slots: dict[str, int] = None
    available_component_slots: list[str] = None
    unavailable_augment_slots: dict[str, int] = None
    available_augment_slots: list[str] = None
    current_resistances: dict[str, int] = None
    remaining_resistances: dict[str, int] = None
    allocated_slots: dict[str, int] = None
    component_csv_path: str = "data/component_data.csv"
    augment_csv_path: str = "data/augment_data.csv"
    weapon_template: str = "one-hand-offhand"
    character_level: int = 100


    def __post_init__(self):
        self.set_defaults()
        self.calculate_remaining_resistances()
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
        self.remaining_resistances = {res: max(0, 80 - self.current_resistances[res]) for res in self.resistance_types}


    def check_available_slots(self, unavailable_gear_slots) -> list[str]:
        """Calculate available gear slots based on the weapon template and blocked slots."""
        available_gear_slots = self.all_gear_slots.copy()
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
        
        for slot, status in unavailable_gear_slots.items():
            if (status is True) and (slot == "Weapon"):
                for gear in ["One-Handed", "Two-Handed", "Ranged"]:
                    try:
                        available_gear_slots.remove(gear)
                    except ValueError:
                        pass
            elif status is True:
                try:
                    available_gear_slots.remove(slot)
                except ValueError:
                    pass
        
        return available_gear_slots


    def show_slot_allocation(self, slot_status) -> None:
        # Allocated items
        self.allocated_slots = {slot: item for slot, item in slot_status.items() if item is not None}
        # Free slots
        self.free_slots = [slot for slot, item in slot_status.items() if item is None]
        print(f"{len(self.allocated_slots.keys())} out of {len(slot_status.keys())} slots allocated")
        ic(self.allocated_slots)
        ic(self.free_slots)


    def calculate_penalty(self, current_resistances: dict[str, int]) -> None:
        penalty = 0
        for res in self.resistance_types:
            penalty += max(0, 80 - current_resistances[res])
        ic(penalty)
