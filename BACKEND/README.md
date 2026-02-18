# AEROKOU Drone Control Backend

This is the FastAPI backend for the AEROKOU Drone Control system.

## Prerequisites

- Python 3.12+ (or compatible)
- Virtual Environment (recommended)

## Setup

1. **Activate Virtual Environment:**
   Open a PowerShell terminal in this directory (`BACKEND`) and run:
   ```powershell
   .\venv\Scripts\activate
   ```

2. **Install Dependencies (if needed):**
   ```powershell
   pip install -r requirements.txt
   ```
   *(Note: Ensure pymavlink_custom is correctly placed or installed)*

## Running the Backend

To start the server, run:
```powershell
python main.py
```

The server will start on `http://0.0.0.0:8000`.

## Configuration
- Configuration is loaded from `config.json`.
- MAVLink definitions are expected in the `PYMAVLINK_PATH` defined in `main.py`.

## API Documentation
Once running, you can view the automatic API docs at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
