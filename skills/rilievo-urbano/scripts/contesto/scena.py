#!/usr/bin/env python3
"""Motore generico, fase 1: lotto.json → scena.json (stessa cartella di lotto.json).

Uso:  python scena.py <cartella o file lotto.json>
Coordinate locali in metri: origine = lotto.origine, x = Est, y = Nord, z = quota relativa all'origine.
Dati: catasto AdE vettorializzato, DTM LiDAR 1 m (Regione Sardegna), tendenza Copernicus fuori dal DTM,
osservazioni della scheda. Nessuna geometria da Google. Tutti i valori del singolo lotto stanno in lotto.json.
"""
import json, math, os, sys
from shapely.geometry import Polygon, Point, LineString
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

# --- Database Geotopografico regionale (DBGT, 1:2000): geometria più precisa del catasto, se scaricata
DB = D.get("dbgt", {})
def dbgt(chiave):
    rel = DB.get(chiave)
    if not rel or not os.path.exists(P_(rel)): return []
    out = []
    def anello(r): return [loc(q[0], q[1]) for q in r]
    for f in jload(rel)["features"]:
        g = f["geometry"]; c = g["coordinates"]; t_ = g["type"]
        if t_ == "Polygon": c, t_ = [c], "MultiPolygon"
        if t_ == "LineString": c, t_ = [c], "MultiLineString"
        if t_ == "MultiPolygon":
            out += [Polygon(anello(r[0]), [anello(h) for h in r[1:]]).buffer(0) for r in c]
        elif t_ == "MultiLineString":
            out += [LineString(anello(l)) for l in c if len(l) > 1]
    return out
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
# perimetro del progetto (IFC planimetricamente giusto): sostituisce il lotto catastale; ciò che il catasto dava al lotto
# oltre il filo del progetto, se tocca la sede stradale, è strada (evita strettoie dove il catasto sporge sulla sede)
P03_CATASTO = P03
if LT.get("perimetro_progetto") and os.path.exists(os.path.join(HERE, LT["perimetro_progetto"])):
    _PP = json.load(open(os.path.join(HERE, LT["perimetro_progetto"]), encoding="utf-8"))
    _o = _PP["origine"]
    if abs(_o["lat"] - O[0]) > 1e-9 or abs(_o["lng"] - O[1]) > 1e-9:
        _x0, _y0 = loc(_o["lng"], _o["lat"]); _PP["anello"] = [[x + _x0, y + _y0] for x, y in _PP["anello"]]
    P03 = Polygon(_PP["anello"]).buffer(0)
    print(f"lotto dal perimetro di progetto: {P03.area:.0f} m² (catasto {P03_CATASTO.area:.0f} m²)")

# --- sedime stradale: aree 'strada' + particelle che di fatto sono strada
AGG = indici(ST.get("punti_aggiunti_al_sedime"), ST.get("particelle_aggiunte_al_sedime", []))
_DB_STRADE = dbgt("strade")
if _DB_STRADE:   # DBGT: sede stradale da recinzione a recinzione (fotogrammetria 1:2000)
    _sd = unary_union(_DB_STRADE)
    _ex = P03_CATASTO.difference(P03.buffer(0.05)).intersection(_sd.buffer(4.0))   # fascia catastale oltre il filo di progetto
    sedime = unary_union([_sd, _ex]).buffer(0.3).buffer(-0.3).difference(P03)
else:            # catasto: aree 'strada' + particelle che di fatto sono strada
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
# --- profilo stradale: quota del DTM lungo gli assi delle strade, lisciata (mediana + media mobile), così le
# irregolarità del DTM (muri spalmati, auto, vegetazione) non diventano dossi; trasversalmente pendenza a schiena
_ASSI = [ln.intersection(area.buffer(15)) for ln in dbgt("assi")]
_ax_xy, _ax_z = [], []
for ln in _ASSI:
    for part in getattr(ln, "geoms", [ln]):
        if part.is_empty or part.geom_type != "LineString" or part.length < 3: continue
        n_ = max(2, int(part.length))
        P_s = [part.interpolate(k * part.length / n_) for k in range(n_ + 1)]
        z_ = np.array([trend(q.x, q.y) for q in P_s])
        h_ = int(ST.get("lisciatura_profilo_m", 9)) // 2
        zm = np.array([np.median(z_[max(0, k-h_):k+h_+1]) for k in range(len(z_))])
        zs_ = np.array([zm[max(0, k-h_):k+h_+1].mean() for k in range(len(zm))])
        _ax_xy += [(q.x, q.y) for q in P_s]; _ax_z += list(zs_)
