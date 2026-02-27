from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import sys
import os
import json
import time
import threading
import asyncio
import signal

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[WebSocket] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WebSocket] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Create a copy of the set to avoid issues if it changes during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)

manager = ConnectionManager()

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
# telemetry_data now stores multiple drones keyed by their ID
telemetry_data: Dict[int, Any] = {}
global_logs: List[Dict[str, Any]] = []
state_lock = threading.Lock()
stop_event = threading.Event()
system_running = threading.Event()
        
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
    drone_id: Optional[int] = None

class GotoRequest(BaseModel):
    lat: float
    lon: float
    alt: float
    drone_id: Optional[int] = None

# --- Background Telemetry Logic ---
def telemetry_update_loop():
    global vehicle_instance, telemetry_data, global_logs
    print("[Telemetry] Loop started")
    
    # We need an event loop to handle broadcasting
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def broadcast_telemetry():
        while not system_running.is_set():
            with state_lock:
                # Prepare data for broadcast
                drones_list = []
                for d_id, data in telemetry_data.items():
                    drones_list.append({
                        "id": d_id,
                        **data
                    })
                
                current_logs = list(global_logs)
                global_logs.clear()

            if drones_list or current_logs:
                await manager.broadcast({
                    "type": "telemetry",
                    "data": {
                        "drones": drones_list,
                        "logs": current_logs,
                        "connected": len(drones_list) > 0
                    }
                })
            await asyncio.sleep(0.2) # 5Hz Broadcast Rate

    # Start the broadcast task in the background
    threading.Thread(target=loop.run_until_complete, args=(broadcast_telemetry(),), daemon=True).start()

    while not system_running.is_set():
        if vehicle_instance is None:
            time.sleep(1)
            continue
            
        try:
            # Get all detected drone IDs
            ids = vehicle_instance.drone_ids
            if not ids:
                # If no IDs yet, try to fetch them
                ids = vehicle_instance.get_all_drone_ids()

            for d_id in ids:
                try:
                    # Poll position
                    pos = vehicle_instance.get_pos(drone_id=d_id)
                    
                    with state_lock:
                        if d_id not in telemetry_data:
                            telemetry_data[d_id] = {
                                "lat": 0.0, "lon": 0.0, "alt": 0.0,
                                "mode": "UNKNOWN", "armed": False, "heading": 0.0
                            }
                        
                        if isinstance(pos, tuple) and len(pos) == 3:
                            telemetry_data[d_id]["lat"], telemetry_data[d_id]["lon"], telemetry_data[d_id]["alt"] = pos
                        
                        # Poll status
                        telemetry_data[d_id]["mode"] = vehicle_instance.get_mode(drone_id=d_id)
                        telemetry_data[d_id]["armed"] = vehicle_instance.is_armed(drone_id=d_id) == 1
                        telemetry_data[d_id]["heading"] = vehicle_instance.get_yaw(drone_id=d_id)
                except Exception as e:
                    print(f"[Telemetry] Error updating drone {d_id}: {e}")
                
        except Exception as e:
            print(f"[Telemetry] Loop error: {e}")
        
        time.sleep(0.1)

# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    global vehicle_instance
    try:
        def init_vehicle():
            global vehicle_instance
            try:
                # Initial drone_id from config, but it will discover others
                vehicle_instance = Vehicle(conn_port, stop_event=stop_event)
                t = threading.Thread(target=telemetry_update_loop, daemon=True)
                t.start()
                print("[System] Backend initialized and telemetry loop running.")
            except Exception as e:
                print(f"[Error] Vehicle connection failed: {e}")

        threading.Thread(target=init_vehicle, daemon=True).start()
    except Exception as e:
        print(f"[Error] Initialization failed: {e}")

@app.on_event("shutdown")
def shutdown_event():
    print("[System] Shutting down...")
    system_running.set()
    stop_event.set() # Bu çok önemli, blocking pymavlink çağrılarını uyandırır
    
    if vehicle_instance:
        try:
            vehicle_instance.vehicle.close()
        except:
            pass
    print("[System] Connection closed and events set.")

