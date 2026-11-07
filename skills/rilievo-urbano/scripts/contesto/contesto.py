#!/usr/bin/env python3
"""Motore generico, fase 2. Uso: python contesto.py <cartella o file lotto.json>
scena.json → contesto.json per scripts/sketchup/costruisci_contesto.rb (schema concordato con
sketchup-expert). Superfici 2.5D triangolate con Delaunay vincolata (libreria `triangle`, opzioni pq30Y:
nessun vertice aggiunto sui bordi, così le superfici adiacenti condividono gli stessi vertici), fasce
verticali dove due superfici confinanti hanno quote diverse (cordoli, salti), muri come sweep di sezioni,
recinzioni su polilinea, edifici estrusi, arredo come parallelepipedi.

Coordinate locali in metri arrotondate al mm: x = Est, y = Nord, z = quota relativa all'incrocio.
"""
import json, math, os, random
import numpy as np, triangle
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union, polygonize
from PIL import Image

import scena as S          # riusa geometrie e funzioni di quota della scena (legge lo stesso lotto.json)

HERE = S.HERE
L, LT, ST, MF = S.L, S.LT, S.ST, S.MF
RID = MF["id"]
sc = json.load(open(os.path.join(HERE, "scena.json")))
scheda = S.scheda
R = lambda v: round(float(v), 3)
random.seed(L.get("seme_casuale", 0))

# ---------------------------------------------------------------- muri: fasce di ingombro (per escluderle)
SP = MF["spessore"]
def striscia(m, w):
    out = [tuple(p) for p in m["punti"]]
    inn = [(p[0] + n[0]*w, p[1] + n[1]*w) for p, n in zip(m["punti"], m["normali_interno"])]
    g = Polygon(out + inn[::-1]).buffer(0)
    return g if g.is_valid else g.buffer(0)
strisce = unary_union([striscia(m, SP - 0.03) for m in sc["muri"]])

# ---------------------------------------------------------------- regioni
from shapely import set_precision
G = 0.05                                   # griglia di aggancio: elimina schegge e lati < 5 cm
def sp(g): return set_precision(g.buffer(0), G)
area = sp(S.area)
strisce = sp(strisce)
carr = sp(S.carreggiata.intersection(area).simplify(0.05))
marc = sp(S.marciapiedi.intersection(area).simplify(0.05).difference(carr))
P03g = sp(S.P03.intersection(area).simplify(0.05))
lotto = sp(P03g.difference(strisce))
fondo = sp(area.difference(unary_union([carr, marc, P03g])).difference(strisce))
def pulisci(g, minarea=0.5):
    """rimuove schegge (parti sottili o minuscole) con apertura morfologica."""
    g = g.buffer(-0.04, join_style=2).buffer(0.04, join_style=2)
    return sp(unary_union([p for p in getattr(g, "geoms", [g]) if p.area >= minarea]))
# partizione esatta: ogni regione pulita è sottratta dalle successive; gli avanzi vanno nel fondo (mai buchi)
# carreggiata e marciapiede: niente apertura morfologica (romperebbe il bordo del cordolo)
marc = sp(marc.difference(carr))
lotto = pulisci(sp(lotto.difference(carr).difference(marc)))
fondo = sp(area.difference(unary_union([carr, marc, lotto, strisce])))

# quota del lotto: sul bordo verso il muro del fronte = sommità del muro; poi scarpata fino al DTM entro 2,5 m
from shapely.geometry import LineString as _LS
_r06 = [m for m in sc["muri"] if m["id"] == RID]
_lines = [(_LS([(p[0], p[1]) for p in m["punti"]]), m) for m in _r06]
def _top_at(x, y):
    best = None
    for ln, m in _lines:
        d = ln.distance(Point(x, y))
        if best is None or d < best[0]: best = (d, ln, m)
    d, ln, m = best
    s_ = ln.project(Point(x, y)); acc = 0.0; P = m["punti"]; Zt = m["z_sommita"]
    for i in range(len(P) - 1):
        L = math.dist(P[i], P[i+1])
        if acc + L >= s_ or i == len(P) - 2:
            t = 0 if L == 0 else min(1, max(0, (s_ - acc) / L)); return d, Zt[i] + (Zt[i+1] - Zt[i]) * t
        acc += L
def z_lotto2(x, y):
    zi = S.trend(x, y)
    d, zt = _top_at(x, y)
    if d >= S.SCARPATA + SP: return zi
    w = max(0.0, (d - SP) / S.SCARPATA); w = w * w * (3 - 2 * w)          # smoothstep
    return zt + (max(zi, zt) - zt) * w if zi > zt else zt + (zi - zt) * w
_vicino_strada = S.sedime.union(S.raccordo).buffer(0.3)   # avanzi a ridosso della strada: quota del marciapiede
_RUM = LT.get("rumore_superficie_m", 0.0)
REG = [("P01", carr, ST["materiale_carreggiata"], lambda x, y: S.z_strada(x, y)),
       ("P02", marc, ST["materiale_marciapiede"], lambda x, y: S.z_marc(x, y)),
       ("P03", lotto, LT["materiale"], lambda x, y: z_lotto2(x, y) + (random.uniform(-_RUM, _RUM) if _top_at(x, y)[0] > SP + 0.3 else 0.0)),
       ("FONDO", fondo, LT["materiale_fasce"], lambda x, y: S.z_marc(x, y) if _vicino_strada.contains(Point(x, y)) else S.trend(x, y))]
MAXA = {"P01": 3.0, "P02": 1.5, "P03": 1.0, "FONDO": 6.0}

def parts(g):
    if isinstance(g, Polygon): return [g] if g.area > 0.05 else []
    return [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon) and p.area > 0.05]

# nodatura di tutti i bordi + densificazione unica (≤ 2 m) → vertici identici sui bordi condivisi
bordi = unary_union([LineString(r.coords) for _, g, _, _ in REG for p in parts(g)
                     for r in [p.exterior, *p.interiors]])
def q(p): return (round(p[0], 3), round(p[1], 3))
def dens_line(coords, step=1.0):   # 1 m come le stazioni dei muri: z_marc è curvo sugli angoli e con 2 m
                                   # il TIN scendeva fino a 9 cm sotto il piede del muro (fessure, SV-18)
    # unisce vertici più vicini di 10 cm (tranne gli estremi, che sono nodi condivisi)
    c2 = [coords[0]]
    for p in coords[1:-1]:
        if math.dist(p, c2[-1]) >= 0.10 and math.dist(p, coords[-1]) >= 0.10: c2.append(p)
    coords = c2 + [coords[-1]]
    out = []
    for a, b in zip(coords, coords[1:]):
        n = max(1, int(math.ceil(math.dist(a, b) / step)))
        out += [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(n)]
    return out + [coords[-1]]
segmenti = []
for ln in getattr(bordi, "geoms", [bordi]):
    c = [q(p) for p in ln.coords]
    segmenti.append(LineString(dens_line(c)))
facce = list(polygonize(unary_union(segmenti)))

def regione_di(f):
    rp = f.representative_point()
    for nome, g, mat, zf in REG:
        if g.buffer(0.01).contains(rp): return nome, mat, zf
    if strisce.buffer(0.01).contains(rp): return None          # sotto i muri: niente superficie
    # schegge perse dall'aggancio alla griglia: regione con la sovrapposizione maggiore, altrimenti fondo
    best = max(REG, key=lambda r: r[1].buffer(0.06).intersection(f).area)
    nome, g, mat, zf = best if best[1].buffer(0.06).intersection(f).area > 0 else REG[3]
    return nome, mat, zf