_ax_xy = np.array(_ax_xy) if _ax_xy else None; _ax_z = np.array(_ax_z) if _ax_z else None
SCHIENA = ST.get("pendenza_trasversale", 0.02)
def z_strada(x, y):
    """quota della carreggiata: profilo lisciato dell'asse più vicino (raccordato sugli incroci) meno la
    pendenza trasversale; senza assi DBGT, il DTM."""
    if _ax_xy is None: return trend(x, y)
    d = np.hypot(_ax_xy[:, 0] - x, _ax_xy[:, 1] - y); dmin = float(d.min())
    if dmin > 12: return trend(x, y)
    RB = ST.get("raccordo_assi_m", 8.0)   # raccordo lungo tra assi che si incontrano: niente gradini agli innesti
    w = np.clip(1.0 - (d - dmin) / RB, 0.0, None) ** 2 / (d + 1.0)
    return float((w * _ax_z).sum() / w.sum()) - SCHIENA * min(dmin, 4.0)
_cb_z = np.array([z_strada(px, py) for px, py in _cb_xy])
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
        "anello": [[round(x, 3), round(y, 3), round(z_strada(x, y), 3)] for x, y in ring(p)]})
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
_DB_REC = dbgt("recinzioni")
def _orient_ok(verso, a, b):
    return verso is None or ((abs(b[1]-a[1]) > abs(b[0]-a[0])) == (verso == "NS"))
