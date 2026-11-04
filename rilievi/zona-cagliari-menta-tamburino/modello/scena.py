#!/usr/bin/env python3
"""Sorgente unica della scena (coordinate locali in metri: origine = incrocio 39.25240 N 9.11527 E,
x = Est, y = Nord, z = quota relativa all'incrocio). Produce scena.json, letto sia dal builder Ruby per
SketchUp 2022 sia dall'anteprima di verifica.

Dati: catasto AdE vettorializzato (../geometria), tendenza del terreno da Copernicus DEM
(terreno_tendenza.json), osservazioni della scheda (../scheda.json). Nessuna geometria da Google.
"""
import json, math, os
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
Z = os.path.dirname(HERE)
O = (39.25240, 9.11527)
KX = 111320 * math.cos(math.radians(O[0])); KY = 111320
EXT = 75.0                      # semilato dell'area modellata (m)
MARCIAPIEDE = 1.5               # larghezza marciapiedi (m), scheda P02
CORDOLO = 0.15

def loc(ln, la): return ((ln - O[1]) * KX, (la - O[0]) * KY)

T = json.load(open(os.path.join(HERE, "terreno_tendenza.json")))
C = T["coef"]
def trend(x, y):
    return C[0] + C[1]*x + C[2]*y + C[3]*x*x + C[4]*x*y + C[5]*y*y - T["z_incrocio_slm"]

scheda = json.load(open(os.path.join(Z, "scheda.json")))
PART = json.load(open(os.path.join(Z, "geometria/catasto_strade_particelle.geojson")))["features"]
FABB = json.load(open(os.path.join(Z, "geometria/catasto_fabbricati.geojson")))["features"]
area = Polygon([(-EXT, -EXT), (EXT, -EXT), (EXT, EXT), (-EXT, EXT)])

def poly(f): return Polygon([loc(*q) for q in f["geometry"]["coordinates"][0]]).buffer(0)
particelle = [(i, poly(f)) for i, f in enumerate(PART) if f["properties"]["tipo"] == "particella"]
strade = [poly(f) for f in PART if f["properties"]["tipo"] == "strada"]

# --- sedime stradale: aree 'strada' + strisce di Via Moravia (a catasto sono particelle 51 e 62)
MORAVIA = [51, 62]
sedime = unary_union(strade + [p for i, p in particelle if i in MORAVIA]).buffer(0.3).buffer(-0.3)
sedime = sedime.intersection(area)
carreggiata = sedime.buffer(-MARCIAPIEDE, join_style=2).buffer(0.5).buffer(-0.5)
_P03 = [p for i, p in particelle if i == 67][0]
# il catasto lascia una fascia tra lotto e sedime: il marciapiede arriva al piede del muro del lotto
raccordo = _P03.buffer(2.5).difference(_P03).intersection(sedime.buffer(2.5))
marciapiedi = sedime.union(raccordo).difference(carreggiata).difference(_P03).intersection(area)

def ring(p, step=2.0):
    """Anello densificato (punti ogni ~step m) per far seguire il terreno ai bordi."""
    pts = list(p.exterior.coords)[:-1]; out = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(n)]
    return out

def polys(g):
    return [g] if isinstance(g, Polygon) else [x for x in getattr(g, "geoms", []) if isinstance(x, Polygon)]

# --- lotto P03 (particella catastale 4258 = indice 67)
P03 = dict(particelle)[67]
tip = min(P03.exterior.coords, key=lambda p: math.hypot(*p))          # spigolo verso l'incrocio
# rialzo Δ del piano del lotto sul terreno di tendenza: piano per 3 punti di controllo (scheda, SV-08/12/18)
cp = [(tip[0], tip[1], 1.35),        # angolo: muro ~1,2 m sopra il marciapiede (SV-12, SV-18; rev. verifica 1)
      (-30.0, 42.0, 0.90),           # lato Tamburino Sardo verso NO: muro ~0,9 m (SV-12)
      (2.0, 35.0, 0.35)]             # lato Via della Menta al cancello: cordolo ~0,2 m, lotto quasi a raso (SV-08)
import numpy as np
A = np.array([[1, x, y] for x, y, _ in cp]); bv = np.array([d for *_, d in cp])
DA, DB, DC = np.linalg.solve(A, bv)
def z_lotto(x, y): return trend(x, y) + max(0.15, DA + DB*x + DC*y)