superfici, quote_vertice = {}, {}   # quote per (regione, vertice) per le fasce
for f in facce:
    r = regione_di(f)
    if not r: continue
    nome, mat, zf = r
    rings = [f.exterior, *f.interiors]
    V, seg, idx = [], [], {}
    for ring in rings:
        cs = [q(p) for p in list(ring.coords)[:-1]]
        ids = []
        for p in cs:
            if p not in idx: idx[p] = len(V); V.append(p)
            ids.append(idx[p])
        seg += [[ids[i], ids[(i+1) % len(ids)]] for i in range(len(ids))]
    holes = [list(Polygon(h).representative_point().coords)[0] for h in f.interiors]
    A = {"vertices": np.array(V), "segments": np.array(seg)}
    if holes: A["holes"] = np.array(holes)
    try:
        t = triangle.triangulate(A, "pq28Ya%.1f" % MAXA[nome])
    except Exception as e:
        print("triangolazione fallita", nome, e); continue
    if "triangles" not in t: continue
    vs = t["vertices"]; tris = t["triangles"]
    s = superfici.setdefault(nome, {"vertici": [], "triangoli": [], "mat": mat})
    base = len(s["vertici"])
    for x, y in vs:
        z = zf(x, y); s["vertici"].append([R(x), R(y), R(z)]); quote_vertice[(nome, q((x, y)))] = z
    for a, b, c in tris:
        pa, pb, pc = vs[a], vs[b], vs[c]
        if (pb[0]-pa[0])*(pc[1]-pa[1]) - (pb[1]-pa[1])*(pc[0]-pa[0]) < 0: b, c = c, b   # antiorari
        s["triangoli"].append([base + int(a), base + int(b), base + int(c), 0])

# ---------------------------------------------------------------- fasce verticali tra regioni confinanti
fasce = {"P02": [], "FONDO": []}
for sg in segmenti:
    cs = [q(p) for p in sg.coords]
    for a, b in zip(cs, cs[1:]):
        zs = {n: (quote_vertice.get((n, a)), quote_vertice.get((n, b))) for n in ("P01", "P02", "P03", "FONDO")}
        zs = {n: v for n, v in zs.items() if None not in v}
        if len(zs) != 2: continue
        (n1, (a1, b1)), (n2, (a2, b2)) = sorted(zs.items(), key=lambda kv: sum(kv[1]))
        if max(abs(a2 - a1), abs(b2 - b1)) < 0.02: continue
        dove = "P02" if {n1, n2} == {"P01", "P02"} else "FONDO"     # cordolo → P02 (C19); altri salti → terreno
        fasce[dove].append([[a[0], a[1], R(a1 - 0.05)], [b[0], b[1], R(b1 - 0.05)], [b[0], b[1], R(b2)], [a[0], a[1], R(a2)]])

def fascia_tris(lista, base):
    V, T = [], []
    for quad in lista:
        i = base + len(V); V += quad; T += [[i, i+1, i+2, 1], [i, i+2, i+3, 1]]
    return V, T

out_sup = []
NOMI = {"P01": "P01 – carreggiate", "P02": "P02 – marciapiedi e cordoli", "P03": LT["nome"],
        "FONDO": "Terreno – lotti di fondo (DTM)"}
TAG = {"P01": "40_Pavimentazioni", "P02": "40_Pavimentazioni", "P03": "60_Terreno", "FONDO": "60_Terreno"}
MAT2 = {"P01": ST["materiale_cordolo"], "P02": ST["materiale_cordolo"], "P03": LT["materiale_fasce"], "FONDO": LT["materiale_fasce"]}
for nome in ("P01", "P02", "P03", "FONDO"):
    s = superfici.get(nome)
    if not s: continue
    V, T = s["vertici"], s["triangoli"]
    fv, ft = fascia_tris(fasce.get(nome, []), len(V))
    out_sup.append({"nome": NOMI[nome], "tag": TAG[nome], "materiali": [s["mat"], MAT2[nome]],
                    "vertici": V + fv, "triangoli": T + ft, "smooth_deg": 25})

# ---------------------------------------------------------------- muri (sweep di sezioni a 4 punti)
def zin(m, x, y):
    return z_lotto2(x, y) if m["id"] == RID else S.trend(x, y)
muri = []
for m in sc["muri"]:
    st = []
    for p, n, zb, zt in zip(m["punti"], m["normali_interno"], m["z_base"], m["z_sommita"]):
        ix, iy = p[0] + n[0]*SP, p[1] + n[1]*SP
        st.append([[R(p[0]), R(p[1]), R(zb - 0.05)], [R(p[0]), R(p[1]), R(zt)],
                   [R(ix), R(iy), R(zt)], [R(ix), R(iy), R(min(zt, zin(m, ix, iy)) - 0.05)]])
    # tratti ≤ 8 m (getti): la verifica legge l'ingombro verticale di ogni contenitore
    if m["id"] == RID or len(st) <= 9:
        muri.append({"nome": m["nome"], "tag": "20_Recinzioni", "materiale": m["materiale"], "stazioni": st, "smooth_deg": 20})
    else:
        i0, k = 0, 0
        while i0 < len(st) - 1:
            i1 = min(len(st) - 1, i0 + 8); k += 1
            muri.append({"nome": f"{m['nome']} tratto {k}", "tag": "20_Recinzioni", "materiale": m["materiale"],
                         "stazioni": st[i0:i1+1], "smooth_deg": 20})
            i0 = i1

# ---------------------------------------------------------------- recinzioni (asse = mezzeria della testa del muro)
MAT_REC = {"rete": ("C20", "C20_rete"), "ringhiera": ("C06", "C06_ringhiera"), "doghe": ("C05", "C05_doghe")}
recinzioni = []
for r in [r for r in sc["recinzioni"] if r["tipo"] not in ("ringhiera", "doghe", "grigliato", "telo")]:
    pal, ret = MAT_REC[r["tipo"]]
    muro = [m for m in sc["muri"] if m["id"] == r["id"]]
    def asse_pt(x, y, z):
        best = min(((mm, i) for mm in muro for i, p in enumerate(mm["punti"])),
                   key=lambda t: math.dist(t[0]["punti"][t[1]], (x, y)))
        n = best[0]["normali_interno"][best[1]]
        return [R(x + n[0]*SP/2), R(y + n[1]*SP/2), R(z)]
    pts = [asse_pt(*p) for p in r["punti"]]
    # tratti ≤ 8 m (stessa logica del muro: la verifica legge l'ingombro verticale)
    i0 = 0; k = 0
    while i0 < len(pts) - 1:
        i1 = min(len(pts) - 1, i0 + 8); k += 1
        recinzioni.append({"nome": f"{r['nome']} tratto {k}", "tag": "20_Recinzioni", "asse": pts[i0:i1+1],
                           "passo": r.get("passo_paletti", 2.0), "h": r["altezza"], "gap": 0.0, "lato_palo": 0.04,
                           "def_palo": f"REC_paletto_{r['tipo']}", "materiale_palo": f"{pal}_paletti_{r['tipo']}",
                           "materiale_rete": ret})
        i0 = i1