# --- Signal Handling for Clean Exit ---
def handle_exit(sig, frame):
    print(f"\n[System] Signal {sig} received, forcing exit...")
    system_running.set()
    stop_event.set()
    # Give it a moment to cleanup then force exit
    os._exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Frontend'e log gonderme
def log_send(msg: str, type: str="info"):
    with state_lock: global_logs.append({"msg": msg, "type": type})

# --- API Endpoints ---
@app.get("/")
def root():
    return {"message": "AEROKOU Drone controll Backend is online."}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep connection alive and wait for client to disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(websocket)

@app.get("/telemetry")
def get_telemetry():
    """Returns the current real-time state of all drones."""
    with state_lock:
        current_logs = list(global_logs)
        global_logs.clear()
        
        drones_list = []
        for d_id, data in telemetry_data.items():
            drones_list.append({"id": d_id, **data})

        return {
            "connected": len(drones_list) > 0,
            "drones": drones_list,
            "logs": current_logs
        }

@app.post("/command/arm", response_model=CommandResponse)
def arm_drone(drone_id: Optional[int] = None):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    target_ids = [drone_id] if drone_id else vehicle_instance.drone_ids
    for d_id in target_ids:
        vehicle_instance.arm_disarm(arm=True, drone_id=d_id)
        log_send(f"Drone {d_id}: Armed")
    return CommandResponse(status="success", message=f"Arm command sent to {len(target_ids)} drone(s)")

@app.post("/command/disarm", response_model=CommandResponse)
def disarm_drone(drone_id: Optional[int] = None):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    target_ids = [drone_id] if drone_id else vehicle_instance.drone_ids
    for d_id in target_ids:
        vehicle_instance.arm_disarm(arm=False, drone_id=d_id)
        log_send(f"Drone {d_id}: Disarmed")
    return CommandResponse(status="success", message=f"Disarm command sent to {len(target_ids)} drone(s)")

@app.post("/command/mode", response_model=CommandResponse)
def set_drone_mode(request: ModeRequest):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    target_ids = [request.drone_id] if request.drone_id else vehicle_instance.drone_ids
    try:
        for d_id in target_ids:
            vehicle_instance.set_mode(mode=request.mode.upper(), drone_id=d_id)
        return CommandResponse(status="success", message=f"Mode changed to {request.mode} for {len(target_ids)} drone(s)")
    except Exception as e:
        raise HTTPException(500, f"Failed to change mode: {str(e)}")

@app.post("/command/start-mission", response_model=CommandResponse)
def start_mission(background_tasks: BackgroundTasks, drone_id: Optional[int] = None):
    if not vehicle_instance: raise HTTPException(503, "Drone not connected")
    
    stop_event.clear()
    target_ids = [drone_id] if drone_id else vehicle_instance.drone_ids

    def handle_mission(d_ids):
        for d_id in d_ids:
            log_send(f"Drone {d_id}: Mission starting: GUIDED mode")
            vehicle_instance.set_mode(mode="GUIDED", drone_id=d_id)
            vehicle_instance.arm_disarm(arm=True, drone_id=d_id)
            log_send(f"Drone {d_id}: Taking off to {ALT}m")
            vehicle_instance.multiple_takeoff(ALT, drone_id=d_id)

        # Basic wait loop (simplified for multiple drones)
        start_time = time.time()
        while not stop_event.is_set() and time.time() - start_time < 30:
            time.sleep(1)
        
        for d_id in d_ids:
            log_send(f"Drone {d_id}: Moving to destination")
            vehicle_instance.go_to(loc=LOC, alt=ALT, drone_id=d_id)
        
    background_tasks.add_task(handle_mission, target_ids)
    return CommandResponse(status="success", message=f"Mission initiated for {len(target_ids)} drone(s)")


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
