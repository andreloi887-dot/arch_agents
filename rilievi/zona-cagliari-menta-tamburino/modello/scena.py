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
# proiezione locale esatta (azimutale equidistante sull'ellissoide WGS84, centrata sull'incrocio): metri veri
from pyproj import Transformer
_AEQD = f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +ellps=WGS84 +units=m +no_defs"
_TO_LOC = Transformer.from_crs("EPSG:4326", _AEQD, always_xy=True)
_TO_LL = Transformer.from_crs(_AEQD, "EPSG:4326", always_xy=True)
_TO_UTM = Transformer.from_crs(_AEQD, "EPSG:7791", always_xy=True)
def ll_of(x, y):
    lng, lat = _TO_LL.transform(x, y); return lat, lng
EXT = 75.0                      # semilato dell'area modellata (m)
MARCIAPIEDE = 1.5               # larghezza marciapiedi (m), scheda P02
CORDOLO = 0.15

def loc(ln, la): return tuple(_TO_LOC.transform(ln, la))

T = json.load(open(os.path.join(HERE, "terreno_tendenza.json")))      # Copernicus: solo fuori dal DTM
C = T["coef"]
def trend_cop(x, y):
    return C[0] + C[1]*x + C[2]*y + C[3]*x*x + C[4]*x*y + C[5]*y*y - T["z_incrocio_slm"]

# DTM LiDAR 1 m (Regione Sardegna): base del terreno. Quote relative all'incrocio.
import tifffile, numpy as np
DM = json.load(open(os.path.join(HERE, "dtm_lidar_1m.json")))
DTM = tifffile.imread(os.path.join(HERE, "dtm_lidar_1m.tif")).astype(float)
# locale → UTM 32N (RDN2008): trasformazione affine stimata su 3 punti (errore < 1 mm entro 150 m)
_P = [(0.0, 0.0), (100.0, 0.0), (0.0, 100.0)]
_U = [_TO_UTM.transform(x, y) for x, y in _P]
_AFF = (_U[0], ((_U[1][0]-_U[0][0])/100, (_U[1][1]-_U[0][1])/100), ((_U[2][0]-_U[0][0])/100, (_U[2][1]-_U[0][1])/100))
def to_utm(x, y):
    (e0, n0), (ex, nx), (ey, ny) = _AFF
    return e0 + ex*x + ey*y, n0 + nx*x + ny*y
def _zabs(x, y):
    E, N = to_utm(x, y)
    c = (E - DM["bordo_sinistro_E"]) / DM["passo"] - 0.5
    r = (DM["bordo_superiore_N"] - N) / DM["passo"] - 0.5
    c0, r0 = int(math.floor(c)), int(math.floor(r))
    if not (0 <= c0 < DTM.shape[1]-1 and 0 <= r0 < DTM.shape[0]-1): return None
    fc, fr = c - c0, r - r0; q = DTM[r0:r0+2, c0:c0+2]
    return q[0,0]*(1-fc)*(1-fr) + q[0,1]*fc*(1-fr) + q[1,0]*(1-fc)*fr + q[1,1]*fc*fr
Z0 = _zabs(0, 0)
def trend(x, y):
    """quota del suolo (DTM LiDAR) relativa all'incrocio; fuori copertura: tendenza Copernicus."""
    z = _zabs(x, y)
    return (z - Z0) if z is not None else trend_cop(x, y)

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
_P03 = [p for i, p in particelle if i == 67][0].buffer(-1.0, join_style=1, quad_segs=8).buffer(1.0, join_style=1, quad_segs=8)
# il catasto lascia una fascia tra lotto e sedime: il marciapiede arriva al piede del muro del lotto
raccordo = _P03.buffer(4.0).difference(_P03).intersection(sedime.buffer(4.0))
marciapiedi = sedime.union(raccordo).difference(carreggiata).difference(_P03).intersection(area)

