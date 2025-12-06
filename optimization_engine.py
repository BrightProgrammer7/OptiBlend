import numpy as np
from scipy.optimize import linprog
from typing import List, Dict, Any
from waste_management import WasteStream, KilnOperationalParameters

def calculate_optimal_mix(
    waste_streams: List[WasteStream], 
    params: KilnOperationalParameters
) -> Dict[str, Any]:
    """
    Calculates the optimal waste mix to maximize TSR and Minimize Cost
    while maintaining stable PCI and staying within chemical limits.
    
    Uses Linear Programming.
    """
    
    # 1. Objective Function: Minimize Cost
    # linprog minimizes c @ x
    # We want to minimize Cost.
    # c = [cost_1, cost_2, ..., cost_n]
    c = np.array([w.cost for w in waste_streams])
    
    # 2. Constraints
    # Variables x_i = mass (tons/hour) of waste stream i
    
    # Constraint A: Total Feed Rate <= Capacity
    # sum(x_i) <= params.feed_rate_capacity
    A_ub = []
    b_ub = []
    
    # Total mass constraints
    A_ub.append([1] * len(waste_streams))
    b_ub.append(params.feed_rate_capacity)
    
    # Constraint B: PCI Target (Soft constraint or bound?)
    # We want Mix PCI approx Target PCI.
    # Mix PCI = sum(x_i * PCI_i) / sum(x_i) = Target
    # sum(x_i * PCI_i) - Target * sum(x_i) = 0
    # This is non-linear if sum(x_i) is variable. 
    # To simplify for Linear Programming, let's fix the goal:
    # We want to ACHIEVE a certain TSR derived heat.
    # But simpler: ensure the Weighted Average PCI is within range?
    # Let's enforce: sum(x_i * PCI_i) >= Target_PCI * Total_Mass_Lower_Bound ??
    # Actually, usually we set the Total Feed Rate to a specific setpoint or let it float.
    # Let's assume we want to MAXIMIZE TSR (Feed Rate of waste) subject to constraints.
    
    # If we want to MAXIMIZE TSR, we want to MAXIMIZE sum(x_i).
    # Since linprog is MINIMIZE, we can minimize -sum(x_i).
    # But we also want to minimize COST.
    # Multi-objective: Minimize (Weight1 * Cost - Weight2 * TotalMass)
    # Let's prioritize TSR (Maximize Mass) primarily, Cost secondarily.
    # Coeffs = Cost_i - Large_Constant
    
    # However, the user asked: "Objective Function: Maximize tsr_percentage AND Minimize cost."
    # Let's construct `c` as: Cost - (HighValue * 1) 
    # So finding higher x_i reduces the objective function more.
    c = np.array([w.cost - 100000 for w in waste_streams]) # Heavily favor high utilization
    
    # Constraint: Chemical Limits
    # sum(x_i * Sulfur_i) / sum(x_i) <= Max_Sulfur
    # sum(x_i * (Sulfur_i - Max_Sulfur)) <= 0
    sulfur_coeffs = [w.sulfur_content - params.max_sulfur for w in waste_streams]
    A_ub.append(sulfur_coeffs)
    b_ub.append(0)
    
    # sum(x_i * Chloride_i) / sum(x_i) <= Max_Chloride
    # sum(x_i * (Chloride_i - Max_Chloride)) <= 0
    chloride_coeffs = [w.chloride_content - params.max_chloride for w in waste_streams]
    A_ub.append(chloride_coeffs)
    b_ub.append(0)
    
    # Constraint: PCI Stability (Target +/- 5%)
    # This implies the AVG PCI of the mix must be within range.
    # Avg_PCI = sum(x_i * PCI_i) / sum(x_i)
    # Target * 0.95 <= Avg_PCI <= Target * 1.05
    
    # Lower bound: sum(x_i * (PCI_i - 0.95 * Target)) >= 0
    # -> sum(x_i * -(PCI_i - 0.95 * Target)) <= 0
    pci_lower_coeffs = [-(w.pci_value - 0.95 * params.target_pci) for w in waste_streams]
    A_ub.append(pci_lower_coeffs)
    b_ub.append(0)
    
    # Upper bound: sum(x_i * (PCI_i - 1.05 * Target)) <= 0
    pci_upper_coeffs = [w.pci_value - 1.05 * params.target_pci for w in waste_streams]
    A_ub.append(pci_upper_coeffs)
    b_ub.append(0)

    # Bounds for each variable: 0 <= x_i <= Available Mass
    bounds = [(0, w.available_mass) for w in waste_streams]
    
    # Solve
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    
    if res.success:
        result_mix = {}
        total_mass = 0
        total_heat = 0
        total_sulfur_mass = 0
        total_chloride_mass = 0
        total_cost = 0
        
        for i, val in enumerate(res.x):
            if val > 1e-3: # Filter tiny values
                result_mix[waste_streams[i].name] = round(val, 2)
                total_mass += val
                total_heat += val * waste_streams[i].pci_value
                total_sulfur_mass += val * waste_streams[i].sulfur_content
                total_chloride_mass += val * waste_streams[i].chloride_content
                total_cost += val * waste_streams[i].cost
                
        avg_pci = total_heat / total_mass if total_mass > 0 else 0
        avg_sulfur = total_sulfur_mass / total_mass if total_mass > 0 else 0
        avg_chloride = total_chloride_mass / total_mass if total_mass > 0 else 0
        
        return {
            "status": "Target Achieved",
            "mix_ton_per_hour": result_mix,
            "total_feed_rate": round(total_mass, 2),
            "avg_pci": round(avg_pci, 2),
            "avg_sulfur_percent": round(avg_sulfur, 4),
            "avg_chloride_percent": round(avg_chloride, 4),
            "total_cost_per_hour": round(total_cost, 2),
            "tsr_projection": "Calculated based on fossil fuel baseline (not provided)"
        }
    else:
        return {
            "status": "Optimization Failed",
            "reason": res.message
        }

if __name__ == "__main__":
    # Test Optimization
    streams = [
        WasteStream("Tires", pci_value=7500, humidity=0.02, chloride_content=0.01, sulfur_content=1.5, density=0.4, cost=50, available_mass=5.0),
        WasteStream("RDF_High_Quality", pci_value=4500, humidity=0.15, chloride_content=0.5, sulfur_content=0.3, density=0.2, cost=20, available_mass=10.0),
        WasteStream("Biomass_Agro", pci_value=3200, humidity=0.30, chloride_content=0.05, sulfur_content=0.1, density=0.3, cost=10, available_mass=20.0),
        WasteStream("Industrial_Sludge", pci_value=1200, humidity=0.60, chloride_content=0.02, sulfur_content=0.8, density=1.1, cost=-10, available_mass=8.0), # Negative cost = revenue
    ]
    
    # Target PCI 4500 +/- 5%
    # Max Sulfur 1.0%
    # Max Chloride 0.5%
    params = KilnOperationalParameters(
        target_pci=4500,
        max_sulfur=1.0,
        max_chloride=0.8,
        target_tsr=0.8,
        feed_rate_capacity=15.0 # Max 15 tons/hour injector capacity
    )
    
    result = calculate_optimal_mix(streams, params)
    import json
    print(json.dumps(result, indent=2))
