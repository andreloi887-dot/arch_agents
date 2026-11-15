"""Arredi degli interni dagli ingombri indicati in planimetria (fase 3 della filiera).

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P arredi_interni.py -- <cartella modello>
  python arredi_interni.py -- <cartella modello> --blend contesto_progetto.blend        (Blender come modulo)

Dopo finiture_interni.py e prima di percorsi_camera.py. Riscrive contesto_progetto.blend; si può rilanciare.
Legge <modello>/arredi.json:
  stile    colori (hex) di legno, laccato, tessuto, tessuto_accento, piano_cucina, metallo, nero, tappeto
  arredi   elenco di pezzi: villa, vano, tipo, anello [[x, y], ...] in coordinate locali del contesto (l'ingombro in pianta)
Tipi: armadio, letto, comodino, madia_tv, scrivania (con sedia), parete_tv, cucina (ingombro a L o a C: basi, piano,
pensili dove non c'è un infisso, piano cottura, lavello, colonna), zona_giorno (senza anello: divano, tavolino e tappeto di
fronte alla parete TV, tavolo con posti_tavolo sedie nel posto libero più ampio).
Regole: il fronte di un mobile è il lato lungo verso il centro della stanza; la testata del letto è il lato corto contro
il muro; ogni pezzo sta sul pavimento del suo vano. Mobili parametrici, fatti di volumi semplici con spigoli smussati:
danno misure e proporzioni giuste; sedute e tessili andranno sostituiti con modelli di libreria per i render finali.
Ogni oggetto porta la proprietà "ingombro" (anello in pianta): percorsi_camera.py la usa per non mettere la camera
dentro i mobili.
"""
import bpy, json, math, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, registro
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

argv, opt = argomenti()
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
if opt("--blend"): bpy.ops.wm.open_mainfile(filepath=os.path.join(USCITA, opt("--blend")))
A = json.load(open(os.path.join(MOD, "arredi.json"), encoding="utf-8"))
log = registro(os.path.join(USCITA, "arredi_interni.log"))
scn = bpy.context.scene
ST = {"legno": "#C8A47A", "laccato": "#EDE7DA", "tessuto": "#D9D0C1", "tessuto_accento": "#B98466", "piano_cucina": "#DAD5CC",
      "metallo": "#3A3632", "nero": "#141414", "tappeto": "#CFC4B2", **A.get("stile", {})}

def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]
RUV = {"legno": 0.45, "laccato": 0.35, "tessuto": 0.95, "tessuto_accento": 0.95, "piano_cucina": 0.3, "metallo": 0.4, "nero": 0.25, "tappeto": 1.0}
MATS = {}
def mat(k):
    if k not in MATS:
        m = bpy.data.materials.get("Arredo " + k) or bpy.data.materials.new("Arredo " + k); m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = lin(ST[k]); b.inputs["Roughness"].default_value = RUV[k]
        b.inputs["Metallic"].default_value = 1.0 if k == "metallo" else 0.0; MATS[k] = m
    return MATS[k]

radice = bpy.data.collections.get("PROGETTO") or scn.collection
ARR = bpy.data.collections.get("PRG_Arredi")
if not ARR: ARR = bpy.data.collections.new("PRG_Arredi"); radice.children.link(ARR)
for o in list(ARR.objects): bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------------------------------------ vani e infissi
vani = []
for ob in scn.objects:
    if "vano" not in ob or ob.type != "MESH": continue
    W = [ob.matrix_world @ v.co for v in ob.data.vertices]; z0 = min(w.z for w in W)
    base = [Polygon([W[i].xy[:] for i in pl.vertices]) for pl in ob.data.polygons if all(W[i].z < z0 + 0.05 for i in pl.vertices)]
    pol = unary_union([q for q in base if q.is_valid and q.area > 1e-6]).buffer(0.01)
    if pol.is_empty: continue
    if pol.geom_type != "Polygon": pol = max(pol.geoms, key=lambda q: q.area)
    vani.append({"nome": ob["vano"], "pol": pol, "z0": z0 + 0.004, "villa": int(ob.get("villa", 1))})
