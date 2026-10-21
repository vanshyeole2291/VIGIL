"""
AI Traffic De-Congestion System — Configuration
================================================
Edit these values to match your camera setup and preferences.
"""

import os

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Primary video — user-provided traffic footage
VIDEO_PATH = os.path.join(BASE_DIR, "assets", "videos", "ambulance_emergency_corridor.mp4")
FALLBACK_VIDEO_PATHS = [
    os.path.join(BASE_DIR, "..", "yolov8-multiple-vehicle-detection", "tf.mp4"),
    os.path.join(BASE_DIR, "..", "SynchroFlow--Smart-Traffic-Management-System-main", "video3.mp4"),
]

# YOLO model — custom fine-tuned weights for traffic & emergency vehicles
USER_BEST_MODEL = r"C:\Users\HP\Downloads\model\model\best (12).pt"
if os.path.exists(os.path.join(BASE_DIR, "models", "best_indian_traffic.pt")):
    MODEL_NAME = os.path.join(BASE_DIR, "models", "best_indian_traffic.pt")
elif os.path.exists(USER_BEST_MODEL):
    MODEL_NAME = USER_BEST_MODEL
elif os.path.exists(os.path.join(BASE_DIR, "models", "best (12).pt")):
    MODEL_NAME = os.path.join(BASE_DIR, "models", "best (12).pt")
else:
    MODEL_NAME = os.path.join(BASE_DIR, "models", "best.pt")
FALLBACK_MODEL_NAME = os.path.join(BASE_DIR, "models", "best_trained_v12.pt")

# ─── Video Processing ─────────────────────────────────────────────────────────
FRAME_WIDTH  = 1280
FRAME_HEIGHT = 720
TARGET_FPS   = 30
PROCESS_EVERY_N_FRAMES = 2      # Skip every other frame for speed
CONFIDENCE_THRESHOLD   = 0.35  # Calibrated detection threshold for high-precision traffic and emergency perception

# ─── Vehicle & Agent Classes (Label-Driven Single Source of Truth) ───────────
VEHICLE_CLASSES = {
    "car":        1.0,
    "motorcycle": 0.5,
    "bus":        3.0,
    "truck":      3.0,
    "rickshaw":   0.8,  # Indian 3-Wheeler Auto-Rickshaw (IRC:106 / Indo-HCM)
    "auto":       0.8,
    "bicycle":    0.2,
    "person":     0.1,  # Pedestrian
    "ambulance":  0.0,  # Emergency vehicle: triggers immediate preemption override
}
AMBULANCE_CLASS_KEYWORDS = ["ambulance", "emergency", "fire", "rescue"]

# ─── Passenger Car Unit (PCU) Standard Equivalents (IRC:106 / Indo-HCM / HCM) ──
# Standardizes mixed heterogeneous traffic queues into equivalent car units
PCU_WEIGHTS = {
    "car":        1.0,
    "motorcycle": 0.5,
    "bus":        3.0,
    "truck":      3.0,
    "rickshaw":   0.8,  # Indian Auto-Rickshaw (3-Wheeler) standard PCU
    "auto":       0.8,
    "bicycle":    0.2,
    "person":     0.1,  # Used for pedestrian crossing occupancy
    "ambulance":  0.0,  # Emergency vehicle: triggers immediate preemption override
}

# Compatibility alias
VEHICLE_WEIGHTS = PCU_WEIGHTS

# ─── Lane Polygon Definitions (normalized 0–1 coordinates) ───────────────────
# Format: list of (x_norm, y_norm) points for each lane quadrant.
LANE_POLYGONS = {
    "North": [(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)],
    "South": [(0.5, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 1.0)],
}

