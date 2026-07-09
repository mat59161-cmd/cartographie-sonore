#!/usr/bin/env python3
"""
dem_to_png.py — Convertit un DEM lourd (GeoJSON / XYZ / CSV) en heightmap
PNG légère pour le viewer 3D (module Façades 3D de index.html).

Principe : le gros fichier reste sur ton disque ; on ne publie sur GitHub
que deux petits fichiers :
  dem.png   — altitudes encodées sur 16 bits (canaux R+G, précision
              (zmax-zmin)/65535, typiquement < 1 mm sur un site urbain)
  dem.json  — géoréférencement (bbox, zmin/zmax, mode CRS)

Usage :
  python dem_to_png.py dem.geojson
  python dem_to_png.py dem.geojson --size 1024        # côté max en pixels (défaut 1024)
  python dem_to_png.py dem.geojson --res 3            # ou résolution en mètres/pixel
  python dem_to_png.py dem.xyz --out data/facades/    # dossier de sortie

Entrées acceptées :
  .geojson : Point/MultiPoint/LineString avec Z (3e coordonnée ou champ Z/ALT/ELEV)
  .xyz/.csv/.txt : colonnes x y z (espaces, tab ou virgules)

Dépendances : numpy + Pillow (pip install numpy pillow). scipy optionnel
(interpolation linéaire plus lisse) ; sans scipy, remplissage par dilatations.
"""

import json, os, sys, argparse
import numpy as np
from PIL import Image

EXT = 20037508.342789244

def ll2merc(lon, lat):
    x = lon * EXT / 180.0
    y = np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)) * 6378137.0
    return x, y

def crs_mode(x, y):
    ax, ay = abs(x), abs(y)
    if ax <= 180 and ay <= 90:
        return 'wgs84'
    if ax > 2_500_000 or ay > 2_500_000:
        return '3857'
    return 'local'

def load_points(path):
    ext = os.path.splitext(path)[1].lower()
    pts = []
    if ext in ('.geojson', '.json'):
        gj = json.load(open(path, encoding='utf-8'))
        for f in gj.get('features', []):
            g = f.get('geometry') or {}
            p = f.get('properties') or {}
            zp = None
            for k in p:
                if k.upper() in ('Z', 'ALT', 'ALTITUDE', 'ELEV', 'ELEVATION', 'HEIGHT'):
                    try: zp = float(p[k])
                    except (TypeError, ValueError): pass
                    break
            def eat(c):
                if not c or len(c) < 2: return
                z = c[2] if len(c) > 2 else zp
                if z is None: return
                pts.append((c[0], c[1], float(z)))
            t = g.get('type', '')
            if t == 'Point': eat(g['coordinates'])
            elif t == 'MultiPoint':
                for c in g['coordinates']: eat(c)
            elif t == 'LineString':
                for c in g['coordinates']: eat(c)
            elif t == 'MultiLineString':
                for l in g['coordinates']:
                    for c in l: eat(c)
    else:
        raw = open(path, encoding='utf-8').read().replace(',', ' ')
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) < 3: continue
            try: pts.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError: continue
    if len(pts) < 3:
        sys.exit('✗ Moins de 3 points 3D lisibles — vérifie le fichier (Z présent ?).')
    return np.asarray(pts, dtype=np.float64)