infissi, porte_ = [], []
for ob in scn.objects:
    if ob.get("ifc_classe") in ("IfcWindow", "IfcDoor") and ob.type == "MESH" and ob.data.vertices:
        r_ = MultiPoint([(ob.matrix_world @ v.co).xy[:] for v in ob.data.vertices]).minimum_rotated_rectangle
        if r_.geom_type != "Polygon" or r_.length > 14: continue          # cancelli e recinzioni non contano
        infissi.append(r_)
        if ob["ifc_classe"] == "IfcDoor": porte_.append(r_)
INF = unary_union(infissi) if infissi else Polygon()
PORTE = unary_union(porte_) if porte_ else Polygon()

# ------------------------------------------------------------------------------------------------ costruzione
class Pezzo:
    """un mobile: volumi rigidi (spigolo smussato 4 mm) e volumi morbidi (cuscini, materassi: smusso largo)."""
    def __init__(s, o, u, v, z0): s.o, s.u, s.v, s.z0 = Vector(o), Vector(u), Vector(v), z0; s.b = {"duro": ([], [], []), "morbido": ([], [], [])}; s.m = []
    def _m(s, k):
        if k not in s.m: s.m.append(k)
        return s.m.index(k)
    def P(s, a, b): q = s.o + s.u * a + s.v * b; return q.x, q.y
    def scat(s, u0, u1, v0, v1, z0, z1, k, tipo="duro"):
        V, F, M = s.b[tipo]; n = len(V)
        for z in (s.z0 + z0, s.z0 + z1):
            for a, b in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)): V.append((*s.P(a, b), z))
        F += [(n, n + 3, n + 2, n + 1), (n + 4, n + 5, n + 6, n + 7), (n, n + 1, n + 5, n + 4), (n + 1, n + 2, n + 6, n + 5),
              (n + 2, n + 3, n + 7, n + 6), (n + 3, n, n + 4, n + 7)]; M += [s._m(k)] * 6
    def cil(s, a, b, r0, r1, z0, z1, k, seg=20):
        V, F, M = s.b["duro"]; n = len(V); cx, cy = s.P(a, b)
        for z, r in ((s.z0 + z0, r0), (s.z0 + z1, r1)):
            for i in range(seg): V.append((cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), z))
        for i in range(seg):
            j = (i + 1) % seg; F.append((n + i, n + j, n + seg + j, n + seg + i)); M.append(s._m(k))
        F += [tuple(n + i for i in reversed(range(seg))), tuple(n + seg + i for i in range(seg))]; M += [s._m(k)] * 2
    def fine(s, nome, villa, tipo, ingombro):
        for parte, (V, F, M) in s.b.items():
            if not V: continue
            me = bpy.data.meshes.new(nome); me.from_pydata(V, [], F)
            for k in s.m: me.materials.append(mat(k))
            me.polygons.foreach_set("material_index", M); me.update()
            ob = bpy.data.objects.new(nome + ("" if parte == "duro" else " (tessili)"), me); ARR.objects.link(ob)
            ob["villa"] = villa; ob["arredo"] = tipo; ob["ingombro"] = [c for q in ingombro.exterior.coords[:-1] for c in q]
            bv = ob.modifiers.new("Smusso", "BEVEL"); bv.limit_method = "ANGLE"
            bv.width, bv.segments = (0.004, 2) if parte == "duro" else (0.035, 4)
            if parte == "morbido":
                for pl in me.polygons: pl.use_smooth = True

def vano_di(villa, q):
    return next((v for v in vani if v["villa"] == villa and v["pol"].contains(Point(q))), None)
def libero(v, q):
    """distanza dai muri del punto q, -1 fuori dal vano."""
    return v["pol"].exterior.distance(Point(q)) if v["pol"].contains(Point(q)) else -1.0
def telaio(anello, v):
    """rettangolo minimo dell'ingombro: centro, asse lungo u, asse corto vv rivolto verso il centro della stanza, lati."""
    r = list(Polygon(anello).minimum_rotated_rectangle.exterior.coords)
    c = (Vector(r[0]) + Vector(r[2])) / 2; l1, l2 = Vector(r[1]) - Vector(r[0]), Vector(r[2]) - Vector(r[1])
    lu, lv = (l1, l2) if l1.length >= l2.length else (l2, l1); u, vv = lu.normalized(), lv.normalized()
    if libero(v, c - vv * (lv.length / 2 + 0.35)) > libero(v, c + vv * (lv.length / 2 + 0.35)): vv = -vv
    return c, u, vv, lu.length, lv.length

