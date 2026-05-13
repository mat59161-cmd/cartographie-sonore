#!/usr/bin/env python3
"""
Génère manifest.json pour le viewer 5-scénarios.

Structure attendue :
  data/
    vibreur/          ← vibreur seul
    vibreur_trafic/   ← vibreur + trafic routier
    hx50/             ← HX50 seule
    hx50_trafic/      ← HX50 + trafic routier
    tout/             ← vibreur + HX50 + trafic (scénario complet)
    BUILDINGS.geojson
    road_traffic_final_3857.geojson
    manifest.json     ← généré par ce script

Usage : python generate_manifest.py
"""

import json, re, os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

SCENARIOS = [
    'vibreur', 'vibreur_dem',
    'vibreur_trafic', 'vibreur_trafic_dem',
    'hx50', 'hx50_dem',
    'hx50_trafic', 'hx50_trafic_dem',
    'tout', 'tout_dem'
]

def scan_folder(folder):
    path = os.path.join(DATA_DIR, folder)
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path) if re.match(r'iso_T-?\d+_H\d+\.geojson', f))

manifest = {'temperatures': [], 'humidities': []}
all_files = []

for sc in SCENARIOS:
    files = scan_folder(sc)
    manifest[sc] = files
    all_files.extend(files)

temps = sorted(set(int(m.group(1)) for f in all_files if (m := re.search(r'T(-?\d+)', f))))
hums = sorted(set(int(m.group(1)) for f in all_files if (m := re.search(r'H(\d+)', f))))

manifest['temperatures'] = temps
manifest['humidities'] = hums

out = os.path.join(DATA_DIR, 'manifest.json')
with open(out, 'w') as f:
    json.dump(manifest, f, indent=2)

print('✓ manifest.json généré')
print(f'  Températures : {temps}')
print(f'  Humidités    : {hums}')
for sc in SCENARIOS:
    n = len(manifest[sc])
    marker = '✓' if n > 0 else '·'
    print(f'  {marker} {sc:<20} : {n} fichiers')
if os.path.exists(os.path.join(DATA_DIR, 'BUILDINGS.geojson')):
    print('  ✓ BUILDINGS.geojson trouvé')
if os.path.exists(os.path.join(DATA_DIR, 'road_traffic_final_3857.geojson')):
    print('  ✓ road_traffic_final_3857.geojson trouvé')
