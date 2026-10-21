import sys
import os

# 1. Patch core/tracker.py
with open("core/tracker.py", "r", encoding="utf-8") as f:
    tracker_code = f.read()

old_tracker_decel = """        self.acceleration = (curr_speed_px - self.speed_px_sec) / dt
        if self.acceleration < -70.0:
            self.had_sudden_decel = True
            self.last_decel_spike_time = time.time()
        elif time.time() - getattr(self, 'last_decel_spike_time', 0.0) > 4.0:
            self.had_sudden_decel = False"""

new_tracker_decel = """        self.acceleration = (curr_speed_px - self.speed_px_sec) / dt
        # Genuine violent deceleration impact: was moving at speed (> 80 px/s ≈ 20 km/h) and suddenly collapsed to standstill (< 25 px/s)
        # Prevents normal slow crawling and stop-and-go queueing in dense traffic from falsely flagging decel spikes
        if self.speed_px_sec > 80.0 and curr_speed_px < 25.0 and self.acceleration < -120.0:
            self.had_sudden_decel = True
            self.last_decel_spike_time = time.time()
        elif time.time() - getattr(self, 'last_decel_spike_time', 0.0) > 3.0:
            self.had_sudden_decel = False"""

if old_tracker_decel in tracker_code:
    tracker_code = tracker_code.replace(old_tracker_decel, new_tracker_decel, 1)
    with open("core/tracker.py", "w", encoding="utf-8") as f:
        f.write(tracker_code)
    print("SUCCESS: core/tracker.py decel spike calibrated!")

# 2. Patch core/accident_detector.py
with open("core/accident_detector.py", "r", encoding="utf-8") as f:
    acc_code = f.read()

old_acc_cand = """                had_decel = getattr(t1, 'had_sudden_decel', False) or getattr(t2, 'had_sudden_decel', False)
                iou_thresh = getattr(config, 'ACCIDENT_OVERLAP_IOU', 0.18)
                is_candidate = (iou >= iou_thresh) or (iou >= 0.12 and had_decel)"""

new_acc_cand = """                had_decel = getattr(t1, 'had_sudden_decel', False) or getattr(t2, 'had_sudden_decel', False)
                iou_thresh = getattr(config, 'ACCIDENT_OVERLAP_IOU', 0.45)
                # In dense queues, vehicles stop bumper-to-bumper. A crash requires severe overlap or impact decel shockwave
                is_candidate = (iou >= iou_thresh and had_decel) or (iou >= 0.55)"""

if old_acc_cand in acc_code:
    acc_code = acc_code.replace(old_acc_cand, new_acc_cand, 1)

old_acc_dwell = """            if at_least_one_stopped and dwell >= confirm_time:"""

new_acc_dwell = """            # In heavy traffic, queued vehicles are never an accident unless had_decel impact or extreme collision penetration
            if (both_stopped or is_red) and not cand["had_decel"] and cand["max_iou"] < 0.55:
                expired_pairs.append(pair_key)
                continue

            if at_least_one_stopped and (cand["had_decel"] or cand["max_iou"] >= 0.55) and dwell >= confirm_time:"""

if old_acc_dwell in acc_code:
    acc_code = acc_code.replace(old_acc_dwell, new_acc_dwell, 1)

with open("core/accident_detector.py", "w", encoding="utf-8") as f:
    f.write(acc_code)

print("SUCCESS: core/accident_detector.py calibrated against false positives!")