if _DB_REC:
    # FRONTI SU STRADA. Ogni lotto edificato ha il suo fronte (attributi dal rilievo: muro della scheda, oppure
    # `per_edificio.<id>.fronte_strada` in lotto.json). Il muro segue la recinzione DBGT dove esiste e, dove il
    # DBGT non la disegna, il bordo della sede stradale (che nel DBGT va da recinzione a recinzione, angoli curvi
    # compresi). Un tratto è "su strada" solo se è vicino alla sede E parallelo al suo bordo; gli altri tratti
    # DBGT sono confini interni. Il fronte del lotto di progetto ha il suo muro.
    _PE = L.get("edifici", {}).get("per_edificio", {})
    _PART = dict(particelle)
    def _idx_part_di(c_):
        for j, p in particelle:
            if p.contains(c_) and j not in IL_TUTTE: return j
        return None
    def _idx_edificio(eid):
        e = [x for x in scheda["edifici"] if x["id"] == eid][0]
        return _idx_part_di(poly(FABB[e["impronta"]["indice"]]).centroid)
    _cand = []   # (attributi, indice particella, zona o None); attributi["_ed"] = impronta dell'edificio
    def _impronta_edificio(eid):
        e = [x for x in scheda["edifici"] if x["id"] == eid][0]
        return poly(FABB[e["impronta"]["indice"]])
    for mc in L.get("muri_contorno", []):
        j_ = _idx_edificio(mc["edificio"])
        if j_ is None: continue
        zona = Point(*loc(mc["presso"][1], mc["presso"][0])).buffer(mc.get("raggio_m", 8.0)) if mc.get("presso") else None
        r = RW[mc["id"]]
        _cand.append(({"id": mc["id"], "nome": f"{mc['id']} – {r['tipo']}", "mat": mc.get("materiale", r["materiali"][0]),
                       "hm": mc.get("altezza_muro", h_of(r)), "sopra": mc.get("sopra"), "verso": mc.get("verso"),
                       "pilastri_passo": mc.get("pilastri_passo"), "copertina": mc.get("copertina", True),
                       "cancelli": mc.get("cancelli", []), "_ed": _impronta_edificio(mc["edificio"])}, j_, zona))
    EID = {e["impronta"]["indice"]: e for e in scheda["edifici"]}
    _con_mc = {mc["edificio"] for mc in L.get("muri_contorno", [])}
    for i, f in enumerate(FABB):
        eid = EID[i]["id"] if i in EID else f"CTX{i:02d}"
        fs = _PE.get(eid, {}).get("fronte_strada")
        if not fs or eid in _con_mc: continue
        j_ = _idx_part_di(poly(f).centroid)
        if j_ is None: continue
        _cand.append(({"id": fs.get("id", f"RS-{eid}"), "nome": f"{fs.get('id', 'RS-' + eid)} – {fs.get('tipo', 'recinzione su strada')}",
                       "mat": fs.get("materiale", "C04"), "hm": fs.get("muro_h", 1.8), "sopra": fs.get("sopra"), "verso": None,
                       "pilastri_passo": fs.get("pilastri_passo"), "copertina": fs.get("copertina", True),
                       "cancelli": fs.get("cancelli", []), "_ed": poly(f)}, j_, None))
    # edifici presenti solo nel DBGT (stesso elenco e indici della sezione edifici)
    _DBE = [g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area) for g in dbgt("edifici")]
    _DBE = [Polygon(g.exterior) for g in _DBE if not g.is_empty and g.area > 8]
    for jd, g in enumerate(_DBE):
        fs = _PE.get(f"DB{jd:02d}", {}).get("fronte_strada")
        if not fs: continue
        j_ = _idx_part_di(g.centroid)
        if j_ is None: continue
        eid = f"DB{jd:02d}"
        _cand.append(({"id": fs.get("id", f"RS-{eid}"), "nome": f"{fs.get('id', 'RS-' + eid)} – {fs.get('tipo', 'recinzione su strada')}",
                       "mat": fs.get("materiale", "C04"), "hm": fs.get("muro_h", 1.8), "sopra": fs.get("sopra"), "verso": None,
                       "pilastri_passo": fs.get("pilastri_passo"), "copertina": fs.get("copertina", True),
                       "cancelli": fs.get("cancelli", []), "_ed": g}, j_, None))
    _edificate = {j for j, p in particelle if any(p.contains(poly(f).centroid) for f in FABB)} | {c[1] for c in _cand}
    _VICINI = ST.get("distanza_fronte_particella_m", 6.0)
    def _proprietario(mid):
        """particella a cui appartiene un punto del fronte su strada: la più vicina entro _VICINI metri."""
        # precedenza alle particelle edificate (le strisce catastali strette davanti ai lotti non contano)
        for gruppo in (lambda j: j in _edificate or j in IL_TUTTE, lambda j: True):
            best, bd = None, _VICINI
            for j, p in particelle:
                if not gruppo(j): continue
                d_ = p.distance(mid)
                if d_ < bd: best, bd = j, d_
            if best is not None: return best
        return None
    _CI = L.get("confini_interni", {"altezza": 1.8, "spessore": 0.2, "materiale": "C04"})
    _DEF = {"id": "RS", "nome": "RS – recinzione su strada", "mat": _CI.get("materiale", "C04"),
            "hm": _CI.get("altezza", 1.8), "sopra": None, "verso": None}
    _fronte_lotto = P03.exterior.buffer(1.5).intersection(sedime.buffer(3.0))
    _FAB_CAT = unary_union([poly(f) for f in FABB] + dbgt("edifici"))
    _sed_bd = sedime.boundary
    def _parallelo(a_, b_, tol=30.0):
        m_ = Point((a_[0]+b_[0])/2, (a_[1]+b_[1])/2); s_ = _sed_bd.project(m_)
        p1, p2 = _sed_bd.interpolate(max(0, s_ - 0.7)), _sed_bd.interpolate(s_ + 0.7)
        t1 = math.atan2(p2.y - p1.y, p2.x - p1.x); t2 = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
        d_ = abs((math.degrees(t1 - t2) + 90) % 180 - 90)
        return d_ <= tol
    def _attr(mid, a_, b_, interno_se_non_parallelo=True):
        if interno_se_non_parallelo and (sedime.distance(mid) > 2.0 or not _parallelo(a_, b_)): return "CI"
        j_ = _proprietario(mid)
        if j_ is None or j_ in IL_TUTTE: return None
        if j_ not in _edificate: return "CI"          # campo o terreno incolto: rete (vedi _muro_interno)
        # le zone (presso/raggio) hanno la precedenza; poi, nella stessa particella, l'edificio più vicino al tratto
        z_ = [at for at, jj, zona in _cand if jj == j_ and zona is not None and zona.contains(mid)]
        if z_: return z_[0]
        c_ = [at for at, jj, zona in _cand if jj == j_ and zona is None and _orient_ok(at.get("verso"), a_, b_)]
        if not c_: c_ = [at for at, jj, zona in _cand if jj == j_ and zona is None]
        c_.sort(key=lambda at: at["_ed"].distance(mid))
        return c_[0] if c_ else _DEF
    def _normali_prop(seg_pts):
        ns = []   # normale verso l'interno della proprietà = lontano dalla strada
        for j, (x, y) in enumerate(seg_pts):
            a2 = seg_pts[max(0, j-1)]; b2 = seg_pts[min(len(seg_pts)-1, j+1)]
            dx, dy = b2[0]-a2[0], b2[1]-a2[1]; Ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy/Ln, dx/Ln
            if sedime.distance(Point(x + nx, y + ny)) < sedime.distance(Point(x - nx, y - ny)): nx, ny = -nx, -ny
            ns.append((nx, ny))
        return ns
    nci = 0
    _CANC = {}
    def _muro_strada(seg_pts, at, fonte):
        ns = _normali_prop(seg_pts)
        base = [round(z_marc(x, y) if sedime.distance(Point(x, y)) < 2.5 else trend(x, y), 3) for x, y in seg_pts]
        interno = [round(trend(x + nx*IN, y + ny*IN), 3) for (x, y), (nx, ny) in zip(seg_pts, ns)]
        # il DTM vicino ai muri esagera il salto: il muro può superare l'altezza di rilievo di 0,8 m al massimo
        top = [round(max(b + at["hm"], min(zi + 0.1, b + at["hm"] + ST.get("eccesso_muro_max_m", 0.3))), 3) for b, zi in zip(base, interno)]
        scena["muri"].append({"id": at["id"], "nome": at["nome"], "materiale": at["mat"], "spessore": 0.25,
            "punti": [[round(x, 3), round(y, 3)] for x, y in seg_pts],
            "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns], "z_base": base,
            "z_sommita": top, "z_terreno_interno": interno, "confidenza": "media", "quote": fonte,
            "pilastri_passo": at.get("pilastri_passo"), "copertina": at.get("copertina", True), "su_strada": True})
        if at.get("cancelli"): _CANC.setdefault(at["id"], at["cancelli"])
        if at.get("sopra"):
            t, h2, m2 = at["sopra"]
            scena["recinzioni"].append({"id": at["id"], "nome": f"{at['id']} – {t}", "tipo": t, "materiale": m2, "altezza": h2,
                "passo_paletti": 2.0, "punti": [[round(x, 3), round(y, 3), tt] for (x, y), tt in zip(seg_pts, top)]})
    def _muro_interno(seg_pts):
        global nci
        nci += 1; ns = _normali_prop(seg_pts)
        zb = [round(min(trend(x + nx, y + ny), trend(x - nx, y - ny)), 3) for (x, y), (nx, ny) in zip(seg_pts, ns)]
        lontano = _FAB_CAT.distance(LineString(seg_pts).centroid) > _CI.get("rete_oltre_m", 12.0)
        hmuro = _CI.get("cordolo_rete_m", 0.3) if lontano else _CI["altezza"]
        scena["muri"].append({"id": f"CI{nci:02d}", "nome": f"CI{nci:02d} – " + ("rete di campagna (DBGT)" if lontano else "recinzione (DBGT)"),
            "materiale": _CI["materiale"], "spessore": _CI["spessore"], "punti": [[round(x, 3), round(y, 3)] for x, y in seg_pts],
            "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns], "z_base": zb,
            "z_sommita": [round(z + hmuro, 3) for z in zb], "confidenza": "media", "quote": "DBGT + DTM"})
        if lontano:
            scena["recinzioni"].append({"id": f"CI{nci:02d}", "nome": f"CI{nci:02d} – rete", "tipo": "rete", "materiale": "C20",
                "altezza": _CI.get("altezza_rete_m", 1.5), "passo_paletti": 2.5,
                "punti": [[round(x, 3), round(y, 3), round(z + hmuro, 3)] for (x, y), z in zip(seg_pts, zb)]})
    # nessuna recinzione dentro la sede stradale (le recinzioni DBGT a volte attraversano il marciapiede)
    linee_r = unary_union(_DB_REC).intersection(area.buffer(-0.5)).difference(sedime.union(marciapiedi).buffer(-0.3))
    from shapely.ops import linemerge as _lm
    linee_r = _lm(linee_r) if linee_r.geom_type == "MultiLineString" else linee_r
    coperti = [linee_r.buffer(1.2), _fronte_lotto]
    for ln in getattr(linee_r, "geoms", [linee_r]):
        if ln.geom_type != "LineString" or ln.length < 1.0: continue
        pts = dens(list(ln.coords), 1.0)
        cls = []
        for a_, b_ in zip(pts, pts[1:]):
            mid = Point((a_[0]+b_[0])/2, (a_[1]+b_[1])/2)
            cls.append(None if _fronte_lotto.contains(mid) else _attr(mid, a_, b_))
        k0 = 0
        while k0 < len(cls):
            k1 = k0
            while k1 + 1 < len(cls) and cls[k1 + 1] is cls[k0]: k1 += 1
            seg_pts = pts[k0:k1 + 2]; at = cls[k0]; k0 = k1 + 1
            if at is None or len(seg_pts) < 2 or LineString(seg_pts).length < 1.0: continue
            if at == "CI": _muro_interno(seg_pts)
            else: _muro_strada(seg_pts, at, "DBGT + DTM")
    # fronti senza recinzione DBGT: bordo della sede stradale, 15 cm dentro la proprietà, assegnato tratto per tratto
    # alla particella più vicina (il catasto è sfasato: il confine può stare metri indietro rispetto alla sede)
    cop = unary_union(coperti)
    resto = _sed_bd.intersection(area.buffer(-0.5)).difference(cop)
    for part in getattr(resto, "geoms", [resto]):
        if part.is_empty or part.geom_type != "LineString" or part.length < 1.5: continue
        off = part.parallel_offset(0.15, "left")
        if off.is_empty or off.geom_type != "LineString" or sedime.contains(off.interpolate(0.5, normalized=True)):
            off = part.parallel_offset(0.15, "right")
        if off.is_empty or off.geom_type != "LineString": off = part
        pts = dens(list(off.coords), 1.0)
        cls = [_attr(Point((a_[0]+b_[0])/2, (a_[1]+b_[1])/2), a_, b_, False) for a_, b_ in zip(pts, pts[1:])]
        k0 = 0
        while k0 < len(cls):
            k1 = k0
            while k1 + 1 < len(cls) and cls[k1 + 1] is cls[k0]: k1 += 1
            seg_pts = pts[k0:k1 + 2]; at = cls[k0]; k0 = k1 + 1
            if at is None or len(seg_pts) < 2 or LineString(seg_pts).length < 1.5: continue
            if at == "CI": _muro_interno(seg_pts)
            else: _muro_strada(seg_pts, at, "bordo sede stradale DBGT + DTM")
