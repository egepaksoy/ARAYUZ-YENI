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
    "last_update": 0,
    "logs": []
}
stop_event = threading.Event()
system_running = threading.Event()
state_lock = threading.Lock()
        
with open(CONFIG_FILE, "r") as f:
    conf = json.load(f)

conn_port = conf["CONN-PORT"]
drone_id = conf["DRONE"]["id"]
ALT = conf["DRONE"]["alt"]
LOC = conf["DRONE"]["loc"]

is_running = threading.Event()

# --- Models ---
class CommandResponse(BaseModel):
    status: str
    message: str

class TakeoffRequest(BaseModel):
    altitude: float

class ModeRequest(BaseModel):
    mode: str

class GotoRequest(BaseModel):
    lat: float
    lon: float
    alt: float

# --- Background Telemetry Logic ---
def telemetry_update_loop(drone_id: int):
    global vehicle_instance, telemetry_data
    print(f"[Telemetry] Loop started for Drone ID: {drone_id}")
    
    while not system_running.is_set():
        if vehicle_instance is None:
            time.sleep(1)
            continue
            
        try:
            # We don't want the global stop_event to kill the telemetry loop, 
            # but the Vehicle methods use it. So we must ensure it's clear 
            # for telemetry to work.
            if stop_event.is_set() and not system_running.is_set():
                # If stop_event is set but system is still running, 
                # it means a mission was stopped, but we still want telemetry.
                # However, the Vehicle class's recv_match loops will exit.
                # So we should be careful.
                pass

            with state_lock:
                # Poll position - Note: get_pos uses stop_event internally!
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
            # If it fails due to stop_event, we don't want to mark it as disconnected permanently
            telemetry_data["connected"] = False
        
        time.sleep(0.5) # Reduced frequency to be safer with blocking calls

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
    system_running.set()
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
        current_logs = list(telemetry_data["logs"])
        telemetry_data["logs"] = [] # Clear logs after sending

        if telemetry_data["connected"]:
            return {
                "connected": True,
                "lat": telemetry_data["lat"],
                "lon": telemetry_data["lon"],
                "alt": telemetry_data["alt"],
                "mode": telemetry_data["mode"],
                "armed": telemetry_data["armed"],
                "heading": telemetry_data["heading"],
                "last_update": telemetry_data["last_update"],
                "logs": current_logs
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
                "test_jitter": True,
                "logs": current_logs
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

@app.post("/command/mode", response_model=CommandResponse)
def set_drone_mode(request: ModeRequest):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    try:
        vehicle_instance.set_mode(mode=request.mode.upper())
        return CommandResponse(status="success", message=f"Mode changed to {request.mode}")
    except Exception as e:
        raise HTTPException(500, f"Failed to change mode: {str(e)}")

@app.post("/command/start-mission", response_model=CommandResponse)
def start_mission(background_tasks: BackgroundTasks):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    
    # Reset stop_event to allow loops to run
    stop_event.clear()

    def handle_mission():
        with state_lock: telemetry_data["logs"].append({"msg": "Mission starting: GUIDED mode", "type": "info"})
        vehicle_instance.set_mode(mode="GUIDED")
        vehicle_instance.arm_disarm(arm=True)
        with state_lock: telemetry_data["logs"].append({"msg": f"Taking off to {ALT}m", "type": "info"})
        vehicle_instance.multiple_takeoff(ALT)

        # TODO: drondan konum cekmek gerekince telemetry_data degiskenini kullan

        while not stop_event.is_set():
            if telemetry_data["alt"] * 1.1 >= ALT:
                break
        
        with state_lock: telemetry_data["logs"].append({"msg": "Moving to destination", "type": "info"})
        vehicle_instance.go_to(loc=LOC, alt=ALT)
        print("Drone hedefe gidiyor")

        start_time = time.time()
        while not stop_event.is_set():
            if time.time() - start_time >= 0.5:
                if vehicle_instance.on_location(loc=LOC, drone_loc=(telemetry_data["lat"], telemetry_data["lon"]), seq=0):
                    break
        
        with state_lock: telemetry_data["logs"].append({"msg": "Arrived at destination, landing", "type": "info"})
        print("Drone konuma ulasti iniyor")
        vehicle_instance.set_mode(mode="LAND")

        
    background_tasks.add_task(handle_mission)
    return CommandResponse(status="success", message=f"Takeoff to {ALT}m initiated")

@app.post("/command/failsafe-mission", response_model=CommandResponse)
def failsafe_mission():
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")

    def failsafe_drone_id(vehicle, drone_id, home_pos=None):
        if home_pos == None:
            print(f"{drone_id}>> Failsafe alıyor")
            vehicle.set_mode(mode="RTL", drone_id=drone_id)

        # guıdedli rtl
        else:
            print(f"{drone_id}>> Failsafe alıyor")
            vehicle.set_mode(mode="GUIDED", drone_id=drone_id)

            alt = vehicle.get_pos(drone_id=drone_id)[2]
            vehicle.go_to(loc=home_pos, alt=alt, drone_id=drone_id)

            start_time = time.time()
            while True:
                if time.time() - start_time > 3:
                    print(f"{drone_id}>> RTL Alıyor...")
                    start_time = time.time()

                if vehicle.on_location(loc=home_pos, drone_loc=(telemetry_data["lat"], telemetry_data["lon"]), drone_id=drone_id):
                    print(f"{drone_id}>> iniş gerçekleşiyor")
                    vehicle.set_mode(mode="LAND", drone_id=drone_id)
                    break

    thraeds = []
    for d_id in vehicle_instance.drone_ids:
        args = (vehicle_instance, d_id)

        thrd = threading.Thread(target=failsafe_drone_id, args=args)
        thrd.start()
        thraeds.append(thrd)


    for t in thraeds:
        t.join()

    print(f"{vehicle_instance.drone_ids} id'li Drone(lar) Failsafe aldi")
    
    if not stop_event.is_set():
        stop_event.set()

    return CommandResponse(status="success", message="Landing initiated")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
