#!/usr/bin/env python3
"""Motore generico, fase 1: lotto.json → scena.json (stessa cartella di lotto.json).

Uso:  python scena.py <cartella o file lotto.json>
Coordinate locali in metri: origine = lotto.origine, x = Est, y = Nord, z = quota relativa all'origine.
Dati: catasto AdE vettorializzato, DTM LiDAR 1 m (Regione Sardegna), tendenza Copernicus fuori dal DTM,
osservazioni della scheda. Nessuna geometria da Google. Tutti i valori del singolo lotto stanno in lotto.json.
"""
import json, math, os, sys
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points
from pyproj import Transformer
import tifffile, numpy as np

_arg = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LOTTO", "lotto.json"))
LOTTO_PATH = os.path.join(_arg, "lotto.json") if os.path.isdir(_arg) else _arg
HERE = os.path.dirname(LOTTO_PATH)                 # cartella del lotto: ingressi relativi e uscite
L = json.load(open(LOTTO_PATH, encoding="utf-8"))
D, ST, LT = L["dati"], L["strade"], L["lotto"]
MF = LT["muro_fronte"]
def P_(rel): return os.path.normpath(os.path.join(HERE, rel))
def jload(rel): return json.load(open(P_(rel), encoding="utf-8"))

O = (L["origine"]["lat"], L["origine"]["lng"])
_AEQD = f"+proj=aeqd +lat_0={O[0]} +lon_0={O[1]} +ellps=WGS84 +units=m +no_defs"
_TO_LOC = Transformer.from_crs("EPSG:4326", _AEQD, always_xy=True)
_TO_LL = Transformer.from_crs(_AEQD, "EPSG:4326", always_xy=True)
_TO_UTM = Transformer.from_crs(_AEQD, D.get("crs_dtm", "EPSG:7791"), always_xy=True)
def ll_of(x, y):
    lng, lat = _TO_LL.transform(x, y); return lat, lng
def loc(ln, la): return tuple(_TO_LOC.transform(ln, la))
EXT = float(L["semilato_m"])
MARCIAPIEDE = ST["marciapiede_m"]
MARC = ST["rialzo_marciapiede_m"]
BLEND = ST["raccordo_angoli_m"]
IN = MF["campionamento_interno_m"]
HMAX = MF["altezza_massima_m"]
SCARPATA = MF["scarpata_m"]

T = jload(D["terreno_tendenza"]); C = T["coef"]
def trend_cop(x, y):
    return C[0] + C[1]*x + C[2]*y + C[3]*x*x + C[4]*x*y + C[5]*y*y - T["z_incrocio_slm"]

DM = jload(D["dtm_json"])
DTM = tifffile.imread(P_(D["dtm_tif"])).astype(float)
# locale → UTM del DTM: affine stimata su 3 punti (errore < 1 mm entro 150 m)
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
    """quota del suolo (DTM LiDAR) relativa all'origine; fuori copertura: tendenza Copernicus."""
    z = _zabs(x, y)
    return (z - Z0) if z is not None else trend_cop(x, y)

scheda = jload(D["scheda"])
PART = jload(D["particelle"])["features"]
FABB = jload(D["fabbricati"])["features"]
area = Polygon([(-EXT, -EXT), (EXT, -EXT), (EXT, EXT), (-EXT, EXT)])

def poly(f): return Polygon([loc(*q) for q in f["geometry"]["coordinates"][0]]).buffer(0)
particelle = [(i, poly(f)) for i, f in enumerate(PART) if f["properties"]["tipo"] == "particella"]
strade = [poly(f) for f in PART if f["properties"]["tipo"] == "strada"]
def trova_particella(latlng):
    """indice della particella che contiene il punto [lat, lng]: più robusto dell'indice, che cambia
    se si rivettorializza il catasto."""
    pt = Point(*loc(latlng[1], latlng[0]))
    for i, g in particelle:
        if g.contains(pt): return i
    sys.exit(f"nessuna particella contiene il punto {latlng}")
def indici(punti, indici_vecchi):
    return [trova_particella(q) for q in punti] if punti else list(indici_vecchi)
IL = trova_particella(LT["punto"]) if "punto" in LT else LT["indice_particella"]
_rr = LT.get("raggio_angoli_m", 0.0)
def _arrotonda(p):
    return p.buffer(-_rr, join_style=1, quad_segs=8).buffer(_rr, join_style=1, quad_segs=8) if _rr > 0 else p
