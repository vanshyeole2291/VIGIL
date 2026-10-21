"""
scripts/generate_ai_test_videos.py
==================================
Synthesizes 4 realistic AI benchmark test videos for the VIGIL system:
1. assets/videos/ai_north_high_density.mp4: Heavy multi-lane vehicle queue (8-12 vehicles) for testing high-density Webster signal prioritization.
2. assets/videos/ai_south_accident.mp4: Vehicle collision with sudden deceleration impact, overlap, and stationary dwell for testing accident detection and evidence logging.
3. assets/videos/ai_west_ambulance.mp4: White emergency vehicle with active alternating red/blue rooftop strobes for testing instant priority preemption.
4. assets/videos/ai_east_light_flow.mp4: Light traffic flow (1 car clearing) for testing quick 5s clearance and early green truncation.
"""

import os
import cv2
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 640, 360
FPS = 30.0
DURATION_SEC = 15
TOTAL_FRAMES = int(FPS * DURATION_SEC)

def draw_road(frame, lanes=2, vertical=False):
    """Draw realistic asphalt roadway with curbs, lane dashes, and crosswalk."""
    frame[:] = (45, 105, 50)  # Grass background
    
    if not vertical:
        # Horizontal road
        road_top = 80
        road_bot = 280
        cv2.rectangle(frame, (0, road_top), (W, road_bot), (60, 60, 60), -1)
        # Curbs
        cv2.line(frame, (0, road_top), (W, road_top), (200, 200, 200), 3)
        cv2.line(frame, (0, road_bot), (W, road_bot), (200, 200, 200), 3)
        # Center dashed divider
        mid_y = (road_top + road_bot) // 2
        for x in range(0, W, 40):
            cv2.line(frame, (x, mid_y), (min(W, x + 24), mid_y), (255, 255, 255), 2)
        # Stop line
        cv2.line(frame, (W - 80, road_top), (W - 80, road_bot), (255, 255, 255), 4)
    else:
        # Vertical road
        road_left = 180
        road_right = 460
        cv2.rectangle(frame, (road_left, 0), (road_right, H), (60, 60, 60), -1)
        # Curbs
        cv2.line(frame, (road_left, 0), (road_left, H), (200, 200, 200), 3)
        cv2.line(frame, (road_right, 0), (road_right, H), (200, 200, 200), 3)
        # Center dashed divider
        mid_x = (road_left + road_right) // 2
        for y in range(0, H, 40):
            cv2.line(frame, (mid_x, y), (mid_x, min(H, y + 24)), (255, 255, 255), 2)
        # Stop line
        cv2.line(frame, (road_left, H - 70), (road_right, H - 70), (255, 255, 255), 4)