def sedia(p, c, verso):
    """sedia con il sedile in c e lo schienale dalla parte opposta a 'verso' (coordinate locali del pezzo p)."""
    cu, cv = c; du = Vector(verso).normalized(); dv = Vector((-du.y, du.x))
    def b(a0, a1, b0, b1, z0, z1, k, t="duro"):
        pts = [Vector((cu, cv)) + du * a + dv * bb for a, bb in ((a0, b0), (a1, b1))]
        p.scat(min(pts[0].x, pts[1].x), max(pts[0].x, pts[1].x), min(pts[0].y, pts[1].y), max(pts[0].y, pts[1].y), z0, z1, k, t)
    for sa in (-0.19, 0.16):
        for sb in (-0.19, 0.16): b(sa, sa + 0.03, sb, sb + 0.03, 0, 0.44, "legno")
    b(-0.22, 0.22, -0.22, 0.22, 0.44, 0.49, "tessuto", "morbido"); b(-0.22, -0.19, -0.21, 0.21, 0.49, 0.84, "legno")

def armadio(p, L, W, H=2.40):
    p.scat(-L / 2, L / 2, -W / 2, W / 2 - 0.06, 0, 0.08, "metallo"); p.scat(-L / 2, L / 2, -W / 2, W / 2 - 0.022, 0.08, H, "laccato")
    n = max(1, round(L / 0.5)); la = L / n
    for i in range(n):
        u0 = -L / 2 + i * la
        p.scat(u0 + 0.0015, u0 + la - 0.0015, W / 2 - 0.02, W / 2, 0.08, H, "laccato")
        um = u0 + (la - 0.03 if i % 2 == 0 else 0.012)                       # maniglie a coppie, al centro di due ante
        p.scat(um, um + 0.018, W / 2, W / 2 + 0.012, 0.95, 1.30, "legno")

def letto(p, L, W, v, c, u):
    testata_meno = libero(v, c - u * (L / 2 + 0.2)) <= libero(v, c + u * (L / 2 + 0.2)); s = 1 if testata_meno else -1
    def U(a, b): return (min(s * a, s * b), max(s * a, s * b))
    p.scat(*U(-L / 2 + 0.08, L / 2 - 0.08), -W / 2 + 0.08, W / 2 - 0.08, 0, 0.10, "metallo")
    p.scat(*U(-L / 2, L / 2), -W / 2, W / 2, 0.10, 0.30, "legno"); p.scat(*U(-L / 2, -L / 2 + 0.05), -W / 2, W / 2, 0.30, 1.05, "legno")
    p.scat(*U(-L / 2 + 0.06, L / 2 - 0.02), -W / 2 + 0.02, W / 2 - 0.02, 0.30, 0.52, "laccato", "morbido")
    p.scat(*U(-L / 2 + 0.68, L / 2 + 0.01), -W / 2 - 0.03, W / 2 + 0.03, 0.49, 0.585, "tessuto", "morbido")
    p.scat(*U(L / 2 - 0.55, L / 2 - 0.08), -W / 2 - 0.035, W / 2 + 0.035, 0.58, 0.605, "tessuto_accento", "morbido")
    n = 2 if W > 1.3 else 1; lc = min(0.72, W / n - 0.10)
    for i in range(n):
        cv = -W / 2 + (i + 0.5) * W / n; p.scat(*U(-L / 2 + 0.10, -L / 2 + 0.55), cv - lc / 2, cv + lc / 2, 0.52, 0.66, "laccato", "morbido")

def comodino(p, L, W):
    p.scat(-L / 2 + 0.04, L / 2 - 0.04, -W / 2 + 0.04, W / 2 - 0.05, 0, 0.12, "metallo"); p.scat(-L / 2, L / 2, -W / 2, W / 2, 0.12, 0.46, "legno")
    p.scat(-L / 2 + 0.01, L / 2 - 0.01, W / 2, W / 2 + 0.004, 0.14, 0.285, "legno"); p.scat(-L / 2 + 0.01, L / 2 - 0.01, W / 2, W / 2 + 0.004, 0.295, 0.445, "legno")
    p.cil(0, -0.05, 0.065, 0.065, 0.46, 0.475, "metallo"); p.cil(0, -0.05, 0.008, 0.008, 0.475, 0.70, "metallo"); p.cil(0, -0.05, 0.12, 0.085, 0.62, 0.82, "tessuto")