_AGL = indici(LT.get("punti_aggiunti_al_lotto"), LT.get("particelle_aggiunte_al_lotto", []))   # particelle che il catasto disegna separate ma fanno parte del lotto
P03 = _arrotonda(unary_union([dict(particelle)[i] for i in [IL] + _AGL]).buffer(0.3, join_style=2).buffer(-0.3, join_style=2))
IL_TUTTE = set([IL] + _AGL)                 # lotto di progetto (P03: nome storico della variabile)

# --- sedime stradale: aree 'strada' + particelle che di fatto sono strada
AGG = indici(ST.get("punti_aggiunti_al_sedime"), ST.get("particelle_aggiunte_al_sedime", []))
sedime = unary_union(strade + [p for i, p in particelle if i in AGG]).buffer(0.3).buffer(-0.3)
sedime = sedime.intersection(area)
carreggiata = sedime.buffer(-MARCIAPIEDE, join_style=2).buffer(0.5).buffer(-0.5)
# il catasto lascia una fascia tra lotto e sedime: il marciapiede arriva al piede del muro del lotto
_RL = ST.get("raccordo_lotto_m", 4.0)
raccordo = P03.buffer(_RL).difference(P03).intersection(sedime.buffer(_RL))
marciapiedi = sedime.union(raccordo).difference(carreggiata).difference(P03).intersection(area)

_carr_b = carreggiata.boundary
# bordo della carreggiata campionato ogni 0,25 m, con la quota DTM di ogni campione
_cb_xy = np.array([p for ln in getattr(_carr_b, "geoms", [_carr_b])
                   for a, b in zip(ln.coords, ln.coords[1:])
                   for p in [(a[0] + (b[0]-a[0])*k/max(1, int(math.ceil(math.dist(a, b)/0.25))),
                              a[1] + (b[1]-a[1])*k/max(1, int(math.ceil(math.dist(a, b)/0.25))))
                             for k in range(max(1, int(math.ceil(math.dist(a, b)/0.25))))]])
_cb_z = np.array([trend(px, py) for px, py in _cb_xy])
PEND = ST.get("pendenza_marciapiede", 0.015)
def z_marc(x, y):
    """quota del marciapiede: bordo della carreggiata (DTM) + rialzo + pendenza verso la strada.
    La quota del bordo è una media pesata dei campioni entro dmin + BLEND, così sugli angoli tra strade
    a pendenza diversa non si crea un gradino dove cambia la strada più vicina."""
    d = np.hypot(_cb_xy[:, 0] - x, _cb_xy[:, 1] - y)
    dmin = float(d.min())
    w = np.clip(1.0 - (d - dmin) / BLEND, 0.0, None) ** 2 / (d + 0.5)
    zb = float((w * _cb_z).sum() / w.sum())
    return zb + MARC + PEND * min(dmin, 3.0)

def ring(p, step=2.0):
    pts = list(p.exterior.coords)[:-1]; out = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        n = max(1, int(math.dist(a, b) / step))
        out += [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(n)]
    return out

def polys(g):
    return [g] if isinstance(g, Polygon) else [x for x in getattr(g, "geoms", []) if isinstance(x, Polygon)]

tip = min(P03.exterior.coords, key=lambda p: math.hypot(*p))          # spigolo del lotto più vicino all'origine
def z_lotto(x, y):
    """DTM; a ridosso del fronte su strada la quota è presa più all'interno, dove il DTM non risente del
    salto del muro; sul bordo la sommità del muro (≤ altezza massima), poi scarpata fino al DTM."""
    d = sedime.distance(Point(x, y))
    if d > SCARPATA: return trend(x, y)
    q = nearest_points(sedime, Point(x, y))[0]
    zs = z_marc(q.x, q.y)
    cand = [trend(x + IN*math.cos(a), y + IN*math.sin(a)) for a in [k*math.pi/4 for k in range(8)]
            if P03.contains(Point(x + IN*math.cos(a), y + IN*math.sin(a)))
            and sedime.distance(Point(x + IN*math.cos(a), y + IN*math.sin(a))) > 1.0]
    zi = max(cand) if cand else trend(x, y)
    zbordo = zs + min(max(zi - zs, MF["altezza_minima_m"]), HMAX)
    w = min(1.0, d / SCARPATA)
    return zbordo * (1 - w) + max(zi, zbordo) * w

