#!/usr/bin/env python3
"""
Génère manifest.json à partir des fichiers iso_T{X}_H{Y}.geojson présents dans data/.
Lance-le chaque fois que tu ajoutes/retires des GeoJSON :

    python generate_manifest.py

Le manifest.json est lu par index.html pour savoir quels fichiers sont disponibles
(beaucoup plus rapide que de probe chaque fichier un par un).
"""

import json, re, os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith('.geojson'))
iso_files = [f for f in files if re.match(r'iso_T-?\d+_H\d+\.geojson', f)]

temps = sorted(set(int(m.group(1)) for f in iso_files if (m := re.search(r'T(-?\d+)', f))))
hums = sorted(set(int(m.group(1)) for f in iso_files if (m := re.search(r'H(\d+)', f))))

manifest = {
    'temperatures': temps,
    'humidities': hums,
    'files': iso_files,
    'static': [f for f in files if f not in iso_files],
    'total': len(iso_files),
}

out = os.path.join(DATA_DIR, 'manifest.json')
with open(out, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f'✓ manifest.json généré : {len(iso_files)} isosurfaces ({len(temps)} T° × {len(hums)} H%)')
if manifest['static']:
    print(f'  + {len(manifest["static"])} fichiers statiques : {", ".join(manifest["static"])}')
print(f'  Températures : {temps}')
print(f'  Humidités    : {hums}')