# --- cancelli e cancelletti: interrompono il muro del fronte (e la recinzione sopra) e diventano oggetti propri.
# `posizione` è la frazione (0–1) lungo il tratto di fronte più lungo di quel muro, nel verso dei suoi punti.
scena["cancelli"] = []
from shapely.ops import substring as _substr
def _taglia(lista, idx, s0, s1):
    el = lista[idx]; ln = LineString([p[:2] for p in el["punti"]])
    def pezzo(a_, b_):
        if b_ - a_ < 0.3: return None
        g = _substr(ln, a_, b_); pts = list(g.coords)
        def zint(arr):
            out = []
            for q in pts:
                s_ = ln.project(Point(q)); acc = 0.0
                for k in range(len(el["punti"]) - 1):
                    L_ = math.dist(el["punti"][k][:2], el["punti"][k+1][:2])
                    if acc + L_ >= s_ - 1e-9 or k == len(el["punti"]) - 2:
                        t = 0 if L_ == 0 else min(1, max(0, (s_ - acc) / L_)); out.append(round(arr[k] + (arr[k+1] - arr[k]) * t, 3)); break
                    acc += L_
            return out
        nuovo = dict(el)
        if "z_base" in el:
            nuovo["z_base"] = zint(el["z_base"]); nuovo["z_sommita"] = zint(el["z_sommita"])
            if "z_terreno_interno" in el: nuovo["z_terreno_interno"] = zint(el["z_terreno_interno"])
            nn = el["normali_interno"][0]; nuovo["normali_interno"] = [nn for _ in pts]
            nuovo["punti"] = [[round(x, 3), round(y, 3)] for x, y in pts]
        else:
            zz = zint([p[2] for p in el["punti"]]); nuovo["punti"] = [[round(x, 3), round(y, 3), z] for (x, y), z in zip(pts, zz)]
        return nuovo
    parti = [p for p in (pezzo(0, s0), pezzo(s1, ln.length)) if p]
    lista[idx:idx + 1] = parti
