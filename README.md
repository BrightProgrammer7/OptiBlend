# HOLCIM NEXUS: Industrial AI Platform

**Version:** 2.5 (Industrial Sci-Fi Edition)  
**Protocol:** 50/50 Hybrid (Petcoke/Waste)

## Overview
**Holcim Nexus** is a next-generation control system designed to optimize the Thermal Substitution Rate (TSR) in cement kilns. It uses a **Linear Programming (LP)** engine to calculate the perfect fuel mix, balancing a fixed base load of Petcoke with a dynamic mix of alternative waste fuels.

## System Architecture (The "Trinity")

### 1. The Optimization Lab (Simulation Core)
*A "What-If" analysis sandbox for designing fuel mixes.*
- **Launch:** `python lab_server.py`
- **Interface:** Open `optimization_lab.html` in browser.
- **Features:** 
    - 50/50 Protocol Indicator.
    - Real-time emission predictions (Cl, S, Humidity).
    - Dynamic addition of waste streams.

### 2. The Command Deck (Operator Interface)
*A high-performance terminal dashboard for kiln operators.*
- **Launch:** `python operator_cli.py`
- **Features:**
    - Real-time Viz of Vision Data.
    - ASCII Art & ANSI Color coding.
    - Live Inventory Tracking.

### 3. The Sentient Eye (Vision Sensor)
*An IoT-enabled computer vision module.*
- **Launch:** `python vision_analyzer.py`
- **Features:**
    - YOLOv8 Object Detection.
    - Detects: Tires, Plastic, Wood, Biomass.
    - Calculates flow rates (t/h) based on visual surface area.

## The 50/50 Protocol
The system enforces a strict hybrid energy model:
$$ \text{Total Energy} = \text{Base Load} + \text{Alternative Load} $$
- **50% Petcoke (Fixed):** Ensures kiln stability.
- **50% Waste Mix (Optimized):** Maximizes green energy use within emission limits.

## Quick Start
1.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start the Lab Server:**
    ```bash
    python lab_server.py
    ```
3.  **Open the Lab:** [http://localhost:8000/optimization_lab.html](http://localhost:8000/optimization_lab.html)
4.  **Launch Dashboard:** `python operator_cli.py`
5.  **Activate Camera:** `python vision_analyzer.py`

---
*Powered by Holcim AI-Recipe | 2024 Global Hackathon*
