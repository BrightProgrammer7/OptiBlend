# Holcim AI-Recipe: Industrial Waste Optimization

Holcim AI-Recipe is an industrial AI system designed to optimize the **Thermal Substitution Rate (TSR)** in cement kilns by managing alternative fuel mixes (Geocycle). It uses **Gemini 2.5 Flash Live** for multimodal analysis of waste streams and **Linear Programming** for fuel mix optimization.

## Prerequisites

- Python 3.8+
- Google GenAI API Key

## Setup

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**
    Ensure `.env` contains your API key:
    ```env
    GOOGLE_API_KEY=your_key_here
    ```

## Running the System

### 1. Start the AI Server (Backend)
This Python server handles the decision logic, optimization engine, and Gemini connection.
```bash
python main.py
```
*Output: `Running Holcim AI-Recipe Server localhost:9080...`*

### 2. Launch the SCADA Panel (Frontend)
Since you have a local server running, access the dashboard via your browser:

-   **Control Panel**: [http://localhost:8000/mirajxr.html](http://localhost:8000/mirajxr.html)
-   **Landing Page**: [http://localhost:8000/landing.html](http://localhost:8000/landing.html)

*(Or simply open the HTML files directly if not using the local server)*

## How to Use
1.  **Initialize**: Click the **"INITIALIZE SYSTEM"** button on the video feed.
2.  **Monitor**: Watch the real-time video analysis of the "conveyor belt".
3.  **Command**: Speak to the system:
    -   *"Optimize the mix based on current stock."*
    -   *"We have a new delivery of Tires, check the stock levels."*
    -   *"Set the Target PCI to 4800."*
4.  **Action**: The SCADA panel on the right will update automatically with the new optimal fuel mix.