# fronte del lotto sulla strada = bordo del lotto entro 1 m dal sedime
def fronti(p, tol=2.5):
    pts = list(p.exterior.coords); segs = []
    for a, b in zip(pts, pts[1:]):
        mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
        if sedime.distance(Point(mid)) < tol and math.dist(a, b) > 0.3:
            segs.append((a, b))
    # unisce segmenti consecutivi in polilinee
    lines = []
    for a, b in segs:
        if lines and math.dist(lines[-1][-1], a) < 0.05: lines[-1].append(b)
        else: lines.append([a, b])
    if len(lines) > 1 and math.dist(lines[-1][-1], lines[0][0]) < 0.05:
        lines[0] = lines[-1][:-1] + lines[0]; lines.pop()
    return lines

def dens(line, step=1.0):
    out = []
    for a, b in zip(line, line[1:]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(n)]
    return out + [line[-1]]

scena = {"origine": {"lat": O[0], "lng": O[1]}, "unita": "m",
         "fonti": ["Catasto AdE WMS (CC BY 4.0), non allineato: sfasamento ≤ 1–2 m vicino all'incrocio",
                   T["fonte"] + " – tendenza robusta (DSM 30 m: incertezza ±2 m a 70 m dall'incrocio)",
                   "Altezze e rialzi da osservazioni Street View (scheda rev. 2), confidenza media/bassa"],
         "trend_coef": C, "trend_z0": T["z_incrocio_slm"], "terreno": {}, "strade": [], "marciapiedi": [], "lotto": {}, "muri": [], "recinzioni": [],
         "edifici": [], "vegetazione": [], "controllo": {}}

# --- terreno di tendenza su griglia (2 m)
step = 2.0; n = int(2*EXT/step) + 1
scena["terreno"] = {"x0": -EXT, "y0": -EXT, "passo": step, "n": n, "materiale": "TERRENO",
                    "z": [[round(trend(-EXT + i*step, -EXT + j*step), 3) for i in range(n)] for j in range(n)]}

for p in polys(carreggiata):
    scena["strade"].append({"id": "P01", "materiale": "C16",
        "anello": [[round(x, 3), round(y, 3), round(trend(x, y), 3)] for x, y in ring(p)]})
for p in polys(marciapiedi):
    if p.area < 1: continue
    holes = [[[round(x, 3), round(y, 3), round(trend(x, y) + CORDOLO, 3)] for x, y in ring(Polygon(h))] for h in p.interiors]
    scena["marciapiedi"].append({"id": "P02", "materiale": "C17",
        "anello": [[round(x, 3), round(y, 3), round(trend(x, y) + CORDOLO, 3)] for x, y in ring(p)], "fori": holes})

lot = P03.intersection(area)
scena["lotto"] = {"id": "P03", "particella": "4258", "materiale": "PRATO_SECCO",
                  "anello": [[round(x, 3), round(y, 3), round(z_lotto(x, y), 3)] for x, y in ring(lot, 1.5)],
                  "griglia_interna_passo": 3.0,
                  "rialzo_piano": {"a": DA, "b": DB, "c": DC, "punti_controllo": cp},
                  "nota": "superficie = tendenza Copernicus + rialzo Δ(x,y) lineare; prato secco ruderale"}

# --- muro di sostegno R06 lungo i fronti del lotto, recinzione in rete sul tratto di Via della Menta
for k, line in enumerate(fronti(lot)):
    pts = dens(line, 1.0)
    base = [round(trend(x, y) + CORDOLO, 3) for x, y in pts]
    top = [round(max(z_lotto(x, y), trend(x, y) + CORDOLO + 0.20), 3) for x, y in pts]
    scena["muri"].append({"id": "R06", "nome": f"R06 – muro di sostegno P03 tratto {k+1}", "materiale": "C15",
                          "spessore": 0.25, "lato_interno": "sinistra",
                          "punti": [[round(x, 3), round(y, 3)] for x, y in pts], "z_base": base, "z_sommita": top})
    # rete solo dove il fronte guarda Via della Menta (direzione media verso NNE)
    menta = [(x, y) for x, y in pts if x > tip[0] + 1.0 and y >= 24.0]  # SV-16/18: niente rete vicino all'angolo
    if len(menta) > 2:
        scena["recinzioni"].append({"id": "R06", "nome": "R06 – rete elettrosaldata su paletti", "tipo": "rete",
            "materiale": "C20", "altezza": 1.6, "passo_paletti": 2.0,
            "punti": [[round(x, 3), round(y, 3), round(max(z_lotto(x, y), trend(x, y)+CORDOLO+0.20), 3)] for x, y in menta],
            "cancello": {"tipo": "tubolare zincato a 2 ante", "larghezza": 3.0, "y_centro": 26.0, "confidenza": "bassa"}})