# ---------------------------------------------------------------- edifici (LOD1: estrusione dell'impronta)
PIATT = L.get("edifici", {}).get("piattaforma_m", {})   # gronde misurate dal marciapiede: tolgo la piattaforma (nel DTM)
def tetto(imp, zg, forma, pend_pct, h_colmo, sporto=0.0):
    """Copertura a falde sopra l'impronta, alla quota di gronda zg. Regola generale, valida per piante
    qualsiasi: la quota cresce con la distanza dal bordo (padiglione = distanza da tutti i lati, come il
    tetto da scheletro rettilineo; capanna = distanza dai due lati lunghi del rettangolo minimo), con la
    pendenza della scheda, e si ferma al colmo (oltre resta un piano orizzontale). None per tetti piani."""
    f = (forma or "").lower()
    if not f or f.startswith("pian") or not ("padiglione" in f or "capanna" in f or "falda" in f): return None
    k = (pend_pct or 30) / 100.0
    P = Polygon(imp).buffer(0)
    if P.area < 4: return None
    capanna = "capanna" in f
    if sporto and not capanna:   # sporto di gronda: la falda continua oltre il muro e scende di k·sporto
        P = P.buffer(sporto, join_style=2, mitre_limit=3)
        zg = zg - k * sporto
    if capanna:
        mr = list(P.minimum_rotated_rectangle.exterior.coords)[:4]
        e1 = (mr[1][0] - mr[0][0], mr[1][1] - mr[0][1]); e2 = (mr[2][0] - mr[1][0], mr[2][1] - mr[1][1])
        lung, corto = (e1, e2) if math.hypot(*e1) >= math.hypot(*e2) else (e2, e1)
        Lc = math.hypot(*corto); n = (corto[0] / Lc, corto[1] / Lc)
        cx, cy = P.minimum_rotated_rectangle.centroid.coords[0]
        def dist(x, y): return max(0.0, Lc / 2 - abs((x - cx) * n[0] + (y - cy) * n[1]))
        dmax = Lc / 2
    else:
        bd = P.exterior
        def dist(x, y): return bd.distance(Point(x, y)) if P.contains(Point(x, y)) else 0.0
        dmax = max(0.5, max(P.buffer(-0.01).exterior.distance(p) for p in [P.representative_point(), P.centroid] if P.contains(p)))
    hcap = (h_colmo if h_colmo else 1e9)
    # vertici: bordo + anelli interni ogni 0,5 m (spigoli delle falde) + punti sparsi
    pts = []
    rings = [P.exterior.coords]
    if not capanna:
        d = 0.5
        while d < dmax:
            g = P.buffer(-d, join_style=2, mitre_limit=10)
            if g.is_empty: break
            for q in getattr(g, "geoms", [g]): rings.append(q.exterior.coords)
            d += 0.5
    V, seg, idx = [], [], {}
    def add(p):
        p = (round(p[0], 3), round(p[1], 3))
        if p not in idx: idx[p] = len(V); V.append(p)
        return idx[p]
    for r in rings:
        cs = list(r)[:-1]
        ids = [add(p) for p in cs]
        if r is rings[0]: seg += [[ids[i], ids[(i + 1) % len(ids)]] for i in range(len(ids))]
    if capanna:   # linea di colmo come vincolo
        x0, y0 = cx - lung[0], cy - lung[1]; x1, y1 = cx + lung[0], cy + lung[1]
        # colmo come punti (non come vincolo): un vincolo che tocca il bordo manda in errore `triangle`
        ln = LineString([(x0, y0), (x1, y1)]).intersection(P.buffer(-0.05))
        for q in getattr(ln, "geoms", [ln]):
            if q.geom_type == "LineString" and q.length > 0.2:
                nn = max(2, int(q.length / 0.5))
                for kk in range(nn + 1): add(q.interpolate(kk * q.length / nn).coords[0])
    try:
        t = triangle.triangulate({"vertices": np.array(V), "segments": np.array(seg)}, "pq20a2.0")
    except Exception:
        return None
    vs, tris = t["vertices"], t["triangles"]
    out_v = [[R(x), R(y), R(zg + min(k * dist(x, y), hcap))] for x, y in vs]
    out_t = []
    for a_, b_, c_ in tris:
        pa, pb, pc = vs[a_], vs[b_], vs[c_]
        if (pb[0]-pa[0])*(pc[1]-pa[1]) - (pb[1]-pa[1])*(pc[0]-pa[0]) < 0: b_, c_ = c_, b_
        out_t.append([int(a_), int(b_), int(c_)])
    # timpani: sui lati di bordo dove la falda sta sopra la gronda (capanna, tetti tagliati) il muro sale
    # fino alla falda. Regola valida per qualsiasi pianta: lati usati da un solo triangolo.
    from collections import Counter
    cnt = Counter(tuple(sorted(e_)) for t_ in out_t for e_ in ((t_[0], t_[1]), (t_[1], t_[2]), (t_[2], t_[0])))
    timpani = []
    for (i, j), c in cnt.items():
        if c != 1: continue
        zi, zj = out_v[i][2] - zg, out_v[j][2] - zg
        if max(zi, zj) < 0.02: continue
        a0 = len(out_v); out_v.append([out_v[i][0], out_v[i][1], R(zg)])
        b0 = len(out_v); out_v.append([out_v[j][0], out_v[j][1], R(zg)])
        if zi >= 0.02: timpani.append([a0, b0, i])
        if zj >= 0.02: timpani.append([b0, j, i] if zi >= 0.02 else [a0, b0, j])
    return {"vertici": out_v, "triangoli": out_t, "timpani": timpani, "sporto": bool(sporto and not capanna)}

# ---------------------------------------------------------------- dettagli: finestre, balconi, parapetti, fotovoltaico
ORI = {"N": 90, "NE": 45, "E": 0, "SE": -45, "S": -90, "SO": -135, "O": 180, "NO": 135}
def lati(imp):
    """lati dell'impronta con normale esterna e angolo della normale (gradi, 0 = Est, 90 = Nord)."""
    P = Polygon(imp).buffer(0); cs = list(P.exterior.coords)
    if not P.exterior.is_ccw: cs = cs[::-1]
    out = []
    for a, b in zip(cs, cs[1:]):
        L_ = math.dist(a, b)
        if L_ < 0.5: continue
        nx, ny = (b[1] - a[1]) / L_, -(b[0] - a[0]) / L_
        out.append({"a": a, "b": b, "L": L_, "n": (nx, ny), "ang": math.degrees(math.atan2(ny, nx))})
    return out
def _dang(a, b): return abs((a - b + 180) % 360 - 180)
def box(cx, cy, z, l, d, h, rot, mat, nome=None, incl=0.0):
    b_ = {"c": [R(cx), R(cy), R(z)], "dim": [R(l), R(d), R(h)], "rot_deg": round(rot, 2), "materiale": mat}
    if incl: b_["incl_deg"] = round(incl, 2)
    return b_
def _oscurante(tipo):
    o = (str(tipo.get("oscurante", "")) + " " + str(tipo.get("note", ""))).lower()
    if "persian" in o: return "persiane"
    if "avvolg" in o or "tapparell" in o: return "avvolgibile"
    return tipo.get("_oscurante_default", "avvolgibile")
def finestra(out, cx, cy, z, w, h, rot, n, tipo, porta=False):
    """infisso completo: telaio, vetro arretrato, davanzale, oscurante (persiane aperte ai lati o avvolgibile con
    cassonetto). Coordinate: (cx, cy) sul filo esterno del muro, n = normale esterna, z = quota del davanzale."""
    nx, ny = n; f = lambda d: (cx + nx * d, cy + ny * d)
    tel = tipo.get("mat_telaio", "INFISSO"); osc = _oscurante(tipo)
    x, y = f(0.02); out.append(box(x, y, z, w + 0.10, 0.04, h + 0.08, rot, tel))           # telaio (sporge 4 cm)
    x, y = f(0.035); out.append(box(x, y, z + 0.06, w - 0.06, 0.02, h - 0.06, rot, "VETRO")) # vetro
    if not porta:
        x, y = f(0.06); out.append(box(x, y, z - 0.05, w + 0.16, 0.14, 0.05, rot, "DAVANZALE"))
    if osc == "persiane":
        ux, uy = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for sg in (-1, 1):
            px, py = f(0.06)
            out.append(box(px + ux * sg * (w / 2 + w / 4 + 0.04), py + uy * sg * (w / 2 + w / 4 + 0.04), z, w / 2, 0.03, h,
                           rot, tipo.get("mat_oscurante", "PERSIANA")))
    elif osc != "nessuno":
        x, y = f(0.045); out.append(box(x, y, z + h * 0.55, w - 0.04, 0.02, h * 0.45, rot, tipo.get("mat_oscurante", "AVVOLGIBILE")))
        x, y = f(0.05); out.append(box(x, y, z + h + 0.02, w + 0.10, 0.08, 0.18, rot, "CASSONETTO"))
def _tratti(pts, zs):
    for (a_, b_), (za, zb_) in zip(zip(pts, pts[1:]), zip(zs, zs[1:])):
        L_ = math.dist(a_[:2], b_[:2])
        if L_ > 0.05: yield a_, b_, za, zb_, L_, math.degrees(math.atan2(b_[1]-a_[1], b_[0]-a_[0]))
def ringhiera(out, pts, zs, h, mat, passo_bacchette=0.12, passo_montanti=2.0):
    """ringhiera a bacchette: corrimano e traverso basso, bacchette verticali, montanti."""
    for a_, b_, za, zb_, L_, rot in _tratti(pts, zs):
        z0 = min(za, zb_); mx_, my_ = (a_[0]+b_[0])/2, (a_[1]+b_[1])/2
        out.append(box(mx_, my_, z0 + h - 0.04, L_, 0.05, 0.04, rot, mat))
        out.append(box(mx_, my_, z0 + 0.08, L_, 0.03, 0.03, rot, mat))
        n_ = max(1, int(L_ / passo_bacchette))
        for k in range(n_):
            t = (k + 0.5) / n_
            out.append(box(a_[0] + (b_[0]-a_[0])*t, a_[1] + (b_[1]-a_[1])*t, z0 + 0.08, 0.018, 0.018, h - 0.12, rot, mat))
        m_ = max(1, int(L_ / passo_montanti))
        for k in range(m_ + 1):
            t = k / m_
            out.append(box(a_[0] + (b_[0]-a_[0])*t, a_[1] + (b_[1]-a_[1])*t, z0, 0.05, 0.05, h, rot, mat))
