import subprocess
import time
import sys
import os
import signal

def start_system():
    print("="*60)
    print(" HOLCIM AI-RECIPE | SYSTEM LAUNCHER")
    print("="*60)

    # 1. Start the Unified Server (Backend + Dashboard)
    print("[1/2] Starting Unified Server (Port 8000)...")
    # We use sys.executable to ensure we use the same python interpreter
    server_process = subprocess.Popen(
        [sys.executable, "unified_server.py"],
        cwd=os.getcwd(),
        shell=False
    )

    # Wait a moment for server to initialize
    time.sleep(3)

    # 2. Start the Vision Analyzer (IoT Sensor)
    print("[2/2] Starting Vision Sensor (Camera)...")
    vision_process = subprocess.Popen(
        [sys.executable, "vision_analyzer.py"],
        cwd=os.getcwd(),
        shell=False
    )
    
    print("\nSYSTEM IS LIVE!")
    print(" -> Dashboard: http://localhost:8000")
    print(" -> Camera:    Active (Check window)")
    print("="*60)
    print("Press Ctrl+C to stop the system.")

    try:
        # Keep main process alive to monitor children
        while True:
            time.sleep(1)
            # Check if processes are still alive
            if server_process.poll() is not None:
                print("Server process ended unexpectedly.")
                break
            if vision_process.poll() is not None:
                print("Vision process ended unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping Holcim AI-Recipe...")
    finally:
        # Graceful Shutdown
        vision_process.terminate()
        server_process.terminate()
        vision_process.wait()
        server_process.wait()
        print("Shutdown Complete.")

if __name__ == "__main__":
    start_system()
