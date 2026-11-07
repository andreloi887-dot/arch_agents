#!/usr/bin/env python3
"""Una ripresa Street View mirata per ogni edificio della scena: pano più vicino al baricentro, camera puntata
sull'edificio. Serve al rilievo di precisione (facciate, balconi, recinzioni su strada) edificio per edificio.

  python sv_edifici.py <cartella modello con scena.json> [--fov 80] [--pitch 12]

Uscita: <zona>/_rif_google/edifici/<ID>.jpg + manifest.json (heading, distanza, data). Richiede
GOOGLE_MAPS_API_KEY (Street View Static: metadata gratuito, immagine a consumo, rientra nella quota gratuita).
Le immagini restano locali in _rif_google/ (ignorata da git): servono solo a descrivere, mai a ricavare geometria.
"""
import argparse, json, math, os, sys, urllib.parse, urllib.request
from pyproj import Transformer
from shapely.geometry import Polygon

ap = argparse.ArgumentParser()
ap.add_argument("modello"); ap.add_argument("--fov", type=float, default=0); ap.add_argument("--pitch", type=float, default=12)
a = ap.parse_args()
K = os.environ.get("GOOGLE_MAPS_API_KEY") or sys.exit("Serve GOOGLE_MAPS_API_KEY")
M = os.path.abspath(a.modello); Z = os.path.dirname(M)
sc = json.load(open(os.path.join(M, "scena.json"), encoding="utf-8"))
O = sc["origine"]
A = f"+proj=aeqd +lat_0={O['lat']} +lon_0={O['lng']} +ellps=WGS84 +units=m +no_defs"
to_ll = Transformer.from_crs(A, "EPSG:4326", always_xy=True); to_loc = Transformer.from_crs("EPSG:4326", A, always_xy=True)
OUT = os.path.join(Z, "_rif_google", "edifici"); os.makedirs(OUT, exist_ok=True)
def get(url):
    with urllib.request.urlopen(url, timeout=60) as r: return r.read()
man = []
for e in sc["edifici"]:
    c = Polygon(e["impronta"]).centroid; ln, la = to_ll.transform(c.x, c.y)
    meta = json.loads(get("https://maps.googleapis.com/maps/api/streetview/metadata?" + urllib.parse.urlencode(
        {"location": f"{la},{ln}", "radius": 60, "source": "outdoor", "key": K})))
    if meta.get("status") != "OK": print(e["id"], meta.get("status")); continue
    px, py = to_loc.transform(meta["location"]["lng"], meta["location"]["lat"])
    hd = (90 - math.degrees(math.atan2(c.y - py, c.x - px))) % 360
    dist = math.dist((px, py), (c.x, c.y)); fov = a.fov or (90 if dist < 25 else 70)
    img = get("https://maps.googleapis.com/maps/api/streetview?" + urllib.parse.urlencode(
        {"size": "640x480", "pano": meta["pano_id"], "heading": round(hd, 1), "pitch": a.pitch, "fov": fov, "key": K}))
    fn = f"{e['id']}.jpg"; open(os.path.join(OUT, fn), "wb").write(img)
    # orientamento della facciata ripresa: la sua normale guarda verso la camera
    nrm = (hd + 180) % 360
    ori = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"][int(((nrm + 22.5) % 360) // 45)]
    man.append({"id": e["id"], "file": fn, "heading": round(hd, 1), "facciata_ripresa": ori, "dist_m": round(dist, 1),
                "data": meta.get("date"), "pano": [meta["location"]["lat"], meta["location"]["lng"]]})
    print(f"{e['id']}: facciata {ori}, {dist:.0f} m, {meta.get('date')}")
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
