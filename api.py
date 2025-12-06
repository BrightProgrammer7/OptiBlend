from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import json
from typing import List, Dict, Any, Optional

app = FastAPI(title="Holcim AI-Recipe Intelligence API", version="2.0")
DB_PATH = "waste_logs.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"status": "online", "service": "Geocycle Industrial Intelligence"}

@app.get("/api/waste-analysis/latest")
def get_latest_analysis():
    """Returns the most recent frame analysis."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "scan_id": row["id"],
            "timestamp": row["timestamp"],
            "frame_id": row["frame_id"],
            "analysis": json.loads(row["detected_items_json"]),
            "metrics": {
                "total_weight_kg": row["total_weight_kg"],
                "estimated_pci": row["estimated_pci"]
            },
            "status": row["analysis_status"]
        }
    else:
        raise HTTPException(status_code=404, detail="No analysis data found")

@app.get("/api/waste-analysis/batch-summary")
def get_batch_summary(limit: int = 10):
    """Returns the summary of the last N frames (default 10)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scans ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {"count": 0, "frames": []}
    
    frames = []
    total_pci = 0
    valid_frames = 0
    
    for row in rows:
        frames.append({
            "id": row["id"],
            "pci": row["estimated_pci"],
            "weight": row["total_weight_kg"]
        })
        if row["estimated_pci"] > 0:
            total_pci += row["estimated_pci"]
            valid_frames += 1
            
    avg_pci = total_pci / valid_frames if valid_frames > 0 else 0
    
    return {
        "batch_size": len(frames),
        "average_pci": round(avg_pci, 2),
        "history": frames
    }

@app.get("/api/waste-analysis/supply-gap")
def get_supply_gap():
    """Returns the latest Gap Analysis vs 80% TSR Target."""
    # Re-using logic from waste_analysis or just calculating on fly for API
    # Since we didn't persist 'gap_analysis' in 'scans' table, 
    # we calculate it fresh from the latest batch.
    
    TARGET_PCI = 5600.0
    summary = get_batch_summary(limit=10)
    current_pci = summary["average_pci"]
    
    gap = current_pci - TARGET_PCI
    status = "ABOVE TARGET" if gap > 0 else "BELOW TARGET"
    
    recommendation = "Maintain Mix"
    if gap < -500: recommendation = "Action: Increase High-PCI Injector (Tires)"
    elif gap > 500: recommendation = "Action: Reduce High-PCI / Increase Biomass"
    
    return {
        "timestamp": 0, # TODO: add timestamp
        "current_batch_pci": current_pci,
        "target_pci": TARGET_PCI,
        "gap": gap,
        "status": status,
        "recommendation": recommendation
    }

if __name__ == "__main__":
    import uvicorn
    # Allow running directly: python api.py
    uvicorn.run(app, host="0.0.0.0", port=8081)
