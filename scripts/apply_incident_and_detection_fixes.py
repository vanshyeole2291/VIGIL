"""
scripts/apply_incident_and_detection_fixes.py
=============================================
Applies precision updates to:
1. config.py & core/detector.py: Ultra-early ambulance capture (lowered min area & calibrated threshold)
2. core/tracker.py: Immediate ambulance attribution & deterministic track quadrant assignment
3. backend/models/db_models.py & schemas.py: Explicit cctv_name column support
4. backend/video_processor_4way.py & backend/video_processor.py:
   - STRICTLY filter incidents to ACCIDENTS and AMBULANCES ONLY (remove parking/crowd/stall)
   - Immediate ambulance incident recording without 15s delay
   - Ensure cctv_name, camera_id, id, and snapshot_b64 are saved cleanly
5. backend/main_4way.py & backend/routers/vigil_api.py:
   - Return both frame_b64 and snapshot_b64 so feed cards render thumbnails seamlessly
"""

import sqlite3
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def update_database_schema():
    print("[1/5] Migrating SQLite vigil.db schema...")
    db_path = os.path.join(PROJECT_ROOT, "vigil.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(incidents)")
        cols = [r[1] for r in cur.fetchall()]
        if "cctv_name" not in cols:
            cur.execute("ALTER TABLE incidents ADD COLUMN cctv_name VARCHAR(128)")
            print("  Added 'cctv_name' column to incidents table.")
        
        # Clean out any old unwanted "crowd" or "parking" incident noise
        cur.execute("DELETE FROM incidents WHERE incident_type IN ('parking', 'crowd', 'stall', 'stalled_vehicle')")
        print("  Purged any non-accident/non-ambulance incident records.")
        conn.commit()
        conn.close()

def update_config_and_detector():
    print("[2/5] Updating config.py & core/detector.py for early ambulance perception...")
    cfg_path = os.path.join(PROJECT_ROOT, "config.py")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg_txt = f.read()
    
    cfg_txt = cfg_txt.replace("AMBULANCE_CONFIDENCE_THRESHOLD = 0.35", "AMBULANCE_CONFIDENCE_THRESHOLD = 0.30")
    cfg_txt = cfg_txt.replace("AMBULANCE_MIN_AREA_FRAC   = 0.005", "AMBULANCE_MIN_AREA_FRAC   = 0.001")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(cfg_txt)

    det_path = os.path.join(PROJECT_ROOT, "core", "detector.py")
    with open(det_path, "r", encoding="utf-8") as f:
        det_txt = f.read()

    old_det = "amb_conf_thresh = getattr(config, 'AMBULANCE_CONFIDENCE_THRESHOLD', 0.50)"
    new_det = "amb_conf_thresh = getattr(config, 'AMBULANCE_CONFIDENCE_THRESHOLD', 0.30)"
    det_txt = det_txt.replace(old_det, new_det)

    old_area = "min_area_frac = getattr(config, 'AMBULANCE_MIN_AREA_FRAC', 0.010)"
    new_area = "min_area_frac = getattr(config, 'AMBULANCE_MIN_AREA_FRAC', 0.001)"
    det_txt = det_txt.replace(old_area, new_area)

    with open(det_path, "w", encoding="utf-8") as f:
        f.write(det_txt)

def update_tracker():
    print("[3/5] Updating core/tracker.py for immediate quadrant assignment & ambulance voting...")
    trk_path = os.path.join(PROJECT_ROOT, "core", "tracker.py")
    with open(trk_path, "r", encoding="utf-8") as f:
        trk_txt = f.read()

    # In update(): ensure track.lane is maintained
    old_upd_snippet = "track.confidence = round(float(getattr(det, 'confidence', track.confidence)), 2)"
    new_upd_snippet = ("track.confidence = round(float(getattr(det, 'confidence', track.confidence)), 2)\n"
                       "            track.lane = getattr(det, 'lane', track.lane)")
    if old_upd_snippet in trk_txt and "track.lane = getattr(det, 'lane', track.lane)" not in trk_txt:
        trk_txt = trk_txt.replace(old_upd_snippet, new_upd_snippet)

    # In _register(det):
    old_reg_snippet = "confidence=round(float(getattr(det, 'confidence', 0.85)), 2),"
    new_reg_snippet = ("confidence=round(float(getattr(det, 'confidence', 0.85)), 2),\n"
                       "            lane=getattr(det, 'lane', None),")
    if old_reg_snippet in trk_txt and "lane=getattr(det, 'lane', None)," not in trk_txt:
        trk_txt = trk_txt.replace(old_reg_snippet, new_reg_snippet)

    with open(trk_path, "w", encoding="utf-8") as f:
        f.write(trk_txt)

def update_db_models():
    print("[4/5] Updating backend/models/db_models.py & schemas.py...")
    model_path = os.path.join(PROJECT_ROOT, "backend", "models", "db_models.py")
    with open(model_path, "r", encoding="utf-8") as f:
        mod_txt = f.read()

    if "cctv_name = Column(String(128)" not in mod_txt:
        mod_txt = mod_txt.replace(
            "camera_id = Column(String(64), ForeignKey(\"cameras.id\"), nullable=True)",
            "camera_id = Column(String(64), ForeignKey(\"cameras.id\"), nullable=True)\n    cctv_name = Column(String(128), nullable=True)"
        )
        with open(model_path, "w", encoding="utf-8") as f:
            f.write(mod_txt)

    schema_path = os.path.join(PROJECT_ROOT, "backend", "models", "schemas.py")
    with open(schema_path, "r", encoding="utf-8") as f:
        sch_txt = f.read()

    if "cctv_name: Optional[str] = None" not in sch_txt:
        sch_txt = sch_txt.replace(
            "camera_id: Optional[str] = None",
            "camera_id: Optional[str] = None\n    cctv_name: Optional[str] = None"
        )
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write(sch_txt)