def doghe(out, pts, zs, h, mat, alt_doga=0.12, fuga=0.04):
    for a_, b_, za, zb_, L_, rot in _tratti(pts, zs):
        z0 = min(za, zb_); mx_, my_ = (a_[0]+b_[0])/2, (a_[1]+b_[1])/2
        z = z0 + 0.05
        while z + alt_doga <= z0 + h:
            out.append(box(mx_, my_, z, L_, 0.03, alt_doga, rot, mat)); z += alt_doga + fuga
        for k in range(max(1, int(L_ / 2.0)) + 1):
            t = k / max(1, int(L_ / 2.0))
            out.append(box(a_[0] + (b_[0]-a_[0])*t, a_[1] + (b_[1]-a_[1])*t, z0, 0.06, 0.06, h, rot, mat))
def pannello(out, pts, zs, h, mat):
    for a_, b_, za, zb_, L_, rot in _tratti(pts, zs):
        out.append(box((a_[0]+b_[0])/2, (a_[1]+b_[1])/2, min(za, zb_), L_, 0.03, h, rot, mat))
        for k in range(max(1, int(L_ / 2.5)) + 1):
            t = k / max(1, int(L_ / 2.5))
            out.append(box(a_[0] + (b_[0]-a_[0])*t, a_[1] + (b_[1]-a_[1])*t, min(za, zb_), 0.06, 0.06, h, rot, "C20"))
def dettagli(e, zb, h):
    """finestre e balconi dalle facciate della scheda (orientamento, assi, dimensioni, aggetti); per gli edifici
    senza scheda, una finestra ogni ~3,2 m di facciata per piano. Parapetto sui tetti piani."""
    out = []
    piani = e.get("piani") or max(1, round(e["altezza"] / 3.0))
    hp = max(2.6, e["altezza"] / piani)
    z0 = zb + 0.35                      # piano terra poco sopra il terreno più basso
    LS = lati(e["impronta"])
    fac = e.get("facciate") or []
    spec = []                           # (lato, assi, l, h, balcone_piani)
    if fac:
        for f in fac:
            oris = [ORI[o] for o in str(f.get("orientamento") or "").replace(" ", "").split("/") if o in ORI]
            if not oris: continue
            cand = [s for s in LS if min(_dang(s["ang"], o) for o in oris) <= 50 and s["L"] >= 2.0]
            if not cand: continue
            ap = f.get("aperture") or {}
            tipo = (ap.get("tipo") or [{}])[0]
            wl, wh = tipo.get("l_m", 1.0), tipo.get("h_m", 1.3)
            assi_tot = ap.get("assi") or max(1, int(sum(s["L"] for s in cand) / 3.2))
            agg = (f.get("aggetti") or "").lower()
            bal = None
            if f.get("balconi_piani") is not None:      # rilievo strutturato: piani con balcone su questo fronte
                bal = list(f["balconi_piani"])
            elif "balcon" in agg or "terrazz" in agg:
                import re as _re2
                m = _re2.search(r"(\d)\s*\S?\s*piano", agg)
                bal = [int(m.group(1))] if m else list(range(1, piani))
            Ltot = sum(s["L"] for s in cand)
            for s in cand:
                spec.append((s, max(1, round(assi_tot * s["L"] / Ltot)), wl, wh, bal, f.get("balcone_frazione", 0.6),
                         {**tipo, **{k: f[k] for k in ("mat_telaio", "mat_oscurante") if k in f},
                          "_oscurante_default": e.get("_osc", "avvolgibile")}))
        visti = {id(x[0]) for x in spec}
        for s in LS:   # gli altri lati: aperture generiche, meno fitte (fronti non rilevati)
            if id(s) not in visti and s["L"] >= 3.0: spec.append((s, max(1, int(s["L"] / 4.0)), 1.0, 1.2, None, 0.6,
                                                                    {"_oscurante_default": e.get("_osc", "avvolgibile")}))
    else:
        for s in LS:
            if s["L"] >= 3.0: spec.append((s, max(1, int(s["L"] / 3.2)), 1.0, 1.25, None, 0.6,
                                           {"_oscurante_default": e.get("_osc", "avvolgibile")}))
    for s, assi, wl, wh, bal, frz, tinfo in spec:
        (ax, ay), (bx, by) = s["a"], s["b"]; nx, ny = s["n"]
        rot = math.degrees(math.atan2(by - ay, bx - ax))
        assi = min(assi, max(1, int(s["L"] / (wl + 0.6))))
        for k in range(piani):
            zf = z0 + k * hp
            for i in range(assi):
                t = (i + 0.5) / assi
                cx, cy = ax + (bx - ax) * t + nx * 0.03, ay + (by - ay) * t + ny * 0.03
                cx0, cy0 = ax + (bx - ax) * t, ay + (by - ay) * t
                if k == 0 and fac and i == assi // 2 and s is spec[0][0]:
                    finestra(out, cx0, cy0, zf - 0.3, 1.0, 2.3, rot, (nx, ny), {"mat_telaio": "PORTONCINO", "oscurante": "nessuno",
                             "_oscurante_default": "nessuno"}, porta=True); continue
                finestra(out, cx0, cy0, zf + 0.9, wl, wh, rot, (nx, ny), tinfo)
            if bal and k in bal and s["L"] >= 3.0:
                lb = s["L"] * frz if frz != 0.6 else min(s["L"] * 0.6, max(2.5, assi * 2.2)); dp = 1.2
                mx_, my_ = (ax + bx) / 2 + nx * dp / 2, (ay + by) / 2 + ny * dp / 2
                out.append(box(mx_, my_, zf - 0.15, lb, dp, 0.15, rot, e["materiale"]))
                ux, uy = (bx - ax) / s["L"], (by - ay) / s["L"]
                ex, ey = (ax + bx) / 2 + nx * (dp - 0.03), (ay + by) / 2 + ny * (dp - 0.03)
                pa_, pb_ = (ex - ux * lb / 2, ey - uy * lb / 2), (ex + ux * lb / 2, ey + uy * lb / 2)
                ringhiera(out, [pa_, pb_], [zf, zf], 1.0, e.get("mat_ringhiera", "C06"))
                for sg in (-1, 1):
                    sx, sy = (ax + bx) / 2 + ux * sg * lb / 2, (ay + by) / 2 + uy * sg * lb / 2
                    ringhiera(out, [(sx, sy), (sx + nx * dp, sy + ny * dp)], [zf, zf], 1.0, e.get("mat_ringhiera", "C06"))
    if not e.get("_falde"):   # tetto piano: parapetto lungo tutto il perimetro
        for s in LS:
            (ax, ay), (bx, by) = s["a"], s["b"]; nx, ny = s["n"]
            rot = math.degrees(math.atan2(by - ay, bx - ax))
            out.append(box((ax + bx) / 2 - nx * 0.1, (ay + by) / 2 - ny * 0.1, zb + h, s["L"], 0.2, 0.6, rot, e["materiale"]))
    return out