_carr_b = carreggiata.boundary
# bordo della carreggiata campionato ogni 0,25 m, con la quota DTM di ogni campione
_cb_xy = np.array([p for ln in getattr(_carr_b, "geoms", [_carr_b])
                   for a, b in zip(ln.coords, ln.coords[1:])
                   for p in [(a[0] + (b[0]-a[0])*k/max(1, int(math.ceil(math.dist(a, b)/0.25))),
                              a[1] + (b[1]-a[1])*k/max(1, int(math.ceil(math.dist(a, b)/0.25))))
                             for k in range(max(1, int(math.ceil(math.dist(a, b)/0.25))))]])
_cb_z = np.array([trend(px, py) for px, py in _cb_xy])
BLEND = 2.0   # m: i bordi strada entro dmin + BLEND contribuiscono alla quota (raccordo sugli angoli)
def z_marc(x, y):
    """quota del marciapiede: bordo della carreggiata (DTM) + sopraelevazione + pendenza 1,5 % verso la
    strada. Evita che il DTM, che spalma il gradino dei muri, faccia "salire" il marciapiede.
    La quota del bordo è una media pesata dei campioni entro dmin + BLEND: con il solo bordo più vicino,
    sugli angoli tra due strade a pendenza diversa (punta del lotto: Via della Menta sale del 20 %) il
    marciapiede faceva un gradino di ~1,2 m in 1 m dove cambia la strada più vicina."""
    d = np.hypot(_cb_xy[:, 0] - x, _cb_xy[:, 1] - y)
    dmin = float(d.min())
    w = np.clip(1.0 - (d - dmin) / BLEND, 0.0, None) ** 2 / (d + 0.5)
    zb = float((w * _cb_z).sum() / w.sum())
    return zb + MARC + 0.015 * min(dmin, 3.0)


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
P03 = dict(particelle)[67].buffer(-1.0, join_style=1, quad_segs=8).buffer(1.0, join_style=1, quad_segs=8)  # angoli arrotondati r = 1 m (SV-01, SV-12)
tip = min(P03.exterior.coords, key=lambda p: math.hypot(*p))          # spigolo verso l'incrocio
# quote del lotto dal DTM LiDAR. Il DTM a 1 m "spalma" il salto del muro su ~1 m: in prossimità del
# fronte si campiona la quota del lotto 1,2 m all'interno e quella del marciapiede 1,0 m all'esterno.
IN, OUT = 1.6, 1.0
HMAX_R06 = 1.30   # altezza massima del muro R06 dalle foto (SV-12, SV-18): oltre, scarpata erbosa
MARC = 0.10   # sopraelevazione del marciapiede sul DTM (il DTM include già in parte il cordolo)
def z_lotto(x, y):
    """DTM; a ridosso del fronte su strada (entro 1,5 m dal sedime) la quota è presa 1,2 m più all'interno,
    dove il DTM non risente del salto del muro."""
    d = sedime.distance(Point(x, y))
    if d > 2.5: return trend(x, y)
    from shapely.ops import nearest_points
    q = nearest_points(sedime, Point(x, y))[0]
    zs = z_marc(q.x, q.y)                             # marciapiede al piede del muro
    cand = [trend(x + IN*math.cos(a), y + IN*math.sin(a)) for a in [k*math.pi/4 for k in range(8)]
            if P03.contains(Point(x + IN*math.cos(a), y + IN*math.sin(a)))
            and sedime.distance(Point(x + IN*math.cos(a), y + IN*math.sin(a))) > 1.0]
    zi = max(cand) if cand else trend(x, y)
    # sul bordo: sommità del muro (≤ HMAX); verso l'interno la scarpata raggiunge il DTM entro 2,5 m
    zbordo = zs + min(max(zi - zs, 0.20), HMAX_R06)
    w = min(1.0, d / 2.5)
    return zbordo * (1 - w) + max(zi, zbordo) * w if d < 2.5 else zi

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
                   DM["fonte"] + " – quota incrocio %.2f m slm" % Z0,
                   "Altezze e rialzi da osservazioni Street View (scheda rev. 2), confidenza media/bassa"],
         "dtm": {"z0_slm": Z0}, "terreno": {}, "strade": [], "marciapiedi": [], "lotto": {}, "muri": [], "recinzioni": [],
         "edifici": [], "vegetazione": [], "controllo": {}}

