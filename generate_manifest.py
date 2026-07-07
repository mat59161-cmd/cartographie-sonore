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
    facades/          ← (optionnel) sorties de facade_3d_v6.groovy
      <scenario>/         facade_noise[_Txx_Hyy].geojson + building_selection.geojson
      ou à la racine      (repli commun à tous les scénarios)
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

# ── Façades 3D (module intégré au viewer) ────────────────────────
FACADES_DIR = os.path.join(DATA_DIR, 'facades')

def scan_facades(path):
    return sorted(f for f in os.listdir(path)
                  if f.endswith('.geojson')
                  and (f.startswith('facade_noise') or f == 'building_selection.geojson'))

manifest['facades'] = {}
if os.path.isdir(FACADES_DIR):
    root_files = scan_facades(FACADES_DIR)
    if root_files:
        manifest['facades']['_root'] = root_files
    for d in sorted(os.listdir(FACADES_DIR)):
        p = os.path.join(FACADES_DIR, d)
        if os.path.isdir(p):
            files = scan_facades(p)
            if files:
                manifest['facades'][d] = files

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
if manifest['facades']:
    print('  🏢 Façades 3D :')
    for k, files in manifest['facades'].items():
        print(f'     ✓ {k:<18} : {len(files)} fichier(s)')
else:
    print('  · facades/              : rien (optionnel — vue 3D des façades)')
if os.path.exists(os.path.join(DATA_DIR, 'BUILDINGS.geojson')):
    print('  ✓ BUILDINGS.geojson trouvé')
if os.path.exists(os.path.join(DATA_DIR, 'road_traffic_final_3857.geojson')):
    print('  ✓ road_traffic_final_3857.geojson trouvé')