def fotovoltaico(e, zb, h, tt):
    """pannelli: sulle falde rivolte a sud (sottoinsieme dei triangoli del tetto alzato di 7 cm, lontano dal bordo);
    sui tetti piani, file di pannelli inclinati verso sud."""
    P = Polygon(e["impronta"]).buffer(0)
    MW, ML = 1.02, 1.72                      # modulo standard (m): lato lungo lungo la pendenza
    out = []
    if tt:
        # falde = triangoli con la stessa normale; moduli rettangolari in griglia sulle falde rivolte a S/SE/SO
        V = tt["vertici"]; falde = {}
        for a_, b_, c_ in tt["triangoli"]:
            pa, pb, pc = V[a_], V[b_], V[c_]
            ux, uy, uz = pb[0]-pa[0], pb[1]-pa[1], pb[2]-pa[2]; vx, vy, vz = pc[0]-pa[0], pc[1]-pa[1], pc[2]-pa[2]
            nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx; nn = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
            nx, ny, nz = nx/nn, ny/nn, nz/nn
            hh_ = math.hypot(nx, ny)
            if nz > 0.995 or hh_ < 1e-6 or ny / hh_ > -0.5: continue      # falde rivolte a S (±60°)
            k_ = (round(nx, 1), round(ny, 1))
            falde.setdefault(k_, {"n": (nx, ny, nz), "p0": pa, "tri": []})["tri"].append(Polygon([pa[:2], pb[:2], pc[:2]]))
        for k_, F in falde.items():
          for poly_f in getattr(unary_union(F["tri"]).buffer(0.02).buffer(-0.37, join_style=2), "geoms",
                                [unary_union(F["tri"]).buffer(0.02).buffer(-0.37, join_style=2)]):
            if poly_f.is_empty or poly_f.geom_type != "Polygon" or poly_f.area < 3: continue
            nx, ny, nz = F["n"]; hh = math.hypot(nx, ny)
            dx, dy = nx / hh, ny / hh                     # verso valle (orizzontale)
            ax_, ay_ = -dy, dx                            # lungo la linea di gronda
            incl = math.degrees(math.atan2(hh, nz))
            Lp = ML * math.cos(math.radians(incl))        # proiezione orizzontale del modulo
            px0, py0, pz0 = F["p0"]
            def zpl(x, y): return pz0 - (nx * (x - px0) + ny * (y - py0)) / nz
            c0 = poly_f.centroid; cs = list(poly_f.exterior.coords) if poly_f.geom_type == "Polygon" else []
            if not cs: continue
            us = [(q[0]-c0.x)*ax_ + (q[1]-c0.y)*ay_ for q in cs]; vs_ = [(q[0]-c0.x)*dx + (q[1]-c0.y)*dy for q in cs]
            u = min(us) + MW / 2
            while u <= max(us) - MW / 2:
                v = min(vs_) + Lp / 2
                while v <= max(vs_) - Lp / 2:
                    x, y = c0.x + ax_ * u + dx * v, c0.y + ay_ * u + dy * v
                    rect = Polygon([(x + ax_*su*MW/2 + dx*sv*Lp/2, y + ay_*su*MW/2 + dy*sv*Lp/2)
                                    for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
                    if poly_f.contains(rect):
                        rot = math.degrees(math.atan2(-dy, -dx)) - 90   # +y locale verso monte
                        out.append(box(x, y, zpl(x, y) + 0.08 - ML / 2 * math.sin(math.radians(incl)), MW, ML, 0.04,
                                       rot, "FV", incl=incl))
                    v += Lp + 0.02
                u += MW + 0.02
        return {"pannelli": out} if out else None
    dentro = P.buffer(-1.2)
    if dentro.is_empty: return None
    x0, y0, x1, y1 = dentro.bounds; y = y0 + 0.8
    while y < y1 - 0.8:                        # tetto piano: file di moduli inclinati di 20° verso sud
        x = x0 + MW / 2
        while x < x1 - MW / 2:
            rect = Polygon([(x - MW/2, y - 0.8), (x + MW/2, y - 0.8), (x + MW/2, y + 0.8), (x - MW/2, y + 0.8)])
            if dentro.contains(rect): out.append(box(x, y, zb + h + 0.3, MW, ML, 0.04, 0, "FV", incl=20))
            x += MW + 0.02
        y += 2.6
    return {"pannelli": out} if out else None

edifici = []
for e in sc["edifici"]:
    imp = e["impronta"]
    zs = [S.trend(x, y) for x, y in imp]
    zb = min(zs) - 0.05
    piat = PIATT.get(e["id"], 0.0)
    h = e["altezza"] - piat + (max(zs) - min(zs)) * 0.5
    ed = {"nome": e["nome"], "tag": "10_Edifici", "impronta": [[R(x), R(y)] for x, y in imp],
          "z_base": R(zb), "altezza": R(h), "materiale": e["materiale"],
          "materiale_copertura": e.get("manto") or e["materiale"], "lod": e["lod"]}
    colmo = e.get("colmo")
    f_ = (e.get("copertura") or "").lower()
    if not ("padiglione" in f_ or "capanna" in f_ or "falda" in f_):   # tetto piano: la gronda di scheda è la cima del parapetto
        h = max(2.5, h - 0.6); ed["altezza"] = R(h)
    tt = tetto(imp, zb + h, e.get("copertura"), e.get("pendenza_pct"),
               (colmo - e["altezza"]) if colmo else None, (e.get("sporto_cm") or 0) / 100.0)
    if tt: ed["tetto"] = tt
    e["_falde"] = bool(tt)
    e["_osc"] = e.get("oscurante_default") or "avvolgibile"
    ed["elementi"] = dettagli(e, zb, h)
    if e.get("fotovoltaico"):
        fv = fotovoltaico(e, zb, h, tt)
        if fv and "pannelli" in fv: ed["elementi"] += fv["pannelli"]
        elif fv: ed["fotovoltaico"] = fv
    edifici.append(ed)
    for v in e.get("volumi", []):   # volumi alti (torrette) sopra il tetto, con la loro copertura
        Pq = Polygon(imp); c = Pq.centroid if v.get("posizione", "centro") == "centro" else Point(*v["posizione"])
        mr = list(Pq.minimum_rotated_rectangle.exterior.coords)
        ang = math.atan2(mr[1][1] - mr[0][1], mr[1][0] - mr[0][0]); lx, ly = v.get("lati_m", [4.0, 4.0])
        ca, sa = math.cos(ang), math.sin(ang)
        sq = [(c.x + ca*dx - sa*dy, c.y + sa*dx + ca*dy) for dx, dy in [(-lx/2, -ly/2), (lx/2, -ly/2), (lx/2, ly/2), (-lx/2, ly/2)]]
        hv = v.get("altezza_extra", 3.0) + ((colmo - e["altezza"]) if colmo else 0)
        ev = {"nome": f"{e['nome']} – {v.get('nome', 'volume alto')}", "tag": "10_Edifici",
              "impronta": [[R(x), R(y)] for x, y in sq], "z_base": R(zb + h), "altezza": R(hv), "materiale": e["materiale"],
              "materiale_copertura": e.get("manto") or e["materiale"], "lod": 2}
        tv = tetto(sq, zb + h + hv, v.get("copertura", e.get("copertura")), v.get("pendenza_pct", e.get("pendenza_pct")), None,
                   (e.get("sporto_cm") or 0) / 100.0)
        if tv: ev["tetto"] = tv
        ev["elementi"] = [x for x in dettagli({**e, "impronta": sq, "altezza": hv, "piani": max(1, round(hv / 3)),
                                               "facciate": [], "_falde": bool(tv)}, zb + h, hv)]
        edifici.append(ev)

# ---------------------------------------------------------------- arredo e vegetazione
oggetti = []
for a in sc["arredo"]:
    w, d = a.get("dim", [0.3, 0.3] if "pilastr" in a["tipo"] else ([0.12, 0.12] if a["tipo"] == "lampione" else [0.06, 0.06]))
    oggetti.append({"nome": f"{a['id']} – {a['tipo']}", "tag": "30_Arredo" if a["id"].startswith("A") else "20_Recinzioni",
                    "xy": [R(a["xy"][0]), R(a["xy"][1])], "z": R(S.trend(*a["xy"]) + S.MARC - 0.05),
                    "dim": [w, d, R(a["h"] + 0.05)], "materiale": a["materiale"],
                    "rot_deg": a.get("rot_deg", 0.0),
                    "testa": "lampione" if a["tipo"] == "lampione" else ("disco" if "cartello" in a["tipo"] else None)})
vegetazione = []
dettagli = []   # scatole libere (segnaletica, siepi, canneti, recinzioni, cancelli): formato degli elementi degli edifici
MAT_DETT = {"ringhiera": None, "doghe": None, "grigliato": "GRIGLIATO", "telo": "TELO_VERDE"}
recinzioni_dett = []
for r in sc["recinzioni"]:
    if r["tipo"] not in ("ringhiera", "doghe", "grigliato", "telo"): continue
    pts = [p[:2] for p in r["punti"]]; zs = [p[2] for p in r["punti"]]
    if r["tipo"] == "ringhiera": ringhiera(dettagli, pts, zs, r["altezza"], r["materiale"])
    elif r["tipo"] == "doghe": doghe(dettagli, pts, zs, r["altezza"], r["materiale"])
    else: pannello(dettagli, pts, zs, r["altezza"], MAT_DETT[r["tipo"]])
# pilastri e copertine sui muri su strada
for m in sc["muri"]:
    if not m.get("su_strada"): continue
    pts, zt = m["punti"], m["z_sommita"]; ns_ = m["normali_interno"]
    if m.get("copertina", True):
        for (a_, b_, za, zb_, L_, rot), n_ in zip(_tratti(pts, zt), ns_):
            cx, cy = (a_[0]+b_[0])/2 + n_[0]*SP/2, (a_[1]+b_[1])/2 + n_[1]*SP/2
            dettagli.append(box(cx, cy, min(za, zb_) - 0.01, L_ + 0.02, SP + 0.06, 0.06, rot, "COPERTINA"))
    pp = m.get("pilastri_passo")
    if pp:
        acc, prossimo = 0.0, 0.0
        for (a_, b_, za, zb_, L_, rot), n_ in zip(_tratti(pts, zt), ns_):
            while prossimo <= acc + L_:
                t = (prossimo - acc) / L_; x = a_[0] + (b_[0]-a_[0])*t + n_[0]*SP/2; y = a_[1] + (b_[1]-a_[1])*t + n_[1]*SP/2
                zt_ = za + (zb_ - za) * t; zb0 = S.trend(x, y) - 0.1
                dettagli.append(box(x, y, zb0, 0.38, 0.38, zt_ - zb0 + 0.12, rot, m["materiale"]))
                prossimo += pp
            acc += L_
# cancelli: ante (sbarre, doghe o pieno), pilastri ai lati, pensilina in coppi per i pedonali che la hanno
for c_ in sc.get("cancelli", []):
    (ax, ay), (bx, by) = c_["punti"]; L_ = math.dist((ax, ay), (bx, by)); rot = math.degrees(math.atan2(by-ay, bx-ax))
    nx_, ny_ = c_["normale"]; z0 = c_["z"]; h = c_["h"]
    mx_, my_ = (ax+bx)/2 + nx_*SP/2, (ay+by)/2 + ny_*SP/2
    pts = [(ax + nx_*SP/2, ay + ny_*SP/2), (bx + nx_*SP/2, by + ny_*SP/2)]
    if c_["stile"] == "doghe": doghe(dettagli, pts, [z0 + 0.05, z0 + 0.05], h, c_["materiale"], alt_doga=0.14, fuga=0.02)
    elif c_["stile"] == "pieno": pannello(dettagli, pts, [z0 + 0.05, z0 + 0.05], h, c_["materiale"])
    else: ringhiera(dettagli, pts, [z0 + 0.05, z0 + 0.05], h, c_["materiale"], passo_bacchette=0.11, passo_montanti=L_ / 2)
    for sg in (-1, 1):
        dettagli.append(box(mx_ + math.cos(math.radians(rot))*sg*(L_/2 + 0.2), my_ + math.sin(math.radians(rot))*sg*(L_/2 + 0.2),
                            z0 - 0.05, 0.4, 0.4, h + 0.35, rot, c_.get("mat_pilastri", "C04")))
    if c_.get("pensilina"):
        dettagli.append(box(mx_, my_, z0 + h + 0.3, L_ + 0.9, 1.1, 0.12, rot, "C03"))
for v in L.get("vegetazione", []):
    if not v.get("nel_contesto", True): continue
    vs_ = [vv for vv in sc["vegetazione"] if vv["id"] == v["id"]][0]
    forma = v.get("forma", "palma")
    if forma == "siepe":   # siepi sulla sommità dei muri indicati
        for m in sc["muri"]:
            if m["id"] not in v.get("su_muri", []): continue
            for (a_, b_, za, zb_) in zip(m["punti"], m["punti"][1:], m["z_sommita"], m["z_sommita"][1:]):
                L_ = math.dist(a_, b_)
                if L_ < 0.2: continue
                dettagli.append(box((a_[0]+b_[0])/2, (a_[1]+b_[1])/2, min(za, zb_), L_ + 0.1, 0.45, v.get("h", 0.6),
                                    math.degrees(math.atan2(b_[1]-a_[1], b_[0]-a_[0])), "SIEPE"))
        continue
    if forma == "canneto":  # fascia di canne lungo il lato interno del muro indicato
        lmax, fatto = v.get("lunghezza_max_m", 1e9), 0.0
        for m in sc["muri"]:
            if m["id"] != v.get("dietro_muro"): continue
            for p_, n_, (a_, b_) in zip(m["punti"], m["normali_interno"], zip(m["punti"], m["punti"][1:])):
                fatto += math.dist(a_, b_)
                if fatto > lmax: break
                cx, cy = (a_[0]+b_[0])/2 + n_[0]*1.0, (a_[1]+b_[1])/2 + n_[1]*1.0
                dettagli.append(box(cx, cy, S.trend(cx, cy), math.dist(a_, b_) + 0.2, 1.4, v.get("h", 3.5),
                                    math.degrees(math.atan2(b_[1]-a_[1], b_[0]-a_[0])), "CANNETO"))
        continue
    punti = vs_.get("xy_lista") if vs_.get("xy_lista") else ([vs_["xy"]] if "xy" in vs_ else [])
    for k_, (x, y) in enumerate(punti):
        vegetazione.append({"nome": v.get("nome", f"{v['id']} – {v['tipo']}") + (f" {k_+1}" if len(punti) > 1 else ""),
                            "tag": "50_Vegetazione", "xy": [R(x), R(y)], "forma": forma,
                            "z": R(z_lotto2(x, y) if v.get("su_lotto") else S.trend(x, y)), "h": v["h"],
                            "chioma": v.get("chioma", 3.0), "fusto": v.get("fusto", 0.0),
                            "materiale": v.get("materiale", "C27")})

# ---------------------------------------------------------------- lampioni lungo i marciapiedi (passo di scheda, sfalsati)
def _verso_strada(x, y):
    """normale verso la carreggiata e tangente del bordo strada più vicino al punto (x, y)."""
    bd = S.carreggiata.boundary; s_ = bd.project(Point(x, y))
    q = bd.interpolate(s_); q2 = bd.interpolate(s_ + 0.5); q1 = bd.interpolate(max(0, s_ - 0.5))
    tx, ty = q2.x - q1.x, q2.y - q1.y; Lt = math.hypot(tx, ty) or 1.0; tx, ty = tx / Lt, ty / Lt
    nx, ny = q.x - x, q.y - y; Ln = math.hypot(nx, ny) or 1.0
    return (nx / Ln, ny / Ln), (tx, ty)
LP = L.get("lampioni")
if LP:
    bd = S.carreggiata.boundary; cnt_ = 0
    for k_, ln in enumerate(getattr(bd, "geoms", [bd])):
        if ln.length < LP.get("passo_m", 27) * 0.6: continue
        s_ = (LP.get("passo_m", 27) / 2.0) * (k_ % 2) + 3.0
        while s_ < ln.length - 2.0:
            q = ln.interpolate(s_); q2 = ln.interpolate(min(ln.length, s_ + 0.5))
            dx, dy = q2.x - q.x, q2.y - q.y; Ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / Ln, dx / Ln
            if S.carreggiata.contains(Point(q.x + nx * 0.3, q.y + ny * 0.3)): nx, ny = -nx, -ny   # verso il marciapiede
            x, y = q.x + nx * LP.get("dal_cordolo_m", 0.5), q.y + ny * LP.get("dal_cordolo_m", 0.5)
            if S.marciapiedi.buffer(0.1).contains(Point(x, y)) and S.area.buffer(-3).contains(Point(x, y)):
                cnt_ += 1
                oggetti.append({"nome": f"A01 – lampione {cnt_}", "tag": "30_Arredo", "xy": [R(x), R(y)],
                                "z": R(S.z_marc(x, y) - 0.05), "dim": [0.14, 0.14, R(LP.get("h", 8.0))],
                                "materiale": LP.get("materiale", "C20"),
                                "rot_deg": round(math.degrees(math.atan2(-ny, -nx)), 1), "testa": "lampione",
                                "lampione": {"h": LP.get("h", 8.0), "d_base": LP.get("d_base_m", 0.16), "d_cima": LP.get("d_cima_m", 0.08),
                                             "sbraccio": LP.get("sbraccio_m", 0.6), "armatura": LP.get("armatura", [0.7, 0.3, 0.12]),
                                             "plinto": LP.get("plinto", [0.35, 0.35, 0.25])}})
            s_ += LP.get("passo_m", 27)
# i lampioni descritti in arredo (posizioni rilevate) usano la stessa forma
for o in oggetti:
    if o.get("testa") == "lampione" and "lampione" not in o and LP:
        (nx, ny), _ = _verso_strada(*o["xy"])
        o["rot_deg"] = round(math.degrees(math.atan2(ny, nx)), 1)
        o["lampione"] = {"h": o["dim"][2], "d_base": LP.get("d_base_m", 0.16), "d_cima": LP.get("d_cima_m", 0.08),
                         "sbraccio": LP.get("sbraccio_m", 0.6), "armatura": LP.get("armatura", [0.7, 0.3, 0.12]),
                         "plinto": LP.get("plinto", [0.35, 0.35, 0.25])}

# ---------------------------------------------------------------- segnaletica orizzontale: mezzeria, margini, strisce pedonali
SG = L.get("segnaletica_stradale")
incroci, assi_n = [], {}
if SG:
    for f in json.load(open(S.P_(S.DB["assi"]), encoding="utf-8"))["features"] if S.DB.get("assi") else []:
        for l in f["geometry"]["coordinates"]:
            assi_n.setdefault(f["properties"].get("nome") or "?", []).append(LineString([S.loc(q[0], q[1]) for q in l]))
    tutti = [ln for v_ in assi_n.values() for ln in v_]
    nodi = [Point(c) for ln in tutti for c in (ln.coords[0], ln.coords[-1])]
    incroci = [p for p in nodi if sum(1 for q in nodi if q.distance(p) < 1.0) >= 3]
    def zs(x, y): return S.z_strada(x, y) + 0.012
    W_ = SG.get("larghezza_linee_m", 0.12)
    if SG.get("mezzeria", True):
        T_, I_ = SG.get("mezzeria_tratto_m", 3.0), SG.get("mezzeria_intervallo_m", 4.5)
        for ln in tutti:
            ln = ln.intersection(carr.buffer(-1.0))
            for part in getattr(ln, "geoms", [ln]):
                if part.is_empty or part.geom_type != "LineString": continue
                s_ = 0.0
                while s_ + T_ < part.length:
                    a_, b_ = part.interpolate(s_), part.interpolate(s_ + T_)
                    m_ = Point((a_.x+b_.x)/2, (a_.y+b_.y)/2)
                    if all(m_.distance(i_) > SG.get("mezzeria_stop_incrocio_m", 10) for i_ in incroci):
                        dettagli.append(box(m_.x, m_.y, zs(m_.x, m_.y), T_, W_, 0.01,
                                            math.degrees(math.atan2(b_.y-a_.y, b_.x-a_.x)), "SEGNALETICA"))
                    s_ += T_ + I_
    if SG.get("margini", False):   # linee di margine continue, a 0,3 m dal cordolo, interrotte agli incroci
        off = SG.get("margine_dal_cordolo_m", 0.3)
        anello = carr.buffer(-off - W_ / 2).boundary
        for part in getattr(anello, "geoms", [anello]):
            L_ = part.length; s_ = 0.0
            while s_ < L_:
                a_, b_ = part.interpolate(s_), part.interpolate(min(L_, s_ + 1.0))
                m_ = Point((a_.x+b_.x)/2, (a_.y+b_.y)/2)
                if all(m_.distance(i_) > SG.get("margine_stop_incrocio_m", 12) for i_ in incroci) and S.area.buffer(-1).contains(m_):
                    dettagli.append(box(m_.x, m_.y, zs(m_.x, m_.y), math.dist((a_.x, a_.y), (b_.x, b_.y)) + 0.02, W_, 0.01,
                                        math.degrees(math.atan2(b_.y-a_.y, b_.x-a_.x)), "SEGNALETICA"))
                s_ += 1.0
    CARD = {"N": 90, "NE": 45, "E": 0, "SE": -45, "S": -90, "SO": -135, "O": 180, "NO": 135}
    strisce_fatte = []
    for sp in SG.get("strisce_pedonali", []):
        for ln in assi_n.get(sp["strada"], []):
            for estremo, verso in ((ln.coords[0], 1), (ln.coords[-1], -1)):
                if not any(Point(estremo).distance(i_) < 1.0 for i_ in incroci): continue
                if sp.get("incrocio") and Point(estremo).distance(Point(sp["incrocio"])) > 4.0: continue   # solo l'incrocio rilevato
                d0 = sp.get("distanza_incrocio_m", SG.get("distanza_incrocio_m", 6.0)); s0 = d0 if verso == 1 else ln.length - d0
                if not (0 < s0 < ln.length): continue
                c_ = ln.interpolate(s0); c2 = ln.interpolate(min(ln.length, s0 + 0.5) if verso == 1 else max(0, s0 - 0.5))
                if sp.get("lato"):   # solo il ramo che dall'incrocio va verso il lato indicato
                    ang = math.degrees(math.atan2(c_.y - estremo[1], c_.x - estremo[0]))
                    if abs((ang - CARD[sp["lato"]] + 180) % 360 - 180) > 50: continue
                ux, uy = c2.x - c_.x, c2.y - c_.y; Lu = math.hypot(ux, uy) or 1.0; ux, uy = ux/Lu, uy/Lu
                trasv = LineString([(c_.x - uy*12, c_.y + ux*12), (c_.x + uy*12, c_.y - ux*12)]).intersection(carr)
                for tr in getattr(trasv, "geoms", [trasv]):
                    if tr.is_empty or tr.geom_type != "LineString" or not tr.buffer(0.5).intersects(c_.buffer(0.5)): continue
                    if any(tr.centroid.distance(t0.centroid) < 2.0 for t0, _ in strisce_fatte): continue   # assi DBGT doppi
                    s_ = 0.5
                    while s_ < tr.length - 0.5:
                        p_ = tr.interpolate(s_)
                        dettagli.append(box(p_.x, p_.y, zs(p_.x, p_.y), sp.get("profondita_m", 2.5), 0.5, 0.01,
                                            math.degrees(math.atan2(uy, ux)), "SEGNALETICA"))
                        s_ += 1.0
                    strisce_fatte.append((tr, (ux, uy)))

# ---------------------------------------------------------------- segnaletica verticale (cartelli rilevati + attraversamenti)
SEGNALI = {
    "divieto_sosta": {"forma": "tondo", "d": 0.6, "bordo": "SEGN_ROSSO", "campo": "SEGN_BLU", "simbolo": "diagonale"},
    "divieto_fermata": {"forma": "tondo", "d": 0.6, "bordo": "SEGN_ROSSO", "campo": "SEGN_BLU", "simbolo": "croce"},
    "senso_vietato": {"forma": "tondo", "d": 0.6, "bordo": "SEGN_ROSSO", "campo": "SEGN_ROSSO", "simbolo": "barra"},
    "attraversamento_pedonale": {"forma": "quadro", "d": 0.6, "bordo": "SEGN_BIANCO", "campo": "SEGN_BLU", "simbolo": "triangolo"},
    "dare_precedenza": {"forma": "triangolo_giu", "d": 0.9, "bordo": "SEGN_ROSSO", "campo": "SEGN_BIANCO", "simbolo": None},
    "frecce_direzione": {"forma": "freccia", "d": [1.0, 0.25], "bordo": "SEGN_BIANCO", "campo": "SEGN_BLU", "simbolo": None},
    "nome_via": {"forma": "rettangolo", "d": [0.7, 0.25], "bordo": "SEGN_BLU", "campo": "SEGN_BIANCO", "simbolo": None, "parallelo": True},
}
def sul_marciapiede(x, y, dal_cordolo=0.4):
    """porta un punto di arredo sul marciapiede: se cade in carreggiata (o troppo vicino al cordolo) lo sposta
    sul bordo strada più vicino, a `dal_cordolo` metri verso l'esterno."""
    p_ = Point(x, y)
    if not S.carreggiata.buffer(dal_cordolo - 0.05).contains(p_): return x, y
    bd = S.carreggiata.boundary; q = bd.interpolate(bd.project(p_))
    q2 = bd.interpolate(bd.project(p_) + 0.5); tx, ty = q2.x - q.x, q2.y - q.y; Lt = math.hypot(tx, ty) or 1.0
    nx, ny = -ty / Lt, tx / Lt
    if S.carreggiata.contains(Point(q.x + nx * 0.2, q.y + ny * 0.2)): nx, ny = -nx, -ny
    return q.x + nx * dal_cordolo, q.y + ny * dal_cordolo
def cartello(nome, x, y, tipo, h=None, pannello=None, verso=None):
    x, y = sul_marciapiede(x, y)
    sp = dict(SEGNALI[tipo]); (nx, ny), (tx, ty) = _verso_strada(x, y)
    if sp.pop("parallelo", False): rot = math.degrees(math.atan2(ty, tx))            # targa parallela alla strada
    else: rot = math.degrees(math.atan2(ty * (verso or 1), tx * (verso or 1)))         # piastra di fronte al traffico
    o = {"nome": nome, "tag": "30_Arredo", "xy": [R(x), R(y)], "z": R(S.z_marc(x, y) - 0.05),
         "dim": [0.06, 0.06, R(h or (2.6 if sp["forma"] != "rettangolo" else 2.4))], "materiale": "C20",
         "rot_deg": round(rot - 90, 1), "testa": "segnale", "segnale": sp}
    if pannello: o["segnale"]["pannello"] = pannello
    oggetti.append(o)
for k_, sv in enumerate(L.get("segnaletica_verticale", [])):
    pos = S.posiziona(sv)
    if not pos: continue
    cartello(f"A02 – {sv['tipo'].replace('_', ' ')} {k_+1}", pos[0], pos[1], sv["tipo"], sv.get("h"), sv.get("pannello"), sv.get("verso"))
if SG and SG.get("cartelli_attraversamento", True):
    for tr, (ux, uy) in strisce_fatte:     # un cartello su ciascun marciapiede, ai due capi delle strisce
        for q in (tr.coords[0], tr.coords[-1]):
            px, py = q[0] - ux * 1.4, q[1] - uy * 1.4      # 1,4 m prima delle strisce, poi sul marciapiede
            cartello("A02 – attraversamento pedonale", px, py, "attraversamento_pedonale")

# ---------------------------------------------------------------- materiali (+ texture a scacchiera per P02)
pal = {p["id"]: p for p in scheda["palette"]}
def nome_mat(cid):
    p = pal[cid]; slug = "".join(ch if ch.isalnum() else "_" for ch in p["materiale"].lower())[:20].strip("_")
    return f"{cid}_{slug}"
usati = set()
for s in out_sup: usati |= set(s["materiali"])
for m in muri: usati.add(m["materiale"])
for e in edifici: usati |= {e["materiale"], e["materiale_copertura"]}
for o in oggetti: usati.add(o["materiale"])
for e in edifici: usati |= {x["materiale"] for x in e.get("elementi", []) if x["materiale"] in pal}
usati |= {x["materiale"] for x in dettagli if x["materiale"] in pal}
TX = ST.get("texture_marciapiede")
if TX: usati.add(TX["alternato"])
for v in vegetazione: usati.add(v["materiale"])
os.makedirs(os.path.join(HERE, "texture"), exist_ok=True)
def hexrgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
if TX:   # texture a scacchiera del marciapiede
    TXF = f"texture/{TX['materiale']}_marmette_scacchiera.png"
    tex = Image.new("RGB", (160, 160)); px = tex.load()
    for i in range(160):
        for j in range(160):
            c = pal[TX["materiale"]]["hex"] if ((i // 80) + (j // 80)) % 2 == 0 else pal[TX["alternato"]]["hex"]
            px[i, j] = hexrgb(c)
    tex.save(os.path.join(HERE, TXF))
materiali = {}
for cid in sorted(usati):
    m = {"hex": pal[cid]["hex"]}
    if TX and cid == TX["materiale"]:
        m = {"hex": pal[cid]["hex"], "texture": TXF, "modulo_mm": TX.get("modulo_mm", [800, 800])}
    materiali[nome_mat(cid)] = m
for tipo, (pid, rid) in MAT_REC.items():
    if any(r["materiale_palo"] == f"{pid}_paletti_{tipo}" for r in recinzioni):
        materiali[f"{pid}_paletti_{tipo}"] = {"hex": pal[pid]["hex"]}
        materiali[rid] = {"hex": pal[pid]["hex"], "alpha": {"rete": 0.25, "ringhiera": 0.45, "doghe": 0.85}[tipo]}
materiali.update({"SEGN_ROSSO": {"hex": "#C0272D"}, "SEGN_BLU": {"hex": "#1F4E9E"}, "SEGN_BIANCO": {"hex": "#F4F4F2"},
                  "PALO_LUCE": {"hex": "#A9AEB1"}, "ARMATURA": {"hex": "#5E6366"}, "PLINTO": {"hex": "#9C9890"},
                  "INFISSO": {"hex": "#F2F1EC"}, "DAVANZALE": {"hex": "#E4DED2"}, "PERSIANA": {"hex": "#6B4A2E"},
                  "AVVOLGIBILE": {"hex": "#E9E7E2"}, "CASSONETTO": {"hex": "#E2DFD8"}, "COPERTINA": {"hex": "#D9D3C7"},
                  "GRIGLIATO": {"hex": "#B8643A", "alpha": 0.7}, "TELO_VERDE": {"hex": "#2F5A3A", "alpha": 0.9},
                  "PERSIANA_VERDE": {"hex": "#3F5A3C"}, "TELAIO_ROSSO": {"hex": "#A33A2A"}, "TELAIO_GRIGIO": {"hex": "#6E7173"},
                  "SEGNALETICA": {"hex": "#E8E8E4"}, "SIEPE": {"hex": "#4F6B34"}, "CANNETO": {"hex": "#8A8A4E", "alpha": 0.85},
                  "CHIOMA": {"hex": "#556B35"}, "FUSTO": {"hex": "#6B5A48"},
                  "VETRO": {"hex": "#2E3A42"}, "PORTONCINO": {"hex": "#5A4636"},
                  "RINGHIERA": {"hex": "#3C3F41", "alpha": 0.55}, "FV": {"hex": "#1C2A44"}})
def rinomina(c): return nome_mat(c) if c in pal else c
for s in out_sup: s["materiali"] = [rinomina(c) for c in s["materiali"]]
for m in muri: m["materiale"] = rinomina(m["materiale"])
for e in edifici: e["materiale"], e["materiale_copertura"] = rinomina(e["materiale"]), rinomina(e["materiale_copertura"])
for o in oggetti: o["materiale"] = rinomina(o["materiale"])
for e in edifici:
    for x in e.get("elementi", []): x["materiale"] = rinomina(x["materiale"])
for x in dettagli: x["materiale"] = rinomina(x["materiale"])
for v in vegetazione: v["materiale"] = rinomina(v["materiale"])

# ---------------------------------------------------------------- punti di controllo della proiezione
ll_of = S.ll_of
controllo = [{"nome": n, "x": x, "y": y, "lat": round(ll_of(x, y)[0], 9), "lng": round(ll_of(x, y)[1], 9)}
             for n, (x, y) in {f"punta {LT['id']}": tuple(sc["controllo"]["tip_lotto"]),
                                **{k: tuple(v) for k, v in L.get("punti_controllo", {}).items()}}.items()]

# nomi univoci: tratti numerati in modo progressivo per elemento
import re as _re
from collections import defaultdict as _dd
_cnt = _dd(int)
for lst in (muri, recinzioni):
    for it in lst:
        base = _re.sub(r"( tratto \d+)+$", "", it["nome"])
        _cnt[base] += 1
        it["nome"] = f"{base} tratto {_cnt[base]}"
ctx = {"origine": sc["origine"], "applica_allineamento_catasto": False, "controllo": controllo,
       "fonti": sc["fonti"], "materiali": materiali, "superfici": out_sup, "muri": muri, "recinzioni": recinzioni,
       "edifici": edifici, "oggetti": oggetti, "vegetazione": vegetazione, "dettagli": dettagli}
json.dump(ctx, open(os.path.join(HERE, "contesto.json"), "w"), separators=(",", ":"))
nt = sum(len(s["triangoli"]) for s in out_sup)
print(f"superfici {len(out_sup)} ({nt} triangoli), fasce {sum(len(v) for v in fasce.values())}, muri {len(muri)}, "
      f"recinzioni {len(recinzioni)}, edifici {len(edifici)}, oggetti {len(oggetti)}, materiali {len(materiali)}")
