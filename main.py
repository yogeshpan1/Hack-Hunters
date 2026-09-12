from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from data.timetable import get_timetable_for_clash_detection
from clash_detector import (
    detect_clashes,
    detect_capacity_clashes
)


app = FastAPI(
    title="RTE Clash Detection API",
    description="Clash detection API for the Islington College RTE system"
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def home():

    return {
        "message": "RTE Clash Detection API is running"
    }


@app.get("/check-clashes")
def check_clashes():

    entries = get_timetable_for_clash_detection()

    clashes = detect_clashes(entries)

    capacity_clashes = detect_capacity_clashes(entries)

    all_clashes = clashes + capacity_clashes

    return {
        "has_clashes": len(all_clashes) > 0,
        "total_clashes": len(all_clashes),
        "clashes": all_clashes
    }