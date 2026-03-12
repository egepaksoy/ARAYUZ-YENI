from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import signal
from api_controller import DroneController

# --- Setup ---
CONFIG_FILE = r"C:\Users\egepa\OneDrive\Masaüstü\25-26\ARAYUZ\BACKEND\config.json"
app = FastAPI(title="AEROKOU Drone Control Test API")
controller = DroneController(CONFIG_FILE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class CommandResponse(BaseModel):
    status: str
    message: str

class ModeRequest(BaseModel):
    mode: str
    drone_id: Optional[int] = None

# --- Lifecycle ---
@app.on_event("startup")
async def startup():
    controller.start()

@app.on_event("shutdown")
def shutdown():
    controller.stop()

def handle_exit(sig, frame):
    controller.stop()
    os._exit(0)

signal.signal(signal.SIGINT, handle_exit)

# --- Endpoints ---
@app.get("/")
def root():
    return {"status": "online", "message": "AEROKOU Controller Ready"}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await controller.manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        controller.manager.disconnect(websocket)

@app.post("/command/arm", response_model=CommandResponse)
def arm(drone_id: Optional[int] = None):
    controller.arm_disarm(True, drone_id)
    return CommandResponse(status="success", message="Arm command sent")

@app.post("/command/disarm", response_model=CommandResponse)
def disarm(drone_id: Optional[int] = None):
    controller.arm_disarm(False, drone_id)
    return CommandResponse(status="success", message="Disarm command sent")

@app.post("/command/mode", response_model=CommandResponse)
def mode(request: ModeRequest):
    controller.set_mode(request.mode, request.drone_id)
    return CommandResponse(status="success", message=f"Mode set to {request.mode}")

@app.post("/command/start-mission", response_model=CommandResponse)
def start_mission(drone_id: Optional[int] = None):
    controller.start_mission(drone_id)
    return CommandResponse(status="success", message="Mission started")

@app.post("/command/failsafe-mission", response_model=CommandResponse)
def failsafe():
    controller.failsafe()
    return CommandResponse(status="success", message="Failsafe triggered")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
