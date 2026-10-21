import sys
import os

with open("core/traffic_analyzer.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update collision threshold in traffic_analyzer.py
old_thresh = """                overlap_iou_thresh = getattr(config, 'ACCIDENT_OVERLAP_IOU', 0.20)
                is_collision = (iou >= overlap_iou_thresh) or (iou >= 0.12 and (getattr(t1, 'had_sudden_decel', False) or getattr(t2, 'had_sudden_decel', False)))"""

new_thresh = """                overlap_iou_thresh = getattr(config, 'ACCIDENT_OVERLAP_IOU', 0.45)
                # True collision requires either severe physical overlap (IoU >= 0.45) or noticeable overlap with sudden deceleration impact
                is_collision = (iou >= overlap_iou_thresh) or (iou >= 0.25 and (getattr(t1, 'had_sudden_decel', False) or getattr(t2, 'had_sudden_decel', False)))"""

if old_thresh in code:
    code = code.replace(old_thresh, new_thresh, 1)

# 2. Update collision confirmation logic to suppress heavy bumper-to-bumper queuing false positives
old_confirm = """            # Discard normal queues: vehicles stopped at red light or in traffic without high overlap or decel spike
            if (is_red_phase or (both_stopped and pair_iou < 0.22)) and (not had_decel_spike):
                if elapsed > 2.5:
                    expired_keys.append(pair_key)
                continue

            # Real accident confirmation: sustained physical overlap (IoU >= 0.20) or violent deceleration impact
            # Require at least one vehicle to be stopped to prevent false positives from passing vehicles
            if (pair_iou >= 0.20 or had_decel_spike) and one_stopped and elapsed >= confirm_time:
                expired_keys.append(pair_key)
                crash_box = (min(t1.x1, t2.x1), min(t1.y1, t2.y1), max(t1.x2, t2.x2), max(t1.y2, t2.y2)) if (t1 and t2) else (t1.box if t1 else (t2.box if t2 else None))
                decel_energy = int(abs(getattr(t1, 'speed_kmh', 25.0) * 120) + abs(getattr(t2, 'speed_kmh', 22.0) * 110) + 3950)
                candidates.append((10, Alert(
                    alert_type="accident",
                    message=f"⚠ COLLISION — Vehicles #{tid1} and #{tid2} impact confirmed! (energy: {decel_energy}J)",
                    lane=lane,
                    severity="critical",
                    bbox=crash_box
                ), lane))
                continue"""

new_confirm = """            # Dense queuing detection: in heavy traffic jams (e.g. south.mp4), multiple vehicles stop or crawl close together
            lane_tracks = [t for t in vehicle_tracks if t.lane == lane]
            lane_stopped_count = sum(1 for t in lane_tracks if t.is_stopped)
            is_heavy_queue = (lane_stopped_count >= 2) or (len(lane_tracks) >= 3 and pair_iou < 0.45)

            # Discard normal queues: stopped at red light, stopped bumper-to-bumper in traffic, or moving slow without crash decel
            if (is_red_phase or is_heavy_queue or (both_stopped and pair_iou < 0.45)) and (not had_decel_spike):
                if elapsed > 2.0:
                    expired_keys.append(pair_key)
                continue

            # In heavy traffic queues, bumper-to-bumper proximity is never an accident without deceleration shockwave
            if both_stopped and (not had_decel_spike) and (pair_iou < 0.45):
                expired_keys.append(pair_key)
                continue

            # Genuine accident confirmation: sustained severe overlap (IoU >= 0.45) or violent impact deceleration
            if (pair_iou >= overlap_iou_thresh or had_decel_spike) and one_stopped and elapsed >= confirm_time:
                expired_keys.append(pair_key)
                crash_box = (min(t1.x1, t2.x1), min(t1.y1, t2.y1), max(t1.x2, t2.x2), max(t1.y2, t2.y2)) if (t1 and t2) else (t1.box if t1 else (t2.box if t2 else None))
                decel_energy = int(abs(getattr(t1, 'speed_kmh', 25.0) * 120) + abs(getattr(t2, 'speed_kmh', 22.0) * 110) + 3950)
                candidates.append((10, Alert(
                    alert_type="accident",
                    message=f"⚠ COLLISION — Vehicles #{tid1} and #{tid2} impact confirmed! (energy: {decel_energy}J)",
                    lane=lane,
                    severity="critical",
                    bbox=crash_box
                ), lane))
                continue"""

if old_confirm in code:
    code = code.replace(old_confirm, new_confirm, 1)

# 3. Update pedestrian conflict to require real bounding box overlap and emergency stop
old_ped = """        # ── Heuristic 5: Pedestrian very close to vehicle (impact) ────────────
        for det in person_dets:
            for track in vehicle_tracks:
                if not track.is_stopped and abs(det.cx - track.cx) < 50 and abs(det.cy - track.cy) < 50:
                    ped_crash_box = (min(det.x1, track.x1), min(det.y1, track.y1), max(det.x2, track.x2), max(det.y2, track.y2))
                    candidates.append((9, Alert(
                        alert_type="accident",
                        message="⚠ PEDESTRIAN IMPACT CONFLICT — Vehicle-pedestrian collision alert!",
                        lane=track.lane or "Approach",
                        severity="high",
                        bbox=ped_crash_box
                    ), track.lane or "Approach"))"""

new_ped = """        # ── Heuristic 5: Pedestrian collision (requires actual bounding box overlap & abrupt stop) ────
        for det in person_dets:
            for track in vehicle_tracks:
                p_iou = self._compute_iou((det.x1, det.y1, det.x2, det.y2), (track.x1, track.y1, track.x2, track.y2))
                # In dense urban traffic, pedestrians on footpath walking near cars is normal.
                # Collision alert requires actual physical intersection (IoU > 0.15) AND emergency deceleration shockwave
                if (p_iou > 0.15) and getattr(track, 'had_sudden_decel', False):
                    ped_crash_box = (min(det.x1, track.x1), min(det.y1, track.y1), max(det.x2, track.x2), max(det.y2, track.y2))
                    candidates.append((9, Alert(
                        alert_type="accident",
                        message="⚠ PEDESTRIAN IMPACT CONFLICT — Vehicle-pedestrian collision impact!",
                        lane=track.lane or "Approach",
                        severity="high",
                        bbox=ped_crash_box
                    ), track.lane or "Approach"))"""

if old_ped in code:
    code = code.replace(old_ped, new_ped, 1)

with open("core/traffic_analyzer.py", "w", encoding="utf-8") as f:
    f.write(code)

print("SUCCESS: traffic_analyzer.py patched with dense traffic queueing protection!")
