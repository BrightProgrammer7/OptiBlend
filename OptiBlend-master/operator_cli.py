import time
import os
import sys
from datetime import datetime

# Import Modules
from inventory_manager import InventoryManager
from virtual_scale import VirtualScale
try:
    from advanced_optimizer import WasteMixOptimizer
except ImportError:
    # Fallback if pulp not installed, though it should be
    WasteMixOptimizer = None

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class OperatorCLI:
    def __init__(self):
        self.inventory = InventoryManager()
        self.scale = VirtualScale()
        if WasteMixOptimizer:
            self.optimizer = WasteMixOptimizer()
        else:
            self.optimizer = None
            
        # Hardcoded Waste Properties for Optimization (in real app, from DB)
        self.waste_props = {
            "Tires": {"pci": 8000, "chlorine": 0.01, "sulfur": 1.5, "humidity": 0.02},
            "Plastic": {"pci": 6000, "chlorine": 0.05, "sulfur": 0.2, "humidity": 0.10},
            "Wood": {"pci": 3500, "chlorine": 0.02, "sulfur": 0.1, "humidity": 0.20},
            "Biomass": {"pci": 1500, "chlorine": 0.03, "sulfur": 0.1, "humidity": 0.40}
        }
        
    def run_optimization_cycle(self, stock_snapshot):
        if not self.optimizer:
            return {"status": "No Optimizer", "mix": {}}
            
        # Prepare Data for LP
        waste_data = []
        for name, props in self.waste_props.items():
            entry = props.copy()
            entry['name'] = name
            entry['stock'] = stock_snapshot.get(name, 0)
            waste_data.append(entry)
            
        # Standard Constraints
        constraints = {
            "max_chlorine": 0.03,
            "max_humidity": 0.25,
            "min_pci": 3000,
            "max_sulfur": 1.0
        }
        
        try:
            return self.optimizer.solve_optimal_mix(waste_data, constraints)
        except Exception as e:
            return {"status": f"Error: {e}", "mix": {}}

    def start(self):
        try:
            while True:
                # 1. Get Data
                current_vision = self.scale.read_scale() # t/h flow
                current_stock = self.inventory.get_stock()
                
                # 2. Run Optimization (What we SHOULD be doing)
                opt_result = self.run_optimization_cycle(current_stock)
                
                # 3. Render Dashboard
                clear_screen()
                self._render_header()
                self._render_vision_panel(current_vision)
                self._render_optimizer_panel(opt_result)
                self._render_stock_panel(current_stock)
                
                # 4. Simulate Consumption (Optional, slowly drain stock?)
                # For this demo, let's just observe.
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\nShutting down Operator Interface...")
            sys.exit(0)

    def _render_header(self):
        print("\033[92m") # Green
        print(" █▄█ █▀█ █   █▀▀ ▀█▀ █▄ █   █▄ █ █▀▀ ▀▄▀ █ █ █▀▀")
        print(" █ █ █▄█ █▄▄ █▄▄ ▄█▄ █ ▀█   █ ▀█ █▄▄ █ █ █▄█ ▄█▄")
        print(f" SYSTEM VISUALIZER v2.5 | {datetime.now().strftime('%H:%M:%S')}")
        print("\033[0m")
        print("="*60)
        print(" 50/50 HYBRID PROTOCOL: [ACTIVE]")
        print("="*60)
        print("")

    def _render_vision_panel(self, vision_data):
        print(" [ SENTIENT EYE // VISION INPUT ]")
        print("-" * 45)
        print(f" {'TYPE':<15} | {'FLOW (t/h)':<15}")
        print("-" * 45)
        for name, val in vision_data.items():
            print(f" {name:<15} | \033[96m{val:>10.2f}\033[0m") # Cyan
        print("")

    def _render_optimizer_panel(self, result):
        print(" [ NEURAL SOLVER // TARGET MIX ]")
        print("-" * 45)
        if isinstance(result, dict) and "status" in result and result["status"].startswith("Error"):
             print(f" Status: \033[91m{result['status']}\033[0m")
        else:
             status_color = "\033[92m" if result.status == 'Optimal' else "\033[91m"
             print(f" Status: {status_color}{result.status}\033[0m | Z: \033[93m{result.objective_value}\033[0m kcal")
             print("-" * 45)
             for name, pct in result.mix.items():
                 color = "\033[90m" if "Petcoke" in name else "\033[92m" # Dark grey for Petcoke, Green for Waste
                 if pct > 0:
                    print(f" {color}{name:<15} | {pct:>10.2f} %\033[0m")
        print("")

    def _render_stock_panel(self, stock):
        print(" [ WAREHOUSE // STOCKPILE ]")
        print("-" * 45)
        for name, val in stock.items():
            bar_len = int(val / 100)
            bar = "▮" * bar_len
            print(f" {name:<15} | {val:>8.1f} \033[90m{bar}\033[0m")
        print("-" * 45)

if __name__ == "__main__":
    cli = OperatorCLI()
    cli.start()