# --- muri di cinta del contorno (scheda R01–R11) sui fronti strada delle particelle degli edifici
def particella_di(eid):
    e = [x for x in scheda["edifici"] if x["id"] == eid][0]
    c = poly(FABB[e["impronta"]["indice"]]).centroid
    return [p for i, p in particelle if p.contains(c) and i != 67][0]
RW = {r["id"]: r for r in scheda["recinzioni"]}
def h_of(r):
    v = r.get("h", {}).get("m") if isinstance(r.get("h"), dict) else None
    return float(v) if v else 1.5
SOPRA = {"R01": ("ringhiera", 1.0, "C06"), "R02": ("doghe", 1.2, "C05"), "R03": ("ringhiera", 0.8, "C06"),
         "R04": ("doghe", 1.3, "C05")}
MURO_H = {"R01": 1.6, "R02": 2.5, "R03": 1.2, "R04": 0.6}   # parte muraria (scheda: parti)
CONT = [("R01", "E09", None), ("R02", "E08", None), ("R03", "E06", None), ("R04", "E05", None),
        ("R05", "E03", "NS"), ("R11", "E03", "EO"), ("R07", "E02", None), ("R08", "E01", None),
        ("R09", "E11", None), ("R10", "E10", None)]
for rid, eid, verso in CONT:
    try: par = particella_di(eid).intersection(area)
    except IndexError: continue
    r = RW[rid]; mat = r["materiali"][0]
    hm = MURO_H.get(rid, h_of(r))
    linee = fronti(par if isinstance(par, Polygon) else max(polys(par), key=lambda g: g.area), tol=3.0)
    if verso:   # separa i tratti per orientamento (fronte su Via della Menta = N-S, su Via Moravia = E-O)
        sub = []
        for line in linee:
            run = [line[0]]
            for a, b in zip(line, line[1:]):
                ok = (abs(b[1]-a[1]) > abs(b[0]-a[0])) == (verso == "NS")
                if ok: run.append(b)
                else:
                    if len(run) > 1: sub.append(run)
                    run = [b]
            if len(run) > 1: sub.append(run)
        linee = sub
    for line in linee:
        pts = dens(line, 1.0)
        if math.dist(pts[0], pts[-1]) < 2: continue
        base = [round(trend(x, y) + CORDOLO, 3) for x, y in pts]
        scena["muri"].append({"id": rid, "nome": f"{rid} – {r['tipo']}", "materiale": mat, "spessore": 0.25,
                              "punti": [[round(x, 3), round(y, 3)] for x, y in pts], "z_base": base,
                              "z_sommita": [round(b + hm, 3) for b in base], "confidenza": "media"})
        if rid in SOPRA:
            t, h2, m2 = SOPRA[rid]
            scena["recinzioni"].append({"id": rid, "nome": f"{rid} – {t}", "tipo": t, "materiale": m2, "altezza": h2,
                "passo_paletti": 2.0, "punti": [[round(x, 3), round(y, 3), round(b + hm, 3)] for (x, y), b in zip(pts, base)]})

# --- edifici: catasto + quote/materiali della scheda; gli altri LOD1 generici
EID = {e["impronta"]["indice"]: e for e in scheda["edifici"]}
for i, f in enumerate(FABB):
    p = poly(f)
    if not area.contains(p.centroid) or f["properties"]["tagliato_dal_bordo"]: continue
    p = p.intersection(area)
    zb = min(trend(x, y) for x, y in p.exterior.coords)
    e = EID.get(i)
    if e:
        h = e["quote"]["gronda"]["m"]
        mat = e["facciate"][0]["materiale"]
        nome = f'{e["id"]} – {e["indirizzo"]}'
        conf = e["quote"]["gronda"]["confidenza"]
        cop = e["copertura"]
    else:
        h, mat, nome, conf, cop = 6.5, "C04", f"CTX{i:02d} – contesto (LOD1)", "bassa", {"forma": "piana"}
    scena["edifici"].append({"id": e["id"] if e else f"CTX{i:02d}", "nome": nome, "materiale": mat,
        "impronta": [[round(x, 3), round(y, 3)] for x, y in list(p.exterior.coords)[:-1]],
        "z_base": round(zb, 3), "altezza": h, "confidenza_altezza": conf,
        "copertura": cop.get("forma"), "manto": cop.get("manto"), "lod": 1 if not e else 2})

