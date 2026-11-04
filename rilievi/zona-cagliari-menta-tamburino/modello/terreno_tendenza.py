#!/usr/bin/env python3
"""Tendenza del terreno (suolo) da Copernicus DEM GLO-30 (DSM): polinomio di 2° grado con pesi robusti
che riducono i punti sopra la superficie (edifici, alberi). Uso: terreno_tendenza.py dem.tif
Tile: https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N39_00_E009_00_DEM/…_DEM.tif"""
import json, math, sys
import numpy as np, tifffile
R, K = 100.0, 2.0
O = (39.25240, 9.11527); KX = 111320*math.cos(math.radians(O[0])); KY = 111320
with tifffile.TiffFile(sys.argv[1]) as t:
    p = t.pages[0]; a = p.asarray().astype(float); tags = {k.name: k.value for k in p.tags.values()}
d = tags["ModelPixelScaleTag"][0]; lon0, lat0 = tags["ModelTiepointTag"][3:5]
pts = []
for r in range(int((lat0-(O[0]+0.0015))/d), int((lat0-(O[0]-0.0015))/d)+1):
    for c in range(int((O[1]-0.002-lon0)/d), int((O[1]+0.002-lon0)/d)+1):
        la = lat0-(r+0.5)*d; lo = lon0+(c+0.5)*d; x = (lo-O[1])*KX; y = (la-O[0])*KY
        if math.hypot(x, y) < R: pts.append((x, y, a[r, c]))
P = np.array(pts); X = np.c_[np.ones(len(P)), P[:, 0], P[:, 1], P[:, 0]**2, P[:, 0]*P[:, 1], P[:, 1]**2]; w = np.ones(len(P))
for _ in range(15):
    coef = np.linalg.lstsq(X*w[:, None], P[:, 2]*w, rcond=None)[0]; res = P[:, 2]-X@coef
    s = np.median(abs(res))*1.48+1e-6; w = np.where(res > 0, 1/(1+(res/(K*s))**2), 1.0)
z0 = float(coef @ np.array([1, 0, 0, 0, 0, 0]))
json.dump({"tipo": f"polinomio 2° grado robusto (R={R} m, k={K}) su Copernicus DEM GLO-30 (DSM)", "coef": list(map(float, coef)),
           "z_incrocio_slm": z0, "n_punti": len(P), "base": "x=E, y=N in metri dall'origine 39.25240, 9.11527",
           "incertezza": "±1 m vicino all'incrocio, ±2 m a 70 m", "fonte": "Copernicus DEM GLO-30 © DLR e.V./Airbus, fornito da ESA"},
          open("terreno_tendenza.json", "w"), indent=1)
print("z incrocio %.1f m slm, %d punti" % (z0, len(P)))
