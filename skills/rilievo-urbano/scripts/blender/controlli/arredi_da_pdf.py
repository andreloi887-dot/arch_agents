"""Ingombri degli arredi da una planimetria PDF vettoriale di Edificius, come bozza di arredi.json.

  pdftocairo -svg planimetria.pdf planimetria.svg
  python arredi_da_pdf.py <planimetria.svg> <cartella modello> <villa> <uscita.json> [colore=tipo ...]

Nell'SVG i tracciati sono in metri nelle coordinate dell'IFC: basta applicare rotazione e traslazione di
lotto.json → progetto_ifc per averli nelle coordinate del contesto. Si leggono i poligoni pieni dei colori dati
(predefiniti: giallo "100%, 100%, 76" e arancio "100%, 50.1", i colori usati da Andrea per gli ingombri) e per ognuno si
scrive vano, misure e anello. Il tipo (armadio, letto, ...) va poi assegnato leggendo misure e posizione: resta "da_definire".
"""
import bpy, json, math, os, re, sys
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union
svg, MOD, villa, uscita = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
colori = dict(a.split("=") for a in sys.argv[5:]) or {"100%, 100%, 76": "giallo", "100%, 50.1": "arancio"}
P = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8"))["progetto_ifc"]; s = open(svg).read()
bpy.ops.wm.open_mainfile(filepath=os.path.join(MOD, "uscita_blender", "contesto_progetto.blend"))
vani = []
for o in bpy.data.objects:
    if "vano" in o and o.get("villa") == villa:
        W = [o.matrix_world @ v.co for v in o.data.vertices]; z0 = min(w.z for w in W)
        vani.append((o["vano"], unary_union([Polygon([W[i].xy[:] for i in p.vertices]) for p in o.data.polygons if all(W[i].z < z0 + .05 for i in p.vertices)]).buffer(0.01)))
out = []
for m in re.finditer(r'<path[^>]*fill="rgb\(([^)]*)\)"[^>]*d="([^"]+)"[^>]*transform="matrix\([^)]+\)"', s):
    col = next((n for k, n in colori.items() if m.group(1).startswith(k)), None)
    pts = [(float(a), float(b)) for a, b in re.findall(r"[ML] (-?[\d.]+) (-?[\d.]+)", m.group(2))]
    if not col or len(pts) < 4: continue
    q = affinity.translate(affinity.rotate(Polygon(pts[:-1] if pts[0] == pts[-1] else pts), P["rotazione_gradi"], origin=(0, 0)), *P["traslazione"])
    nome, pv = max(vani, key=lambda v: v[1].intersection(q).area)
    if pv.intersection(q).area < 0.5 * q.area: continue                      # ingombro di un'altra villa
    c = list(q.minimum_rotated_rectangle.exterior.coords); l1, l2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    out.append({"villa": villa, "vano": nome, "tipo": "da_definire", "colore": col, "misure_m": [round(max(l1, l2), 2), round(min(l1, l2), 2)],
                "anello": [[round(x, 3), round(y, 3)] for x, y in q.exterior.coords[:-1]]})
    print(col, nome, out[-1]["misure_m"])
json.dump({"arredi": out}, open(uscita, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("scritti", len(out), "ingombri in", uscita)