for rid, canc in (_CANC.items() if _DB_REC else []):
    cand_m = [k for k, m in enumerate(scena["muri"]) if m["id"] == rid]
    if not cand_m: continue
    for cz in sorted(canc, key=lambda c: -c.get("posizione", 0.5)):
        cand_m = [k for k, m in enumerate(scena["muri"]) if m["id"] == rid]
        k = max(cand_m, key=lambda k: LineString(scena["muri"][k]["punti"]).length)
        m = scena["muri"][k]; ln = LineString(m["punti"]); w_ = cz.get("larghezza", 3.5 if cz.get("tipo") == "carraio" else 1.1)
        if ln.length < w_ + 0.6: continue
        sc_ = min(max(cz.get("posizione", 0.5) * ln.length, w_ / 2 + 0.3), ln.length - w_ / 2 - 0.3)
        s0, s1 = sc_ - w_ / 2, sc_ + w_ / 2
        a_, b_ = ln.interpolate(s0), ln.interpolate(s1); zc = z_marc((a_.x + b_.x) / 2, (a_.y + b_.y) / 2)
        scena["cancelli"].append({"id": f"{rid}-{cz.get('tipo', 'cancello')}", "tipo": cz.get("tipo", "carraio"),
            "stile": cz.get("stile", "sbarre"), "materiale": cz.get("materiale", "C06"), "h": cz.get("h", 1.8),
            "pensilina": cz.get("pensilina", False), "punti": [[round(a_.x, 3), round(a_.y, 3)], [round(b_.x, 3), round(b_.y, 3)]],
            "z": round(zc, 3), "normale": m["normali_interno"][0]})
        p0 = m["punti"][0]
        _taglia(scena["muri"], k, s0, s1)
        for j, r in enumerate(scena["recinzioni"]):
            if r["id"] == rid and math.dist(r["punti"][0][:2], p0) < 0.05:
                _taglia(scena["recinzioni"], j, s0, s1); break