def madia_tv(p, L, W):
    for su in (-L / 2 + 0.06, L / 2 - 0.09):
        for sv in (-W / 2 + 0.06, W / 2 - 0.09): p.scat(su, su + 0.03, sv, sv + 0.03, 0, 0.16, "metallo")
    p.scat(-L / 2, L / 2, -W / 2, W / 2 - 0.02, 0.16, 0.76, "legno")
    n = max(2, round(L / 0.45)); la = L / n
    for i in range(n): p.scat(-L / 2 + i * la + 0.0015, -L / 2 + (i + 1) * la - 0.0015, W / 2 - 0.02, W / 2, 0.16, 0.76, "legno")
    p.scat(-0.16, 0.16, -0.12, 0.08, 0.76, 0.775, "nero"); p.scat(-0.02, 0.02, -0.04, 0.0, 0.775, 0.84, "nero"); p.scat(-0.56, 0.56, -0.035, -0.005, 0.82, 1.46, "nero")

def scrivania(p, L, W):
    p.scat(-L / 2, L / 2, -W / 2, W / 2, 0.72, 0.75, "legno")
    for su in (-L / 2 + 0.04, L / 2 - 0.08):
        for sv in (-W / 2 + 0.04, W / 2 - 0.08): p.scat(su, su + 0.04, sv, sv + 0.04, 0, 0.72, "metallo")
    p.scat(-L / 2 + 0.10, -L / 2 + 0.50, -W / 2 + 0.05, W / 2 - 0.05, 0.60, 0.72, "legno")      # cassetto
    p.cil(L / 2 - 0.22, -W / 2 + 0.2, 0.07, 0.07, 0.75, 0.765, "metallo"); p.cil(L / 2 - 0.22, -W / 2 + 0.2, 0.008, 0.008, 0.765, 1.12, "metallo")
    p.cil(L / 2 - 0.22, -W / 2 + 0.2, 0.10, 0.07, 1.05, 1.20, "metallo")
    sedia(p, (0.0, W / 2 + 0.12), (0, -1))

def parete_tv(p, L, W):
    p.scat(-L / 2, L / 2, -W / 2, -W / 2 + 0.02, 0, 2.30, "legno")
    n = int(L / 0.06)
    for i in range(n): p.scat(-L / 2 + i * L / n + 0.01, -L / 2 + i * L / n + 0.04, -W / 2 + 0.02, -W / 2 + 0.038, 0, 2.30, "legno")
    p.scat(-L / 2, L / 2, -W / 2 + 0.038, -W / 2 + 0.45, 0.22, 0.52, "laccato")
    p.scat(-0.72, 0.72, -W / 2 + 0.045, -W / 2 + 0.075, 0.92, 1.74, "nero")
    p.scat(L / 2 - 1.05, L / 2 - 0.05, -W / 2 + 0.038, -W / 2 + 0.26, 1.95, 1.98, "legno")

