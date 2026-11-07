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
REG = [("P01", carr, ST["materiale_carreggiata"], lambda x, y: S.trend(x, y)),
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
for r in sc["recinzioni"]:
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
def tetto(imp, zg, forma, pend_pct, h_colmo):
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
        ln = LineString([(x0, y0), (x1, y1)]).intersection(P)
        for q in getattr(ln, "geoms", [ln]):
            if q.length > 0.2:
                cc = list(q.coords); a_ = add(cc[0]); b_ = add(cc[-1]); seg.append([a_, b_])
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
    return {"vertici": out_v, "triangoli": out_t, "timpani": timpani}

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
    tt = tetto(imp, zb + h, e.get("copertura"), e.get("pendenza_pct"),
               (colmo - e["altezza"]) if colmo else None)
    if tt: ed["tetto"] = tt
    edifici.append(ed)

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
for v in L.get("vegetazione", []):
    if not v.get("nel_contesto", True) or "xy_lista" in v: continue   # macchie di arbusti: meglio nel render
    x, y = [vv for vv in sc["vegetazione"] if vv["id"] == v["id"]][0]["xy"]
    vegetazione.append({"nome": v.get("nome", f"{v['id']} – {v['tipo']}"), "tag": "50_Vegetazione", "xy": [R(x), R(y)],
                        "z": R(z_lotto2(x, y) if v.get("su_lotto") else S.trend(x, y)), "h": v["h"], "chioma": v["chioma"],
                        "materiale": v.get("materiale", "C27")})

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
def rinomina(c): return nome_mat(c) if c in pal else c
for s in out_sup: s["materiali"] = [rinomina(c) for c in s["materiali"]]
for m in muri: m["materiale"] = rinomina(m["materiale"])
for e in edifici: e["materiale"], e["materiale_copertura"] = rinomina(e["materiale"]), rinomina(e["materiale_copertura"])
for o in oggetti: o["materiale"] = rinomina(o["materiale"])
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
       "edifici": edifici, "oggetti": oggetti, "vegetazione": vegetazione}
json.dump(ctx, open(os.path.join(HERE, "contesto.json"), "w"), separators=(",", ":"))
nt = sum(len(s["triangoli"]) for s in out_sup)
print(f"superfici {len(out_sup)} ({nt} triangoli), fasce {sum(len(v) for v in fasce.values())}, muri {len(muri)}, "
      f"recinzioni {len(recinzioni)}, edifici {len(edifici)}, oggetti {len(oggetti)}, materiali {len(materiali)}")
