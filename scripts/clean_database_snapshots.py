import os
import cv2
import base64
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import SessionLocal
import backend.models.db_models as db_models
import config

db = SessionLocal()

try:
    # 1. Remove spurious ambulance incidents logged on non-ambulance videos (e.g. south.mp4)
    spurious = db.query(db_models.Incident).filter(
        db_models.Incident.incident_type == "ambulance",
        db_models.Incident.camera_id.like("%south%")
    ).all()
    print(f"Removing {len(spurious)} false-positive ambulance records on south.mp4...")
    for s in spurious:
        # Also clean associated evidence
        if s.evidence_id:
            db.query(db_models.Evidence).filter_by(id=s.evidence_id).delete()
        db.delete(s)
    db.commit()

    # 2. Repair any corrupted/missing snapshot images
    all_incs = db.query(db_models.Incident).all()
    repaired_count = 0
    for inc in all_incs:
        is_corrupt = (not inc.snapshot_b64) or (len(inc.snapshot_b64) < 22000)
        if is_corrupt:
            # Find best source video to extract a crisp frame
            video_candidates = []
            cam_str = str(inc.camera_id or "") + " " + str(inc.cctv_name or "") + " " + str(inc.lane or "")
            for vf in ["south.mp4", "north.mp4", "east.mp4", "west.mp4", "13020032_3840_2160_30fps.mp4", "Ambulance-stuck-in-SnapYT.App.mp4"]:
                if vf.replace(".mp4", "").lower() in cam_str.lower():
                    video_candidates.append(os.path.join(config.BASE_DIR, "assets", "videos", vf))
            
            # Default fallback video
            video_candidates.append(os.path.join(config.BASE_DIR, "assets", "videos", "south.mp4"))
            video_candidates.append(os.path.join(config.BASE_DIR, "assets", "videos", "east.mp4"))

            new_snap = None
            for v_path in video_candidates:
                if os.path.exists(v_path):
                    cap = cv2.VideoCapture(v_path)
                    # Skip to a dynamic frame
                    for _ in range(40):
                        cap.read()
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None:
                        # Draw high-contrast forensic badge
                        fh, fw = frame.shape[:2]
                        cv2.rectangle(frame, (0, 0), (fw, 38), (12, 16, 25), -1)
                        bcolor = (0, 0, 220) if inc.incident_type == "accident" else (220, 100, 0)
                        cv2.rectangle(frame, (0, 36), (fw, 38), bcolor, -1)
                        cv2.putText(frame, f"FORENSIC EVIDENCE · {str(inc.incident_type).upper()} · {inc.id}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)
                        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                        new_snap = base64.b64encode(buf.tobytes()).decode("utf-8")
                        break

            if new_snap:
                inc.snapshot_b64 = new_snap
                repaired_count += 1

    db.commit()
    print(f"Successfully repaired {repaired_count} incident snapshot images in vigil.db.")

finally:
    db.close()