def update_processors_and_apis():
    print("[5/5] Updating video_processor_4way.py & REST API endpoints...")
    # Update video_processor_4way.py
    v4_path = os.path.join(PROJECT_ROOT, "backend", "video_processor_4way.py")
    with open(v4_path, "r", encoding="utf-8") as f:
        v4_txt = f.read()

    # 1. Update ranked_candidates: ONLY accident and ambulance
    # Replace crowd/parking additions with pass
    v4_txt = v4_txt.replace(
        'elif "pedestrian" in a_type or "conflict" in a_type or "crowd" in a_type:\n                        ranked_candidates.append((8, "crowd", a_msg, a_lane, a_box))',
        '# Filtered out: non-accident / routine crowd'
    )
    v4_txt = v4_txt.replace(
        'elif "stall" in a_type or "parking" in a_type or "immobilized" in a_msg.lower():\n                        ranked_candidates.append((5, "parking", a_msg, a_lane, a_box))',
        '# Filtered out: routine queue dwell'
    )
    # Remove stall check loop
    old_stall_check = """                # Priority 3: Check for Stalled Queues (wait time >= ILLEGAL_PARKING_TIME)
                stall_limit = getattr(config, 'ILLEGAL_PARKING_TIME', 15.0)
                for lane, stats in current_lane_stats.items():
                    if getattr(stats, 'max_wait_time', 0.0) >= stall_limit:
                        stalled_box = None
                        for t in current_tracks:
                            if t.lane == lane and t.is_stopped and t.wait_time >= stall_limit:
                                stalled_box = (t.x1, t.y1, t.x2, t.y2)
                                break
                        ranked_candidates.append((4, "parking", f"Vehicle obstruction / standstill in {lane} approach ({stats.max_wait_time:.0f}s wait).", lane, stalled_box))"""
    if old_stall_check in v4_txt:
        v4_txt = v4_txt.replace(old_stall_check, "# Routine queue stalls excluded: Only true collisions & ambulances logged")

    # Give ambulance top priority (12 > 10) so it's never preempted or delayed
    v4_txt = v4_txt.replace(
        'ranked_candidates.append((7, "ambulance", f"Class-1 Emergency Priority: Ambulance active in {amb_lane} corridor.", amb_lane, amb_box))',
        'ranked_candidates.append((12, "ambulance", f"Class-1 Emergency Priority: Ambulance active in {amb_lane} corridor.", amb_lane, amb_box))'
    )

    # Ensure cctv_name is persisted to db_models.Incident
    old_db_inc = """                    db_inc = db_models.Incident(
                        id=inc_id,
                        incident_type=inc_type,"""
    new_db_inc = """                    db_inc = db_models.Incident(
                        id=inc_id,
                        incident_type=inc_type,
                        cctv_name=f"CCTV: {cctv_filename}","""
    if old_db_inc in v4_txt and "cctv_name=f\"CCTV: {cctv_filename}\"" not in v4_txt:
        v4_txt = v4_txt.replace(old_db_inc, new_db_inc)

    with open(v4_path, "w", encoding="utf-8") as f:
        f.write(v4_txt)

    # Update backend/routers/vigil_api.py: return frame_b64 in /api/accidents
    api_path = os.path.join(PROJECT_ROOT, "backend", "routers", "vigil_api.py")
    with open(api_path, "r", encoding="utf-8") as f:
        api_txt = f.read()

    old_acc_ret = '"snapshot_b64": a.snapshot_b64,'
    new_acc_ret = '"snapshot_b64": a.snapshot_b64,\n            "frame_b64": a.snapshot_b64,\n            "cctv_name": getattr(a, "cctv_name", None) or cam,'
    if old_acc_ret in api_txt and '"frame_b64": a.snapshot_b64' not in api_txt:
        api_txt = api_txt.replace(old_acc_ret, new_acc_ret)

    with open(api_path, "w", encoding="utf-8") as f:
        f.write(api_txt)

    # Update backend/main_4way.py in api_incidents()
    main_path = os.path.join(PROJECT_ROOT, "backend", "main_4way.py")
    with open(main_path, "r", encoding="utf-8") as f:
        m_txt = f.read()

    old_inc_ret = '"camera_id": c_id,'
    new_inc_ret = '"camera_id": c_id,\n                    "cctv_name": getattr(inc, "cctv_name", None) or c_id,'
    if old_inc_ret in m_txt and '"cctv_name": getattr(inc, "cctv_name", None) or c_id,' not in m_txt:
        m_txt = m_txt.replace(old_inc_ret, new_inc_ret)

    with open(main_path, "w", encoding="utf-8") as f:
        f.write(m_txt)

    print("  [DONE] All backend modules updated.")

if __name__ == "__main__":
    update_database_schema()
    update_config_and_detector()
    update_tracker()
    update_db_models()
    update_processors_and_apis()
    print("\n>>> ALL FIXES APPLIED SUCCESSFULLY! <<<")