# --- terreno di tendenza su griglia (2 m)
step = 1.0; n = int(2*EXT/step) + 1
scena["terreno"] = {"x0": -EXT, "y0": -EXT, "passo": step, "n": n, "materiale": "TERRENO",
                    "z": [[round(trend(-EXT + i*step, -EXT + j*step), 3) for i in range(n)] for j in range(n)]}

for p in polys(carreggiata):
    scena["strade"].append({"id": "P01", "materiale": "C16",
        "anello": [[round(x, 3), round(y, 3), round(trend(x, y), 3)] for x, y in ring(p)]})
for p in polys(marciapiedi):
    if p.area < 1: continue
    holes = [[[round(x, 3), round(y, 3), round(trend(x, y) + MARC, 3)] for x, y in ring(Polygon(h))] for h in p.interiors]
    scena["marciapiedi"].append({"id": "P02", "materiale": "C17",
        "anello": [[round(x, 3), round(y, 3), round(trend(x, y) + MARC, 3)] for x, y in ring(p)], "fori": holes})

lot = P03.intersection(area)
scena["lotto"] = {"id": "P03", "particella": "4258", "materiale": "PRATO_SECCO",
                  "anello": [[round(x, 3), round(y, 3), round(z_lotto(x, y), 3)] for x, y in ring(lot, 1.5)],
                  "griglia_interna_passo": 3.0,
                  "nota": "superficie dal DTM LiDAR 1 m; erbe spontanee alte ~1 m (aprile)"}

# --- muro di sostegno R06 lungo i fronti del lotto, recinzione in rete sul tratto di Via della Menta
def normali(pts, poly_in):
    """normale verso l'interno di poly_in per ogni punto della polilinea."""
    out = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i-1)]; b = pts[min(len(pts)-1, i+1)]
        dx, dy = b[0]-a[0], b[1]-a[1]; L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy/L, dx/L
        if not poly_in.contains(Point(x + nx*0.5, y + ny*0.5)): nx, ny = -nx, -ny
        out.append((nx, ny))
    return out

def quote_muro(pts, poly_in, minimo=0.20, hmax=None):
    """base (marciapiede, lato strada) e sommità del muro: DTM per le quote, foto per l'altezza massima."""
    ns = normali(pts, poly_in); zb, zt = [], []
    for (x, y), (nx, ny) in zip(pts, ns):
        b = z_marc(x, y)
        t = trend(x + nx*IN, y + ny*IN)
        h = max(t - b, minimo)
        if hmax: h = min(h, hmax)
        zb.append(round(b, 3)); zt.append(round(b + h, 3))
    return ns, zb, zt

