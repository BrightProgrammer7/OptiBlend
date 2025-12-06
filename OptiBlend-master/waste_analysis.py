import asyncio
import json
import os
import sqlite3
import datetime
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from google import genai
from google.genai import types

# --- Configuration & Constants ---
DB_PATH = "waste_logs.db"
TARGET_TSR_PCI = 5600.0  # 80% TSR Target
FRAME_CALIBRATION_CONSTANT = 50.0  # Adjustable based on camera height

# Calorific Values (kcal/kg) - Dry Basis
PCI_VALUES = {
    "Tires": 8200,
    "Wood": 4500,
    "Plastics": 10500,
    "Paper/Cardboard": 3500,
    "Wet Biomass": 1200,
    "Textiles": 5500,
    "Metals": 0,
    "Mixed Waste": 3500 # Fallback
}

# Density Factors (for weight estimation)
DENSITY_FACTORS = {
    "Tires": 0.8,
    "Wood": 0.6,
    "Plastics": 0.3,
    "Paper/Cardboard": 0.4,
    "Wet Biomass": 0.5,
    "Metals": 0.9,
    "Textiles": 0.3,
    "Mixed Waste": 0.5
}

# Moisture Factors
MOISTURE_FACTORS = {
    "Tires": 1.0,
    "Plastics": 1.0,
    "Wood": 1.0,
    "Textiles": 0.85,
    "Paper/Cardboard": 0.85,
    "Wet Biomass": 0.65,
    "Metals": 1.0,
    "Mixed Waste": 0.8
}

@dataclass
class WasteObject:
    type: str
    count: int
    estimated_size_class: str
    visual_density: str # loose, compact, dense
    confidence: float
    area_percentage: float
    contamination_notes: str
    
    @property
    def compaction_factor(self) -> float:
        if self.visual_density == "dense": return 1.2
        if self.visual_density == "compact": return 1.0
        return 0.7 # loose

    @property
    def estimated_weight(self) -> float:
        """
        Weight Calculation:
        predicted_weight = (area_percentage × compaction_factor × material_density) × frame_calibration_constant
        """
        density = DENSITY_FACTORS.get(self.type, 0.5)
        # area_percentage is 0-100 in input, but formula implies fraction effectively or scaling constant handles it.
        # Let's assume input is percentage (0-100).
        return (self.area_percentage * self.compaction_factor * density) * FRAME_CALIBRATION_CONSTANT

class BatchAnalyzer:
    def __init__(self):
        self.frame_buffer: List[Dict] = [] # Last 10 frames
        self.frame_counter = 0

    def add_frame(self, frame_data: Dict):
        self.frame_buffer.append(frame_data)
        if len(self.frame_buffer) > 10:
            self.frame_buffer.pop(0) # Keep rolling window
        self.frame_counter += 1

    def get_rolling_average_pci(self) -> float:
        if not self.frame_buffer: return 0.0
        total_pci = sum(f['frame_metrics']['estimated_pci_kcal_kg'] for f in self.frame_buffer if f['frame_metrics']['estimated_pci_kcal_kg'] > 0)
        return total_pci / len(self.frame_buffer)

    def generate_gap_report(self, current_pci: float) -> Dict:
        """
        Generate supply gap intelligence based on Target vs Current.
        """
        gap = current_pci - TARGET_TSR_PCI
        status = "ABOVE TARGET" if gap > 0 else "BELOW TARGET"
        
        recommendation = {}
        if gap < -500: # Deficit > 500 kcal
            # Need High PCI
            recommendation = {
                "action": "INCREASE_HIGH_PCI",
                "message": f"Critical Deficit ({gap:.0f} kcal). Increase Tires/Plastics feed.",
                "materials": ["Tires", "Plastics"]
            }
        elif gap > 500: # Surplus
             recommendation = {
                "action": "REDUCE_HIGH_PCI",
                "message": f"High Energy Surplus (+{gap:.0f} kcal). Reduce Tires or increase Biomass.",
                "materials": ["Wet Biomass"]
            }
        else:
            recommendation = {
                 "action": "MAINTAIN",
                 "message": "Stable Operation. Maintain current mix.",
                 "materials": []
            }
            
        return {
            "current_pci": current_pci,
            "target_pci": TARGET_TSR_PCI,
            "gap": gap,
            "status": status,
            "recommendation": recommendation
        }

