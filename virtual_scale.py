import random
import time
from typing import Dict

class VirtualScale:
    """
    Simulates the 'Vision Scale' module.
    Generates synthetic detection events for waste streams on the conveyor.
    """
    
    def __init__(self):
        self.waste_types = ["Tires", "Plastic", "Wood", "Biomass"]
        
    def read_scale(self) -> Dict[str, float]:
        """
        Returns a snapshot of what is currently detected on the belt (in kg/min rate or instantaneous mass).
        Let's assume this returns the detected mass flow rate (t/h) equivalent for this 'tick'.
        """
        # Randomly fluctuate around some 'current' operation values
        detection = {}
        for w in self.waste_types:
            # Base flow + random noise
            # Simulates a noisy conveyor feed
            base = 0
            if w == "Tires": base = 2.0
            elif w == "Plastic": base = 1.5
            elif w == "Wood": base = 5.0
            elif w == "Biomass": base = 8.0
            
            noise = random.uniform(-0.5, 0.5)
            val = max(0.0, base + noise)
            detection[w] = round(val, 2)
            
        return detection

if __name__ == "__main__":
    vs = VirtualScale()
    print("Scale Reading:", vs.read_scale())