# 4-Way Intersection Quadrants (for 2x2 grid composite or 4-way streams)
LANE_POLYGONS_4WAY = {
    "North": [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
    "South": [(0.5, 0.0), (1.0, 0.0), (1.0, 0.5), (0.5, 0.5)],
    "East":  [(0.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 1.0)],
    "West":  [(0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 1.0)],
}

# ─── Signal Timing & Webster ATSC Parameters ─────────────────────────────────
BASE_GREEN_TIME    = 15   # Standard base green time in seconds (solid, non-fluctuating)
GREEN_PER_VEHICLE  = 1.5  # Extra seconds per vehicle in queue
MAX_GREEN_TIME     = 45   # Maximum green time cap to prevent starvation
MIN_GREEN_TIME     = 12   # Guaranteed minimum green time (prevents micro-cycling & rapid switching)
MAX_WAIT_TIME      = 60   # Force green if a lane has waited this long (fairness threshold)
YELLOW_DURATION    = 3    # Standard yellow clearance duration in seconds

# Webster's Optimal Cycle Length & Green Split Constants
WEBSTER_ENABLED            = True   # Use Webster's Delay Minimization algorithm
WEBSTER_LOST_TIME_PER_PHASE = 3.5    # Startup lost time + clearance lost time per phase (sec)
WEBSTER_SATURATION_FLOW     = 1800.0 # Saturation flow rate per hour of green (PCU/hr)
WEBSTER_MIN_CYCLE           = 40.0   # Lower bound on cycle length (seconds)
WEBSTER_MAX_CYCLE           = 120.0  # Upper bound on cycle length (seconds)

# ─── Emergency Preemption & Audio Siren Detection ────────────────────────────
AMBULANCE_OVERRIDE        = True   # Enable visual emergency preemption
OPTICAL_AMBULANCE_HEURISTIC_ENABLED = False # In heavy traffic, do not force-reclassify normal white cars as ambulances
AMBULANCE_CONFIDENCE_THRESHOLD = 0.30 # Calibrated neural confidence threshold: detects genuine Force Traveller ambulance, strictly rejects false bus/car classifications
AMBULANCE_MIN_AREA_FRAC   = 0.001  # Rejects small vehicles/cars in traffic jams; ambulances are larger vehicles
AMBULANCE_WHITE_RATIO     = 0.35   # High threshold for emergency vehicle white body surface
AMBULANCE_EMERGENCY_SCORE = 5.0    # Strict threshold requiring dedicated strobe flashers
AUDIO_SIREN_ENABLED       = True   # Enable acoustic siren analysis
AUDIO_SIREN_PATH        = os.path.join(BASE_DIR, "assets", "audio", "siren.mp3")
SIREN_FREQ_LOW          = 600    # Hz lower bound of emergency siren sweep
SIREN_FREQ_HIGH         = 1600   # Hz upper bound of emergency siren sweep
SIREN_CONFIDENCE_THRESH = 0.40   # Siren detection energy ratio threshold
EMERGENCY_GREEN_HOLD    = 30.0   # Minimum duration for green corridor hold (seconds)

# ─── Accident & Traffic Anomaly Detection ────────────────────────────────────
ENABLE_COLLISION_ALERTS = True   # Enable collision & accident alerts for real-time safety preemption
ACCIDENT_STOP_THRESHOLD = 2.0   # Seconds a vehicle is stopped before flagged
ACCIDENT_OVERLAP_IOU    = 0.45  # Realistic physical impact overlap threshold (rejects normal queue proximity)
COLLISION_CONFIRM_TIME  = 2.5   # 2.0s sustained confirmation time for genuine collisions
ILLEGAL_PARKING_TIME    = 15.0  # Seconds stationary in moving lane before parking/stall alert

# ─── Backend Server ───────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 8000
OPEN_BROWSER_ON_START = True

# ─── Dashboard ────────────────────────────────────────────────────────────────
DASHBOARD_TITLE = "AI Based Traffic Surveillance System"
STREAM_JPEG_QUALITY = 75  # JPEG compression quality for streaming (1–100)

# ─── Camera Sources ──────────────────────────────────────────────────────────
LIVE_FEED_URL = "http://10.128.109.61:8080/video"
# Alternative IP Camera Feeds:
# LIVE_FEED_URL = "https://10.197.135.215:8080/video"
# LIVE_FEED_URL = "http://[2409:4102:6017:f767:ac11:49ff:fe87:679e]:8080/video"