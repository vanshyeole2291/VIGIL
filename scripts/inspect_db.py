with open('backend/video_processor_4way.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if any(k in l for k in ['db_models', 'SessionLocal', 'models.Incident', 'Session']):
        print(f'{i+1}: {l.strip()}')