def fronti(p, tol=2.5):
    """bordo di p affacciato sul sedime, come polilinee."""
    pts = list(p.exterior.coords); segs = []
    for a, b in zip(pts, pts[1:]):
        mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
        if sedime.distance(Point(mid)) < tol and math.dist(a, b) > 0.3:
            segs.append((a, b))
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
         "fonti": ["Catasto AdE WMS (CC BY 4.0), non allineato: sfasamento ≤ 1–2 m vicino all'origine",
                   DM["fonte"] + " – quota origine %.2f m slm" % Z0] + L.get("fonti_extra", []),
         "dtm": {"z0_slm": Z0}, "terreno": {}, "strade": [], "marciapiedi": [], "lotto": {}, "muri": [], "recinzioni": [],
         "edifici": [], "vegetazione": [], "controllo": {}}

step = 1.0; n = int(2*EXT/step) + 1
scena["terreno"] = {"x0": -EXT, "y0": -EXT, "passo": step, "n": n, "materiale": "TERRENO",
                    "z": [[round(trend(-EXT + i*step, -EXT + j*step), 3) for i in range(n)] for j in range(n)]}

for p in polys(carreggiata):
    scena["strade"].append({"id": "P01", "materiale": ST["materiale_carreggiata"],
        "anello": [[round(x, 3), round(y, 3), round(trend(x, y), 3)] for x, y in ring(p)]})
for p in polys(marciapiedi):
    if p.area < 1: continue
    holes = [[[round(x, 3), round(y, 3), round(trend(x, y) + MARC, 3)] for x, y in ring(Polygon(h))] for h in p.interiors]
    scena["marciapiedi"].append({"id": "P02", "materiale": ST["materiale_marciapiede"],
        "anello": [[round(x, 3), round(y, 3), round(trend(x, y) + MARC, 3)] for x, y in ring(p)], "fori": holes})

lot = P03.intersection(area)
scena["lotto"] = {"id": LT["id"], "particella": LT["particella"], "materiale": LT.get("materiale_scena", LT["materiale"]),
                  "anello": [[round(x, 3), round(y, 3), round(z_lotto(x, y), 3)] for x, y in ring(lot, 1.5)],
                  "griglia_interna_passo": 3.0, "nota": LT.get("nota", "")}

def normali(pts, poly_in):
    out = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i-1)]; b = pts[min(len(pts)-1, i+1)]
        dx, dy = b[0]-a[0], b[1]-a[1]; Ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy/Ln, dx/Ln
        if not poly_in.contains(Point(x + nx*0.5, y + ny*0.5)): nx, ny = -nx, -ny
        out.append((nx, ny))
    return out

def quote_muro(pts, poly_in, minimo=0.20, hmax=None):
    ns = normali(pts, poly_in); zb, zt = [], []
    for (x, y), (nx, ny) in zip(pts, ns):
        b = z_marc(x, y)
        t = trend(x + nx*IN, y + ny*IN)
        h = max(t - b, minimo)
        if hmax: h = min(h, hmax)
        zb.append(round(b, 3)); zt.append(round(b + h, 3))
    return ns, zb, zt