def draw_car(frame, x, y, w, h, color=(40, 40, 200), angle=0, headlights=True):
    """Render a passenger car with windshield, roof, wheels, and lights."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    # Shadow
    cv2.rectangle(frame, (x - 2, y - 2), (x + w + 2, y + h + 2), (30, 30, 30), -1)
    # Body
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (20, 20, 20), 1)
    # Windshields
    front_w = int(w * 0.22)
    back_w = int(w * 0.18)
    # Front windshield (assuming rightwards movement)
    cv2.rectangle(frame, (x + w - front_w - 6, y + 4), (x + w - 6, y + h - 4), (160, 190, 210), -1)
    # Rear windshield
    cv2.rectangle(frame, (x + 6, y + 4), (x + 6 + back_w, y + h - 4), (160, 190, 210), -1)
    # Roof
    cv2.rectangle(frame, (x + back_w + 10, y + 3), (x + w - front_w - 10, y + h - 3),
                  tuple(max(0, c - 25) for c in color), -1)
    # Wheels
    cv2.rectangle(frame, (x + 8, y - 3), (x + 22, y), (10, 10, 10), -1)
    cv2.rectangle(frame, (x + w - 22, y - 3), (x + w - 8, y), (10, 10, 10), -1)
    cv2.rectangle(frame, (x + 8, y + h), (x + 22, y + h + 3), (10, 10, 10), -1)
    cv2.rectangle(frame, (x + w - 22, y + h), (x + w - 8, y + h + 3), (10, 10, 10), -1)
    if headlights:
        # Headlights on right
        cv2.rectangle(frame, (x + w - 2, y + 2), (x + w + 2, y + 7), (255, 255, 230), -1)
        cv2.rectangle(frame, (x + w - 2, y + h - 7), (x + w + 2, y + h - 2), (255, 255, 230), -1)
        # Taillights on left
        cv2.rectangle(frame, (x - 2, y + 2), (x, y + 7), (0, 0, 220), -1)
        cv2.rectangle(frame, (x - 2, y + h - 7), (x, y + h - 2), (0, 0, 220), -1)

def draw_ambulance(frame, x, y, w, h, frame_idx=0):
    """Render an emergency ambulance with red cross, side stripes, and flashing strobes."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    # Shadow
    cv2.rectangle(frame, (x - 2, y - 2), (x + w + 2, y + h + 2), (30, 30, 30), -1)
    # White body
    cv2.rectangle(frame, (x, y), (x + w, y + h), (245, 245, 248), -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (40, 40, 40), 2)
    # Red emergency side stripes
    stripe_y = y + int(h * 0.40)
    stripe_h = max(3, int(h * 0.20))
    cv2.rectangle(frame, (x, stripe_y), (x + w, stripe_y + stripe_h), (0, 0, 220), -1)
    # Windshield
    front_w = int(w * 0.20)
    cv2.rectangle(frame, (x + w - front_w - 4, y + 5), (x + w - 4, y + h - 5), (140, 180, 220), -1)
    # Red Cross on roof
    cx = x + int(w * 0.45)
    cy = y + h // 2
    cr_sz = max(4, int(h * 0.25))
    cv2.rectangle(frame, (cx - cr_sz, cy - 2), (cx + cr_sz, cy + 2), (0, 0, 220), -1)
    cv2.rectangle(frame, (cx - 2, cy - cr_sz), (cx + 2, cy + cr_sz), (0, 0, 220), -1)
    # Emergency Lightbar on roof (alternating high-intensity RED and BLUE strobes)
    lb_x = x + int(w * 0.70)
    lb_w = max(14, int(w * 0.16))
    lb_y = y + h // 2 - 5
    lb_h = 10
    phase = (frame_idx // 3) % 2
    if phase == 0:
        red_color = (0, 0, 255)
        blue_color = (255, 80, 20)
    else:
        red_color = (255, 80, 20)
        blue_color = (0, 0, 255)
    # Red strobe
    cv2.rectangle(frame, (lb_x, lb_y), (lb_x + lb_w // 2, lb_y + lb_h), red_color, -1)
    # Blue strobe
    cv2.rectangle(frame, (lb_x + lb_w // 2, lb_y), (lb_x + lb_w, lb_y + lb_h), blue_color, -1)
    # Bright halo
    cv2.circle(frame, (lb_x + lb_w // 4, lb_y + lb_h // 2), 6, red_color, 1)
    cv2.circle(frame, (lb_x + 3 * lb_w // 4, lb_y + lb_h // 2), 6, blue_color, 1)

def generate_video_north_high_density():
    """AI Test Video: North High Density Queue."""
    path = os.path.join(OUTPUT_DIR, "ai_north_high_density.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, FPS, (W, H))
    
    # 8-10 vehicles queued in 2 lanes moving very slowly then queuing at stop line
    vehicles = [
        {"x": 460, "lane": 105, "w": 72, "h": 36, "color": (190, 190, 190), "spd": 0.4},
        {"x": 370, "lane": 105, "w": 68, "h": 34, "color": (40, 120, 200), "spd": 0.4},
        {"x": 280, "lane": 105, "w": 75, "h": 36, "color": (30, 30, 30), "spd": 0.4},
        {"x": 190, "lane": 105, "w": 65, "h": 34, "color": (30, 160, 50), "spd": 0.4},
        {"x": 100, "lane": 105, "w": 70, "h": 35, "color": (180, 50, 40), "spd": 0.4},
        {"x": 480, "lane": 210, "w": 70, "h": 36, "color": (210, 210, 210), "spd": 0.3},
        {"x": 390, "lane": 210, "w": 68, "h": 34, "color": (40, 40, 180), "spd": 0.3},
        {"x": 300, "lane": 210, "w": 74, "h": 36, "color": (160, 160, 60), "spd": 0.3},
        {"x": 210, "lane": 210, "w": 66, "h": 34, "color": (120, 40, 120), "spd": 0.3},
        {"x": 120, "lane": 210, "w": 70, "h": 35, "color": (200, 120, 30), "spd": 0.3},
    ]

    for f in range(TOTAL_FRAMES):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        draw_road(frame, lanes=2)
        cv2.putText(frame, "CAM 1 - NORTH APPROACH [HIGH DENSITY BENCHMARK]", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2)
        for v in vehicles:
            if v["x"] < W - 150:
                v["x"] += v["spd"] * (1.0 - (v["x"] / (W - 120)))
            draw_car(frame, v["x"], v["lane"], v["w"], v["h"], v["color"])
        out.write(frame)
    out.release()
    print(f"[Synthesized] {path}")

def generate_video_south_accident():
    """AI Test Video: South Collision Event with Deceleration Shockwave & Stationary Dwell."""
    path = os.path.join(OUTPUT_DIR, "ai_south_accident.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, FPS, (W, H))

    # Car 1 moves from left to center; Car 2 merges or turns across at center
    c1_x, c1_y = 50.0, 120.0
    c2_x, c2_y = 360.0, 210.0
    c1_spd = 2.8
    collided = False
    collision_frame = 120

    for f in range(TOTAL_FRAMES):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        draw_road(frame, lanes=2)
        cv2.putText(frame, "CAM 2 - SOUTH APPROACH [COLLISION IMPACT BENCHMARK]", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2)
        
        if f < collision_frame:
            c1_x += c1_spd
            c2_x -= 0.6
            c2_y -= 0.4
        else:
            collided = True
            # Impact shudder
            if f < collision_frame + 12:
                shudder = ((f % 2) * 2 - 1) * 3
                c1_x += shudder
                c2_y += shudder
            # Skid marks
            cv2.line(frame, (int(c1_x - 30), int(c1_y + 10)), (int(c1_x + 10), int(c1_y + 10)), (20, 20, 20), 3)
            cv2.line(frame, (int(c1_x - 30), int(c1_y + 26)), (int(c1_x + 10), int(c1_y + 26)), (20, 20, 20), 3)
            # Impact smoke puffs
            for puff in range(4):
                cv2.circle(frame, (int(c1_x + 60 + puff * 8), int(c1_y + 15 + (puff % 2) * 6)),
                           8 + puff * 2, (180, 180, 180), -1)

        draw_car(frame, c1_x, c1_y, 70, 36, (200, 30, 30))
        draw_car(frame, c2_x, c2_y, 70, 36, (40, 80, 180))
        out.write(frame)
    out.release()
    print(f"[Synthesized] {path}")

def generate_video_west_ambulance():
    """AI Test Video: West Emergency Ambulance Preemption."""
    path = os.path.join(OUTPUT_DIR, "ai_west_ambulance.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, FPS, (W, H))

    amb_x = -90.0
    amb_y = 120.0
    amb_spd = 3.6
    # Normal car ahead yielding to shoulder
    car_x = 220.0
    car_y = 120.0

    for f in range(TOTAL_FRAMES):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        draw_road(frame, lanes=2)
        cv2.putText(frame, "CAM 4 - WEST APPROACH [EMERGENCY AMBULANCE PREEMPTION]", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2)
        
        # Advance ambulance
        amb_x += amb_spd
        if amb_x > W + 50:
            amb_x = -90.0

        # Car ahead yields to the lower shoulder
        if amb_x > 80 and car_y < 220:
            car_y += 1.2
            car_x += 1.5
        elif car_x < W + 10:
            car_x += 1.8

        draw_car(frame, car_x, car_y, 68, 34, (50, 150, 210))
        draw_ambulance(frame, amb_x, amb_y, 88, 40, frame_idx=f)
        out.write(frame)
    out.release()
    print(f"[Synthesized] {path}")

def generate_video_east_light_flow():
    """AI Test Video: East Light Flow Clearance."""
    path = os.path.join(OUTPUT_DIR, "ai_east_light_flow.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, FPS, (W, H))

    car_x = -70.0
    car_y = 140.0
    car_spd = 4.0

    for f in range(TOTAL_FRAMES):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        draw_road(frame, lanes=2)
        cv2.putText(frame, "CAM 3 - EAST APPROACH [LIGHT FLOW CLEARANCE]", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2)
        
        car_x += car_spd
        if car_x < W + 80:
            draw_car(frame, car_x, car_y, 70, 36, (30, 180, 80))
        out.write(frame)
    out.release()
    print(f"[Synthesized] {path}")

if __name__ == "__main__":
    print("=" * 60)
    print("GENERATING 4 AI BENCHMARK TEST VIDEOS FOR VIGIL")
    print("=" * 60)
    generate_video_north_high_density()
    generate_video_south_accident()
    generate_video_west_ambulance()
    generate_video_east_light_flow()
    print("=" * 60)
    print("ALL 4 BENCHMARK VIDEOS GENERATED IN assets/videos/")
    print("=" * 60)
