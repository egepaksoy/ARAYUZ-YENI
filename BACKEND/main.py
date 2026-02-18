from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import sys
import os
import json
import time
import threading

# --- Configuration & Paths ---
PYMAVLINK_PATH = r"C:\Users\egepa\OneDrive\Masaüstü\AEROKOU\kodlar\UCUSKODLARI"
CONFIG_FILE = r"C:\Users\egepa\OneDrive\Masaüstü\25-26\ARAYUZ\BACKEND\config.json"

if PYMAVLINK_PATH not in sys.path:
    sys.path.append(PYMAVLINK_PATH)

try:
    from pymavlink_custom.pymavlink_custom import Vehicle
except ImportError as e:
    print(f"[Error] Could not import Vehicle: {e}")
    sys.exit(1)

app = FastAPI(title="AEROKOU Drone controll", description="Persistent FastAPI backend for Real-time Drone Control")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global State ---
vehicle_instance: Optional[Vehicle] = None
telemetry_data: Dict[str, Any] = {
    "connected": False,
    "lat": 0.0,
    "lon": 0.0,
    "alt": 0.0,
    "mode": "UNKNOWN",
    "armed": False,
    "heading": 0.0,
    "last_update": 0
}
stop_event = threading.Event()
state_lock = threading.Lock()
        
with open(CONFIG_FILE, "r") as f:
    conf = json.load(f)

conn_port = conf["CONN-PORT"]
drone_id = conf["DRONE"]["id"]
ALT = conf["DRONE"]["alt"]

is_running = threading.Event()

# --- Models ---
class CommandResponse(BaseModel):
    status: str
    message: str

class TakeoffRequest(BaseModel):
    altitude: float

class GotoRequest(BaseModel):
    lat: float
    lon: float
    alt: float

# --- Background Telemetry Logic ---
def telemetry_update_loop(drone_id: int):
    global vehicle_instance, telemetry_data
    print(f"[Telemetry] Loop started for Drone ID: {drone_id}")
    
    while not stop_event.is_set():
        if vehicle_instance is None:
            time.sleep(1)
            continue
            
        try:
            with state_lock:
                # Poll position
                pos = vehicle_instance.get_pos(drone_id=drone_id)
                if isinstance(pos, tuple) and len(pos) == 3:
                    telemetry_data["lat"], telemetry_data["lon"], telemetry_data["alt"] = pos
                
                # Poll status
                telemetry_data["mode"] = vehicle_instance.get_mode(drone_id=drone_id)
                telemetry_data["armed"] = vehicle_instance.is_armed(drone_id=drone_id) == 1
                telemetry_data["heading"] = vehicle_instance.get_yaw(drone_id=drone_id)
                telemetry_data["last_update"] = time.time()
                telemetry_data["connected"] = True
                
        except Exception as e:
            telemetry_data["connected"] = False
        
        time.sleep(0.2) # 5Hz update rate

# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    global vehicle_instance
    try:
        
        print(f"[System] Connecting to vehicle on {conn_port}...")
        
        def init_vehicle():
            global vehicle_instance
            try:
                vehicle_instance = Vehicle(conn_port, stop_event=stop_event, drone_id=drone_id)
                t = threading.Thread(target=telemetry_update_loop, args=(drone_id,), daemon=True)
                t.start()
                print("[System] Backend initialized and telemetry loop running.")
            except Exception as e:
                print(f"[Error] Vehicle connection failed: {e}")

        threading.Thread(target=init_vehicle, daemon=True).start()
        
    except Exception as e:
        print(f"[Error] Initialization failed: {e}")

@app.on_event("shutdown")
def shutdown_event():
    stop_event.set()
    if vehicle_instance:
        vehicle_instance.vehicle.close()
    print("[System] Connection closed.")

# --- API Endpoints ---
@app.get("/")
def root():
    return {"message": "AEROKOU Drone controll Backend is online."}

@app.get("/telemetry")
def get_telemetry():
    """Returns the current real-time state of the drone with random jitter for testing."""
    import random
    
    with state_lock:
        if telemetry_data["connected"]:
            return {
                "connected": True,
                "lat": telemetry_data["lat"],
                "lon": telemetry_data["lon"],
                "alt": telemetry_data["alt"],
                "mode": telemetry_data["mode"],
                "armed": telemetry_data["armed"],
                "heading": telemetry_data["heading"],
                "last_update": telemetry_data["last_update"]
            }
        else:
            return {
                "connected": False,
                "lat": 0.00,
                "lon": 0.00,
                "alt": 0,
                "mode": "NONE",
                "armed": False,
                "heading": 0.0,
                "last_update": time.time(),
                "test_jitter": True
            }

@app.post("/command/arm", response_model=CommandResponse)
def arm_drone():
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    vehicle_instance.arm_disarm(arm=True)
    return CommandResponse(status="success", message="Arm command sent")

@app.post("/command/disarm", response_model=CommandResponse)
def disarm_drone():
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    vehicle_instance.arm_disarm(arm=False)
    return CommandResponse(status="success", message="Disarm command sent")

@app.post("/command/start-mission", response_model=CommandResponse)
def start_mission(background_tasks: BackgroundTasks):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    
    def handle_mission():
        vehicle_instance.set_mode(mode="GUIDED")
        vehicle_instance.arm_disarm(arm=True)
        vehicle_instance.multiple_takeoff(ALT)

        while not stop_event.is_set():
            if vehicle_instance.get_pos()[2] * 1.1 >= ALT:
                break
            time.sleep(0.05)
        
        start_time = time.time()
        while time.time() - start_time < 5:
            time.sleep(0.01)
        
        vehicle_instance.set_mode(mode="LAND")
        
    background_tasks.add_task(handle_mission)
    return CommandResponse(status="success", message=f"Takeoff to {ALT}m initiated")

@app.post("/command/failsafe-mission", response_model=CommandResponse)
def failsafe_mission():
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    
    if not stop_event.is_set():
        stop_event.set()

    vehicle_instance.set_mode(mode="RTL")
    return CommandResponse(status="success", message="Landing initiated")

@app.post("/command/goto", response_model=CommandResponse)
def goto(req: GotoRequest):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    vehicle_instance.go_to(loc=(req.lat, req.lon), alt=req.alt)
    return CommandResponse(status="success", message=f"Navigation to ({req.lat}, {req.lon}) sent")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
