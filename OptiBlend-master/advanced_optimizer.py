from pulp import *
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class OptimizationResult:
    status: str
    mix: Dict[str, float] # Name -> Percentage (0-100)
    objective_value: float
    details: Dict[str, float]

class WasteMixOptimizer:
    """
    Advanced Linear Programming Optimizer for Holcim AI-Recipe.
    Uses PuLP to solve for optimal waste mix maximizing PCI.
    """
    
    def __init__(self):
        # Initialize Solver
        self.prob = LpProblem("Geocycle_Fuel_Mix_Optimization", LpMaximize)
        
    def solve_optimal_mix(self, waste_data: List[Dict], constraints: Dict) -> OptimizationResult:
        """
        Solves the LP problem using the 'Holcim Nexus' 50/50 Protocol.
        Result is 50% Petcoke (Fixed) + 50% Optimized Waste Mix.
        """
        # 1. Define Petcoke Properties (Base Load)
        PETCOKE_PROPS = {
            "name": "Petcoke",
            "pci": 8200,      # High Caloric Value
            "chlorine": 0.0005, # Low Chlorine (0.05%)
            "sulfur": 0.04,     # High Sulfur (4.0%)
            "humidity": 0.01
        }
        
        # Re-initialize problem
        self.prob = LpProblem("Holcim_Nexus_50_50", LpMaximize)
        
        # 2. Decision Variables (Xi) for Waste Component
        # We optimize the waste fraction within the GLOBAL mix.
        # Max bound for any single waste is 0.5 (since total waste is 0.5)
        waste_names = [w['name'] for w in waste_data]
        waste_vars = LpVariable.dicts("MixFraction", waste_names, lowBound=0, upBound=0.5, cat='Continuous')

        # 3. Objective Function: Maximize Global PCI
        # Z = (0.5 * Petcoke_PCI) + Sum(Xi * Waste_PCI)
        # Since Petcoke is constant, maximizing this is equivalent to maximizing the waste part.
        self.prob += (
            (0.5 * PETCOKE_PROPS['pci']) + 
            lpSum([waste_vars[w['name']] * w['pci'] for w in waste_data])
        ), "Total_PCI"

        # 4. Constraints
        
        # A. Protocol Mass Balance: Sum(Waste) = 0.50
        # The other 0.50 is implicitly Petcoke.
        self.prob += lpSum([waste_vars[w['name']] for w in waste_data]) == 0.50, "Protocol_Half_Waste"
        
        # B. Quality Constraints (Total Mix)
        
        # Chlorine: (0.5 * Pet_Cl) + Sum(Xi * Waste_Cl) <= Limit
        if 'max_chlorine' in constraints:
            self.prob += (
                (0.5 * PETCOKE_PROPS['chlorine']) + 
                lpSum([waste_vars[w['name']] * w['chlorine'] for w in waste_data]) 
                <= constraints['max_chlorine']
            ), "Chlorine_Limit"
            
        # Humidity: (0.5 * Pet_H) + Sum(Xi * Waste_H) <= Limit
        if 'max_humidity' in constraints:
             self.prob += (
                 (0.5 * PETCOKE_PROPS['humidity']) + 
                 lpSum([waste_vars[w['name']] * w['humidity'] for w in waste_data]) 
                 <= constraints['max_humidity']
             ), "Humidity_Limit"
             
        # Sulfur: (0.5 * Pet_S) + Sum(Xi * Waste_S) <= Limit
        if 'max_sulfur' in constraints:
            self.prob += (
                (0.5 * PETCOKE_PROPS['sulfur']) + 
                lpSum([waste_vars[w['name']] * w['sulfur'] for w in waste_data]) 
                <= constraints['max_sulfur']
            ), "Sulfur_Limit"
            
        # Min PCI: (0.5 * Pet_Pci) + Sum(Xi * Waste_Pci) >= Limit
        if 'min_pci' in constraints:
             self.prob += (
                 (0.5 * PETCOKE_PROPS['pci']) + 
                 lpSum([waste_vars[w['name']] * w['pci'] for w in waste_data]) 
                 >= constraints['min_pci']
             ), "Min_PCI_Limit"

        # C. Availability Checks
        for w in waste_data:
            if w.get('stock', 0) <= 0:
                waste_vars[w['name']].upBound = 0

        # 5. Solve
        self.prob.solve(PULP_CBC_CMD(msg=0))
        
        # 6. Extract Results
        status = LpStatus[self.prob.status]
        
        mix_results = {}
        # Explicitly Add Petcoke
        mix_results["Petcoke (Base)"] = 50.0
        
        for w in waste_names:
            val = value(waste_vars[w])
            pct = round(val * 100, 2) if val else 0.0
            if pct > 0:
                mix_results[w] = pct
            
        obj_val = value(self.prob.objective)
        
        # Calculate resulting metrics for details
        # Don't forget the Petcoke contribution!
        total_cl = (0.5 * PETCOKE_PROPS['chlorine']) + sum([value(waste_vars[w['name']]) * w['chlorine'] for w in waste_data])
        total_h = (0.5 * PETCOKE_PROPS['humidity']) + sum([value(waste_vars[w['name']]) * w['humidity'] for w in waste_data])
        total_s = (0.5 * PETCOKE_PROPS['sulfur']) + sum([value(waste_vars[w['name']]) * w['sulfur'] for w in waste_data])

        return OptimizationResult(
            status=status,
            mix=mix_results,
            objective_value=round(obj_val, 2) if obj_val else 0.0,
            details={
                "final_chlorine": round(total_cl, 5),
                "final_humidity": round(total_h, 5),
                "final_sulfur": round(total_s, 5),
                "protocol": "50/50 Nexus"
            }
        )

# --- Test Simulation (as requested in Task 5) ---
if __name__ == "__main__":
    optimizer = WasteMixOptimizer()
    
    # Sample Data
    waste_data = [
        {"name": "Waste A (Tires)", "pci": 8000, "chlorine": 0.01, "sulfur": 1.5, "humidity": 0.02, "stock": 100},
        {"name": "Waste B (Wood)", "pci": 4000, "chlorine": 0.02, "sulfur": 0.1, "humidity": 0.20, "stock": 50},
        {"name": "Waste C (Sludge)", "pci": 1000, "chlorine": 0.05, "sulfur": 0.2, "humidity": 0.60, "stock": 200}
    ]
    
    constraints = {
        "max_chlorine": 0.03, # 3%
        "max_humidity": 0.25, # 25%
        "min_pci": 3000,      # Min 3000 kcal
        "max_sulfur": 1.0     # 1%
    }
    
    print("\n--- Running Simulation ---")
    result = optimizer.solve_optimal_mix(waste_data, constraints)
    print(f"Status: {result.status}")
    print(f"Maximized PCI: {result.objective_value} kcal/kg")
    print("Optimal Mix:")
    for name, pct in result.mix.items():
        print(f"  - {name}: {pct}%")
    print("Final Properties:")
    print(f"  - Chlorine: {result.details['final_chlorine']}")
    print(f"  - Humidity: {result.details['final_humidity']}")
    print("--------------------------\n")
