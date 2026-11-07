#!/usr/bin/env python3
"""Riprese Street View mirate per ogni edificio della scena: fino a 3 viste per edificio (frontale e dalle due
estremità del fronte su strada), camera puntata sul baricentro. Serve al rilievo di precisione edificio per
edificio: balconi per piano, infissi e oscuranti, recinzione su strada, cancelli e cancelletti.

  python sv_edifici.py <cartella modello con scena.json> [--viste 3] [--passo 12] [--pitch 12]

Uscita: <zona>/_rif_google/edifici/<ID>_<k>.jpg + manifest.json (heading, facciata ripresa, distanza, data).
Richiede GOOGLE_MAPS_API_KEY (metadata gratuito; immagini nella quota gratuita). Le immagini restano locali in
_rif_google/ (ignorata da git): servono solo a descrivere, mai a ricavare geometria.
"""
import argparse, json, math, os, sys, urllib.parse, urllib.request
from pyproj import Transformer
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points

ap = argparse.ArgumentParser()
ap.add_argument("modello"); ap.add_argument("--viste", type=int, default=3); ap.add_argument("--passo", type=float, default=12.0)
ap.add_argument("--pitch", type=float, default=12); ap.add_argument("--solo", nargs="*")
a = ap.parse_args()
K = os.environ.get("GOOGLE_MAPS_API_KEY") or sys.exit("Serve GOOGLE_MAPS_API_KEY")
M = os.path.abspath(a.modello); Z = os.path.dirname(M)
sc = json.load(open(os.path.join(M, "scena.json"), encoding="utf-8"))
O = sc["origine"]
A = f"+proj=aeqd +lat_0={O['lat']} +lon_0={O['lng']} +ellps=WGS84 +units=m +no_defs"
to_ll = Transformer.from_crs(A, "EPSG:4326", always_xy=True); to_loc = Transformer.from_crs("EPSG:4326", A, always_xy=True)
OUT = os.path.join(Z, "_rif_google", "edifici"); os.makedirs(OUT, exist_ok=True)
carr = unary_union([Polygon([(p[0], p[1]) for p in s["anello"]]).buffer(0) for s in sc["strade"]])
bordo = carr.boundary
def get(url):
    with urllib.request.urlopen(url, timeout=60) as r: return r.read()
def meta_at(x, y, r=20):
    ln, la = to_ll.transform(x, y)
    m = json.loads(get("https://maps.googleapis.com/maps/api/streetview/metadata?" + urllib.parse.urlencode(
        {"location": f"{la},{ln}", "radius": r, "source": "outdoor", "key": K})))
    return m if m.get("status") == "OK" else None
man = []
for e in sc["edifici"]:
    if a.solo and e["id"] not in a.solo: continue
    c = Polygon(e["impronta"]).centroid
    q = nearest_points(bordo, c)[0]; s_ = bordo.project(q)
    punti = [(q.x, q.y)]
    for d in (-a.passo, a.passo):
        p = bordo.interpolate(s_ + d); punti.append((p.x, p.y))
    visti = set(); k = 0
    for (x, y) in punti[:a.viste]:
        m = meta_at(x, y)
        if not m or m["pano_id"] in visti: continue
        visti.add(m["pano_id"])
        px, py = to_loc.transform(m["location"]["lng"], m["location"]["lat"])
        hd = (90 - math.degrees(math.atan2(c.y - py, c.x - px))) % 360
        dist = math.dist((px, py), (c.x, c.y)); fov = 90 if dist < 25 else 70
        img = get("https://maps.googleapis.com/maps/api/streetview?" + urllib.parse.urlencode(
            {"size": "640x480", "pano": m["pano_id"], "heading": round(hd, 1), "pitch": a.pitch, "fov": fov, "key": K}))
        k += 1; fn = f"{e['id']}_{k}.jpg"; open(os.path.join(OUT, fn), "wb").write(img)
        ori = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"][int((((hd + 180) % 360 + 22.5) % 360) // 45)]
        man.append({"id": e["id"], "file": fn, "heading": round(hd, 1), "facciata_ripresa": ori, "dist_m": round(dist, 1),
                    "data": m.get("date"), "pano_xy": [round(px, 1), round(py, 1)]})
    print(f"{e['id']}: {k} viste")
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
