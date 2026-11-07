#!/usr/bin/env python3
"""Catasto (Agenzia delle Entrate, WMS INSPIRE, CC BY 4.0): scarica e vettorializza fabbricati,
particelle e strade di un'area in GeoJSON lat/lng.

  catasto.py --bbox sud,ovest,nord,est --out geometria/      (area max ~ 300 m di lato per 2048 px)

Il servizio è solo WMS raster (GetFeatureInfo non restituisce attributi): le sagome si ricavano dal
colore dei layer. Precisione ~0,1 m sul raster, ma la POSIZIONE del catasto è spesso sfasata di metri:
le geometrie vanno allineate in SketchUp (scripts/sketchup/importa_catasto.rb). Richiede numpy,
Pillow e opencv-python-headless.
"""
import argparse, json, math, os, sys, urllib.parse, urllib.request
import numpy as np
from PIL import Image
from shapely.geometry import Polygon
try:
    import cv2
except ImportError:
    sys.exit("Serve opencv: pip install opencv-python-headless")

WMS = "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php"
FONTE = "Agenzia delle Entrate – Cartografia catastale WMS, CC BY 4.0"
LAYERS = ["fabbricati", "CP.CadastralParcel", "strade", "codice_plla"]


def getmap(bbox, layer, size, out):
    s, w, n, e = bbox
    q = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "CRS": "EPSG:4258",
         "BBOX": f"{s},{w},{n},{e}", "WIDTH": size, "HEIGHT": size, "LAYERS": layer, "STYLES": "",
         "FORMAT": "image/png", "TRANSPARENT": "true"}
    req = urllib.request.Request(WMS + "?" + urllib.parse.urlencode(q), headers={"User-Agent": "rilievo-urbano/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
        if not r.headers.get("Content-Type", "").startswith("image/"):
            raise RuntimeError(f"{layer}: {data[:200]!r}")
    with open(out, "wb") as f:
        f.write(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bbox", required=True, help="sud,ovest,nord,est (gradi)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--tolleranza", type=float, default=0.25, help="semplificazione dei contorni in metri")
    ap.add_argument("--solo-vettorializza", action="store_true", help="riusa i PNG già scaricati in --out")
    a = ap.parse_args()
    bbox = [float(v) for v in a.bbox.split(",")]
    s, w, n, e = bbox
    N = a.size
    os.makedirs(a.out, exist_ok=True)
    for L in LAYERS:
        if not a.solo_vettorializza:
            getmap(bbox, L, N, os.path.join(a.out, f"catasto_{L}.png"))
    meta = {"bbox_lat_lng": bbox, "crs": "EPSG:4258", "size": N, "fonte": FONTE}
    json.dump(meta, open(os.path.join(a.out, "catasto.meta.json"), "w"), indent=1)

    mx = (e - w) * 111320 * math.cos(math.radians((s + n) / 2)) / N
    my = (n - s) * 111320 / N

    def to_ll(x, y):
        return [round(w + (x + .5) / N * (e - w), 7), round(n - (y + .5) / N * (n - s), 7)]

    def polys(mask, min_m2, tipo, espandi_px):
        """espandi_px: il contorno di OpenCV passa per i centri dei pixel di bordo, cioè mezzo pixel dentro
        la regione, e la regione stessa è separata dalle vicine dalla linea della mappa (ed eventualmente
        dall'erosione). Il poligono viene allargato di espandi_px per riportare il confine sulla mezzeria
        della linea: senza, una particella perde ~0,15 m per lato (≈ 2 % dell'area)."""
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        out = []
        for c in cnts:
            if len(c) < 3 or cv2.contourArea(c) * mx * my < min_m2:   # soglia sull'area grezza: stesso elenco di prima
                continue
            g = Polygon([(float(p[0][0]), float(p[0][1])) for p in c]).buffer(0)
            if espandi_px: g = g.buffer(espandi_px, join_style=2, mitre_limit=3.0)
            if g.geom_type != "Polygon": g = max(g.geoms, key=lambda q: q.area)
            area = g.area * mx * my
            ring = [to_ll(x, y) for x, y in list(g.simplify(a.tolleranza / mx).exterior.coords)[:-1]]
            ring.append(ring[0])
            x, y, bw, bh = cv2.boundingRect(c)
            (rcx, rcy), (rw, rh), ang = cv2.minAreaRect(c)
            out.append({"type": "Feature", "properties": {
                "tipo": tipo, "area_m2": round(area, 1),
                "ingombro_m": sorted([round((rw + 2 * espandi_px) * mx, 1), round((rh + 2 * espandi_px) * my, 1)], reverse=True),
                "centroide": to_ll(g.centroid.x, g.centroid.y),
                "tagliato_dal_bordo": x <= 1 or y <= 1 or x + bw >= N - 1 or y + bh >= N - 1},
                "geometry": {"type": "Polygon", "coordinates": [ring]}})
        return out

    k3 = np.ones((3, 3), np.uint8)
    fb = np.array(Image.open(os.path.join(a.out, "catasto_fabbricati.png")).convert("RGBA")).astype(int)
    m_fb = ((fb[:, :, 3] > 200) & (fb[:, :, 0] > 200) & (fb[:, :, 1] > 100) & (fb[:, :, 1] < 160) & (fb[:, :, 2] < 60))
    fabbricati = polys(cv2.morphologyEx(m_fb.astype(np.uint8) * 255, cv2.MORPH_CLOSE, k3), 8, "fabbricato", 0.5)
    st = np.array(Image.open(os.path.join(a.out, "catasto_strade.png")).convert("RGBA")).astype(int)
    m_st = ((st[:, :, 3] > 200) & (abs(st[:, :, 0] - 150) < 25) & (abs(st[:, :, 1] - 150) < 25)).astype(np.uint8) * 255
    m_st = cv2.morphologyEx(m_st, cv2.MORPH_CLOSE, k3)
    strade = polys(m_st, 50, "strada", 0.5)
    pa = np.array(Image.open(os.path.join(a.out, "catasto_CP.CadastralParcel.png")).convert("RGBA")).astype(int)
    linee = (pa[:, :, 3] > 120) & (pa[:, :, 0] < 110) & (pa[:, :, 1] < 110)
    fill = (~linee).astype(np.uint8) * 255
    fill[m_st > 0] = 0
    # erosione 2×2 per staccare particelle unite da linee interrotte (toglie 1 px su un lato). Fra due
    # particelle restano 3 px fra i contorni (linea 1 px + erosione 1 px + 2 mezzi pixel): +1,5 px a testa
    # riporta il confine sulla mezzeria. L'erosione resta 2×2 per non cambiare l'ordine delle particelle.
    particelle = polys(cv2.erode(fill, np.ones((2, 2), np.uint8)), 5, "particella", 1.5)   # 5 m²: tiene anche i frustoli

    nota = "Posizione NON allineata: il catasto è spesso sfasato. Usare come forma; allineare su Add Location/ortofoto."
    for name, feats in (("catasto_fabbricati.geojson", fabbricati), ("catasto_strade_particelle.geojson", strade + particelle)):
        json.dump({"type": "FeatureCollection", "attribution": FONTE, "nota": nota, "features": feats},
                  open(os.path.join(a.out, name), "w"), indent=1)
    print(f"{len(fabbricati)} fabbricati, {len(particelle)} particelle, {len(strade)} aree stradali -> {a.out}")


if __name__ == "__main__":
    main()
