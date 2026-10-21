with open('backend/models/schemas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
in_traffic_obs = False
for line in lines:
    if 'class TrafficObservationOut(BaseModel):' in line:
        in_traffic_obs = True
    elif 'class Config:' in line and in_traffic_obs:
        in_traffic_obs = False
    
    if in_traffic_obs and 'cctv_name: Optional[str] = None' in line:
        continue # skip
    out.append(line)

with open('backend/models/schemas.py', 'w', encoding='utf-8') as f:
    f.writelines(out)
print('Fixed backend/models/schemas.py')
