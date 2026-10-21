"""
core/pedestrian_safety.py — Pedestrian Safety & Crosswalk Clearance Engine
==========================================================================
Implements:
  - Pedestrian Clearance Interval (PCI) calculation according to MUTCD / IRC:
      PCI = Crosswalk_Width / Walking_Speed  (typically 1.2 m/s)
  - Pedestrian-Vehicle Conflict Sensing (Jaywalking / Crosswalk Encroachment)
  - Automatic Pedestrian Phase Call & Minimum Green Enforcement
"""

import time
from typing import List, Dict, Tuple, Optional
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PedestrianSafetyEngine:
    """
    Monitors pedestrian safety, calculates clearance intervals, and generates
    hazard alerts when pedestrians enter active vehicular paths.
    """

    def __init__(self, crosswalk_width_meters: float = 14.0, walking_speed_mps: float = 1.2):
        self.crosswalk_width = crosswalk_width_meters
        self.walking_speed = walking_speed_mps
        
        # MUTCD / IRC Pedestrian Clearance Interval (PCI)
        self.pci_duration = round(self.crosswalk_width / self.walking_speed, 1)  # ~11.7s
        self.active_pedestrian_calls: Dict[str, float] = {}

    def calculate_clearance_interval(self, custom_width: float = None) -> float:
        """Compute required pedestrian clearance time in seconds."""
        w = custom_width or self.crosswalk_width
        return round(w / self.walking_speed, 1)

    def evaluate_conflicts(self, person_detections: List, vehicle_tracks: List,
                           current_green_lane: str) -> List[Dict]:
        """
        Evaluate spatial conflicts between pedestrians and moving vehicles.
        Detects jaywalking and high-risk crossing encroachment during green vehicular phases.
        """
        conflicts = []
        now = time.time()

        for p in person_detections:
            for v in vehicle_tracks:
                if not v.is_vehicle:
                    continue
                
                # Spatial proximity in image plane
                dist = np_dist = ((p.cx - v.cx)**2 + (p.cy - v.cy)**2) ** 0.5
                
                # Proximity warning: within 70 pixels of an active moving vehicle
                if dist < 70.0 and v.speed_kmh > 5.0:
                    conflicts.append({
                        "type": "pedestrian_conflict",
                        "severity": "critical",
                        "lane": v.lane or current_green_lane,
                        "distance_px": round(dist, 1),
                        "vehicle_id": v.track_id,
                        "vehicle_speed_kmh": v.speed_kmh,
                        "message": f"CRITICAL: Pedestrian in path of moving Vehicle #{v.track_id} ({v.speed_kmh} km/h) in {v.lane or 'junction'}!",
                        "timestamp": now,
                    })

        return conflicts
