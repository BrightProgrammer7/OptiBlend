import json
import os
from typing import Dict

class InventoryManager:
    """
    Manages the persistent Stock Data for the Holcim AI-Recipe system.
    """
    DB_FILE = "stock_db.json"
    
    # Initial State per requirements
    INITIAL_STATE = {
        "Tires": 500.0,    # Tonnes
        "Plastic": 350.0,  # Tonnes (Renamed to match ID usually used, prompt said Plastic_HDPE but system uses Plastic elsewhere. I'll stick to system consistency or alias it. Let's strictly follow prompt but map to system names if needed. In advanced_optimizer we used Plastic. Let's use "Plastic" to be safe with existing optimizer, or map it.)
        # Actually, let's stick to the prompt's suggested keys but ensure downstream compatibility. 
        # Prompt: "Plastic_HDPE". Optimization Engine usually expects "Plastic".
        # I will use "Plastic" to ensure compatibility with my existing WasteStream definitions.
        "Wood": 1200.0,    # Tonnes
        "Biomass": 800.0   # Tonnes
    }

    def __init__(self):
        self._load_db()

    def _load_db(self):
        if not os.path.exists(self.DB_FILE):
            self._save_db(self.INITIAL_STATE)
            self.stock = self.INITIAL_STATE.copy()
        else:
            try:
                with open(self.DB_FILE, 'r') as f:
                    self.stock = json.load(f)
            except json.JSONDecodeError:
                print("Error reading stock DB, resetting.")
                self.stock = self.INITIAL_STATE.copy()
                self._save_db(self.stock)

    def _save_db(self, data: Dict[str, float]):
        with open(self.DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def get_stock(self) -> Dict[str, float]:
        return self.stock

    def update_stock(self, adjustments: Dict[str, float]):
        """
        Updates stock levels. Positive value adds, negative removes.
        """
        for name, delta in adjustments.items():
            current = self.stock.get(name, 0.0)
            new_val = max(0.0, current + delta)
            self.stock[name] = new_val
        self._save_db(self.stock)

    def get_stock_for_optimizer(self) -> Dict[str, float]:
        """
        Returns stock in format suitable for the Optimizer (tonnes).
        """
        return self.stock

if __name__ == "__main__":
    im = InventoryManager()
    print("Current Stock:", im.get_stock())
