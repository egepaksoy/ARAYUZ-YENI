import sys
import os
import json
import time
import threading
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect

# --- Configuration & Paths ---
PYMAVLINK_PATH = sys.path.append("./pymavlink_custsom/pymavlink_custom.py")
if PYMAVLINK_PATH not in sys.path:
    sys.path.append(PYMAVLINK_PATH)

try:
    from pymavlink_custom.pymavlink_custom import Vehicle
except Exception as err:
    print(f"Pymavlink import error: {err}")
    sys.exit(1)

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)

class DroneController:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.manager = ConnectionManager()
        self.vehicle: Optional[Vehicle] = None
        self.telemetry_data: Dict[int, Any] = {}
        self.global_logs: List[Dict[str, Any]] = []
        
        self.state_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.system_running = threading.Event()
        
        self._load_config()
        
    def _load_config(self):
        with open(self.config_file, "r") as f:
            self.conf = json.load(f)
        self.conn_port = self.conf["CONN-PORT"]
        self.target_alt = self.conf["DRONE"]["alt"]
        self.target_loc = self.conf["DRONE"]["loc"]

    def log_send(self, msg: str, log_type: str = "info"):
        with self.state_lock:
            self.global_logs.append({"msg": msg, "type": log_type})

    async def telemetry_broadcast_loop(self):
        while not self.system_running.is_set():
            with self.state_lock:
                drones_list = [{"id": d_id, **data} for d_id, data in self.telemetry_data.items()]
                current_logs = list(self.global_logs)
                self.global_logs.clear()

            if drones_list or current_logs:
                await self.manager.broadcast({
                    "type": "telemetry",
                    "data": {
                        "drones": drones_list,
                        "logs": current_logs,
                        "connected": len(drones_list) > 0
                    }
                })
            await asyncio.sleep(0.2)

    def telemetry_update_loop(self):
        # Setup event loop for broadcast in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        threading.Thread(target=loop.run_until_complete, args=(self.telemetry_broadcast_loop(),), daemon=True).start()

        while not self.system_running.is_set():
            if self.vehicle is None:
                time.sleep(1)
                continue
            
            try:
                ids = self.vehicle.drone_ids or self.vehicle.get_all_drone_ids()
                for d_id in ids:
                    pos = self.vehicle.get_pos(drone_id=d_id)
                    with self.state_lock:
                        if d_id not in self.telemetry_data:
                            self.telemetry_data[d_id] = {"lat": 0, "lon": 0, "alt": 0, "mode": "UNKNOWN", "armed": False, "heading": 0}
                        
                        if isinstance(pos, tuple) and len(pos) == 3:
                            self.telemetry_data[d_id].update({"lat": pos[0], "lon": pos[1], "alt": pos[2]})
                        
                        self.telemetry_data[d_id].update({
                            "mode": self.vehicle.get_mode(drone_id=d_id),
                            "armed": self.vehicle.is_armed(drone_id=d_id) == 1,
                            "heading": self.vehicle.get_yaw(drone_id=d_id)
                        })
            except Exception as e:
                print(f"[Controller] Telemetry Error: {e}")
            time.sleep(0.1)

    def start(self):
        if Vehicle is None:
            print("[Error] Vehicle class not found!")
            return
        
        def run():
            try:
                self.vehicle = Vehicle(self.conn_port, stop_event=self.stop_event)
                self.telemetry_update_loop()
            except Exception as e:
                print(f"[Error] Vehicle Init failed: {e}")

        threading.Thread(target=run, daemon=True).start()


    def stop(self):
        self.system_running.set()
        self.stop_event.set()
        if self.vehicle:
            try: self.vehicle.vehicle.close()
            except: pass

    # --- Commands ---
    def arm_disarm(self, arm: bool, drone_id: Optional[int] = None):
        ids = [drone_id] if drone_id else self.vehicle.drone_ids
        for d_id in ids:
            self.vehicle.arm_disarm(arm=arm, drone_id=d_id)
            self.log_send(f"Drone {d_id}: {'Armed' if arm else 'Disarmed'}")

    def set_mode(self, mode: str, drone_id: Optional[int] = None):
        ids = [drone_id] if drone_id else self.vehicle.drone_ids
        for d_id in ids:
            self.vehicle.set_mode(mode=mode.upper(), drone_id=d_id)
            self.log_send(f"Drone {d_id}: Mode -> {mode}")

    def start_mission(self, drone_id: Optional[int] = None):
        self.stop_event.clear()
        ids = [drone_id] if drone_id else self.vehicle.drone_ids

        def mission_thread():
            for d_id in ids:
                self.log_send(f"Drone {d_id}: Mission Starting")
                self.vehicle.set_mode(mode="GUIDED", drone_id=d_id)
                self.vehicle.arm_disarm(arm=True, drone_id=d_id)
                self.vehicle.multiple_takeoff(self.target_alt, drone_id=d_id)

            time.sleep(5) # Basic wait for takeoff
            for d_id in ids:
                self.vehicle.go_to(loc=self.target_loc, alt=self.target_alt, drone_id=d_id)
        
        threading.Thread(target=mission_thread, daemon=True).start()

    def failsafe(self):
        for d_id in self.vehicle.drone_ids:
            threading.Thread(target=lambda: self.vehicle.set_mode(mode="RTL", drone_id=d_id), daemon=True).start()
        self.stop_event.set()
        self.log_send("FAILSAFE: All drones returning to home", "error")