def cucina(nome, anello, v, villa):
    pol = Polygon(anello).buffer(0); cc = list(pol.exterior.coords)
    k = max(range(len(cc) - 1), key=lambda i: math.dist(cc[i], cc[i + 1])); u = (Vector(cc[k + 1]) - Vector(cc[k])).normalized(); w = Vector((-u.y, u.x))
    o = Vector(cc[0]); loc = [((Vector(q) - o).dot(u), (Vector(q) - o).dot(w)) for q in cc[:-1]]
    def unici(vals):
        out = []
        for x in sorted(vals):
            if not out or x - out[-1] > 0.03: out.append(x)
        return out
    xs, ys = unici(q[0] for q in loc), unici(q[1] for q in loc); lp = Polygon(loc)
    piena = {(i, j) for i in range(len(xs) - 1) for j in range(len(ys) - 1) if lp.contains(Point((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2))}
    rett = []
    while piena:                                              # rettangoli massimi, prima lungo l'asse lungo
        i, j = min(piena); i1 = i
        while (i1 + 1, j) in piena: i1 += 1
        j1 = j
        while all((a, j1 + 1) in piena for a in range(i, i1 + 1)): j1 += 1
        for a in range(i, i1 + 1):
            for b in range(j, j1 + 1): piena.discard((a, b))
        rett.append((xs[i], xs[i1 + 1], ys[j], ys[j1 + 1]))
    p = Pezzo(o, u, w, v["z0"]); moduli = []
    for x0, x1, y0, y1 in rett:
        lungo_x = (x1 - x0) >= (y1 - y0); lung, prof = (x1 - x0, y1 - y0) if lungo_x else (y1 - y0, x1 - x0)
        def box(a0, a1, d0, d1, z0, z1, kk):                   # a lungo la schiera, d in profondità (0 = muro)
            if lungo_x: p.scat(x0 + a0, x0 + a1, *sorted((ym + sg * d0, ym + sg * d1)), z0, z1, kk)
            else: p.scat(*sorted((xm + sg * d0, xm + sg * d1)), y0 + a0, y0 + a1, z0, z1, kk)
        # lato muro: quello con meno spazio libero davanti
        if lungo_x:
            f0 = libero(v, o + u * ((x0 + x1) / 2) + w * (y0 - 0.3)); f1 = libero(v, o + u * ((x0 + x1) / 2) + w * (y1 + 0.3)); sg = 1 if f0 <= f1 else -1; ym = y0 if sg == 1 else y1
        else:
            f0 = libero(v, o + u * (x0 - 0.3) + w * ((y0 + y1) / 2)); f1 = libero(v, o + u * (x1 + 0.3) + w * ((y0 + y1) / 2)); sg = 1 if f0 <= f1 else -1; xm = x0 if sg == 1 else x1
        box(0, lung, 0, prof - 0.06, 0, 0.10, "metallo"); box(0, lung, 0, prof - 0.022, 0.10, 0.86, "laccato")
        box(0, lung, 0, prof + 0.02, 0.86, 0.90, "piano_cucina")
        n = max(1, round(lung / 0.6)); la = lung / n
        for i in range(n):
            a0, a1 = i * la, (i + 1) * la
            box(a0 + 0.0015, a1 - 0.0015, prof - 0.02, prof, 0.10, 0.80, "laccato")       # anta sotto la gola
            mid = (o + u * (x0 + (a0 + a1) / 2) + w * (ym)) if lungo_x else (o + u * xm + w * (y0 + (a0 + a1) / 2))
            finestra = INF.distance(Point(mid.x, mid.y)) < 0.45 if not INF.is_empty else False
            moduli.append({"box": box, "a": (a0, a1), "prof": prof, "finestra": finestra, "lung": lung, "i": i, "n": n})
    # pensili dove non c'è un infisso; piano cottura sulla schiera più lunga, lavello sulla seconda, colonna a un estremo libero
    for m in moduli:
        if not m["finestra"]: m["box"](m["a"][0] + 0.0015, m["a"][1] - 0.0015, 0, 0.35, 1.45, 2.15, "legno")
    schiere = sorted({m["lung"] for m in moduli}, reverse=True)
    def al_centro(lung): return min((m for m in moduli if m["lung"] == lung), key=lambda m: abs((m["a"][0] + m["a"][1]) / 2 - lung / 2))
    m = al_centro(schiere[0]); am = (m["a"][0] + m["a"][1]) / 2; m["box"](am - 0.29, am + 0.29, 0.06, 0.56, 0.90, 0.906, "nero")
    if len(schiere) > 1:
        m = al_centro(schiere[1]); am = (m["a"][0] + m["a"][1]) / 2; m["box"](am - 0.25, am + 0.25, 0.10, 0.50, 0.896, 0.903, "metallo")
        m["box"](am - 0.01, am + 0.01, 0.05, 0.08, 0.90, 1.15, "metallo")
    estremi = [m for m in moduli if m["i"] in (0, m["n"] - 1) and not m["finestra"] and m["lung"] == schiere[-1]]
    if estremi and len(schiere) > 1:
        m = estremi[-1]; m["box"](m["a"][0] + 0.0015, m["a"][1] - 0.0015, 0, m["prof"], 0.90, 2.15, "laccato")
    p.fine(nome, villa, "cucina", pol)
    return len(rett)

def zona_giorno(a, v, villa, tv):
    """divano, tavolino e tappeto di fronte alla parete TV; tavolo da pranzo nel posto libero più ampio."""
    c, u, vv, L, W = tv; occupati = [Polygon(x["anello"]).buffer(0.05) for x in A["arredi"] if x.get("anello") and x["villa"] == villa]
    porte = PORTE.buffer(float(a.get("distanza_porte_m", 0.5))); n_p = int(a.get("posti_tavolo", 6)); lt = 0.6 * (n_p // 2); x0, y0, x1, y1 = v["pol"].bounds
    def divano_a(d): return Polygon([tuple(c + vv * (W / 2 + d + sv) + u * su) for su, sv in ((-1.15, -0.475), (1.15, -0.475), (1.15, 0.475), (-1.15, 0.475))])
    def zona_tv(d): return Polygon([tuple(c + u * su + vv * sv) for su, sv in ((-1.2, 0), (1.2, 0), (1.2, W / 2 + d), (-1.2, W / 2 + d))])
    def tavolo_con(d):
        """posto del tavolo (180×90 con le sedie: zona 2,3×2,0 m) più lontano da muri e mobili, dato il divano a distanza d."""
        occ = unary_union(occupati + ([divano_a(d).buffer(0.15), zona_tv(d)] if d else [])); meglio = None
        for asse in (u, vv):
            pa = Vector((-asse.y, asse.x)); i = 0
            while x0 + 0.15 * i < x1:
                j = 0
                while y0 + 0.15 * j < y1:
                    q = Vector((x0 + 0.15 * i, y0 + 0.15 * j)); j += 1
                    zona = Polygon([tuple(q + asse * sa + pa * sb) for sa, sb in ((-lt / 2 - 0.15, -0.95), (lt / 2 + 0.15, -0.95), (lt / 2 + 0.15, 0.95), (-lt / 2 - 0.15, 0.95))])
                    if not v["pol"].buffer(-0.05).contains(zona) or zona.intersects(occ) or zona.intersects(porte): continue
                    voto = min(v["pol"].exterior.distance(Point(q)), occ.distance(Point(q)))
                    if meglio is None or voto > meglio[0]: meglio = (voto, q, asse, pa, zona)
                i += 1
        return meglio
    # distanza del divano dalla TV: la più comoda (3,0 m) che lascia posto anche al tavolo; se non c'è, la più comoda e basta
    possibili = [d for d in [3.0 - 0.1 * k for k in range(11)] if v["pol"].buffer(-0.08).contains(divano_a(d))]
    dist = next((d for d in possibili if tavolo_con(d)), possibili[0] if possibili else None)
    meglio = tavolo_con(dist); fatti = []
    if dist:
        cs = c + vv * (W / 2 + dist); p = Pezzo(cs, u, -vv, v["z0"])           # il divano guarda la TV: fronte = -vv
        p.scat(-1.15, 1.15, -0.475, 0.475, 0, 0.06, "metallo"); p.scat(-1.15, 1.15, -0.475, 0.475, 0.06, 0.40, "tessuto", "morbido")
        p.scat(-1.15, 1.15, -0.475, -0.25, 0.40, 0.82, "tessuto", "morbido")
        for su in (-1.15, 0.97): p.scat(su, su + 0.18, -0.25, 0.475, 0.40, 0.62, "tessuto", "morbido")
        for i in range(3): p.scat(-0.97 + i * 0.6467 + 0.01, -0.97 + (i + 1) * 0.6467 - 0.01, -0.25, 0.46, 0.40, 0.52, "tessuto", "morbido")
        for su in (-0.93, 0.55): p.scat(su, su + 0.40, -0.27, -0.12, 0.52, 0.86, "tessuto_accento", "morbido")
        ing = Polygon([tuple(cs + u * su + vv * sv) for su, sv in ((-1.15, -0.475), (1.15, -0.475), (1.15, 0.475), (-1.15, 0.475))])
        p.fine(f"Divano v{villa}", villa, "divano", ing); fatti.append(ing)
        fronte_tv, fronte_div = -W / 2 + 0.45, W / 2 + dist - 0.475          # il tavolino sta a metà tra mobile TV e divano
        ct = c + vv * ((fronte_tv + fronte_div) / 2); pt = min(0.30, max(0.20, (fronte_div - fronte_tv) / 2 - 0.42)); p = Pezzo(ct, u, vv, v["z0"])
        p.scat(-1.4, 1.4, -0.95, 0.95, 0, 0.012, "tappeto")
        p.scat(-0.55, 0.55, -pt, pt, 0.30, 0.335, "legno")
        for su in (-0.50, 0.47):
            for sv in (-pt + 0.05, pt - 0.08): p.scat(su, su + 0.03, sv, sv + 0.03, 0.012, 0.30, "metallo")
        ing = Polygon([tuple(ct + u * su + vv * sv) for su, sv in ((-0.55, -pt), (0.55, -pt), (0.55, pt), (-0.55, pt))])
        p.fine(f"Tavolino e tappeto v{villa}", villa, "tavolino", ing); fatti.append(ing)
    else: log(f"AVVISO villa {villa}: il divano non entra di fronte alla parete TV")
    if meglio:
        _, q, asse, pa, zona = meglio; p = Pezzo(q, asse, pa, v["z0"])
        p.scat(-lt / 2, lt / 2, -0.45, 0.45, 0.72, 0.76, "legno")
        for su in (-lt / 2 + 0.08, lt / 2 - 0.14):
            for sv in (-0.37, 0.31): p.scat(su, su + 0.06, sv, sv + 0.06, 0, 0.72, "legno")
        for i in range(n_p // 2):
            cu = -lt / 2 + 0.3 + 0.6 * i; sedia(p, (cu, 0.62), (0, -1)); sedia(p, (cu, -0.62), (0, 1))
        p.fine(f"Tavolo da {n_p} v{villa}", villa, "tavolo", zona.buffer(-0.2))
    else: log(f"AVVISO villa {villa}: nessun posto libero per il tavolo da {n_p}")
    return bool(dist), bool(meglio)

# ------------------------------------------------------------------------------------------------ pezzi
conta = {}; tele_tv = {}
for a in A["arredi"]:
    if not a.get("anello"): continue
    villa = int(a.get("villa", 1)); pol = Polygon(a["anello"]); v = vano_di(villa, pol.representative_point().coords[0])
    if v is None: log("AVVISO: fuori da ogni vano:", a["tipo"], a.get("vano")); continue
    t = a["tipo"]; conta[t] = conta.get(t, 0) + 1; nome = f"{t} {v['nome']} v{villa} {conta[t]}"
    if t == "cucina": cucina(nome, a["anello"], v, villa); continue
    c, u, vv, L, W = telaio(a["anello"], v); p = Pezzo(c, u, vv, v["z0"])
    if t == "armadio": armadio(p, L, W)
    elif t == "letto": letto(p, L, W, v, c, u)
    elif t == "comodino": comodino(p, L, W)
    elif t == "madia_tv": madia_tv(p, L, W)
    elif t == "scrivania": scrivania(p, L, W)
    elif t == "parete_tv": parete_tv(p, L, W); tele_tv[(villa, v["nome"])] = (c, u, vv, L, W)
    else: log("AVVISO: tipo non previsto:", t); continue
    p.fine(nome, villa, t, pol)
for a in A["arredi"]:
    if a["tipo"] != "zona_giorno": continue
    villa = int(a.get("villa", 1)); chiave = next((k for k in tele_tv if k[0] == villa and k[1].startswith(a["vano"])), None)
    if not chiave: log("AVVISO: zona giorno senza parete TV in", a["vano"]); continue
    v = next(x for x in vani if x["villa"] == villa and x["nome"] == chiave[1] and x["pol"].contains(Point(tele_tv[chiave][0])))
    ok = zona_giorno(a, v, villa, tele_tv[chiave]); conta["zona_giorno"] = conta.get("zona_giorno", 0) + 1
    log("zona giorno villa", villa, "| divano", ok[0], "| tavolo", ok[1])
log("arredi:", json.dumps(conta, ensure_ascii=False), "| oggetti", len(ARR.objects))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend")); log("fine")