# --- muri di sostegno DBGT: altezza = salto del DTM fra i due lati (+ coronamento); esclusi quelli già modellati
_DB_MS = dbgt("muri_sostegno")
if _DB_MS:
    _gia = unary_union([LineString(m["punti"]).buffer(1.5) for m in scena["muri"] if len(m["punti"]) > 1]) \
        if scena["muri"] else Polygon()
    nms = 0
    for ln in _DB_MS:
        ln = ln.intersection(area.buffer(-0.5)).difference(_gia)
        for part in getattr(ln, "geoms", [ln]):
            if part.is_empty or part.geom_type != "LineString" or part.length < 2: continue
            # mai sulla sede stradale (marciapiedi compresi) né sul fronte del lotto, che ha già il suo muro
            if part.intersection(sedime.buffer(0.3)).length > 0.3 * part.length: continue
            if part.distance(P03.exterior) < 1.5 and part.intersection(P03.exterior.buffer(1.5)).length > 0.5 * part.length: continue
            pts = dens(list(part.coords), 1.0); ns, zb, zt = [], [], []
            for j, (x, y) in enumerate(pts):
                a2 = pts[max(0, j-1)]; b2 = pts[min(len(pts)-1, j+1)]
                dx, dy = b2[0]-a2[0], b2[1]-a2[1]; Ln = math.hypot(dx, dy) or 1.0
                nx, ny = -dy/Ln, dx/Ln
                za, zbb = trend(x + nx*1.5, y + ny*1.5), trend(x - nx*1.5, y - ny*1.5)
                if za < zbb: nx, ny, za, zbb = -nx, -ny, zbb, za      # normale verso il lato alto
                ns.append((nx, ny)); zb.append(round(zbb, 3)); zt.append(round(za + 0.2, 3))
            if max(t - b for t, b in zip(zt, zb)) < 0.6: continue
            nms += 1
            scena["muri"].append({"id": f"MS{nms:02d}", "nome": f"MS{nms:02d} – muro di sostegno (DBGT)", "materiale": "C15",
                "spessore": 0.3, "punti": [[round(x, 3), round(y, 3)] for x, y in pts],
                "normali_interno": [[round(a, 4), round(b, 4)] for a, b in ns], "z_base": zb, "z_sommita": zt,
                "confidenza": "media", "quote": "DBGT + DTM"})
_ids_db = {m["id"] for m in scena["muri"]} | ({mc["id"] for mc in L.get("muri_contorno", [])} if _DB_REC else set())
for mc in ([m for m in L.get("muri_contorno", []) if m["id"] not in _ids_db] if _DB_REC else L.get("muri_contorno", [])):
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
        top = [round(max(b + hm, min(zi + 0.1, b + hm + ST.get("eccesso_muro_max_m", 0.3))), 3) for b, zi in zip(base, interno)]
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
_DB_ED = [g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area) for g in dbgt("edifici")]
_DB_ED = [Polygon(g.exterior) for g in _DB_ED if not g.is_empty and g.area > 8]
_usati = set()
def _da_dbgt(p):
    """sagoma DBGT corrispondente all'impronta catastale p (massima sovrapposizione, catasto sfasato ≤ 3 m)."""
    best, ba = None, 0.0
    for j, g in enumerate(_DB_ED):
        if j in _usati: continue
        a_ = g.intersection(p.buffer(1.5)).area
        if a_ > ba: best, ba = j, a_
    if best is not None and ba > 0.3 * min(p.area, _DB_ED[best].area):
        _usati.add(best); return _DB_ED[best]
    return None
for i, f in enumerate(FABB):
    p = poly(f)
    if not area.contains(p.centroid) or f["properties"]["tagliato_dal_bordo"]: continue
    g_ = _da_dbgt(p) if _DB_ED else None
    if g_ is not None: p = g_
    p = p.intersection(area)
    if p.geom_type != "Polygon": p = max(polys(p), key=lambda q: q.area)
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
        "pendenza_pct": cop.get("pendenza_pct"),
        "sporto_cm": (ov or {}).get("sporto_cm", cop.get("sporto_cm")),
        "fotovoltaico": bool((ov or {}).get("fotovoltaico", cop.get("fotovoltaico") or
                             any("fotovolt" in str(x) for x in cop.get("elementi", [])))),
        "piani": (ov or {}).get("piani") or (e or {}).get("piani_ft"),
        "facciate": (ov or {}).get("facciate") or (e or {}).get("facciate", []), "volumi": (ov or {}).get("volumi", []),
        "oscurante_default": (ov or {}).get("oscurante"), "mat_ringhiera": (ov or {}).get("mat_ringhiera", "C06")})
# edifici del DBGT senza corrispondenza in catasto (spesso più recenti): LOD1 generici
for j, g in enumerate(_DB_ED):
    if j in _usati or not area.contains(g.centroid): continue
    ov = LE.get("per_edificio", {}).get(f"DB{j:02d}", {})
    zb = min(trend(x, y) for x, y in g.exterior.coords)
    scena["edifici"].append({"id": f"DB{j:02d}", "nome": f"DB{j:02d} – contesto DBGT ({ov.get('nota', 'LOD1')})",
        "materiale": ov.get("materiale", LE.get("materiale_generico", "C04")),
        "impronta": [[round(x, 3), round(y, 3)] for x, y in list(g.exterior.coords)[:-1]], "z_base": round(zb, 3),
        "altezza": ov.get("altezza", LE.get("altezza_generica_m", 6.5)), "confidenza_altezza": "bassa",
        "copertura": ov.get("copertura", "piana"), "manto": ov.get("manto"), "lod": 1,
        "colmo": ov.get("colmo"), "pendenza_pct": ov.get("pendenza_pct")})

