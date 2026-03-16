#!/usr/bin/env python3
"""
Génère manifest.json pour le viewer cartographique.

Structure attendue :
  data/
    base/           ← isosurfaces sans trafic
      iso_T0_H40.geojson ...
    traffic/        ← isosurfaces avec trafic
      iso_T0_H40.geojson ...
    road_traffic.geojson  ← couche routes (optionnel)
    manifest.json         ← généré par ce script

Usage : python generate_manifest.py
"""

import json, re, os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def scan_folder(folder):
    path = os.path.join(DATA_DIR, folder)
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path) if re.match(r'iso_T-?\d+_H\d+\.geojson', f))

base_files = scan_folder('base')
traffic_files = scan_folder('traffic')
all_files = base_files + traffic_files

temps = sorted(set(int(m.group(1)) for f in all_files if (m := re.search(r'T(-?\d+)', f))))
hums = sorted(set(int(m.group(1)) for f in all_files if (m := re.search(r'H(\d+)', f))))

manifest = {
    'temperatures': temps,
    'humidities': hums,
    'base': base_files,
    'traffic': traffic_files,
}

out = os.path.join(DATA_DIR, 'manifest.json')
with open(out, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f'✓ manifest.json généré')
print(f'  Températures : {temps}')
print(f'  Humidités    : {hums}')
print(f'  Sans trafic  : {len(base_files)} fichiers dans base/')
print(f'  Avec trafic  : {len(traffic_files)} fichiers dans traffic/')
if os.path.exists(os.path.join(DATA_DIR, 'road_traffic.geojson')):
    print(f'  road_traffic.geojson trouvé ✓')
