from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time.time()
resp = True

@app.get("/")
def root():
    if time.time() - start_time >= 10:
        start_time = time.time()
        if resp:
            resp = False
            text = "is_running"
        else:
            resp = True
            text = "is_down"
    
    return {"status": text}