# --- quote misurate dal DSM LiDAR (se disponibile): gronda, colmo, forma del tetto; alberi dalla vegetazione
_DSMJ = D.get("dsm", {}).get("json")
if _DSMJ and os.path.exists(P_(_DSMJ)):
    _DM2 = jload(_DSMJ); _RS = {k: tifffile.imread(P_(v)) for k, v in _DM2["raster"].items()}
    _TU = Transformer.from_crs(_AEQD, _DM2["crs"], always_xy=True)
    def _rc(x, y):
        E_, N_ = _TU.transform(x, y)
        return int((_DM2["bordo_superiore_N"] - N_) / _DM2["passo"]), int((E_ - _DM2["bordo_sinistro_E"]) / _DM2["passo"])
    def dsm(k, x, y):
        r_, c_ = _rc(x, y); a_ = _RS[k]
        return float(a_[r_, c_]) if 0 <= r_ < a_.shape[0] and 0 <= c_ < a_.shape[1] else float("nan")
    ANNO = D["dsm"].get("anno", "?")
    for e in scena["edifici"]:
        P_e = Polygon(e["impronta"]); x0, y0, x1, y1 = P_e.bounds
        celle = [(x + 0.5, y + 0.5) for x in range(int(x0) - 1, int(x1) + 2) for y in range(int(y0) - 1, int(y1) + 2)
                 if P_e.buffer(-0.3).contains(Point(x + 0.5, y + 0.5))]
        if len(celle) < 6: continue
        zt = np.array([dsm("edifici", x, y) - Z0 for x, y in celle])
        zg_ = np.array([trend(x, y) for x, y in celle])
        alto = (zt - zg_) > 2.0
        e["dsm_copertura"] = round(float(alto.mean()), 2)
        if alto.mean() < 0.6:   # edificio assente nel DSM (costruito dopo il volo) o troppo piccolo: restano le stime
            e["quote_fonte"] = f"stima (assente nel DSM {ANNO})"; continue
        bordo = np.array([P_e.exterior.distance(Point(c)) < 1.3 for c in celle])
        g_abs = float(np.percentile(zt[alto & bordo] if (alto & bordo).sum() >= 4 else zt[alto], 35))
        c_abs = float(np.percentile(zt[alto], 97))
        e["gronda_z"] = round(g_abs, 2); e["colmo_z"] = round(c_abs, 2)
        e["quote_fonte"] = f"DSM LiDAR {ANNO}"
        dz = c_abs - g_abs
        dmax = max(0.5, max(P_e.exterior.distance(Point(c)) for c in celle))
        f_ = (e.get("copertura") or "").lower()
        falde = "padiglione" in f_ or "capanna" in f_ or "falda" in f_
        if dz < 0.6:
            e["copertura"] = "piana"; e["colmo"] = None
        else:
            if not falde: e["copertura"] = "a padiglione"
            e["pendenza_pct"] = round(min(50, max(15, 100 * dz / dmax)), 0)
        # volume alto (torretta, attico) riconosciuto dal DSM: celle oltre il colmo del corpo principale
        alti = [c for c, z in zip(celle, zt) if z > g_abs + max(2.6, 0.75 * dz + 2.0)]
        if len(alti) >= 6 and not e.get("volumi"):
            from shapely.geometry import MultiPoint
            g_t = MultiPoint(alti).convex_hull.buffer(0.5)
            if g_t.area >= 6:
                e["volumi_dsm"] = {"impronta": [[round(x, 2), round(y, 2)] for x, y in list(g_t.minimum_rotated_rectangle.exterior.coords)[:-1]],
                                   "quota_z": round(float(np.percentile([z for z in zt if z > g_abs + 2.6], 90)), 2)}
    # alberi: massimi locali del modello delle chiome (vegetazione − terreno), fuori da edifici e carreggiata
    alberi = []
    edif_ = unary_union([Polygon(e["impronta"]).buffer(1.0) for e in scena["edifici"]])
    griglia = [(x + 0.5, y + 0.5) for x in range(int(-EXT), int(EXT)) for y in range(int(-EXT), int(EXT))]
    chm = {}
    for x, y in griglia:
        v_ = dsm("vegetazione", x, y) - Z0 - trend(x, y); chm[(x, y)] = v_ if v_ == v_ else 0.0
    for (x, y), h_ in chm.items():
        if h_ < L.get("alberi_dsm", {}).get("altezza_min_m", 2.5): continue
        if any(chm.get((x + dx, y + dy), 0) > h_ for dx in range(-2, 3) for dy in range(-2, 3) if (dx or dy)): continue
        p_ = Point(x, y)
        if edif_.contains(p_) or carreggiata.contains(p_) or not area.buffer(-1).contains(p_): continue
        n_ = sum(1 for dx in range(-4, 5) for dy in range(-4, 5) if chm.get((x + dx, y + dy), 0) > 0.45 * h_)
        alberi.append((round(x, 2), round(y, 2), round(h_, 1), round(2 * math.sqrt(n_ / math.pi), 1)))
    # verifica sull'ortofoto più recente: l'albero c'è ancora se la chioma è scura e verde (non erba secca o suolo)
    _OJ = D.get("ortofoto")
    if _OJ and os.path.exists(P_(_OJ)):
        from PIL import Image as _Im
        _OM = jload(_OJ); _OA = np.asarray(_Im.open(os.path.join(os.path.dirname(P_(_OJ)), _OM.get("file", "ortofoto.jpg"))).convert("RGB")).astype(float)
        _OT = Transformer.from_crs(_AEQD, _OM["crs"], always_xy=True); _oe0, _on0, _oe1, _on1 = _OM["bbox"]; _omp = _OM["m_px"]
        AD_ = L.get("alberi_dsm", {})
        def _verde(x, y, r):
            E_, N_ = _OT.transform(x, y); c_ = (E_ - _oe0) / _omp; r_ = (_on1 - N_) / _omp; R_ = max(2, int(r / _omp))
            w_ = _OA[max(0, int(r_ - R_)):int(r_ + R_), max(0, int(c_ - R_)):int(c_ + R_)]
            if w_.size == 0: return False
            exg = float(np.mean((2 * w_[:, :, 1] - w_[:, :, 0] - w_[:, :, 2]) / (w_.sum(2) + 1)))
            return exg >= AD_.get("verde_min", 0.085) and float(w_.mean()) <= AD_.get("luminosita_max", 115)
        prima = len(alberi)
        alberi = [t for t in alberi if _verde(t[0], t[1], t[3] * 0.35)]
        scena["alberi_dsm_controllo"] = {"trovati": prima, "presenti_ortofoto": len(alberi)}
    scena["alberi_dsm"] = [{"xy": [x, y], "h": h_, "chioma": max(1.5, min(9.0, d_))} for x, y, h_, d_ in alberi]