# --- arredo e vegetazione dell'angolo (posizioni descrittive dalla scheda e dalle riprese, non misurate)
menta_line = [p for p in scena["muri"][0]["punti"] if p[0] > tip[0] + 0.5]
def lungo_menta(dist, offset):
    """punto sul fronte di Via della Menta a 'dist' m dalla punta, spostato di 'offset' m (+ = verso strada)."""
    acc, prev = 0.0, tip
    for q in menta_line:
        d = math.dist(prev, q)
        if acc + d >= dist and d > 0:
            t = (dist - acc) / d; x = prev[0] + (q[0]-prev[0])*t; y = prev[1] + (q[1]-prev[1])*t
            ux, uy = (q[0]-prev[0])/d, (q[1]-prev[1])/d      # direzione del fronte (verso N)
            return (round(x + uy*offset, 2), round(y - ux*offset, 2))   # normale verso E = strada
        acc += d; prev = q
    return menta_line[-1]
def fronte_y(yq, offset):
    """punto del fronte su Via della Menta alla quota planimetrica y=yq (polilinea reale), spostato di
    'offset' m lungo la normale (+ = verso la strada, - = dentro il lotto)."""
    ml = sorted(menta_line, key=lambda p: p[1])
    for a, b in zip(ml, ml[1:]):
        if a[1] <= yq <= b[1] and b[1] > a[1]:
            t = (yq - a[1]) / (b[1] - a[1]); x = a[0] + (b[0]-a[0])*t
            d = math.dist(a, b); ux, uy = (b[0]-a[0])/d, (b[1]-a[1])/d
            return (round(x + uy*offset, 2), round(yq - ux*offset, 2))
    return tuple(ml[-1])
lamp = lungo_menta(2.0, 0.6); cartello = fronte_y(15.5, 0.8)
palma = fronte_y(17.5, -1.0)   # Phoenix giovane senza fusto: visibile in SV-16/SV-18, coperta dalle erbe in SV-12, fuori campo in SV-08
scena["arredo"] = [
    {"id": "A01", "tipo": "lampione", "xy": list(lamp), "h": 8.0, "materiale": "C20", "nota": "sul marciapiede all'angolo, lato Via della Menta"},
    {"id": "A02", "tipo": "cartello divieto di sosta", "xy": list(cartello), "h": 2.4, "materiale": "C20"},
    {"id": "R06", "tipo": "blocco cls con scritta (pilastro recinzione)", "xy": list(fronte_y(33.0, 0.0)), "h": 1.5, "materiale": "C15", "dim": [1.2, 0.3]},
    {"id": "A02", "tipo": "pilastrino cls con targa Via della Menta", "xy": [round(tip[0]+0.4, 2), round(tip[1]+0.3, 2)], "h": 1.3, "materiale": "C15"},
]
scena["vegetazione"] = [
    {"id": "V02", "tipo": "palma Phoenix giovane (senza fusto)", "xy": list(palma), "h": 2.6, "chioma": 4.0, "su_lotto": True, "confidenza": "bassa"},
    {"id": "V-P03", "tipo": "arbusti ruderali", "xy_lista": [[-10, 22], [-18, 33], [-6, 30], [-12, 42], [0, 45]], "h": 1.2, "chioma": 2.0, "su_lotto": True},
]
scena["controllo"] = {"tip_lotto": [round(tip[0], 2), round(tip[1], 2)], "area_lotto_m2": round(lot.area, 1),
                      "sedime_m2": round(sedime.area, 1), "carreggiata_m2": round(carreggiata.area, 1),
                      "z_tip_lotto": round(z_lotto(*tip), 2), "z_marciapiede_tip": round(trend(*tip) + CORDOLO, 2)}
json.dump(scena, open(os.path.join(HERE, "scena.json"), "w"), indent=0)
print(json.dumps(scena["controllo"]), len(scena["edifici"]), "edifici,", len(scena["muri"]), "muri,", len(scena["recinzioni"]), "recinzioni")
