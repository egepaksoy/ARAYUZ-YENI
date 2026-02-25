# 🤖 Project AEROKOU Drone controll - TODO List

## Phase 1: Backend Infrastructure (Python/FastAPI)

- [x] **1.1 Refactor Backend Architecture**: Convert `main.py` from a linear script into a persistent FastAPI application.
- [ ] **1.2 Real-time Telemetry Engine**: Implement a background thread that constantly polls the `Vehicle` for data (Lat, Lon, Alt, Heading, Battery).
- [x] **1.3 Command API Endpoints**:
  - `POST /arm`: Arm/Disarm the drone.
  - `POST /takeoff`: Initiate takeoff to a specified altitude.
  - `POST /land`: Command the drone to land.
  - `POST /goto`: Send the drone to specific coordinates.
- [ ] **1.4 WebSocket Integration**: Set up a WebSocket server to push telemetry data to the frontend in real-time (no more polling!).

## Phase 2: Computer Vision & Streaming

- [ ] **2.1 Integrated Vision Pipeline**: Port logic from `basit-goruntu.py` into the backend.
- [ ] **2.2 MJPEG Video Stream**: Create a `/video_feed` endpoint that streams the live OpenCV-processed camera feed (with detected shapes/targets).

## Phase 3: Frontend Development (React)

- [x] **3.1 Dashboard Layout**: Create a "Jarvis-style" dark UI with modules for telemetry and video.
- [ ] **3.2 Connection Manager**: Implement WebSocket/API services to communicate with the Python backend.
- [ ] **3.3 Interactive Map**: Add a map (Leaflet or Google Maps) to track the drone's position in real-time.
- [ ] **3.4 Control Panel**: Build the button interface for manual flight commands.

## Phase 4: Integration & Testing

- [ ] **4.1 SITL Testing**: Verify the UI works with a simulated drone (ArduPilot/PX4 SITL).
- [ ] **4.2 Latency Optimization**: Tune the video and telemetry stream for minimum delay.
- [ ] **4.3 Final Polish**: Add Jarvis-inspired witty notifications and status logs.
