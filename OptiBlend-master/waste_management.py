from dataclasses import dataclass
from typing import List, Optional

@dataclass
class WasteStream:
    """
    Represents a waste stream (Fuel alternative) for the kiln.
    Corresponds to the former 'Ingredient'.
    """
    name: str
    pci_value: float       # Net Calorific Value (kcal/kg)
    humidity: float        # Percentage (0.0 to 1.0) or specific unit
    chloride_content: float # Percentage
    sulfur_content: float   # Percentage
    density: float         # kg/m3
    cost: float            # Currency per ton
    available_mass: float  # Tons available in stock
    
    def __post_init__(self):
        if self.pci_value < 0:
            raise ValueError("PCI value cannot be negative")
        if self.available_mass < 0:
            raise ValueError("Available mass cannot be negative")

@dataclass
class KilnOperationalParameters:
    """
    Operational limits and targets for the kiln.
    Corresponds to the former 'ChefProfile'.
    """
    target_pci: float      # Target avg PCI (e.g., 4500 kcal/kg)
    max_sulfur: float      # Max allowed sulfur % in mix
    max_chloride: float    # Max allowed chlorine % in mix
    target_tsr: float      # Target Thermal Substitution Rate (0.0 to 1.0)
    feed_rate_capacity: float # Total tons/hour the kiln can accept

# --- Global State / Data Store ---

# Typical Geocycle Morroco Waste Streams
WAW_STREAMS = [
    {
        "name": "Tires",
        "pci_value": 7500,
        "humidity": 0.05,
        "chloride_content": 0.01,
        "sulfur_content": 1.2,
        "density": 0.5,
        "cost": 50,
        "available_mass": 200
    },
    {
        "name": "Plastic",
        "pci_value": 6000,
        "humidity": 0.10,
        "chloride_content": 0.05,
        "sulfur_content": 0.2,
        "density": 0.3,
        "cost": 30,
        "available_mass": 500
    },
    {
        "name": "Wood",
        "pci_value": 3500,
        "humidity": 0.20,
        "chloride_content": 0.02,
        "sulfur_content": 0.1,
        "density": 0.6,
        "cost": 20,
        "available_mass": 300
    },
    {
        "name": "Biomass",
        "pci_value": 1500,
        "humidity": 0.40,
        "chloride_content": 0.03,
        "sulfur_content": 0.1,
        "density": 0.4,
        "cost": 10,
        "available_mass": 1000
    }
]

# Initial Kiln Parameters
KILN_PARAMS = KilnOperationalParameters(
    target_pci=4500,
    max_sulfur=1.0,
    max_chloride=0.1,
    target_tsr=0.80,
    feed_rate_capacity=50.0 
)