def main():
    ap = argparse.ArgumentParser(description='DEM -> heightmap PNG pour le viewer 3D')
    ap.add_argument('input', help='dem.geojson / .xyz / .csv')
    ap.add_argument('--size', type=int, default=1024, help='côté max en pixels (défaut 1024)')
    ap.add_argument('--res', type=float, default=None, help='résolution en m/pixel (prioritaire sur --size)')
    ap.add_argument('--out', default='.', help='dossier de sortie (défaut : courant)')
    ap.add_argument('--smooth', type=float, default=None,
                    help='lissage du relief : sigma gaussien en mètres (défaut : 2 x la cellule ; 0 = brut)')
    a = ap.parse_args()

    print(f'Lecture de {a.input} ...')
    P = load_points(a.input)
    n_in = len(P)
    mode = crs_mode(P[0, 0], P[0, 1])
    if mode == 'wgs84':
        P[:, 0], P[:, 1] = ll2merc(P[:, 0], P[:, 1])
        mode = '3857'
    print(f'  {n_in:,} points · CRS détecté : {mode}')

    x0, y0 = P[:, 0].min(), P[:, 1].min()
    x1, y1 = P[:, 0].max(), P[:, 1].max()
    zmin, zmax = float(P[:, 2].min()), float(P[:, 2].max())
    if zmax - zmin < 0.01: zmax = zmin + 0.01
    W, H = x1 - x0, y1 - y0
    if W <= 0 or H <= 0:
        sys.exit('✗ Emprise dégénérée.')

    if a.res:
        nx, ny = max(2, int(round(W / a.res))), max(2, int(round(H / a.res)))
    else:
        s = a.size / max(W, H)
        nx, ny = max(2, int(round(W * s))), max(2, int(round(H * s)))
    cell = W / nx
    print(f'  Emprise {W:.0f} x {H:.0f} m · grille {nx} x {ny} px (~{cell:.1f} m/px) · z [{zmin:.2f} ; {zmax:.2f}] m')

    # Rasterisation : moyenne des points par cellule (ligne 0 = nord = y max)
    ix = np.clip(((P[:, 0] - x0) / W * nx).astype(int), 0, nx - 1)
    iy = np.clip(((y1 - P[:, 1]) / H * ny).astype(int), 0, ny - 1)
    ssum = np.zeros((ny, nx)); cnt = np.zeros((ny, nx))
    np.add.at(ssum, (iy, ix), P[:, 2]); np.add.at(cnt, (iy, ix), 1)
    known = cnt > 0
    Z = np.where(known, ssum / np.maximum(cnt, 1), np.nan)
    print(f'  Cellules renseignées : {known.sum():,}/{nx*ny:,} ({100*known.mean():.1f} %)')

    # Remplissage des trous
    try:
        from scipy.interpolate import griddata
        jj, ii = np.mgrid[0:ny, 0:nx]
        kn = np.column_stack([ii[known], jj[known]])
        kv = Z[known]
        miss = ~known
        if miss.any():
            q = np.column_stack([ii[miss], jj[miss]])
            v = griddata(kn, kv, q, method='linear')
            bad = np.isnan(v)
            if bad.any():
                v[bad] = griddata(kn, kv, q[bad], method='nearest')
            Z[miss] = v
        print('  Interpolation : scipy griddata (linéaire + nearest en bordure)')
    except ImportError:
        it = 0
        while np.isnan(Z).any() and it < 4000:
            m = np.isnan(Z)
            s = np.zeros_like(Z); c = np.zeros_like(Z)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0: continue
                    sh = np.roll(np.roll(Z, dy, 0), dx, 1)
                    ok = ~np.isnan(sh)
                    s[ok] += sh[ok]; c[ok] += 1
            fill = m & (c > 0)
            Z[fill] = s[fill] / c[fill]
            it += 1
        print(f'  Interpolation : dilatation ({it} passes, scipy absent)')

    # Lissage (supprime les cônes/arêtes du TIN issus des points épars)
    sm = a.smooth if a.smooth is not None else 2.0 * cell
    if sm > 0:
        sigma_px = sm / cell
        try:
            from scipy.ndimage import gaussian_filter
            Z = gaussian_filter(Z, sigma=sigma_px, mode='nearest')
            meth = 'gaussien scipy'
        except ImportError:
            it = max(1, min(40, int(round(1.5 * sigma_px * sigma_px))))
            for _ in range(it):
                Pd = np.pad(Z, 1, mode='edge')
                Z = (Pd[:-2,:-2]+Pd[:-2,1:-1]+Pd[:-2,2:]+Pd[1:-1,:-2]+Pd[1:-1,1:-1]
                     +Pd[1:-1,2:]+Pd[2:,:-2]+Pd[2:,1:-1]+Pd[2:,2:]) / 9.0
            meth = f'box 3x3 x{it}'
        print(f'  Lissage : sigma {sm:.1f} m ({meth})')
    else:
        print('  Lissage : désactivé (--smooth 0)')

    # Encodage 16 bits sur R+G
    v16 = np.clip(np.round((Z - zmin) / (zmax - zmin) * 65535), 0, 65535).astype(np.uint32)
    img = np.zeros((ny, nx, 3), dtype=np.uint8)
    img[:, :, 0] = (v16 >> 8).astype(np.uint8)
    img[:, :, 1] = (v16 & 255).astype(np.uint8)

    os.makedirs(a.out, exist_ok=True)
    png_path = os.path.join(a.out, 'dem.png')
    json_path = os.path.join(a.out, 'dem.json')
    Image.fromarray(img, 'RGB').save(png_path, optimize=True)
    meta = {'format': 'heightmap-rg16', 'mode': mode, 'file': 'dem.png',
            'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1,
            'zmin': zmin, 'zmax': zmax, 'nx': nx, 'ny': ny}
    json.dump(meta, open(json_path, 'w'), indent=1)

    # Auto-vérification (aller-retour d'encodage)
    zr = zmin + (img[:, :, 0].astype(np.float64) * 256 + img[:, :, 1]) / 65535 * (zmax - zmin)
    err = np.abs(zr - Z).max()
    kb = os.path.getsize(png_path) / 1024
    in_mb = os.path.getsize(a.input) / 1e6
    print(f'✓ {png_path}  ({kb:.0f} Ko)  +  dem.json')
    print(f'  Précision verticale : ± {(zmax-zmin)/65535/2*1000:.2f} mm (erreur max vérifiée {err*1000:.2f} mm)')
    print(f'  Réduction : {in_mb:.1f} Mo -> {kb/1024:.2f} Mo  (x{in_mb/(kb/1024):.0f})')
    print(f'  -> à poser dans data/facades/ (avec dem.json), puis relancer generate_manifest.py')

if __name__ == '__main__':
    main()
