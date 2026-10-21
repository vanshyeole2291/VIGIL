"""
core/lane_manager.py — Virtual Lane Polygon & PCU Queue Manager
================================================================
Defines virtual lane zones at intersections, maps tracked vehicles to lanes,
and computes lane statistics: vehicle count, Passenger Car Unit (PCU) volume,
area density, average approach speeds, and starvation wait metrics.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


@dataclass
class LaneStats:
    """Statistical state for a single intersection approach lane / quadrant."""
    name:              str
    vehicle_count:     int   = 0
    pcu_count:         float = 0.0     # Equivalent passenger car units (IRC/HCM)
    person_count:      int   = 0
    ambulance_present: bool  = False
    fire_truck_present: bool = False
    emergency_present: bool  = False
    density_ratio:     float = 0.0     # 0.0–1.0 (polygon area occupancy)
    avg_speed_kmh:     float = 0.0     # Average vehicle approach speed
    avg_wait_time:     float = 0.0     # Average queue stopped duration (seconds)
    max_wait_time:     float = 0.0     # Longest individual vehicle delay
    queue_length:      int   = 0       # Count of stationary/stopped vehicles
    flow_per_min:      float = 0.0     # Estimated throughput
    
    @property
    def congestion_index(self) -> float:
        """Normalized congestion index [0.0 - 1.0] driven by PCU load and area occupancy."""
        # Baseline threshold: 15 PCUs per quadrant approach
        return round(min(1.0, (self.pcu_count / 15.0) * 0.7 + self.density_ratio * 0.3), 2)
        
    @property
    def congestion_level(self) -> str:
        ci = self.congestion_index
        if ci < 0.2:
            return "free"
        elif ci < 0.5:
            return "light"
        elif ci < 0.8:
            return "moderate"
        else:
            return "heavy"
    
    @property
    def priority_score(self) -> float:
        """
        Dynamic ATSC priority score combining PCU load, queue length,
        area density, and wait starvation aging.
        """
        score = self.pcu_count * 3.0
        score += self.density_ratio * 40.0
        score += self.queue_length * 2.5
        score += self.avg_wait_time * 0.8
        
        if self.ambulance_present:
            score += 99999.0  # Absolute priority override
        return round(score, 2)


class LaneManager:
    """
    Manages intersection quadrant polygons, point-in-polygon assignment,
    and PCU load tracking.
    """
    
    LANE_COLORS = {
        "North": (255, 100, 100),  # Light Blue
        "South": (100, 255, 100),  # Light Green
        "East":  (100, 100, 255),  # Coral
        "West":  (255, 255, 100),  # Yellow
    }
    
    def __init__(self, frame_width: int, frame_height: int,
                 polygons: Dict[str, List[Tuple[float, float]]] = None):
        self.fw = frame_width
        self.fy = frame_height
        
        raw = polygons or getattr(config, 'LANE_POLYGONS_4WAY', config.LANE_POLYGONS)
        
        # Convert normalized coordinates to pixel space
        self.lane_polys: Dict[str, np.ndarray] = {}
        for lane_name, norm_pts in raw.items():
            pts = [(int(x * frame_width), int(y * frame_height)) for x, y in norm_pts]
            self.lane_polys[lane_name] = np.array(pts, dtype=np.int32)
        
        self.lane_names = list(self.lane_polys.keys())
        
        # Contour area in pixels²
        self.lane_areas: Dict[str, float] = {
            name: max(1.0, cv2.contourArea(poly))
            for name, poly in self.lane_polys.items()
        }
        
        self.stats: Dict[str, LaneStats] = {
            name: LaneStats(name=name) for name in self.lane_names
        }
    
    def assign_lane(self, cx: int, cy: int) -> Optional[str]:
        """Test centroid against lane boundary polygons."""
        pt = (float(cx), float(cy))
        for name, poly in self.lane_polys.items():
            if cv2.pointPolygonTest(poly, pt, measureDist=False) >= 0:
                return name
        return None
    
    def update(self, tracks) -> Dict[str, LaneStats]:
        """Aggregate tracks into lane statistics."""
        lane_vehicles:  Dict[str, List]  = {n: [] for n in self.lane_names}
        lane_pcu:       Dict[str, float] = {n: 0.0 for n in self.lane_names}
        lane_persons:   Dict[str, int]   = {n: 0   for n in self.lane_names}
        lane_ambul:     Dict[str, bool]  = {n: False for n in self.lane_names}
        lane_fire:      Dict[str, bool]  = {n: False for n in self.lane_names}
        lane_em:        Dict[str, bool]  = {n: False for n in self.lane_names}
        lane_stopped:   Dict[str, int]   = {n: 0   for n in self.lane_names}
        lane_wait:      Dict[str, List[float]] = {n: [] for n in self.lane_names}
        lane_speeds:    Dict[str, List[float]] = {n: [] for n in self.lane_names}
        lane_bbox_area: Dict[str, float] = {n: 0.0 for n in self.lane_names}
        
        for track in tracks:
            lane = self.assign_lane(track.cx, track.cy)
            track.lane = lane
            
            if lane is None:
                continue
            
            if track.is_vehicle:
                lane_vehicles[lane].append(track)
                
                # PCU attribution
                pcu_val = getattr(track, 'pcu', 1.0)
                lane_pcu[lane] += pcu_val
                
                # Physical area occupancy
                lane_bbox_area[lane] += (track.w * track.h)
                
                if track.is_stopped:
                    lane_stopped[lane] += 1
                lane_wait[lane].append(track.wait_time)
                
                if hasattr(track, 'speed_kmh'):
                    lane_speeds[lane].append(track.speed_kmh)
                
                is_ft = getattr(track, 'is_fire_truck', False) or track.label in ["fire_truck", "firetruck"]
                is_amb = track.is_ambulance or track.label == "ambulance"
                is_em = getattr(track, 'is_emergency_vehicle', False) or is_amb or is_ft
                
                if is_ft:
                    lane_fire[lane] = True
                if is_amb:
                    lane_ambul[lane] = True
                if is_em:
                    lane_em[lane] = True
                    lane_ambul[lane] = True
            
            elif track.is_person:
                lane_persons[lane] += 1
        
        # Update LaneStats dataclass
        for name in self.lane_names:
            waits  = lane_wait[name]
            speeds = lane_speeds[name]
            area   = self.lane_areas[name]
            
            s = self.stats[name]
            s.vehicle_count     = len(lane_vehicles[name])
            s.pcu_count         = round(lane_pcu[name], 1)
            s.person_count      = lane_persons[name]
            s.ambulance_present = lane_ambul[name]
            s.fire_truck_present = lane_fire[name]
            s.emergency_present = lane_em[name]
            s.density_ratio     = min(1.0, lane_bbox_area[name] / max(area, 1.0))
            s.avg_speed_kmh     = round(sum(speeds) / len(speeds), 1) if speeds else 0.0
            s.avg_wait_time     = round(sum(waits) / len(waits), 1) if waits else 0.0
            s.max_wait_time     = round(max(waits), 1) if waits else 0.0
            s.queue_length      = lane_stopped[name]
        
        return self.stats
    
    def draw_lanes(self, frame: np.ndarray, show_labels: bool = True) -> np.ndarray:
        """Render semi-transparent lane overlays and HUD labels."""
        overlay = frame.copy()
        
        for name, poly in self.lane_polys.items():
            color = self.LANE_COLORS.get(name, (200, 200, 200))
            stats = self.stats[name]
            
            # Shading
            alpha = 0.12 if stats.vehicle_count == 0 else 0.22
            cv2.fillPoly(overlay, [poly], color)
            cv2.polylines(frame, [poly], isClosed=True, color=color, thickness=2)
            
            if show_labels:
                M = cv2.moments(poly)
                if M["m00"] != 0:
                    lx = int(M["m10"] / M["m00"])
                    ly = int(M["m01"] / M["m00"])
                else:
                    lx, ly = poly[0]
                
                # Lane Header Tag
                header_text = f"{name}: {stats.vehicle_count}v ({stats.pcu_count:.1f} PCU)"
                cv2.putText(frame, header_text, (lx - 55, ly - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2, cv2.LINE_AA)
                
                # Congestion status badge
                cong_text = f"{stats.congestion_level.upper()} ({stats.congestion_index * 100:.0f}%)"
                cong_color = {
                    "FREE": (0, 255, 0),
                    "LIGHT": (0, 220, 150),
                    "MODERATE": (0, 165, 255),
                    "HEAVY": (0, 0, 255),
                }.get(stats.congestion_level.upper(), (255, 255, 255))
                
                cv2.putText(frame, cong_text, (lx - 55, ly + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, cong_color, 1, cv2.LINE_AA)
        
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        return frame
    
    def get_priority_order(self) -> List[str]:
        return sorted(self.lane_names, key=lambda n: self.stats[n].priority_score, reverse=True)
    
    def get_max_wait_lane(self) -> Optional[Tuple[str, float]]:
        if not self.stats:
            return None
        best = max(self.stats.items(), key=lambda x: x[1].max_wait_time)
        return best[0], best[1].max_wait_time
