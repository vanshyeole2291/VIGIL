import sys
import os

with open("core/detector.py", "r", encoding="utf-8") as f:
    code = f.read()

# Add class-agnostic NMS before return detections
old_ret = """        return detections
    
    def draw(self, frame: np.ndarray, detections: List[Detection],"""

new_ret = """        # Class-agnostic duplicate NMS: suppress duplicate nested bounding boxes on same vehicle
        if len(detections) > 1:
            detections.sort(key=lambda d: d.confidence, reverse=True)
            suppressed = set()
            for i in range(len(detections)):
                if i in suppressed:
                    continue
                d1 = detections[i]
                for j in range(i + 1, len(detections)):
                    if j in suppressed:
                        continue
                    d2 = detections[j]
                    ix1 = max(d1.x1, d2.x1)
                    iy1 = max(d1.y1, d2.y1)
                    ix2 = min(d1.x2, d2.x2)
                    iy2 = min(d1.y2, d2.y2)
                    iw = max(0, ix2 - ix1)
                    ih = max(0, iy2 - iy1)
                    inter = iw * ih
                    if inter > 0:
                        a1 = (d1.x2 - d1.x1) * (d1.y2 - d1.y1)
                        a2 = (d2.x2 - d2.x1) * (d2.y2 - d2.y1)
                        union = a1 + a2 - inter
                        iou = inter / float(max(1, union))
                        containment = max(inter / float(max(1, a1)), inter / float(max(1, a2)))
                        if (iou > 0.55 or containment > 0.72) and (d1.is_vehicle and d2.is_vehicle):
                            if d2.is_ambulance and not d1.is_ambulance:
                                suppressed.add(i)
                                break
                            else:
                                suppressed.add(j)

            detections = [d for idx, d in enumerate(detections) if idx not in suppressed]

        return detections
    
    def draw(self, frame: np.ndarray, detections: List[Detection],"""

if old_ret in code:
    code = code.replace(old_ret, new_ret, 1)
    with open("core/detector.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: Added duplicate suppression NMS to core/detector.py!")
else:
    print("Target not found in detector.py!")
