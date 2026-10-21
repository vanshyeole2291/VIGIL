"""
core/signal_optimizer.py — Webster-Driven Adaptive Traffic Signal Optimizer
============================================================================
Implements:
  - F.V. Webster's Optimum Delay Minimization:
      Co = (1.5 * L + 5) / (1 - Y)
      gi = (yi / Y) * (Co - L)
  - Passenger Car Unit (PCU) & Vehicle Density Proportional Timing
  - High-Density Priority Dispatch & Starvation Safeguard (60s)
  - Multimodal Emergency Vehicle Preemption (Visual + Audio Siren)
  - Manual operator override controls & interactive pause/resume
  - 4-Phase Cycle: North → South → East → West with dynamic demand-based dispatch
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from enum import Enum
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class SignalState(str, Enum):
    GREEN  = "green"
    YELLOW = "yellow"
    RED    = "red"


@dataclass
class LaneSignal:
    """Current signal timing state for one approach quadrant."""
    name:        str
    state:       SignalState = SignalState.RED
    time_left:   float       = 0.0     # Seconds remaining in active phase
    last_green:  float       = 0.0     # Epoch timestamp when last green ended
    total_green: float       = 0.0     # Cumulative green duration served
    total_wait:  float       = 0.0     # Cumulative wait time accumulated


class SignalOptimizer:
    """
    State-of-the-Art Adaptive Traffic Signal Controller.
    
    Synthesizes Webster's delay-minimizing cycle formulation with real-time
    vehicle queue sensing, density-proportional green allocation, acoustic siren preemption,
    and hard starvation guarantees.
    """
    
    PHASE_ORDER = ["North", "South", "East", "West"]
    
    def __init__(self):
        now = time.time()
        self.signals: Dict[str, LaneSignal] = {
            name: LaneSignal(name=name, last_green=now) for name in self.PHASE_ORDER
        }
        
        # Phase Management
        self._phase_idx       = 0
        self._phase_start     = now
        self._phase_duration  = getattr(config, 'MIN_GREEN_TIME', 10.0)
        self._in_yellow       = False
        self._yellow_start    = 0.0
        
        # Interactive Pause Control
        self.is_paused: bool  = False
        self._pause_start: float = 0.0
        
        # Emergency Preemption
        self.emergency_lane:    Optional[str] = None
        self.emergency_active:  bool  = False
        self.emergency_start:   float = 0.0
        self.emergency_source:  str   = "visual"
        
        # Manual Override
        self.manual_override_active: bool = False
        self.manual_override_lane: Optional[str] = None
        self.manual_override_end: float = 0.0
        
        # Webster Telemetry
        self.webster_cycle_length: float = 60.0
        self.critical_flow_ratio:  float = 0.45
        self.lane_green_splits:    Dict[str, float] = {name: 15.0 for name in self.PHASE_ORDER}
        
        # Cycle metrics
        self.total_cycles:    int = 0
        self.phase_history:   List[Dict] = []
        
        # Activate initial phase
        self._activate_phase(self._phase_idx)
    
    @property
    def current_lane(self) -> str:
        return self.PHASE_ORDER[self._phase_idx]
    
    @property
    def current_state(self) -> SignalState:
        return self.signals[self.current_lane].state

    @property
    def time_left(self) -> float:
        return self.signals[self.current_lane].time_left

    def pause(self):
        """Pause signal progression."""
        if not self.is_paused:
            self.is_paused = True
            self._pause_start = time.time()

    def resume(self):
        """Resume signal progression from paused state."""
        if self.is_paused:
            now = time.time()
            pause_duration = now - self._pause_start
            self._phase_start += pause_duration
            if self._in_yellow:
                self._yellow_start += pause_duration
            if self.manual_override_active:
                self.manual_override_end += pause_duration
            self.is_paused = False

    def toggle_pause(self) -> bool:
        """Toggle pause state and return new state."""
        if self.is_paused:
            self.resume()
        else:
            self.pause()
        return self.is_paused
    
    def calculate_webster_splits(self, lane_stats: Dict) -> Tuple[float, Dict[str, float]]:
        """
        Compute Webster's Optimum Cycle Length (Co) and Phase Green Splits (gi)
        strictly proportional to real-time detected vehicle counts and lane density.
        High-density lanes strictly receive proportionally longer green times.
        """
        num_phases = len(self.PHASE_ORDER)
        lost_per_phase = getattr(config, 'WEBSTER_LOST_TIME_PER_PHASE', 3.5)
        total_lost_time = num_phases * lost_per_phase  # L
        
        min_green = float(getattr(config, 'MIN_GREEN_TIME', 10.0))
        max_green = float(getattr(config, 'MAX_GREEN_TIME', 60.0))
        min_cycle = float(getattr(config, 'WEBSTER_MIN_CYCLE', 40.0))
        max_cycle = float(getattr(config, 'WEBSTER_MAX_CYCLE', 120.0))
        
        # 1. Compute composite demand score Di strictly from real-time YOLO detections
        demands = {}
        for name in self.PHASE_ORDER:
            stats = lane_stats.get(name) if lane_stats else None
            veh_count = float(getattr(stats, 'vehicle_count', 0) if stats else 0)
            pcu = float(getattr(stats, 'pcu_count', 0.0) if stats else 0.0)
            density_ratio = float(getattr(stats, 'density_ratio', 0.0) if stats else 0.0)
            queue_len = float(getattr(stats, 'queue_length', 0) if stats else 0)
            
            # High-sensitivity demand composite: PCU + vehicle count + occupancy density
            di = max(0.5, (pcu * 2.0) + (veh_count * 1.5) + (density_ratio * 25.0) + (queue_len * 1.5))
            demands[name] = di
            
        total_demand = sum(demands.values())
        if total_demand <= 0:
            total_demand = 1.0
            
        # 2. Critical flow ratio Y bounded between 0.20 and 0.85
        bounded_Y = min(0.85, max(0.20, min(0.85, (total_demand / 40.0) * 0.75)))
        self.critical_flow_ratio = round(bounded_Y, 3)
        
        # 3. Webster's Optimal Cycle Length Co = (1.5 * L + 5) / (1 - Y)
        raw_Co = (1.5 * total_lost_time + 5.0) / (1.0 - bounded_Y)
        Co = float(max(min_cycle, min(max_cycle, raw_Co)))
        self.webster_cycle_length = round(Co, 1)
        
        # 4. Total effective green budget
        effective_green = max(min_green * num_phases, Co - total_lost_time)
        
        # 5. Proportionally allocate green splits strictly proportional to each lane's demand
        splits = {}
        for name in self.PHASE_ORDER:
            ratio = demands[name] / total_demand
            raw_gi = ratio * effective_green
            # Low/empty demand lanes receive brief clearance (5s), heavy lanes receive extended time
            if demands[name] <= 0.6:
                gi = 5.0
            else:
                gi = round(float(max(min_green, min(max_green, raw_gi))), 1)
            splits[name] = gi
            
        # Guarantee ordering invariant: highest demand lane strictly receives >= green time
        max_demand_lane = max(self.PHASE_ORDER, key=lambda n: demands[n])
        min_demand_lane = min(self.PHASE_ORDER, key=lambda n: demands[n])
        if splits[max_demand_lane] < splits[min_demand_lane]:
            splits[max_demand_lane], splits[min_demand_lane] = splits[min_demand_lane], splits[max_demand_lane]
            
        self.lane_green_splits = splits
        return self.webster_cycle_length, splits
    
    def compute_green_time(self, stats, lane_stats: Dict = None) -> float:
        """
        Calculate green duration for the given approach dynamically and
        strictly proportional to real-time detected vehicle counts and lane density.
        High-density lanes receive proportionally longer green times.
        """
        if getattr(stats, 'ambulance_present', False) or getattr(stats, 'emergency_present', False):
            return getattr(config, 'EMERGENCY_GREEN_HOLD', 30.0)
        
        lane_name = getattr(stats, 'name', self.current_lane)
        
        if lane_stats:
            _, splits = self.calculate_webster_splits(lane_stats)
            if lane_name in splits:
                return splits[lane_name]
        
        # Direct rule-based proportional fallback based on vehicle count & density
        veh_count = getattr(stats, 'vehicle_count', 0) if stats else 0
        pcu = getattr(stats, 'pcu_count', veh_count) if stats else 0
        density_ratio = getattr(stats, 'density_ratio', 0.0) if stats else 0.0
        
        min_green = float(getattr(config, 'MIN_GREEN_TIME', 10.0))
        max_green = float(getattr(config, 'MAX_GREEN_TIME', 60.0))
        
        # Proportional green scaling
        calculated = min_green + (pcu * 2.5) + (veh_count * 1.5) + (density_ratio * 20.0)
        return float(max(min_green, min(max_green, round(calculated, 1))))
    
    def trigger_emergency(self, lane: str, source: str = "visual"):
        """Trigger emergency preemption (visual ambulance/fire-truck or secondary acoustic siren)."""
        if lane not in self.PHASE_ORDER:
            return
        
        # Invariant: Visual detection has absolute precedence over acoustic siren
        if self.emergency_active and self.emergency_source == "visual" and source == "audio":
            return
        
        # If currently audio emergency and visual arrives, visual overrides immediately
        if self.emergency_active and self.emergency_source == "audio" and source == "visual":
            self.emergency_source = "visual"
            self.emergency_lane = lane
            self.emergency_start = time.time()
            if self.current_lane == lane and self.current_state == SignalState.GREEN:
                self.signals[lane].time_left = getattr(config, 'EMERGENCY_GREEN_HOLD', 30.0)
                return
            if not self._in_yellow:
                self._in_yellow = True
                self._yellow_start = time.time()
                self.signals[self.current_lane].state = SignalState.YELLOW
                self.signals[self.current_lane].time_left = config.YELLOW_DURATION
            return
        
        self.emergency_active = True
        self.emergency_lane   = lane
        self.emergency_source = source
        self.emergency_start  = time.time()
        
        # If already green on emergency lane, just hold it
        if self.current_lane == lane and self.current_state == SignalState.GREEN:
            self.signals[lane].time_left = getattr(config, 'EMERGENCY_GREEN_HOLD', 30.0)
            return
        
        # If currently green on another lane, transition via Yellow clearance first (Safety Invariant)
        if not self._in_yellow:
            self._in_yellow = True
            self._yellow_start = time.time()
            self.signals[self.current_lane].state = SignalState.YELLOW
            self.signals[self.current_lane].time_left = config.YELLOW_DURATION
    
    def clear_emergency(self):
        """Disengage emergency preemption and resume equitable cycling."""
        self.emergency_active = False
        self.emergency_lane   = None
        self._emergency_cooldown_until = 0.0  # Immediate reset so genuine visual ambulances are never blocked
        self._in_yellow = False
        
        # Restore and advance to next waiting phase
        self._advance_phase({})
    
    def trigger_manual_override(self, lane: str, duration: float = 30.0):
        """Force manual green signal on a specific lane for a designated duration."""
        if lane not in self.PHASE_ORDER:
            return
        self.manual_override_active = True
        self.manual_override_lane = lane
        self.manual_override_end = time.time() + duration
        
        self._phase_idx = self.PHASE_ORDER.index(lane)
        self._activate_phase(self._phase_idx)
        self._phase_duration = duration
    
    def update(self, lane_stats: Dict, has_audio_siren: bool = False, audio_lane: Optional[str] = None) -> Dict[str, SignalState]:
        """
        Main optimizer tick executed once per frame.
        Evaluates emergency overrides (visual primary, audio secondary fallback),
        yellow transitions, and phase advancements.
        """
        # If paused, freeze all timer calculations and maintain current states
        if self.is_paused:
            return self._get_signal_states()
            
        now = time.time()
        elapsed = now - self._phase_start
        
        # ── 1. Manual Override Handling ─────────────────────────────────────
        if self.manual_override_active:
            if now >= self.manual_override_end:
                self.manual_override_active = False
                self.manual_override_lane = None
                self._advance_phase(lane_stats)
            else:
                self.signals[self.current_lane].time_left = max(0.0, self.manual_override_end - now)
                return self._get_signal_states()
        
        # ── 2. Emergency Preemption: Visual (Primary) & Audio (Secondary) ───
        visual_emergency_lanes = [
            name for name, stats in lane_stats.items()
            if getattr(stats, 'emergency_present', False) or getattr(stats, 'ambulance_present', False) or getattr(stats, 'fire_truck_present', False)
        ]
        
        cooldown_ok = now > getattr(self, '_emergency_cooldown_until', 0.0)
        
        # Visual is the PRIMARY mechanism: IMMEDIATE preemption, never blocked by cooldown
        if visual_emergency_lanes and getattr(config, 'AMBULANCE_OVERRIDE', True):
            self._last_amb_time = now
            target = visual_emergency_lanes[0]
            if not self.emergency_active or self.emergency_lane != target or self.emergency_source != "visual":
                self.trigger_emergency(target, source="visual")
        # Audio is strictly a SECONDARY FALLBACK when no visual vehicle is detected
        elif not visual_emergency_lanes and has_audio_siren and getattr(config, 'AUDIO_SIREN_ENABLED', True):
            if not self.emergency_active and cooldown_ok:
                target_audio = audio_lane if (audio_lane in self.PHASE_ORDER) else self.current_lane
                self.trigger_emergency(target_audio, source="audio")
        elif self.emergency_active:
            # Clear ONLY when visual emergency vehicle has fully cleared the quadrant
            hold_sec = getattr(config, 'EMERGENCY_GREEN_HOLD', 12.0)
            if self.emergency_source == "visual":
                amb_cleared = (now - getattr(self, '_last_amb_time', 0.0) > 3.0)
                if not visual_emergency_lanes and amb_cleared:
                    self.clear_emergency()
            elif self.emergency_source == "audio":
                if not has_audio_siren and (now - self.emergency_start > hold_sec):
                    self.clear_emergency()
        
        # Hard safety invariant: Prevent infinite signal starvation (max 25s preemption hold)
        max_preempt_sec = getattr(config, 'EMERGENCY_MAX_PREEMPTION', 25.0)
        if self.emergency_active and (now - self.emergency_start > max_preempt_sec):
            self.clear_emergency()
        
        # ── 3. Emergency Active Execution ───────────────────────────────────
        if self.emergency_active:
            # Handle yellow clearance before emergency green switch
            if self._in_yellow:
                yellow_elapsed = now - self._yellow_start
                self.signals[self.current_lane].time_left = max(0.0, config.YELLOW_DURATION - yellow_elapsed)
                if yellow_elapsed >= config.YELLOW_DURATION:
                    self._in_yellow = False
                    # Switch all to RED, target to GREEN
                    self._phase_idx = self.PHASE_ORDER.index(self.emergency_lane)
                    self._activate_phase(self._phase_idx)
                    self._phase_duration = getattr(config, 'EMERGENCY_GREEN_HOLD', 30.0)
            else:
                # Keep emergency lane green
                hold_remaining = max(0.0, (self.emergency_start + getattr(config, 'EMERGENCY_GREEN_HOLD', 30.0)) - now)
                self.signals[self.current_lane].time_left = hold_remaining
            return self._get_signal_states()
        
        # ── 4. Yellow Transition Phase ──────────────────────────────────────
        if self._in_yellow:
            yellow_elapsed = now - self._yellow_start
            self.signals[self.current_lane].time_left = max(0.0, config.YELLOW_DURATION - yellow_elapsed)
            
            if yellow_elapsed >= config.YELLOW_DURATION:
                self._in_yellow = False
                self.signals[self.current_lane].state = SignalState.RED
                self._advance_phase(lane_stats)
            
            return self._get_signal_states()
        
        # ── 5. Active Green Phase ───────────────────────────────────────────
        time_left = max(0.0, self._phase_duration - elapsed)
        self.signals[self.current_lane].time_left = time_left
        
        if elapsed >= self._phase_duration:
            # Initiate safe yellow transition
            self._in_yellow = True
            self._yellow_start = now
            self.signals[self.current_lane].state = SignalState.YELLOW
            self.signals[self.current_lane].time_left = config.YELLOW_DURATION
        
        return self._get_signal_states()
    
    def _advance_phase(self, lane_stats: Dict):
        """
        Select next signal phase strictly prioritizing waiting lanes with the highest
        real-time vehicle density / queue demand, while honoring starvation limits.
        """
        now = time.time()
        
        # 1. Starvation Prevention (Fairness Invariant): If a lane waited > 60s, serve it
        starvation_candidate = None
        longest_wait = 0.0
        max_wait_thresh = getattr(config, 'MAX_WAIT_TIME', 60.0)
        
        for name, sig in self.signals.items():
            if name == self.current_lane:
                continue
            wait = now - sig.last_green
            if wait > max_wait_thresh and wait > longest_wait:
                starvation_candidate = name
                longest_wait = wait
        
        if starvation_candidate:
            next_lane = starvation_candidate
            self._phase_idx = self.PHASE_ORDER.index(next_lane)
        else:
            # 2. Strictly prioritize waiting lanes by real-time vehicle counts & density
            remaining = [n for n in self.PHASE_ORDER if n != self.current_lane]
            
            def density_priority_score(name):
                s = lane_stats.get(name) if lane_stats else None
                if not s:
                    return 0.0
                if getattr(s, 'ambulance_present', False) or getattr(s, 'emergency_present', False):
                    return 99999.0
                veh_count = float(getattr(s, 'vehicle_count', 0))
                pcu = float(getattr(s, 'pcu_count', 0.0))
                density = float(getattr(s, 'density_ratio', 0.0))
                queue = float(getattr(s, 'queue_length', 0))
                wait = now - self.signals[name].last_green
                # Heavy weight on vehicle count and density, with wait aging
                return (pcu * 4.0) + (veh_count * 3.0) + (density * 45.0) + (queue * 3.0) + (wait * 0.3)
            
            best_lane = max(remaining, key=density_priority_score)
            self._phase_idx = self.PHASE_ORDER.index(best_lane)
        
        self._activate_phase(self._phase_idx)
        
        # 3. Compute optimal green duration for newly activated phase strictly proportional to its density
        stats = lane_stats.get(self.current_lane) if lane_stats else None
        if stats:
            self._phase_duration = self.compute_green_time(stats, lane_stats)
            self.signals[self.current_lane].time_left = self._phase_duration
        
        self.total_cycles += 1
    
    def _activate_phase(self, idx: int):
        """Activate signal phase (sets active to GREEN, others to RED)."""
        lane = self.PHASE_ORDER[idx]
        now = time.time()
        
        for name, sig in self.signals.items():
            sig.state = SignalState.RED
            sig.time_left = 0.0
        
        self.signals[lane].state      = SignalState.GREEN
        self.signals[lane].last_green = now
        self._phase_start             = now
        self._phase_duration          = getattr(config, 'BASE_GREEN_TIME', 10.0)
        
        self.phase_history.append({
            "lane": lane,
            "timestamp": now,
            "duration": self._phase_duration,
            "webster_cycle": self.webster_cycle_length
        })
        if len(self.phase_history) > 100:
            self.phase_history.pop(0)
    
    def _get_signal_states(self) -> Dict[str, SignalState]:
        return {name: sig.state for name, sig in self.signals.items()}
    
    def update_phase_duration(self, lane_stats: Dict):
        """Dynamically adjust green duration for the current active phase based on detected density."""
        if self._in_yellow or self.emergency_active or self.manual_override_active or self.is_paused:
            return
        stats = lane_stats.get(self.current_lane)
        if stats:
            now = time.time()
            elapsed = now - self._phase_start
            veh_count = getattr(stats, 'vehicle_count', 0)
            queue_len = getattr(stats, 'queue_length', 0)
            
            # Dynamic early truncation: if green lane has completely emptied out after at least 6s,
            # advance immediately to waiting heavy traffic
            if elapsed >= 6.0 and veh_count == 0 and queue_len == 0:
                other_demands = sum(getattr(lane_stats.get(l), 'vehicle_count', 0) for l in self.PHASE_ORDER if l != self.current_lane)
                if other_demands > 0:
                    self._phase_duration = elapsed
                    self.signals[self.current_lane].time_left = 0.0
                    return
            
            new_dur = self.compute_green_time(stats, lane_stats)
            self._phase_duration = max(elapsed + 2.0, new_dur)
            self.signals[self.current_lane].time_left = max(0.0, self._phase_duration - elapsed)

    def draw_signal_panel(self, frame, x: int = 10, y: int = 10) -> None:
        """Render compact signal status panel on the frame."""
        import cv2
        COLORS = {
            SignalState.GREEN:  (0, 255, 0),
            SignalState.YELLOW: (0, 200, 255),
            SignalState.RED:    (0, 0, 255),
        }
        panel_w, panel_h = 220, 150
        cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (20, 20, 20), -1)
        cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), (80, 80, 80), 1)
        
        cv2.putText(frame, "ATSC SIGNAL CONTROLLER", (x + 10, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
        
        py = y + 42
        for lane in self.PHASE_ORDER:
            sig = self.signals[lane]
            col = COLORS.get(sig.state, (100, 100, 100))
            is_active = (lane == self.current_lane)
            
            # Indicator dot
            cv2.circle(frame, (x + 20, py), 6, col, -1)
            if is_active:
                cv2.circle(frame, (x + 20, py), 9, col, 1)
            
            txt = f"{lane:5s}: {sig.state.value.upper()}"
            if is_active:
                txt += f" ({sig.time_left:.0f}s)"
            
            cv2.putText(frame, txt, (x + 36, py + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255) if is_active else (150, 150, 150), 1, cv2.LINE_AA)
            py += 24

    def get_metrics(self) -> Dict:
        """Return serializable metric dictionary of current signal states and splits."""
        return {
            "signals": {
                name: {
                    "state": sig.state.value,
                    "time_left": round(sig.time_left, 1),
                    "last_green": sig.last_green
                }
                for name, sig in self.signals.items()
            },
            "current_lane": self.current_lane,
            "current_state": self.current_state.value,
            "time_left": round(self.time_left, 1),
            "is_paused": self.is_paused,
            "total_cycles": self.total_cycles,
            "emergency_active": self.emergency_active,
            "emergency_lane": self.emergency_lane,
            "emergency_source": self.emergency_source,
            "manual_override": self.manual_override_active,
            "webster_cycle_length": self.webster_cycle_length,
            "critical_flow_ratio": self.critical_flow_ratio,
            "lane_green_splits": self.lane_green_splits
        }
