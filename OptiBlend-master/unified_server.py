from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import json
import asyncio
from datetime import datetime

# Import Internal Modules
from inventory_manager import InventoryManager
from advanced_optimizer import WasteMixOptimizer

app = FastAPI(title="Holcim AI-Recipe Unified Platform")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Systems
inventory_mgr = InventoryManager()
optimizer = WasteMixOptimizer()

# State
latest_telemetry = {
    "timestamp": None,
    "vision_data": {},
    "status": "Waiting for Signal..."
}

# --- Data Models ---
class TelemetryInput(BaseModel):
    timestamp: float
    vision_data: Dict[str, float] # Class -> % or t/h

class InventoryUpdate(BaseModel):
    adjustments: Dict[str, float]

class OptimizationRequest(BaseModel):
    waste_data: List[Dict]
    constraints: Dict

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# --- API Endpoints ---

@app.get("/")
def read_root():
    return FileResponse('index.html')

@app.get("/dashboard")
def read_dashboard():
    return FileResponse('dash.html')

@app.get("/create-account.html")
def read_create_account():
    return FileResponse('create-account.html')

@app.get("/dash.html")
def read_dash_direct():
    return FileResponse('dash.html')

@app.get("/dashboard.html")
def read_dashboard_legacy():
    return FileResponse('dash.html')

@app.get("/optimization_lab.html")
def read_optimization_lab():
    return FileResponse('optimization_lab.html')

# 1. Telemetry / IoT Endpoint
@app.post("/api/telemetry")
async def receive_telemetry(data: TelemetryInput):
    global latest_telemetry
    latest_telemetry = {
        "timestamp": data.timestamp,
        "vision_data": data.vision_data,
        "status": "Online"
    }
    # Broadcast to Frontend via WebSocket
    await manager.broadcast({
        "type": "telemetry_update",
        "data": latest_telemetry
    })
    return {"status": "ok"}

# 2. Inventory API
@app.get("/api/inventory")
def get_inventory():
    return inventory_mgr.get_stock()

@app.post("/api/inventory/update")
def update_inventory(update: InventoryUpdate):
    inventory_mgr.update_stock(update.adjustments)
    # Broadcast update
    return inventory_mgr.get_stock()

# 3. Optimization API (Lab Logic)
@app.post("/api/optimize")
def solve_optimization(request: OptimizationRequest):
    # This endpoint is flexible: accepts explicit waste_data for simulation (Lab Mode)
    # OR uses current stock if waste_data empty (Operational Mode - TODO if needed)
    
    try:
        result = optimizer.solve_optimal_mix(request.waste_data, request.constraints)
        return {
            "status": result.status,
            "objective_value": result.objective_value,
            "mix": result.mix,
            "details": result.details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Real-time Socket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep alive check
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Serve Static Files (mostly for optional assets, but Dashboard is served at root)
# Serve Static Files
app.mount("/static", StaticFiles(directory="."), name="static")
app.mount("/styles", StaticFiles(directory="styles"), name="styles")
app.mount("/js", StaticFiles(directory="js"), name="js")

if __name__ == "__main__":
    print("Starting Unified Holcim Platform on Port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