# --- muro di sostegno lungo i fronti del lotto, recinzione sul tratto indicato
RF = LT.get("recinzione_fronte")
VP = MF.get("vicino_punta")
for k, line in enumerate(fronti(lot)):
    pts = dens(line, 1.0)
    ns, base, top = quote_muro(pts, lot, minimo=MF["altezza_minima_m"], hmax=HMAX)
    if VP:   # vicino alla punta il DTM a 1 m non risolve il salto: altezza minima dalle foto
        top = [round(max(t, b + VP["altezza_minima_m"]), 3) if math.dist(p, tip) < VP["raggio_m"] else t
               for p, b, t in zip(pts, base, top)]
    i0 = 0; t = 0
    while i0 < len(pts) - 1:      # tratti ≤ 8 m (getti)
        i1 = min(len(pts) - 1, i0 + 8)
        t += 1
        scena["muri"].append({"id": MF["id"], "nome": f"{MF['nome']} tratto {t}", "materiale": MF["materiale"],
            "spessore": MF["spessore"], "punti": [[round(x, 3), round(y, 3)] for x, y in pts[i0:i1+1]],
            "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns[i0:i1+1]],
            "z_base": base[i0:i1+1], "z_sommita": top[i0:i1+1], "quote": "DTM LiDAR 1 m"})
        i0 = i1
    if RF:
        sel = [(i, x, y) for i, (x, y) in enumerate(pts)
               if x > tip[0] + RF.get("x_min_da_punta", -1e9) and y >= RF.get("y_min", -1e9)]
        if len(sel) > 2:
            rec = {"id": MF["id"], "nome": RF["nome"], "tipo": RF["tipo"], "materiale": RF["materiale"],
                   "altezza": RF["altezza"], "passo_paletti": RF.get("passo_paletti", 2.0),
                   "punti": [[round(x, 3), round(y, 3), top[i]] for i, x, y in sel]}
            if "cancello" in RF: rec["cancello"] = RF["cancello"]
            scena["recinzioni"].append(rec)

# --- muri di cinta del contorno sui fronti strada delle particelle degli edifici
def particella_di(eid):
    e = [x for x in scheda["edifici"] if x["id"] == eid][0]
    c = poly(FABB[e["impronta"]["indice"]]).centroid
    return [p for i, p in particelle if p.contains(c) and i not in IL_TUTTE][0]
RW = {r["id"]: r for r in scheda["recinzioni"]}
def h_of(r):
    v = r.get("h", {}).get("m") if isinstance(r.get("h"), dict) else None
    return float(v) if v else 1.5
for mc in L.get("muri_contorno", []):
    rid, eid, verso = mc["id"], mc["edificio"], mc.get("verso")
    try: par = particella_di(eid).intersection(area)
    except IndexError: continue
    r = RW[rid]; mat = r["materiali"][0]
    hm = mc.get("altezza_muro", h_of(r))
    pin = par if isinstance(par, Polygon) else max(polys(par), key=lambda g: g.area)
    linee = fronti(pin, tol=3.0)
    if verso:   # tiene solo i tratti con quell'orientamento (NS o EO)
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
        ns, base, interno = quote_muro(pts, pin, minimo=0.0)
        top = [round(max(b + hm, zi + 0.1), 3) for b, zi in zip(base, interno)]
        scena["muri"].append({"id": rid, "nome": f"{rid} – {r['tipo']}", "materiale": mat, "spessore": 0.25,
                              "punti": [[round(x, 3), round(y, 3)] for x, y in pts],
                              "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns], "z_base": base,
                              "z_sommita": top, "z_terreno_interno": interno, "confidenza": "media"})
        if mc.get("sopra"):
            t, h2, m2 = mc["sopra"]
            scena["recinzioni"].append({"id": rid, "nome": f"{rid} – {t}", "tipo": t, "materiale": m2, "altezza": h2,
                "passo_paletti": 2.0, "punti": [[round(x, 3), round(y, 3), tt] for (x, y), tt in zip(pts, top)]})

# --- edifici: catasto + quote/materiali della scheda; gli altri LOD1 generici
LE = L.get("edifici", {})
EID = {e["impronta"]["indice"]: e for e in scheda["edifici"]}
for i, f in enumerate(FABB):
    p = poly(f)
    if not area.contains(p.centroid) or f["properties"]["tagliato_dal_bordo"]: continue
    p = p.intersection(area)
    zb = min(trend(x, y) for x, y in p.exterior.coords)
    e = EID.get(i)
    if e:
        h = e["quote"]["gronda"]["m"]; mat = e["facciate"][0]["materiale"]
        nome = f'{e["id"]} – {e["indirizzo"]}'; conf = e["quote"]["gronda"]["confidenza"]; cop = e["copertura"]
    else:
        h, mat, nome, conf, cop = (LE.get("altezza_generica_m", 6.5), LE.get("materiale_generico", "C04"),
                                   f"CTX{i:02d} – contesto (LOD1)", "bassa", {"forma": "piana"})
    ov = LE.get("per_edificio", {}).get(e["id"] if e else f"CTX{i:02d}")
    if ov:   # dati per singolo edificio da lotto.json (es. edifici di sfondo osservati in 3D)
        h = ov.get("altezza", h); mat = ov.get("materiale", mat)
        cop = {**cop, "forma": ov.get("copertura", cop.get("forma")), "manto": ov.get("manto", cop.get("manto")),
               "pendenza_pct": ov.get("pendenza_pct", cop.get("pendenza_pct"))}
        if not e: nome = f"CTX{i:02d} – contesto ({ov.get('nota', 'LOD2')})"
    scena["edifici"].append({"id": e["id"] if e else f"CTX{i:02d}", "nome": nome, "materiale": mat,
        "impronta": [[round(x, 3), round(y, 3)] for x, y in list(p.exterior.coords)[:-1]],
        "z_base": round(zb, 3), "altezza": h, "confidenza_altezza": conf,
        "copertura": cop.get("forma"), "manto": cop.get("manto"), "lod": 1 if not e else 2,
        "colmo": (ov or {}).get("colmo") or ((e or {}).get("quote", {}).get("colmo") or {}).get("m"),
        "pendenza_pct": cop.get("pendenza_pct")})