class WasteStreamAnalyzer:
    """
    Main controller for Industrial Waste Intelligence.
    """
    def __init__(self, db_path="waste_logs.db"):
        self.db_path = db_path
        self._init_db()
        self.client = genai.Client(http_options={'api_version': 'v1beta'})
        self.model = "gemini-2.0-flash-exp" # Using Flash for speed/cost
        self.batch_processor = BatchAnalyzer()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS scans
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      timestamp REAL, 
                      frame_id INTEGER,
                      detected_items_json TEXT, 
                      total_weight_kg REAL,
                      estimated_pci REAL,
                      analysis_status TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS batch_reports
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp REAL,
                      avg_pci REAL,
                      gap_analysis_json TEXT)''')
        conn.commit()
        conn.close()
        
    def _save_scan(self, frame_id, analysis_result, status="success"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO scans (timestamp, frame_id, detected_items_json, total_weight_kg, estimated_pci, analysis_status) VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.datetime.now().timestamp(), 
                   frame_id,
                   json.dumps(analysis_result['detected_items']),
                   analysis_result['frame_metrics']['total_waste_weight_kg'],
                   analysis_result['frame_metrics']['estimated_pci_kcal_kg'],
                   status))
        conn.commit()
        conn.close()

    async def analyze_frame(self, image_bytes_base64: str, frame_id: int = 0) -> Dict[str, Any]:
        
        # Industrial System Instruction
        SYSTEM_PROMPT = """
        Analyze this industrial waste stream image. You are part of an automated kiln feed optimization system for a cement kiln.
        TASK: Detect and classify all visible waste objects. Return ONLY valid JSON with no markdown.
        
        DETECTION CATEGORIES: Tires, Plastics, Wood, Paper/Cardboard, Wet Biomass, Metals, Textiles, Mixed Waste
        
        JSON OUTPUT STRUCTURE (return ONLY this):
        {
          "frame_analysis": {
            "objects_detected": [
              { "type": "Tires", "count": 2, "estimated_size_class": "large", "visual_density": "compact", "confidence": 0.94, "area_percentage": 12.5, "contamination_notes": "minimal" }
            ],
            "overall_cleanliness": "clean",
            "moisture_visual_estimate": "dry",
            "notes": "..."
          }
        }
        """
        
        try:
            image_data = base64.b64decode(image_bytes_base64)
            
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_text(text=SYSTEM_PROMPT),
                    types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
                ]
            )
            
            raw_text = response.text.strip()
            if raw_text.startswith("```json"): raw_text = raw_text[7:]
            if raw_text.endswith("```"): raw_text = raw_text[:-3]
            
            data = json.loads(raw_text)
            
            # --- Logic Engine ---
            detected_items = []
            frame_objects = data.get("frame_analysis", {}).get("objects_detected", [])
            
            total_weight = 0.0
            weighted_pci_sum = 0.0
            
            for obj_data in frame_objects:
                obj = WasteObject(
                    type=obj_data.get("type", "Mixed Waste"),
                    count=obj_data.get("count", 1),
                    estimated_size_class=obj_data.get("estimated_size_class", "medium"),
                    visual_density=obj_data.get("visual_density", "loose"),
                    confidence=obj_data.get("confidence", 0.0),
                    area_percentage=obj_data.get("area_percentage", 0.0),
                    contamination_notes=obj_data.get("contamination_notes", "")
                )
                
                weight = obj.estimated_weight
                pci_val = PCI_VALUES.get(obj.type, 3500)
                moisture_f = MOISTURE_FACTORS.get(obj.type, 0.8)
                
                # PCI Contribution
                weighted_pci_sum += (pci_val * weight * moisture_f)
                total_weight += weight
                
                detected_items.append({
                    "type": obj.type,
                    "count": obj.count,
                    "total_weight_kg": round(weight, 2),
                    "confidence": obj.confidence,
                    "area_percentage": obj.area_percentage
                })
                
            frame_pci = (weighted_pci_sum / total_weight) if total_weight > 0 else 0.0
            
            # Batch Intelligence
            frame_report = {
                "detected_items": detected_items,
                "frame_metrics": {
                    "total_waste_weight_kg": round(total_weight, 2),
                    "estimated_pci_kcal_kg": round(frame_pci, 0),
                     "moisture_estimate_percent": 10 if data.get("frame_analysis",{}).get("moisture_visual_estimate") == "dry" else 40,
                     "contamination_risk": "Low"
                }
            }
            
            # Save & Audit
            self._save_scan(frame_id, frame_report)
            self.batch_processor.add_frame(frame_report)
            
            # Rolling Average Check
            batch_pci = self.batch_processor.get_rolling_average_pci()
            gap_data = self.batch_processor.generate_gap_report(batch_pci)
            
            # Final Output Payload
            return {
                "timestamp": datetime.datetime.now().isoformat(),
                "frame_id": frame_id,
                "analysis": frame_report,
                "batch_intelligence": {
                    "rolling_10frame_pci_kcal_kg": round(batch_pci, 0),
                    "vs_target_80tsr_kcal_kg": TARGET_TSR_PCI,
                    "gap_analysis": gap_data
                }
            }

        except Exception as e:
            print(f"Analysis Error: {e}")
            return {"error": str(e)}

if __name__ == "__main__":
    print("Waste Analysis Module Loaded.")
