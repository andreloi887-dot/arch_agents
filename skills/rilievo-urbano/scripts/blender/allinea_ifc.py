"""Allineamento di un IFC non georiferito al lotto del contesto (prima di importa_progetto.py).

  blender -b -P allinea_ifc.py -- <cartella modello> <file.ifc> [--scrivi]

Pianta: il perimetro del progetto (inviluppo di muri e solai) si adatta al lotto del rilievo: lati verso le strade
sul bordo della sede (superfici P01/P02 di contesto.json), lati verso i vicini sul confine catastale (P03).
Ricerca a griglia (rotazione ±6°, traslazione ±4 m attorno al centro) e rifinitura; lo scarto si misura sul 85 %
dei punti migliori, così una parte di progetto che esce dal lotto catastale (marciapiede, punta) non sposta tutto.
Quota: mediana di (quota del rilievo − quota IFC) del terreno IFC che cade su carreggiate e marciapiedi esistenti;
è un valore di partenza: con "ville" in lotto.json ogni villa prende la quota dal suo cancello.
Con --scrivi aggiorna lotto.json → progetto_ifc (file, rotazione_gradi, traslazione, dz).
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, z_piano
import ifcopenshell, ifcopenshell.geom
from shapely import affinity
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

argv, opt = argomenti()
MOD, IFC = os.path.abspath(argv[0]), os.path.abspath(argv[1])
CT = json.load(open(os.path.join(MOD, "contesto.json"), encoding="utf-8"))
def unione(prefissi):
    return unary_union([Polygon([s["vertici"][i][:2] for i in t[:3]]).buffer(0.01) for s in CT["superfici"]
                        if s["nome"].startswith(prefissi) for t in s["triangoli"]]).buffer(-0.01)
LOT, STRADE = unione(("P03",)), unione(("P01", "P02"))
if LOT.geom_type == "MultiPolygon": LOT = max(LOT.geoms, key=lambda g: g.area)
BORDO_S, BORDO_L = STRADE.boundary, LOT.exterior
def scarto(x, y):
    """distanza dal bordo giusto: della sede stradale se il punto è vicino a una strada, altrimenti del confine."""
    pt = Point(x, y)
    return BORDO_S.distance(pt) if STRADE.distance(pt) < 3.0 else BORDO_L.distance(pt)

f = ifcopenshell.open(IFC); st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
pts, sito = [], []
for el in f.by_type("IfcProduct"):
    if not el.Representation or el.is_a("IfcSpace") or el.is_a("IfcOpeningElement"): continue
    if not (el.is_a("IfcWall") or el.is_a("IfcSlab") or el.is_a("IfcSite")): continue
    try: g = ifcopenshell.geom.create_shape(st, el).geometry
    except Exception: continue
    v = g.verts
    if el.is_a("IfcSite"):
        F = g.faces; sito += [[(v[3 * i], v[3 * i + 1], v[3 * i + 2]) for i in F[k:k + 3]] for k in range(0, len(F), 3)]
    else: pts += [(v[i], v[i + 1]) for i in range(0, len(v), 3)]
cx = sorted(p[0] for p in pts)[len(pts) // 2]; cy = sorted(p[1] for p in pts)[len(pts) // 2]
PER = MultiPoint([p for p in pts if abs(p[0] - cx) < 60 and abs(p[1] - cy) < 60]).convex_hull
CAMP = [PER.exterior.interpolate(d) for d in [i * 0.5 for i in range(int(PER.exterior.length / 0.5))]]
C0 = PER.centroid; T0 = (LOT.centroid.x - C0.x, LOT.centroid.y - C0.y)
def trasf(x, y, r, t):
    c, s = math.cos(math.radians(r)), math.sin(math.radians(r)); return x * c - y * s + t[0], x * s + y * c + t[1]
def costo(r, t):
    d = sorted(scarto(*trasf(p.x, p.y, r, t)) for p in CAMP)[:int(0.85 * len(CAMP))]
    return (sum(x * x for x in d) / len(d)) ** 0.5
best = None
for r in [i * 0.5 for i in range(-12, 13)]:
    # centro del progetto ruotato sul centro del lotto, poi spostamenti ±4 m
    cr = trasf(C0.x, C0.y, r, (0, 0)); base = (LOT.centroid.x - cr[0], LOT.centroid.y - cr[1])
    for dx in [i * 0.5 for i in range(-8, 9)]:
        for dy in [i * 0.5 for i in range(-8, 9)]:
            c_ = costo(r, (base[0] + dx, base[1] + dy))
            if best is None or c_ < best[0]: best = (c_, r, base[0] + dx, base[1] + dy)
c_, r, tx, ty = best
for passo in (0.2, 0.1, 0.05, 0.02):
    migliorato = True
    while migliorato:
        migliorato = False
        for d in ((passo, 0, 0), (-passo, 0, 0), (0, passo, 0), (0, -passo, 0), (0, 0, passo), (0, 0, -passo)):
            c2 = costo(r + d[0], (tx + d[1], ty + d[2]))
            if c2 < c_: c_, r, tx, ty, migliorato = c2, r + d[0], tx + d[1], ty + d[2], True
# quota: terreno IFC sulle strade esistenti
TRI, TZ = [], []
for s in CT["superfici"]:
    if not s["nome"].startswith(("P01", "P02")): continue
    for t in s["triangoli"]:
        q3 = [s["vertici"][i] for i in t[:3]]; TRI.append(Polygon([q[:2] for q in q3])); TZ.append(q3)
ALB = STRtree(TRI); dzs = []
for t in sito:
    x, y = trasf(sum(p[0] for p in t) / 3, sum(p[1] for p in t) / 3, r, (tx, ty)); pt = Point(x, y)
    for k in ALB.query(pt):
        if TRI[k].contains(pt): dzs.append(z_piano(TZ[k], x, y) - sum(p[2] for p in t) / 3); break
dzs.sort(); dz = dzs[len(dzs) // 2] if dzs else 0.0
q25, q75 = (dzs[len(dzs) // 4], dzs[3 * len(dzs) // 4]) if dzs else (0, 0)
ris = {"file": os.path.relpath(IFC, MOD).replace("\\", "/"), "rotazione_gradi": round(r, 2), "traslazione": [round(tx, 2), round(ty, 2)], "dz": round(dz, 2)}
print("ALLINEAMENTO", json.dumps(ris, ensure_ascii=False))
print(f"scarto del perimetro (85 % dei punti): {c_:.2f} m RMS; quota: {len(dzs)} campioni, p25/p75 {q25:.2f}/{q75:.2f}")
if "--scrivi" in argv:
    lp = os.path.join(MOD, "lotto.json"); L = json.load(open(lp, encoding="utf-8"))
    L.setdefault("progetto_ifc", {}).update(ris)
    json.dump(L, open(lp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("scritto in", lp)