# --- muri di confine interni: lati delle particelle lontani dalla strada, fuori dagli edifici
CI = L.get("confini_interni")
if CI:
    from shapely import set_precision
    from shapely.ops import linemerge
    edif = unary_union([Polygon(e["impronta"]) for e in scena["edifici"]]).buffer(0.3)
    gia = unary_union([Point(p).buffer(0.01) for m in scena["muri"] for p in m["punti"]] +
                      [__import__("shapely.geometry", fromlist=["LineString"]).LineString(m["punti"]).buffer(1.0)
                       for m in scena["muri"] if len(m["punti"]) > 1])
    # solo particelle edificate (i campi aperti non hanno muri); le linee di particelle diverse a meno di
    # 1,2 m l'una dall'altra (strisce strette del catasto) diventano una sola: si tiene la prima
    costruite = [p for i, p in particelle if p.intersects(area) and i not in IL_TUTTE
                 and any(p.contains(Polygon(e["impronta"]).representative_point()) for e in scena["edifici"])]
    tenute, occ = [], None
    for p in costruite:
        ln = set_precision(p.exterior, 0.25)
        if occ is not None: ln = ln.difference(occ)
        if ln.is_empty: continue
        tenute.append(ln)
        occ = ln.buffer(1.2) if occ is None else occ.union(ln.buffer(1.2))
    linee = unary_union(tenute)
    linee = linee.difference(sedime.buffer(CI.get("distanza_min_strada_m", 1.5))).difference(edif).difference(gia)
    linee = linee.difference(P03.buffer(0.3)) if CI.get("escludi_lotto", False) else linee
    linee = linee.intersection(area.buffer(-1.0))
    linee = linemerge(linee) if not linee.is_empty and linee.geom_type != "LineString" else linee
    nci = 0
    for ln in getattr(linee, "geoms", [linee]):
        if ln.is_empty or ln.geom_type != "LineString" or ln.length < CI.get("lunghezza_min_m", 2.0): continue
        pts = dens(list(ln.simplify(0.2).coords), 1.0)
        if len(pts) < 2: continue
        ns = []
        for j, (x, y) in enumerate(pts):
            a_ = pts[max(0, j-1)]; b_ = pts[min(len(pts)-1, j+1)]
            dx, dy = b_[0]-a_[0], b_[1]-a_[1]; Ln = math.hypot(dx, dy) or 1.0
            ns.append((round(-dy/Ln, 4), round(dx/Ln, 4)))
        zb = [round(trend(x, y) - 0.1 * CI["spessore"], 3) for x, y in pts]
        nci += 1
        scena["muri"].append({"id": f"CI{nci:02d}", "nome": f"CI{nci:02d} – muro di confine interno", "materiale": CI["materiale"],
                              "spessore": CI["spessore"], "punti": [[round(x, 3), round(y, 3)] for x, y in pts],
                              "normali_interno": [list(n) for n in ns], "z_base": zb,
                              "z_sommita": [round(z + CI["altezza"], 3) for z in zb], "confidenza": "bassa",
                              "quote": "regola generale (confini catastali)"})

# --- arredo e vegetazione, posizionati rispetto al fronte del lotto (descrittivi, non misurati)
_fpts = []
for _m in [m for m in scena["muri"] if m["id"] == MF["id"]]:
    _fpts += _m["punti"] if not _fpts else _m["punti"][1:]