# --- muri di confine interni: lati delle particelle lontani dalla strada, fuori dagli edifici
CI = L.get("confini_interni")
if CI and not _DB_REC:
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
_carr_bd = carreggiata.boundary
def _edificio_poly(eid):
    for e_ in scena["edifici"]:
        if e_["id"] == eid: return Polygon(e_["impronta"])
    return None
def vicino_a(eid, offset=0.5):
    """punto del marciapiede davanti all'edificio: sul bordo della carreggiata più vicino, spostato verso l'edificio."""
    P_ = _edificio_poly(eid)
    if P_ is None: return None
    q = nearest_points(_carr_bd, P_.centroid)[0]; c = P_.centroid
    d = math.dist((q.x, q.y), (c.x, c.y)) or 1.0
    return (round(q.x + (c.x - q.x) / d * offset, 2), round(q.y + (c.y - q.y) / d * offset, 2))
def punti_giardino(eid, n, dist_min=3.0):
    """n punti nel giardino dell'edificio (particella meno edificio e fasce sui confini), i più lontani da tutto."""
    P_ = _edificio_poly(eid)
    if P_ is None: return []
    try: par = particella_di(eid)
    except IndexError: par = P_.buffer(8)
    g = par.buffer(-1.2).difference(P_.buffer(2.0)).difference(sedime.buffer(1.5)).intersection(area)
    if g.is_empty: return []
    x0, y0, x1, y1 = g.bounds; cand = []
    for i_ in range(int(x0), int(x1) + 1):
        for j_ in range(int(y0), int(y1) + 1):
            pt_ = Point(i_ + 0.5, j_ + 0.5)
            if g.contains(pt_): cand.append((g.exterior.distance(pt_) if g.geom_type == "Polygon" else 1.0, pt_))
    cand.sort(key=lambda t: -t[0]); out = []
    for _, pt_ in cand:
        if all(pt_.distance(Point(o)) >= dist_min for o in out): out.append((round(pt_.x, 2), round(pt_.y, 2)))
        if len(out) >= n: break
    return out
def posiziona(a):
    if "xy" in a: return tuple(a["xy"])
    if "vicino_a" in a: return vicino_a(a["vicino_a"], a.get("offset", 0.5))
    if "lungo_fronte_m" in a: return lungo_fronte(a["lungo_fronte_m"], a.get("offset", 0.0))
    if "fronte_y" in a: return fronte_y(a["fronte_y"], a.get("offset", 0.0))
    if "da_punta" in a: return (round(tip[0] + a["da_punta"][0], 2), round(tip[1] + a["da_punta"][1], 2))
    return None
CHIAVI_POS = {"lungo_fronte_m", "fronte_y", "offset", "da_punta", "orienta_fronte", "nel_contesto", "nome", "materiale",
              "vicino_a", "giardino_di"}
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
    if "giardino_di" in v:
        o["xy_lista"] = [list(q) for eid in (v["giardino_di"] if isinstance(v["giardino_di"], list) else [v["giardino_di"]])
                         for q in punti_giardino(eid, v.get("n", 1))]
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