for k, line in enumerate(fronti(lot)):
    pts = dens(line, 1.0)
    ns, base, top = quote_muro(pts, lot, hmax=HMAX_R06)
    # angolo: le foto (SV-12, SV-18) mostrano il muro alto ~1,0–1,2 m fino alla punta, dove il DTM a 1 m
    # non risolve il salto: entro 6 m dalla punta l'altezza minima è 1,0 m
    top = [round(max(t, b + 1.0), 3) if math.dist(p, tip) < 6.0 else t for p, b, t in zip(pts, base, top)]
    # spezzato in tratti ≤ 8 m (getti/campate): la verifica legge l'ingombro verticale di ogni contenitore
    i0 = 0; t = 0
    while i0 < len(pts) - 1:
        i1 = min(len(pts) - 1, i0 + 8)
        t += 1
        scena["muri"].append({"id": "R06", "nome": f"R06 – muro di sostegno P03 tratto {t}", "materiale": "C15",
            "spessore": 0.25, "punti": [[round(x, 3), round(y, 3)] for x, y in pts[i0:i1+1]],
            "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns[i0:i1+1]],
            "z_base": base[i0:i1+1], "z_sommita": top[i0:i1+1], "quote": "DTM LiDAR 1 m"})
        i0 = i1
    menta = [(i, x, y) for i, (x, y) in enumerate(pts) if x > tip[0] + 1.0 and y >= 24.0]  # SV-16/18: niente rete vicino all'angolo
    if len(menta) > 2:
        scena["recinzioni"].append({"id": "R06", "nome": "R06 – rete elettrosaldata su paletti", "tipo": "rete",
            "materiale": "C20", "altezza": 1.6, "passo_paletti": 2.0,
            "punti": [[round(x, 3), round(y, 3), top[i]] for i, x, y in menta],
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
        pin = par if isinstance(par, Polygon) else max(polys(par), key=lambda g: g.area)
        ns, base, interno = quote_muro(pts, pin, minimo=0.0)
        top = [round(max(b + hm, zi + 0.1), 3) for b, zi in zip(base, interno)]
        scena["muri"].append({"id": rid, "nome": f"{rid} – {r['tipo']}", "materiale": mat, "spessore": 0.25,
                              "punti": [[round(x, 3), round(y, 3)] for x, y in pts],
                              "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns], "z_base": base,
                              "z_sommita": top, "z_terreno_interno": interno, "confidenza": "media"})
        if rid in SOPRA:
            t, h2, m2 = SOPRA[rid]
            scena["recinzioni"].append({"id": rid, "nome": f"{rid} – {t}", "tipo": t, "materiale": m2, "altezza": h2,
                "passo_paletti": 2.0, "punti": [[round(x, 3), round(y, 3), t] for (x, y), t in zip(pts, top)]})

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
_r06pts = []
for _m in [m for m in scena["muri"] if m["id"] == "R06"]:
    _r06pts += _m["punti"] if not _r06pts else _m["punti"][1:]
menta_line = [p for p in _r06pts if p[0] > tip[0] + 0.5]
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
    {"id": "R06", "tipo": "blocco cls con scritta (pilastro recinzione)", "xy": list(fronte_y(33.0, -0.15)), "h": 1.5, "materiale": "C15", "dim": [1.2, 0.3],
     "rot_deg": round(math.degrees(math.atan2(*reversed([b - a for a, b in zip(fronte_y(32.0, 0), fronte_y(34.0, 0))]))), 1)},
    {"id": "A02", "tipo": "pilastrino cls con targa Via della Menta", "xy": [round(tip[0]+0.4, 2), round(tip[1]+0.3, 2)], "h": 1.3, "materiale": "C15"},
]
scena["vegetazione"] = [
    {"id": "V02", "tipo": "palma Phoenix giovane (senza fusto)", "xy": list(palma), "h": 2.6, "chioma": 4.0, "su_lotto": True, "confidenza": "bassa"},
    {"id": "V-P03", "tipo": "arbusti ruderali", "xy_lista": [[-10, 22], [-18, 33], [-6, 30], [-12, 42], [0, 45]], "h": 1.2, "chioma": 2.0, "su_lotto": True},
]
scena["controllo"] = {"tip_lotto": [round(tip[0], 2), round(tip[1], 2)], "area_lotto_m2": round(lot.area, 1),
                      "sedime_m2": round(sedime.area, 1), "carreggiata_m2": round(carreggiata.area, 1),
                      "z_tip_lotto": round(z_lotto(*tip), 2), "z_marciapiede_tip": round(trend(*tip) + MARC, 2)}
# camere: manifest locale di gmaps.py se c'è, altrimenti la copia versionata accanto a questo script
_man_path = next((p for p in [os.path.join(Z, "_rif_google/manifest_riprese.json"), os.path.join(HERE, "manifest_riprese.json")]
                  if os.path.exists(p)), None)
_man = json.load(open(_man_path, encoding="utf-8")) if _man_path else {"riprese": []}
scena["camere"] = {r["id"]: [round(v, 3) for v in loc(r["lng"], r["lat"])] for r in _man["riprese"]}
json.dump(scena, open(os.path.join(HERE, "scena.json"), "w"), indent=0)
print(json.dumps(scena["controllo"]), len(scena["edifici"]), "edifici,", len(scena["muri"]), "muri,", len(scena["recinzioni"]), "recinzioni")
