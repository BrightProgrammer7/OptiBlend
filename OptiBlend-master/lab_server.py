from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
from advanced_optimizer import WasteMixOptimizer, OptimizationResult

app = FastAPI(title="Holcim AI-Recipe Optimization Lab")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

optimizer = WasteMixOptimizer()

# --- Data Models ---

class WasteInput(BaseModel):
    name: str
    pci: float
    chlorine: float
    sulfur: float
    humidity: float
    stock: float

class ConstraintsInput(BaseModel):
    max_chlorine: float
    max_humidity: float
    min_pci: float
    max_sulfur: Optional[float] = 1.0

class OptimizationRequest(BaseModel):
    waste_data: List[WasteInput]
    constraints: ConstraintsInput

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Lab Server Online", "module": "PuLP Optimizer"}

@app.post("/solve", response_model=Dict)
def solve_mix(request: OptimizationRequest):
    # Convert Pydantic models to list of dicts expected by optimizer
    waste_dicts = [w.dict() for w in request.waste_data]
    constraints_dict = request.constraints.dict()
    
    try:
        result = optimizer.solve_optimal_mix(waste_dicts, constraints_dict)
        return {
            "status": result.status,
            "objective_value": result.objective_value,
            "mix": result.mix,
            "details": result.details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting Lab Server on Port 8082...")
    uvicorn.run(app, host="0.0.0.0", port=8082)
