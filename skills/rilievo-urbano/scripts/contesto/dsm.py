#!/usr/bin/env python3
"""DSM LiDAR 1 m della Regione Sardegna (volo 2008, fascia costiera; tavole ASC "_WGS" in UTM 32N): mosaico e
ritaglio sull'area del lotto. Produce, nella cartella del modello, tre raster allineati (float32, quote assolute):
dsm_2008.tif (superficie), dsm_2008_edifici.tif, dsm_2008_vegetazione.tif + dsm_2008.json (griglia).

  python dsm.py <cartella o file lotto.json>

lotto.json → dati.dsm = {"superficie": [...asc], "edifici": [...asc], "vegetazione": [...asc]} (percorsi relativi).
Gli indici delle tavole e i link di scarico sono nel WFS regionale `dbu:QU2k_fasciacostiera2008_DTM_DSM1m`
(e `dbu:QU2k_DTM_DSM1m_centri_urbani_2013` per i centri urbani).
"""
import json, math, os, sys
import numpy as np, tifffile

a = os.path.abspath(sys.argv[1]); LP = os.path.join(a, "lotto.json") if os.path.isdir(a) else a
M = os.path.dirname(LP); L = json.load(open(LP, encoding="utf-8"))
from pyproj import Transformer
O = (L["origine"]["lat"], L["origine"]["lng"]); EXT = float(L["semilato_m"]) + 10
E0, N0 = Transformer.from_crs("EPSG:4326", "EPSG:32632", always_xy=True).transform(O[1], O[0])
e0, e1, n0, n1 = math.floor(E0 - EXT * 1.05) - 0.5, math.ceil(E0 + EXT * 1.05) + 0.5, math.floor(N0 - EXT * 1.05) - 0.5, math.ceil(N0 + EXT * 1.05) + 0.5
W, H = int(e1 - e0), int(n1 - n0)

def leggi_asc(p):
    with open(p) as f:
        hd = {}
        for _ in range(6):
            k, v = f.readline().split(); hd[k.upper()] = float(v)
        z = np.loadtxt(f, dtype=np.float32)
    return hd, z

def mosaico(files):
    out = np.full((H, W), np.nan, dtype=np.float32)
    for rel in files:
        hd, z = leggi_asc(os.path.normpath(os.path.join(M, rel)))
        nod = hd.get("NODATA_VALUE", -9999); z[z == nod] = np.nan
        cs = hd["CELLSIZE"]; xl = hd["XLLCENTER"]; yl = hd["YLLCENTER"]; nr = int(hd["NROWS"])
        # riga 0 = Nord: centro cella (i, j) = (xl + j·cs, yl + (nr-1-i)·cs)
        for i_out in range(H):
            n_c = n1 - 0.5 - i_out                 # centro della riga di uscita
            i_in = int(round(nr - 1 - (n_c - yl) / cs))
            if not (0 <= i_in < nr): continue
            j0 = int(round((e0 + 0.5 - xl) / cs)); js = np.arange(j0, j0 + W)
            ok = (js >= 0) & (js < z.shape[1])
            row = np.full(W, np.nan, dtype=np.float32); row[ok] = z[i_in, js[ok]]
            m = np.isnan(out[i_out]) & ~np.isnan(row); out[i_out][m] = row[m]
    return out

D = L["dati"]["dsm"]; meta = {"crs": "EPSG:32632", "bordo_sinistro_E": e0, "bordo_superiore_N": n1, "passo": 1.0,
                              "fonte": "Regione Autonoma della Sardegna – DSM LiDAR 1 m, volo 2008 (fascia costiera)", "raster": {}}
for chiave, nome in (("superficie", "dsm_2008.tif"), ("edifici", "dsm_2008_edifici.tif"), ("vegetazione", "dsm_2008_vegetazione.tif")):
    if not D.get(chiave): continue
    z = mosaico(D[chiave]); tifffile.imwrite(os.path.join(M, nome), z)
    meta["raster"][chiave] = nome
    print(nome, z.shape, "copertura %.0f %%" % (100 * np.mean(~np.isnan(z))))
json.dump(meta, open(os.path.join(M, "dsm_2008.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
