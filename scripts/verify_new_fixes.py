import urllib.request
import json
import time

def test_api():
    print("Testing /api/system/health...")
    with urllib.request.urlopen("http://localhost:8000/api/system/health", timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"  Health: {data['status']}, Clean unique incidents: {data['database']['total_incidents']}")

    print("\nTesting default 4-Way unassigned state (No video by default)...")
    with urllib.request.urlopen("http://localhost:8000/api/four-way/state", timeout=5) as resp:
        st = json.loads(resp.read().decode("utf-8"))
        for d, info in st["directions"].items():
            print(f"  {d}: connected={info['connected']}, source='{info['source']}'")
            assert not info['connected'], f"Expected {d} to start unassigned, but got {info['source']}"
    print("  [PASS] 4-way section starts with NO video placed by default!")

    print("\nTesting dynamically assigning a video source to North...")
    req = urllib.request.Request(
        "http://localhost:8000/api/four-way/switch-source",
        data=json.dumps({"camera_id": "North", "source": "assets/videos/Ambulance-stuck-in-SnapYT.App.mp4"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"  Switch result: {res}")
        assert res.get("status") in ("success", "scheduled")
    
    time.sleep(1.0)
    with urllib.request.urlopen("http://localhost:8000/api/four-way/state", timeout=5) as resp:
        st = json.loads(resp.read().decode("utf-8"))
        north_info = st["directions"]["North"]
        print(f"  North after switch: connected={north_info['connected']}, source='{north_info['source']}'")
        assert north_info["connected"]
        assert "Ambulance-stuck-in-SnapYT.App.mp4" in north_info["source"]
    print("  [PASS] Dynamic assignment succeeded! Video plays when user puts it.")

    # Reset North back to empty
    req_reset = urllib.request.Request(
        "http://localhost:8000/api/four-way/switch-source",
        data=json.dumps({"camera_id": "North", "source": ""}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_reset, timeout=5) as resp:
        pass

    print("\nTesting /api/incidents deduplication (no repeated incidents)...")
    with urllib.request.urlopen("http://localhost:8000/api/incidents", timeout=5) as resp:
        inc_list = json.loads(resp.read().decode("utf-8"))
        seen = set()
        duplicates = 0
        for inc in inc_list:
            key = (inc["type"], inc["camera_id"])
            if key in seen:
                duplicates += 1
            seen.add(key)
        print(f"  Total returned in feed: {len(inc_list)}, Unique (type, camera) pairs: {len(seen)}, duplicates: {duplicates}")
        assert duplicates == 0, f"Found {duplicates} duplicate incidents in feed!"
    print("  [PASS] Incident feed returns only unique incidents with zero duplicate flooding!")

if __name__ == "__main__":
    test_api()