_FA = LT.get("fronte_arredo", {})
fronte_line = [p for p in _fpts if p[0] > tip[0] + _FA.get("x_min_da_punta", -1e9)] or _fpts
def lungo_fronte(dist, offset):
    """punto sul fronte a 'dist' m dalla punta, spostato di 'offset' m (+ = verso strada)."""
    acc, prev = 0.0, tip
    for q in fronte_line:
        d = math.dist(prev, q)
        if acc + d >= dist and d > 0:
            t = (dist - acc) / d; x = prev[0] + (q[0]-prev[0])*t; y = prev[1] + (q[1]-prev[1])*t
            ux, uy = (q[0]-prev[0])/d, (q[1]-prev[1])/d
            return (round(x + uy*offset, 2), round(y - ux*offset, 2))
        acc += d; prev = q
    return fronte_line[-1]
def fronte_y(yq, offset):
    """punto del fronte alla y=yq, spostato di 'offset' m lungo la normale (+ = strada, - = lotto)."""
    ml = sorted(fronte_line, key=lambda p: p[1])
    for a, b in zip(ml, ml[1:]):
        if a[1] <= yq <= b[1] and b[1] > a[1]:
            t = (yq - a[1]) / (b[1] - a[1]); x = a[0] + (b[0]-a[0])*t
            d = math.dist(a, b); ux, uy = (b[0]-a[0])/d, (b[1]-a[1])/d
            return (round(x + uy*offset, 2), round(yq - ux*offset, 2))
    return tuple(ml[-1])
def posiziona(a):
    if "xy" in a: return tuple(a["xy"])
    if "lungo_fronte_m" in a: return lungo_fronte(a["lungo_fronte_m"], a.get("offset", 0.0))
    if "fronte_y" in a: return fronte_y(a["fronte_y"], a.get("offset", 0.0))
    if "da_punta" in a: return (round(tip[0] + a["da_punta"][0], 2), round(tip[1] + a["da_punta"][1], 2))
    return None
CHIAVI_POS = {"lungo_fronte_m", "fronte_y", "offset", "da_punta", "orienta_fronte", "nel_contesto", "nome", "materiale"}
scena["arredo"] = []
for a in L.get("arredo", []):
    o = {"id": a["id"], "tipo": a["tipo"], "xy": list(posiziona(a)), "h": a["h"], "materiale": a["materiale"]}
    o.update({k: v for k, v in a.items() if k not in CHIAVI_POS and k not in o})
    if a.get("orienta_fronte") and "fronte_y" in a:
        dy = a["orienta_fronte"]
        p1, p2 = fronte_y(a["fronte_y"] - dy, 0), fronte_y(a["fronte_y"] + dy, 0)
        o["rot_deg"] = round(math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0])), 1)
    scena["arredo"].append(o)
scena["vegetazione"] = []
for v in L.get("vegetazione", []):
    o = {"id": v["id"], "tipo": v["tipo"]}
    pos = posiziona(v)
    if pos: o["xy"] = list(pos)
    o.update({k: val for k, val in v.items() if k not in CHIAVI_POS and k not in o})
    scena["vegetazione"].append(o)
scena["controllo"] = {"tip_lotto": [round(tip[0], 2), round(tip[1], 2)], "area_lotto_m2": round(lot.area, 1),
                      "sedime_m2": round(sedime.area, 1), "carreggiata_m2": round(carreggiata.area, 1),
                      "z_tip_lotto": round(z_lotto(*tip), 2), "z_marciapiede_tip": round(trend(*tip) + MARC, 2)}
_man_path = next((P_(p) for p in D.get("manifest", []) if os.path.exists(P_(p))), None)
_man = json.load(open(_man_path, encoding="utf-8")) if _man_path else {"riprese": []}
scena["camere"] = {r["id"]: [round(v, 3) for v in loc(r["lng"], r["lat"])] for r in _man["riprese"]}
json.dump(scena, open(os.path.join(HERE, "scena.json"), "w"), indent=0)
print(json.dumps(scena["controllo"]), len(scena["edifici"]), "edifici,", len(scena["muri"]), "muri,", len(scena["recinzioni"]), "recinzioni")
