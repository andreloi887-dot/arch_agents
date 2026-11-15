"""Arredi degli interni dagli ingombri indicati in planimetria (fase 3 della filiera).

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P arredi_interni.py -- <cartella modello>
  python arredi_interni.py -- <cartella modello> --blend contesto_progetto.blend        (Blender come modulo)

Dopo finiture_interni.py e prima di percorsi_camera.py. Riscrive contesto_progetto.blend; si può rilanciare.
Legge <modello>/arredi.json:
  stile    colori (hex) di legno, laccato, tessuto, tessuto_accento, piano_cucina, metallo, nero, tappeto
  arredi   elenco di pezzi: villa, vano, tipo, anello [[x, y], ...] in coordinate locali del contesto (l'ingombro in pianta)
Tipi: armadio, letto, comodino, madia_tv, scrivania (con sedia), parete_tv, cucina (ingombro in linea, a L o a C, diviso
in moduli da 60 cm: frigo e colonna forno-microonde in fondo a una schiera, lavello e lavastoviglie sulla schiera più
libera, piano cottura con cappa su un'altra, basi, piano, paraschizzi, pensili dove non c'è una finestra), zona_giorno (senza anello: divano, tavolino e tappeto di
fronte alla parete TV, tavolo con posti_tavolo sedie vicino alla cucina, con distanza_porte_m liberi davanti alle porte
interne; "tavolo_contro_vano": tavolo addossato al muro in comune con quel vano, e parete TV, divano e tavolino spostati lungo
il loro muro di quanto serve).
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
from shapely.prepared import prep

argv, opt = argomenti()
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
if opt("--blend"): bpy.ops.wm.open_mainfile(filepath=os.path.join(USCITA, opt("--blend")))
A = json.load(open(os.path.join(MOD, "arredi.json"), encoding="utf-8"))
log = registro(os.path.join(USCITA, "arredi_interni.log"))
scn = bpy.context.scene
ST = {"legno": "#C8A47A", "laccato": "#EDE7DA", "tessuto": "#D9D0C1", "tessuto_accento": "#B98466", "piano_cucina": "#DAD5CC",
      "metallo": "#3A3632", "nero": "#141414", "tappeto": "#CFC4B2", "inox": "#C4C4C0", **A.get("stile", {})}

def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]
RUV = {"legno": 0.45, "laccato": 0.35, "tessuto": 0.95, "tessuto_accento": 0.95, "piano_cucina": 0.3, "metallo": 0.4, "nero": 0.25, "tappeto": 1.0, "inox": 0.3}
MATS = {}
def mat(k):
    if k not in MATS:
        m = bpy.data.materials.get("Arredo " + k) or bpy.data.materials.new("Arredo " + k); m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = lin(ST[k]); b.inputs["Roughness"].default_value = RUV[k]
        b.inputs["Metallic"].default_value = 1.0 if k in ("metallo", "inox") else 0.0; MATS[k] = m
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
infissi, porte_, interne_, infissi_z = [], [], [], []                       # interne_: porte tra due stanze (rifatte da finiture_interni.py)
for ob in scn.objects:
    if ob.get("ifc_classe") in ("IfcWindow", "IfcDoor") and ob.type == "MESH" and ob.data.vertices:
        r_ = MultiPoint([(ob.matrix_world @ v.co).xy[:] for v in ob.data.vertices]).minimum_rotated_rectangle
        if r_.geom_type != "Polygon" or r_.length > 14: continue          # cancelli e recinzioni non contano
        infissi.append(r_); zz = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]; infissi_z.append((r_, min(zz), max(zz)))
        if ob["ifc_classe"] == "IfcDoor": porte_.append(r_)
        if ob.get("sostituita"): interne_.append(r_)
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
    for kr, (x0, x1, y0, y1) in enumerate(rett):
        lungo_x = (x1 - x0) >= (y1 - y0); lung, prof = (x1 - x0, y1 - y0) if lungo_x else (y1 - y0, x1 - x0)
        # lato muro: quello con meno spazio libero davanti
        if lungo_x: f0 = libero(v, o + u * ((x0 + x1) / 2) + w * (y0 - 0.3)); f1 = libero(v, o + u * ((x0 + x1) / 2) + w * (y1 + 0.3)); sg = 1 if f0 <= f1 else -1; m0 = y0 if sg == 1 else y1
        else: f0 = libero(v, o + u * (x0 - 0.3) + w * ((y0 + y1) / 2)); f1 = libero(v, o + u * (x1 + 0.3) + w * ((y0 + y1) / 2)); sg = 1 if f0 <= f1 else -1; m0 = x0 if sg == 1 else x1
        def pt(a_, d, lungo_x=lungo_x, x0=x0, y0=y0, m0=m0, sg=sg):       # a_ lungo la schiera, d in profondità (0 = muro) → locale
            return (x0 + a_, m0 + sg * d) if lungo_x else (m0 + sg * d, y0 + a_)
        def box(a0, a1, d0, d1, z0, z1, kk, pt=pt):
            (xa, ya), (xb, yb) = pt(a0, d0), pt(a1, d1); p.scat(min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb), z0, z1, kk)
        def mondo(a_, d, pt=pt): q = pt(a_, d); return o + u * q[0] + w * q[1]
        n = max(1, round(lung / 0.6)); la = lung / n
        for i in range(n):
            a0, a1 = i * la, (i + 1) * la; am = (a0 + a1) / 2
            dietro = Polygon([tuple(mondo(a0, -0.45)), tuple(mondo(a1, -0.45)), tuple(mondo(a1, 0.02)), tuple(mondo(a0, 0.02))])
            moduli.append({"box": box, "pt": pt, "a": (a0, a1), "am": am, "prof": prof, "lung": lung, "i": i, "n": n, "r": kr, "ruolo": None,
                           "angolo": lp.contains(Point(pt(am, prof + 0.3))),                     # fronte chiuso da un'altra schiera
                           "finestra": any(r_.intersects(dietro) and zb < v["z0"] + 2.15 and zt > v["z0"] + 1.0 for r_, zb, zt in infissi_z),
                           "al_muro": i in (0, n - 1) and libero(v, mondo(-0.25 if i == 0 else lung + 0.25, prof / 2)) < 0})
    # ruoli. Colonne (frigo, forno e microonde): due moduli in fondo a una schiera, meglio se contro un muro, senza finestra dietro.
    # Lavello e lavastoviglie sulla schiera con più moduli liberi; piano cottura su un'altra schiera, se c'è posto
    def di(r): return sorted((m for m in moduli if m["r"] == r), key=lambda m: m["i"])
    def libero_(m): return m["ruolo"] is None and not m["angolo"]
    coppie = []
    for r in {m["r"] for m in moduli}:
        mm = di(r)
        for capo, vicino in ((mm[0], mm[1] if len(mm) > 1 else None), (mm[-1], mm[-2] if len(mm) > 1 else None)):
            if vicino and libero_(capo) and libero_(vicino) and not capo["finestra"] and not vicino["finestra"]: coppie.append((capo, vicino))
    if coppie:
        capo, vicino = max(coppie, key=lambda c_: (c_[0]["al_muro"], -c_[0]["lung"])); capo["ruolo"], vicino["ruolo"] = "frigo", "forno"
    else:
        solo = next((m for m in moduli if libero_(m) and m["i"] in (0, m["n"] - 1) and not m["finestra"]), None)
        if solo: solo["ruolo"] = "frigo"
        log(f"AVVISO {nome}: non c'è posto per due colonne: forno sotto il piano cottura, niente microonde")
    conta_l = {r: sum(libero_(m) for m in di(r)) for r in {m["r"] for m in moduli}}; r_acqua = max(conta_l, key=lambda r: conta_l[r])
    lib = [m for m in di(r_acqua) if libero_(m)]
    if lib:
        lav = min(lib, key=lambda m: abs(m["am"] - m["lung"] / 2)); lav["ruolo"] = "lavello"
        acc = [m for m in lib if abs(m["i"] - lav["i"]) == 1 and libero_(m)]
        if acc: acc[0]["ruolo"] = "lavastoviglie"
    resto = [m for m in moduli if libero_(m) and not m["finestra"]] or [m for m in moduli if libero_(m)]
    if resto:
        pc = max(resto, key=lambda m: (m["r"] != r_acqua, not any(x["ruolo"] == "lavello" and x["r"] == m["r"] and abs(x["i"] - m["i"]) == 1 for x in moduli)))
        pc["ruolo"] = "cottura" if coppie else "cottura_forno"
    ZC, ZP, ZS, ZA, HP = 0.10, 0.86, 0.90, 1.45, 2.15                 # zoccolo, sotto il piano, sopra il piano, pensili da-a
    def forno(box, a0, a1, d, z0):
        box(a0 + 0.003, a1 - 0.003, d, d + 0.02, z0, z0 + 0.595, "nero"); box(a0 + 0.003, a1 - 0.003, d + 0.02, d + 0.022, z0 + 0.50, z0 + 0.595, "inox")
        box(a0 + 0.06, a1 - 0.06, d + 0.02, d + 0.05, z0 + 0.455, z0 + 0.475, "inox")
    for m in moduli:
        box, (a0, a1), prof, am, ruolo = m["box"], m["a"], m["prof"], m["am"], m["ruolo"]; f = prof - 0.02
        if ruolo in ("frigo", "forno"):
            box(a0, a1, 0, prof - 0.06, 0, ZC, "metallo"); box(a0, a1, 0, f, ZC, HP, "laccato")
            if ruolo == "frigo":                               # frigo combinato a vista, in acciaio: congelatore sotto, frigo sopra
                box(a0 + 0.004, a1 - 0.004, f, prof + 0.03, ZC + 0.02, 0.78, "inox"); box(a0 + 0.004, a1 - 0.004, f, prof + 0.03, 0.79, HP - 0.20, "inox")
                box(a0 + 0.0015, a1 - 0.0015, f, prof, HP - 0.19, HP, "laccato")
                lato = a0 + 0.06 if m["i"] == 0 else a1 - 0.08
                box(lato, lato + 0.02, prof + 0.03, prof + 0.065, 0.45, 0.74, "metallo"); box(lato, lato + 0.02, prof + 0.03, prof + 0.065, 0.83, 1.35, "metallo")
            else:                                              # colonna: cestone, forno, microonde, anta
                box(a0 + 0.0015, a1 - 0.0015, f, prof, ZC, 0.70, "laccato"); forno(box, a0, a1, f, 0.715)
                box(a0 + 0.003, a1 - 0.003, f, prof, 1.325, 1.705, "nero"); box(a1 - 0.14, a1 - 0.003, prof, prof + 0.002, 1.325, 1.705, "inox")
                box(a1 - 0.165, a1 - 0.15, prof, prof + 0.03, 1.36, 1.67, "inox")
                box(a0 + 0.0015, a1 - 0.0015, f, prof, 1.72, HP, "laccato")
            continue
        box(a0, a1, 0, prof - 0.06, 0, ZC, "metallo"); box(a0, a1, 0, 0.012, ZS, ZA, "piano_cucina")              # zoccolo e paraschizzi
        alto = 0.66 if ruolo == "lavello" else ZP                                                                   # sotto il lavello il mobile è più basso: c'è la vasca
        box(a0, a1, 0, f, ZC, alto, "laccato")
        if ruolo == "lavello":
            v0, v1, b0, b1 = am - 0.25, am + 0.25, 0.10, 0.50
            for q in ((a0, v0, 0, prof + 0.02), (v1, a1, 0, prof + 0.02), (v0, v1, 0, b0), (v0, v1, b1, prof + 0.02)): box(*q, ZP, ZS, "piano_cucina")
            box(v0, v1, b0, b1, ZS - 0.19, ZS - 0.185, "inox")
            for q in ((v0 - 0.004, v0, b0, b1), (v1, v1 + 0.004, b0, b1), (v0, v1, b0 - 0.004, b0), (v0, v1, b1, b1 + 0.004)): box(*q, ZS - 0.19, ZS + 0.002, "inox")
            p.cil(*m["pt"](am, 0.055), 0.018, 0.018, ZS, ZS + 0.28, "inox"); box(am - 0.012, am + 0.012, 0.055, 0.25, ZS + 0.26, ZS + 0.284, "inox")
            box(a0 + 0.0015, a1 - 0.0015, f, prof, ZC, 0.80, "laccato")
        else:
            box(a0, a1, 0, prof + 0.02, ZP, ZS, "piano_cucina")
            if ruolo == "lavastoviglie":
                box(a0 + 0.003, a1 - 0.003, f, prof, ZC, 0.80, "inox"); box(a0 + 0.08, a1 - 0.08, prof, prof + 0.03, 0.72, 0.74, "metallo")
            elif ruolo == "cottura_forno": forno(box, a0, a1, f, 0.20); box(a0 + 0.0015, a1 - 0.0015, f, prof, ZC, 0.195, "laccato")
            elif ruolo == "cottura":                           # cassettoni sotto il piano cottura
                for z0_, z1_ in ((ZC, 0.44), (0.445, 0.80)): box(a0 + 0.0015, a1 - 0.0015, f, prof, z0_, z1_, "laccato")
            else: box(a0 + 0.0015, a1 - 0.0015, f, prof, ZC, 0.80, "laccato")                                      # anta sotto la gola
        if ruolo in ("cottura", "cottura_forno"):
            box(am - 0.29, am + 0.29, 0.06, 0.56, ZS, ZS + 0.006, "nero")
            for da, dd in ((-0.14, 0.19), (0.14, 0.19), (-0.14, 0.43), (0.14, 0.43)): p.cil(*m["pt"](am + da, dd), 0.085, 0.085, ZS + 0.006, ZS + 0.0065, "metallo", seg=24)
        if not m["finestra"]:
            box(a0 + 0.0015, a1 - 0.0015, 0, 0.35, ZA, HP, "legno")
            if ruolo in ("cottura", "cottura_forno"): box(a0 + 0.02, a1 - 0.02, 0.012, 0.47, ZA - 0.035, ZA, "inox")     # cappa sotto il pensile
    p.fine(nome, villa, "cucina", pol)
    log(f"{nome}: moduli", ", ".join(f"{m['ruolo'] or ('angolo' if m['angolo'] else 'base')}{'' if not m['finestra'] else ' (finestra)'}" for m in moduli))
    return len(rett)

def zona_giorno(a, v, villa, tv):
    """divano, tavolino e tappeto di fronte alla parete TV; tavolo da pranzo nel posto libero più ampio."""
    c, u, vv, L, W, nome_tv = tv; occupati = [Polygon(x["anello"]).buffer(0.05) for x in A["arredi"] if x.get("anello") and x["villa"] == villa]
    sue = [q for q in porte_ if q.distance(v["pol"]) < 0.3]              # porte della stanza
    cucine = [x["pol"] for x in vani if x["villa"] == villa and x["nome"].startswith("Cucina")]
    verso_cucina = min(sue, key=lambda q: min(q.distance(k_) for k_ in cucine)) if sue and cucine else None
    interne = [q for q in sue if any(q.equals(k_) for k_ in interne_)]; altre = [q for q in sue if q not in interne]
    d_porte = float(a.get("distanza_porte_m", 0.9)); porte = Polygon(); n_p = int(a.get("posti_tavolo", 6)); lt = max(1.4, 0.6 * (n_p // 2)); wt = 0.45 if n_p > 4 else 0.40; x0, y0, x1, y1 = v["pol"].bounds
    # il divano sta di fronte alla TV a distanza d e può scostarsi di lato di sh (lo schermo resta davanti al divano)
    def divano_a(d, sh=0.0): return Polygon([tuple(c + vv * (W / 2 + d + sv) + u * (su + sh)) for su, sv in ((-1.15, -0.475), (1.15, -0.475), (1.15, 0.475), (-1.15, 0.475))])
    def zona_tv(d, sh=0.0): return MultiPoint([tuple(c + u * su) for su in (-0.75, 0.75)] + list(divano_a(d, sh).exterior.coords)).convex_hull
    stato = {"porte": Polygon(), "chiave": None, "fatti": {}}
    def tavolo_con(d, sh=0.0):
        """posto del tavolo (con le sedie), dato il divano a distanza d: vicino alla cucina, libero da mobili e porte."""
        if (d, sh, stato["chiave"]) in stato["fatti"]: return stato["fatti"][(d, sh, stato["chiave"])]
        occ = unary_union(occupati + ([divano_a(d, sh).buffer(0.15), zona_tv(d, sh)] if d else [])); meglio = None
        vietato = prep(unary_union([occ, stato["porte"]])); stanza = prep(v["pol"].buffer(-0.05))
        for asse in (u, vv):
            pa = Vector((-asse.y, asse.x)); i = 0
            while x0 + 0.1 * i < x1:
                j = 0
                while y0 + 0.1 * j < y1:
                    q = Vector((x0 + 0.1 * i, y0 + 0.1 * j)); j += 1
                    zona = Polygon([tuple(q + asse * sa + pa * sb) for sa, sb in ((-lt / 2 - 0.15, -wt - 0.5), (lt / 2 + 0.15, -wt - 0.5), (lt / 2 + 0.15, wt + 0.5), (-lt / 2 - 0.15, wt + 0.5))])
                    if not stanza.contains(zona) or vietato.intersects(zona): continue
                    # il tavolo sta vicino alla cucina; senza cucina accanto, nel punto più lontano da muri e mobili
                    voto = -verso_cucina.distance(Point(q)) if verso_cucina is not None else min(v["pol"].exterior.distance(Point(q)), occ.distance(Point(q)))
                    # il passaggio davanti alle altre porte interne (disimpegno) conta più della vicinanza alla cucina
                    voto += 2.0 * min([2.5] + [k_.distance(zona) for k_ in interne if k_ is not verso_cucina])
                    if meglio is None or voto > meglio[0]: meglio = (voto, q, asse, pa, zona)
                i += 1
        stato["fatti"][(d, sh, stato["chiave"])] = meglio; return meglio
    # divano: distanza dalla TV la più comoda (da 3,0 m a scendere) e scostamento laterale il più piccolo che lasciano posto al tavolo
    def possibili(sh): return [d for d in [3.0 - 0.1 * k for k in range(11)] if v["pol"].buffer(-0.08).contains(divano_a(d, sh))]
    scosti = [0.0] + [sg * 0.2 * k for k in (1, 2, 3) for sg in (1, -1)]
    dist, sh, meglio = (possibili(0.0)[0] if possibili(0.0) else None), 0.0, None
    contro = a.get("tavolo_contro_vano"); prove_ = None
    if contro:
        # tavolo addossato al muro in comune con un altro vano (scelta di chi arreda): lato lungo sul muro, sedie sul lato libero
        # e alle teste, nel tratto più lontano dalle porte interne. Parete TV, divano e tavolino si spostano lungo il loro muro
        # di quanto basta per lasciargli posto
        vicini = [x for x in vani if x["villa"] == villa and x is not v and x["nome"].startswith(contro) and x["pol"].distance(v["pol"]) < 0.45]
        def pezzi(g): return [t for t in ([g] if g.geom_type == "LineString" else getattr(g, "geoms", [])) if t.geom_type == "LineString"]
        tratti = [t for x in vicini for t in pezzi(v["pol"].simplify(0.05).exterior.intersection(x["pol"].buffer(0.45)))]
        if tratti:
            tr = max(tratti, key=lambda t: t.length); pa_, pb_ = Vector(tr.coords[0]), Vector(tr.coords[-1]); w = (pb_ - pa_).normalized()
            n = Vector((-w.y, w.x)); n = n if v["pol"].contains(Point(tuple((pa_ + pb_) / 2 + n * 0.5))) else -n
            def zona_muro(s_): return Polygon([tuple(pa_ + w * (s_ + sa) + n * sb) for sa, sb in ((-lt / 2 - 0.5, 0.02), (lt / 2 + 0.5, 0.02), (lt / 2 + 0.5, 0.05 + 2 * wt + 0.5), (-lt / 2 - 0.5, 0.05 + 2 * wt + 0.5))])
            vietato = unary_union([q.buffer(d_porte) for q in interne] + [q.buffer(0.3) for q in altre] + [o_ for o_ in occupati if not o_.intersects(Polygon([tuple(c + u * su + vv * sv) for su, sv in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))]).buffer(-0.05))])
            cand = [s_ for s_ in [0.05 * k for k in range(int(tr.length / 0.05) + 1)] if v["pol"].buffer(0.02).contains(zona_muro(s_)) and not zona_muro(s_).intersects(vietato)]
            if cand:
                s_ = max(cand, key=lambda s_: (round(min([3.0] + [q.distance(zona_muro(s_)) for q in interne]), 1), -abs(s_ - tr.length / 2)))
                zona = zona_muro(s_); meglio = (0, pa_ + w * s_ + n * (0.03 + wt), w, n, zona, True)
                ud = u if u.dot(n) > 0 else -u; tv0 = Polygon([tuple(c + u * su + vv * sv) for su, sv in ((-L / 2, -W / 2), (L / 2, -W / 2), (L / 2, W / 2), (-L / 2, W / 2))]); c0 = c.copy(); mossa = None
                for k in range(40):
                    c = c0 + ud * 0.1 * k; tvk = Polygon([tuple(q + ud * 0.1 * k) for q in map(Vector, tv0.exterior.coords[:-1])])
                    if not v["pol"].buffer(0.06).contains(tvk): break
                    dd = next((d for d in possibili(0.0) if not divano_a(d).buffer(0.15).intersects(zona) and not zona_tv(d).intersects(zona)), None)
                    if dd and not tvk.intersects(zona.buffer(0.1)): mossa = (0.1 * k, dd); break
                if mossa:
                    dist, sh = mossa[1], 0.0
                    for o_ in ARR.objects:
                        if o_.name.startswith(nome_tv):
                            o_.location.x += ud.x * mossa[0]; o_.location.y += ud.y * mossa[0]
                            o_["ingombro"] = [c_ for q in tv0.exterior.coords[:-1] for c_ in (q[0] + ud.x * mossa[0], q[1] + ud.y * mossa[0])]
                    log(f"zona giorno villa {villa}: tavolo contro il muro verso {vicini[0]['nome']}; parete TV, divano e tavolino spostati di {mossa[0]:.1f} m; divano a {dist:.1f} m dalla TV")
                    prove_ = []
                else: c = c0; meglio = None; log(f"AVVISO villa {villa}: con il tavolo contro il muro verso {contro} parete TV e divano non trovano posto; tavolo con le regole generali")
        if prove_ is None and not meglio: log(f"AVVISO villa {villa}: nessun tratto di muro libero verso {contro}; tavolo con le regole generali")
    # passaggio libero davanti alle porte: quello chiesto davanti alle porte interne (verso disimpegno e cucina), che non si
    # tocca finché c'è un'altra soluzione; davanti alle portefinestre si riduce via via finché il tavolo trova posto
    prove = [(d_porte, d_porte - 0.1 * k) for k in range(int(round((d_porte - 0.1) / 0.1)) + 1)] + [(d_porte - 0.1 * k, 0.1) for k in range(1, 5)]
    for di, dp in (prove if prove_ is None else prove_):
        stato["chiave"] = (di, dp); stato["porte"] = unary_union([q.buffer(di) for q in interne] + [q.buffer(dp) for q in altre]) if sue else Polygon()
        trovato = next(((d, s_) for s_ in scosti for d in possibili(s_) if d >= 2.4 and tavolo_con(d, s_)), None) or next(((d, s_) for s_ in scosti for d in possibili(s_) if tavolo_con(d, s_)), None)
        if trovato:
            dist, sh = trovato; meglio = tavolo_con(dist, sh)
            log(f"zona giorno villa {villa}: divano a {dist:.1f} m dalla TV, scostato di {sh:.1f} m; {di:.1f} m liberi davanti alle porte interne, {dp:.1f} m davanti alle portefinestre"); break
    fatti = []
    if dist:
        cs = c + vv * (W / 2 + dist) + u * sh; p = Pezzo(cs, u, -vv, v["z0"])           # il divano guarda la TV: fronte = -vv
        p.scat(-1.15, 1.15, -0.475, 0.475, 0, 0.06, "metallo"); p.scat(-1.15, 1.15, -0.475, 0.475, 0.06, 0.40, "tessuto", "morbido")
        p.scat(-1.15, 1.15, -0.475, -0.25, 0.40, 0.82, "tessuto", "morbido")
        for su in (-1.15, 0.97): p.scat(su, su + 0.18, -0.25, 0.475, 0.40, 0.62, "tessuto", "morbido")
        for i in range(3): p.scat(-0.97 + i * 0.6467 + 0.01, -0.97 + (i + 1) * 0.6467 - 0.01, -0.25, 0.46, 0.40, 0.52, "tessuto", "morbido")
        for su in (-0.93, 0.55): p.scat(su, su + 0.40, -0.27, -0.12, 0.52, 0.86, "tessuto_accento", "morbido")
        ing = Polygon([tuple(cs + u * su + vv * sv) for su, sv in ((-1.15, -0.475), (1.15, -0.475), (1.15, 0.475), (-1.15, 0.475))])
        p.fine(f"Divano v{villa}", villa, "divano", ing); fatti.append(ing)
        fronte_tv, fronte_div = -W / 2 + 0.45, W / 2 + dist - 0.475          # il tavolino sta a metà tra mobile TV e divano
        ct = c + vv * ((fronte_tv + fronte_div) / 2) + u * sh; pt = min(0.30, max(0.20, (fronte_div - fronte_tv) / 2 - 0.42)); p = Pezzo(ct, u, vv, v["z0"])
        p.scat(-1.4, 1.4, -0.95, 0.95, 0, 0.012, "tappeto")
        p.scat(-0.55, 0.55, -pt, pt, 0.30, 0.335, "legno")
        for su in (-0.50, 0.47):
            for sv in (-pt + 0.05, pt - 0.08): p.scat(su, su + 0.03, sv, sv + 0.03, 0.012, 0.30, "metallo")
        ing = Polygon([tuple(ct + u * su + vv * sv) for su, sv in ((-0.55, -pt), (0.55, -pt), (0.55, pt), (-0.55, pt))])
        p.fine(f"Tavolino e tappeto v{villa}", villa, "tavolino", ing); fatti.append(ing)
    else: log(f"AVVISO villa {villa}: il divano non entra di fronte alla parete TV")
    if meglio:
        _, q, asse, pa, zona = meglio[:5]; al_muro = len(meglio) > 5; p = Pezzo(q, asse, pa, v["z0"])
        p.scat(-lt / 2, lt / 2, -wt, wt, 0.72, 0.76, "legno")
        for su in (-lt / 2 + 0.08, lt / 2 - 0.14):
            for sv in (-wt + 0.08, wt - 0.14): p.scat(su, su + 0.06, sv, sv + 0.06, 0, 0.72, "legno")
        lato = (n_p - 2 if al_muro else n_p // 2); passo_s = lt / lato
        for i in range(lato):
            cu = -lt / 2 + passo_s * (i + 0.5); sedia(p, (cu, wt + 0.17), (0, -1))
            if not al_muro: sedia(p, (cu, -wt - 0.17), (0, 1))
        if al_muro: sedia(p, (lt / 2 + 0.17, 0), (-1, 0)); sedia(p, (-lt / 2 - 0.17, 0), (1, 0))
        p.fine(f"Tavolo da {n_p} v{villa}", villa, "tavolo", zona.buffer(-0.2) if not al_muro else zona.buffer(-0.12))
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
    elif t == "parete_tv": parete_tv(p, L, W); tele_tv[(villa, v["nome"])] = (c, u, vv, L, W, nome)
    else: log("AVVISO: tipo non previsto:", t); continue
    p.fine(nome, villa, t, pol)
for a in A["arredi"]:
    if a["tipo"] != "zona_giorno": continue
    villa = int(a.get("villa", 1)); chiave = next((k for k in tele_tv if k[0] == villa and k[1].startswith(a["vano"])), None)
    if not chiave: log("AVVISO: zona giorno senza parete TV in", a["vano"]); continue
    v = next(x for x in vani if x["villa"] == villa and x["nome"] == chiave[1] and x["pol"].contains(Point(tele_tv[chiave][0])))
    ok = zona_giorno(a, v, villa, tele_tv[chiave]); conta["zona_giorno"] = conta.get("zona_giorno", 0) + 1
    log("zona giorno villa", villa, "| divano", ok[0], "| tavolo", ok[1])
# nessun mobile nello spazio spazzato dalle ante (proprietà "battuta" scritta da finiture_interni.py)
for o in scn.objects:
    if "battuta" not in o: continue
    bt = Polygon(list(zip(list(o["battuta"])[0::2], list(o["battuta"])[1::2]))).buffer(-0.03)
    for m_ in ARR.objects:
        ing = Polygon(list(zip(list(m_["ingombro"])[0::2], list(m_["ingombro"])[1::2]))).buffer(0)
        if int(m_.get("villa", 1)) == int(o.get("villa", 1)) and ing.intersects(bt) and not m_.name.endswith("(tessili)"):
            log(f"AVVISO: {o.name} aprendosi urta {m_.name} ({ing.intersection(bt).area:.2f} m² di sovrapposizione)")
log("arredi:", json.dumps(conta, ensure_ascii=False), "| oggetti", len(ARR.objects))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "contesto_progetto.blend"))
log("salvato", os.path.join(USCITA, "contesto_progetto.blend")); log("fine")
