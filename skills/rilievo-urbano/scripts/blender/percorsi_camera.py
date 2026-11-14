"""Percorsi di camera generati dalle regole (fasi 3 e 4 della filiera, vedi PROCEDIMENTO.md).

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P percorsi_camera.py -- <cartella modello>
          [--render] [--motore EEVEE|WORKBENCH] [--scala 50] [--passo 2] [--samples 8] [--solo drone,strada,interni]
          [--villa 1,2] [--fotogrammi 1,200,400]
  python percorsi_camera.py -- <cartella modello> --blend contesto.blend ...     (Blender come modulo: pip install bpy)

Percorsi (camere animate, un fotogramma chiave per fotogramma, velocità costante):
  PERCORSO_drone           giro completo attorno al lotto, in quota, sguardo sul lotto; parte dal lato del sole,
                           così le prime facciate inquadrate sono in luce
  PERCORSO_strada_<nome>   camminata ad altezza d'occhio lungo ogni strada che tocca il lotto (asse DBGT, spostato
                           sul lato opposto al lotto), sguardo in avanti che si gira verso il lotto quando è davanti
  PERCORSO_interni_villa<n>  visita di ogni unità abitativa: dentro dalla porta d'ingresso, stanza per stanza attraverso
                           le porte (che si nascondono: porta aperta), luce a soffitto in ogni stanza. Servono i vani
                           IfcSpace con il nome della stanza. Piani raggiunti solo da scala: da fare
Avvicinamento all'ingresso: da aggiungere.
--fotogrammi 1,200,400: con --render, solo questi fotogrammi (immagini chiave) invece del video.

Valori in <modello>/lotto.json → "percorsi" (tutti facoltativi; i predefiniti sono in PRED qui sotto).
Lotto: <modello>/perimetro_progetto.json se c'è (scritto da importa_progetto.py), altrimenti la superficie del lotto
di contesto.json.

Controlli automatici (fase 4): per ogni percorso la distanza minima dagli ostacoli attorno alla camera e la quota
sul terreno; i fotogrammi sotto soglia finiscono nel log e in percorsi.json ("avvisi").

Uscite in <modello>/uscita_blender/: scena_percorsi.blend, percorsi.json (punti, durata, avvisi: indipendente dal
software, serve anche a Sequencer in Unreal); con --render anteprime/<percorso>/f_####.png e anteprime/<percorso>.mp4
(FFmpeg). Il render riprende dai fotogrammi già fatti. WORKBENCH: animatic veloce senza luce reale, per giudicare
solo il movimento (utile senza scheda grafica); EEVEE: anteprima con sole e materiali.
"""
import bpy, json, math, os, shutil, subprocess, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, registro
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import linemerge, unary_union

argv, opt = argomenti()
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
if opt("--blend"): bpy.ops.wm.open_mainfile(filepath=os.path.join(USCITA, opt("--blend")))
L = json.load(open(os.path.join(MOD, "lotto.json"), encoding="utf-8"))
log = registro(os.path.join(USCITA, "percorsi.log"))
scn = bpy.context.scene
log("scena", bpy.data.filepath)

PRED = {"fps": 25, "risoluzione": [1920, 1080], "occhio_m": 1.65, "focale_strada_mm": 24, "focale_drone_mm": 28,
        "velocita_cammino_m_s": 1.6,
        "drone": {"quota_m": 26.0, "distanza_dal_lotto_m": 28.0, "durata_s": 24.0, "mira_m": 3.0},
        "strada": {"scostamento_m": 1.5, "distanza_max_dal_lotto_m": 15.0, "margine_area_m": 12.0, "raggio_dal_lotto_m": 45.0,
                   "lunghezza_minima_m": 25.0, "sguardo_avanti_m": 10.0, "peso_lotto": 0.5},
        "interni": {"occhio_m": 1.55, "velocita_m_s": 0.7, "focale_mm": 18, "spazio_libero_m": 0.25, "fuori_dalla_porta_m": 2.5,
                    "oltre_la_porta_m": 0.6, "giro_sguardo_s": 1.5, "luce_w_m2": 12.0, "luce_colore": [1.0, 0.9, 0.78],
                    "esterni": ["Cortile", "Balcone", "Veranda", "Terrazza", "Portico", "Giardino"], "ingressi": {}},
        "spazio_libero_m": 0.6, "collezioni_suolo": ["Terreno", "Strade"]}
def unisci(a, b):
    return {k: (unisci(a[k], b[k]) if isinstance(a[k], dict) and isinstance(b.get(k), dict) else b.get(k, a[k])) for k in a}
PAR = unisci(PRED, {k: v for k, v in L.get("percorsi", {}).items() if not k.startswith("_")})
FPS = int(PAR["fps"]); SOLO = opt("--solo")

O = L["origine"]
def locale(lat, lng):
    """equirettangolare sull'ellissoide, come importa_contesto.py."""
    a, e2 = 6378137.0, 0.00669437999014; la = math.radians(O["lat"])
    Mr = a * (1 - e2) / (1 - e2 * math.sin(la) ** 2) ** 1.5; Nr = a / math.sqrt(1 - e2 * math.sin(la) ** 2)
    return (math.radians(lng - O["lng"]) * Nr * math.cos(la), math.radians(lat - O["lat"]) * Mr)

# ------------------------------------------------------------------------------------------------ lotto
pp = os.path.join(MOD, "perimetro_progetto.json")
if os.path.exists(pp):
    LOTTO = Polygon(json.load(open(pp, encoding="utf-8"))["anello"]).buffer(0); log("lotto: perimetro di progetto")
else:
    CT = json.load(open(os.path.join(MOD, "contesto.json"), encoding="utf-8"))
    s = next(s for s in CT["superfici"] if s["nome"].startswith(L["lotto"]["id"]))
    V = s["vertici"]; LOTTO = unary_union([Polygon([V[i][:2] for i in t]) for t in s["triangoli"]]).buffer(0.01)
    log("lotto: superficie del contesto", s["nome"])
CEN = LOTTO.centroid
RAGGIO = max(CEN.distance(Point(p)) for p in LOTTO.convex_hull.exterior.coords)

deps = bpy.context.evaluated_depsgraph_get()
CAMERE_PRIMA = [o for o in scn.objects if o.name.startswith("PERCORSO_")]
for o in CAMERE_PRIMA: bpy.data.objects.remove(o, do_unlink=True)      # rilancio: i percorsi si rifanno da capo
deps.update()
SUOLO = set(PAR["collezioni_suolo"])
def terreno(x, y, da=500.0):
    """quota del suolo: il primo oggetto delle collezioni di suolo sotto (x, y); chiome, lampioni e tetti si saltano.
    Senza suolo sotto il punto, la prima superficie incontrata."""
    z, primo = da, None
    for _ in range(40):
        hit, loc, _n, _i, ob, _m = scn.ray_cast(deps, Vector((x, y, z)), Vector((0, 0, -1)))
        if not hit: return primo
        if any(c.name in SUOLO for c in ob.users_collection): return loc.z
        if primo is None: primo = loc.z
        z = loc.z - 0.02
    return primo
def spazio(p, r):
    """distanza dall'ostacolo più vicino attorno alla camera (8 direzioni orizzontali), al massimo r."""
    m = r
    for k in range(8):
        a = k * math.pi / 4
        hit, loc, *_ = scn.ray_cast(deps, p, Vector((math.cos(a), math.sin(a), 0)), distance=r)
        if hit: m = min(m, (loc - p).length)
    return m

def liscia(v, n):
    """media mobile centrata su 2n+1 valori (estremi con finestra ridotta)."""
    return [sum(v[max(0, i - n):i + n + 1]) / len(v[max(0, i - n):i + n + 1]) for i in range(len(v))]

# ------------------------------------------------------------------------------------------------ camere
def coll(nome):
    c = bpy.data.collections.get(nome)
    if not c: c = bpy.data.collections.new(nome); scn.collection.children.link(c)
    return c
PERCORSI = []
def percorso(nome, tipo, punti, mire, focale, libero=None):
    """camera animata: punti e mire = una posizione (x, y, z) per fotogramma."""
    cd = bpy.data.cameras.new(nome); cd.lens = focale; cd.sensor_width = 36; cd.clip_start = 0.05 if tipo == "interni" else 0.1; cd.clip_end = 2000
    co = bpy.data.objects.new(nome, cd); coll("Percorsi").objects.link(co)
    co.rotation_mode = "XYZ"; prec = None
    for i, (p, m) in enumerate(zip(punti, mire)):
        e = (Vector(m) - Vector(p)).to_track_quat("-Z", "Y").to_euler("XYZ")
        if prec: e.make_compatible(prec)          # niente salti di 360° tra un fotogramma e il successivo
        prec = e.copy(); co.location = p; co.rotation_euler = e
        co.keyframe_insert("location", frame=i + 1); co.keyframe_insert("rotation_euler", frame=i + 1)
    lib = libero or PAR["spazio_libero_m"]; avvisi = []
    for i, p in enumerate(punti):
        if i % 5: continue
        d = spazio(Vector(p), lib); z = terreno(p[0], p[1])
        if d < lib: avvisi.append({"fotogramma": i + 1, "ostacolo_a_m": round(d, 2)})
        elif tipo != "interni" and z is not None and p[2] - z < 0.5: avvisi.append({"fotogramma": i + 1, "sul_terreno_m": round(p[2] - z, 2)})
    lung = sum((Vector(punti[i + 1]) - Vector(punti[i])).length for i in range(len(punti) - 1))
    co["percorso"] = tipo; co["fotogrammi"] = len(punti); co["res"] = list(PAR["risoluzione"])
    PERCORSI.append({"nome": nome, "tipo": tipo, "fotogrammi": len(punti), "durata_s": round(len(punti) / FPS, 2),
                     "lunghezza_m": round(lung, 1), "focale_mm": focale, "avvisi": avvisi,
                     "punti": [[round(c, 3) for c in p] for p in punti[::FPS]],
                     "mire": [[round(c, 3) for c in m] for m in mire[::FPS]]})
    log(f"{nome}: {len(punti)} fotogrammi, {len(punti) / FPS:.1f} s, {lung:.0f} m, avvisi {len(avvisi)}")
    return co

# ------------------------------------------------------------------------------------------------ drone
def drone():
    D = PAR["drone"]; n = int(round(D["durata_s"] * FPS)); R = RAGGIO + D["distanza_dal_lotto_m"]
    z0 = terreno(CEN.x, CEN.y) or 0.0
    sole = scn.get("sole"); az = float(sole["azimut"]) if sole else 180.0     # azimut da Nord, orario
    punti, mire = [], []
    for i in range(n):
        a = math.radians(az + 360.0 * i / n)                                  # giro orario visto dall'alto
        punti.append((CEN.x + R * math.sin(a), CEN.y + R * math.cos(a), z0 + D["quota_m"]))
        mire.append((CEN.x, CEN.y, z0 + D["mira_m"]))
    percorso("PERCORSO_drone", "drone", punti, mire, PAR["focale_drone_mm"])

# ------------------------------------------------------------------------------------------------ strade
def assi_strade():
    """assi DBGT uniti per nome di strada, in coordinate locali, ritagliati all'area del contesto."""
    p = L["dati"].get("dbgt", {}).get("assi")
    if not p or not os.path.exists(os.path.join(MOD, p)): return {}
    S = PAR["strada"]; lato = L["semilato_m"] - S["margine_area_m"]; area = box(-lato, -lato, lato, lato)
    area = area.intersection(LOTTO.buffer(S["raggio_dal_lotto_m"]))        # la camminata resta dove il lotto si vede
    per_nome = {}
    for f in json.load(open(os.path.join(MOD, p), encoding="utf-8"))["features"]:
        g = f["geometry"]; linee = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        nome = (f["properties"].get("nome") or "senza nome").strip()
        for ln in linee: per_nome.setdefault(nome, []).append(LineString([locale(c[1], c[0]) for c in ln]))
    out = {}
    for nome, linee in per_nome.items():
        m = linemerge(unary_union(linee)).intersection(area)
        pezzi = [q for q in (m.geoms if hasattr(m, "geoms") else [m]) if q.geom_type == "LineString" and q.length > 0]
        pezzi = [q for q in pezzi if q.distance(LOTTO) <= S["distanza_max_dal_lotto_m"] and q.length >= S["lunghezza_minima_m"]]
        if pezzi: out[nome] = max(pezzi, key=lambda q: q.length)
    return out

def strada(nome, asse):
    S = PAR["strada"]; passo = PAR["velocita_cammino_m_s"] / FPS
    # si cammina verso il lotto: parte l'estremo più lontano dal punto dell'asse più vicino al lotto
    s_lotto = asse.project(CEN)
    if s_lotto < asse.length / 2: asse = LineString(list(asse.coords)[::-1])
    n = int(asse.length / passo); pts = [asse.interpolate(i * passo) for i in range(n + 1)]
    fin = int(round(4.0 / passo))                                           # curve arrotondate su ±4 m
    xs = liscia([p.x for p in pts], fin); ys = liscia([p.y for p in pts], fin)
    # lato opposto al lotto: un solo segno per tutto il percorso (maggioranza), così la camera non attraversa la strada
    tang = [(xs[min(i + 1, n)] - xs[max(i - 1, 0)], ys[min(i + 1, n)] - ys[max(i - 1, 0)]) for i in range(n + 1)]
    tang = [(tx / (math.hypot(tx, ty) or 1), ty / (math.hypot(tx, ty) or 1)) for tx, ty in tang]
    voto = sum(1 if (-ty * (CEN.x - x) + tx * (CEN.y - y)) > 0 else -1 for (tx, ty), x, y in zip(tang, xs, ys))
    sg = -1 if voto > 0 else 1
    xs = [x - ty * sg * S["scostamento_m"] for x, (tx, ty) in zip(xs, tang)]
    ys = [y + tx * sg * S["scostamento_m"] for y, (tx, ty) in zip(ys, tang)]
    zs = [terreno(x, y) for x, y in zip(xs, ys)]
    zs = [z if z is not None else next((q for q in zs if q is not None), 0.0) for z in zs]
    zs = [z + PAR["occhio_m"] for z in liscia(zs, int(round(2.0 / passo)))]  # niente scatti su cordoli e caditoie
    av = int(round(S["sguardo_avanti_m"] / passo)); z_lotto = (terreno(CEN.x, CEN.y) or 0.0) + PAR["occhio_m"]
    punti, mire = [], []
    for i in range(n + 1 - av):
        p = Vector((xs[i], ys[i], zs[i])); t = (Vector((xs[i + av], ys[i + av], zs[i + av])) - p).normalized()
        dl = Vector((CEN.x, CEN.y, z_lotto)) - p; dl.z *= 0.5; dl.normalize()
        w = S["peso_lotto"] * max(0.0, t.dot(dl) + 0.2) / 1.2                  # il lotto alle spalle non attira lo sguardo
        punti.append(tuple(p)); mire.append(tuple(p + (t + w * dl).normalized() * 10.0))
    # sguardo lisciato: la mira è il risultato di due direzioni che cambiano, va tenuta morbida
    k = int(round(1.0 * FPS))
    mire = list(zip(liscia([m[0] for m in mire], k), liscia([m[1] for m in mire], k), liscia([m[2] for m in mire], k)))
    pulito = "".join(c if c.isalnum() else "_" for c in nome.title()).strip("_")
    percorso("PERCORSO_strada_" + pulito, "strada", punti, mire, PAR["focale_strada_mm"])

# ------------------------------------------------------------------------------------------------ interni
def interni():
    """un percorso per ogni unità (vani collegati da porte) che ha una porta d'ingresso dal cortile: si entra, si visita
    ogni stanza passando dalle porte e si torna nel disimpegno. Vani = oggetti nascosti con la proprietà "vano"
    (importa_progetto.py); le porte attraversate si nascondono (porta aperta). Una luce per stanza, a soffitto."""
    from shapely.geometry import MultiPoint
    from shapely.ops import nearest_points
    I = PAR["interni"]; passo = I["velocita_m_s"] / FPS
    solo_ville = [int(x) for x in opt("--villa").split(",")] if opt("--villa") else None
    vani = []
    for ob in scn.objects:
        if "vano" not in ob or ob.type != "MESH": continue
        W = [ob.matrix_world @ v.co for v in ob.data.vertices]; z0 = min(w.z for w in W); z1 = max(w.z for w in W)
        base = [Polygon([W[i].xy[:] for i in pl.vertices]) for pl in ob.data.polygons if all(W[i].z < z0 + 0.05 for i in pl.vertices)]
        pol = unary_union([q for q in base if q.is_valid and q.area > 1e-6]).buffer(0.01)
        if pol.is_empty: continue
        if pol.geom_type != "Polygon": pol = max(pol.geoms, key=lambda q: q.area)
        vani.append({"nome": ob["vano"], "ob": ob.name, "pol": pol, "z0": z0, "z1": z1, "villa": int(ob.get("villa", 1)),
                     "esterno": ob["vano"].startswith(tuple(I["esterni"])), "porte": []})
    if not vani: log("interni: nessun vano nella scena (serve contesto_progetto.blend con gli IfcSpace)"); return
    def dentro(v):
        """punto di vista della stanza: il punto interno più lontano dai muri."""
        best, pb = -1.0, v["pol"].representative_point(); x0, y0, x1, y1 = v["pol"].bounds; n = 24
        for i in range(n + 1):
            for j in range(n + 1):
                q = Point(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * j / n)
                if v["pol"].contains(q):
                    d = v["pol"].exterior.distance(q)
                    if d > best: best, pb = d, q
        return pb
    for v in vani: v["centro"] = dentro(v)
    # porte: centro, larghezza e normale dal rettangolo minimo in pianta; vani toccati sullo stesso piano
    porte = []
    for ob in scn.objects:
        if ob.get("ifc_classe") != "IfcDoor" or ob.type != "MESH" or not ob.data.vertices: continue
        W = [ob.matrix_world @ v.co for v in ob.data.vertices]; zmin = min(w.z for w in W)
        r = list(MultiPoint([w.xy[:] for w in W]).minimum_rotated_rectangle.exterior.coords)
        l1 = Vector(r[1]) - Vector(r[0]); l2 = Vector(r[2]) - Vector(r[1])
        lungo, corto = (l1, l2) if l1.length >= l2.length else (l2, l1)
        c = Point(sum(q[0] for q in r[:4]) / 4, sum(q[1] for q in r[:4]) / 4)
        vicini = sorted((v["pol"].distance(c), k) for k, v in enumerate(vani) if v["z0"] - 0.4 <= zmin <= v["z1"] - 1.0)
        tocca = [k for d, k in vicini if d < 0.6][:2]
        porte.append({"ob": ob.name, "c": c, "z": zmin, "larg": lungo.length, "n": corto.normalized() if corto.length else Vector((1, 0)),
                      "vani": tocca, "villa": int(ob.get("villa", 1))})
    archi = {k: [] for k in range(len(vani))}          # vano → [(altro vano, porta | None, punto di passaggio)]
    for kp, pt in enumerate(porte):
        ins = [k for k in pt["vani"] if not vani[k]["esterno"]]
        if len(ins) == 2:
            archi[ins[0]].append((ins[1], kp, pt["c"])); archi[ins[1]].append((ins[0], kp, pt["c"]))
    # stanze senza porta verso le altre (cucina a vista): passaggio libero verso il vano adiacente, se la visuale è libera
    for k, v in enumerate(vani):
        if v["esterno"] or archi[k]: continue
        for j, u in sorted(enumerate(vani), key=lambda t: v["pol"].distance(t[1]["pol"])):
            if j == k or u["esterno"] or abs(u["z0"] - v["z0"]) > 0.3 or v["pol"].distance(u["pol"]) > 0.6: continue
            a_, b_ = nearest_points(v["pol"].buffer(-0.5), u["pol"].buffer(-0.5)) if not v["pol"].buffer(-0.5).is_empty and not u["pol"].buffer(-0.5).is_empty else nearest_points(v["pol"], u["pol"])
            o_ = Vector((a_.x, a_.y, v["z0"] + 1.2)); d_ = Vector((b_.x, b_.y, v["z0"] + 1.2)) - o_
            if d_.length < 1e-3 or not scn.ray_cast(deps, o_, d_.normalized(), distance=d_.length)[0]:
                pm = Point((a_.x + b_.x) / 2, (a_.y + b_.y) / 2)
                archi[k].append((j, None, pm)); archi[j].append((k, None, pm)); break
    # unità: componenti connesse dei vani interni
    visti, unita = set(), []
    for k, v in enumerate(vani):
        if v["esterno"] or k in visti: continue
        comp, coda = [], [k]; visti.add(k)
        while coda:
            a_ = coda.pop(); comp.append(a_)
            for j, _p, _c in archi[a_]:
                if j not in visti: visti.add(j); coda.append(j)
        unita.append(comp)
    luci = bpy.data.collections.get("Luci interni")
    if luci:
        for o in list(luci.objects): bpy.data.objects.remove(o, do_unlink=True)
    n_un = {}
    for comp in sorted(unita, key=lambda c: (vani[c[0]]["villa"], min(vani[k]["z0"] for k in c))):
        villa = vani[comp[0]]["villa"]
        if solo_ville and villa not in solo_ville: continue
        n_un[villa] = n_un.get(villa, 0) + 1
        nome = f"PERCORSO_interni_villa{villa}" + (f"_{n_un[villa]}" if n_un[villa] > 1 else "")
        stanze = ", ".join(vani[k]["nome"] for k in comp)
        # ingresso: porta con un solo vano interno di questa unità e, dall'altra parte, un cortile o niente (non un balcone)
        cand = []
        for kp, pt in enumerate(porte):
            ins = [k for k in pt["vani"] if k in comp]; altri = [k for k in pt["vani"] if k not in comp]
            if len(ins) != 1 or any(vani[k]["esterno"] and not vani[k]["nome"].startswith("Cortile") for k in altri): continue
            if any(not vani[k]["esterno"] for k in altri): continue
            cand.append((kp, ins[0]))
        voluta = I["ingressi"].get(nome)
        if voluta: cand = [c for c in cand if porte[c[0]]["ob"] == voluta] or cand
        if not cand: log(f"{nome}: nessun ingresso dal cortile (piano raggiunto da scala o da veranda: da fare) – {stanze}"); continue
        # la porta d'ingresso è quella larga come una porta, non una portafinestra; a parità, soggiorno o disimpegno
        kp0, k0 = min(cand, key=lambda c: (abs(porte[c[0]]["larg"] - 1.0) > 0.25, not vani[c[1]]["nome"].startswith(("Soggiorno", "Ingresso", "Dis")), abs(porte[c[0]]["larg"] - 1.0)))
        def attraverso(kp, da, verso):
            """due punti ai lati della porta, sulla sua normale: la camera la passa dritta, lontana dagli stipiti."""
            pt = porte[kp]; c = Vector((pt["c"].x, pt["c"].y)); n = pt["n"].copy()
            if n.dot(Vector((verso.x, verso.y)) - c) < 0: n = -n
            return [tuple(c - n * I["oltre_la_porta_m"]), tuple(c + n * I["oltre_la_porta_m"])]
        usate = {kp0}; tappe = []; c0 = vani[k0]["centro"]
        pt0 = porte[kp0]; n0 = pt0["n"].copy(); cc = Vector((pt0["c"].x, pt0["c"].y))
        if n0.dot(Vector((c0.x, c0.y)) - cc) < 0: n0 = -n0
        tappe.append((tuple(cc - n0 * I["fuori_dalla_porta_m"]), vani[k0]["z0"]))
        tappe += [(q, vani[k0]["z0"]) for q in attraverso(kp0, None, c0)]
        fatti = set()
        def visita(k):
            fatti.add(k); v = vani[k]; tappe.append(((v["centro"].x, v["centro"].y), v["z0"]))
            for j, kp, pm in sorted(archi[k], key=lambda t: vani[t[0]]["pol"].area):   # prima le stanze piccole
                if j in fatti: continue
                if kp is not None:
                    usate.add(kp); tappe.extend((q, v["z0"]) for q in attraverso(kp, k, vani[j]["centro"]))
                else: tappe.append(((pm.x, pm.y), v["z0"]))
                visita(j)
                if kp is not None: tappe.extend((q, v["z0"]) for q in reversed(attraverso(kp, k, vani[j]["centro"])))
                else: tappe.append(((pm.x, pm.y), v["z0"]))
                tappe.append(((v["centro"].x, v["centro"].y), v["z0"]))
        visita(k0)
        while len(tappe) > 1 and tappe[-1][0] == tappe[-2][0]: tappe.pop()
        linea = LineString([t[0] for t in tappe]); n = max(2, int(linea.length / passo))
        pts = [linea.interpolate(i * passo) for i in range(n + 1)]
        fin = int(round(0.35 / passo))                                    # angoli appena arrotondati: le porte sono strette
        xs = liscia([q.x for q in pts], fin); ys = liscia([q.y for q in pts], fin)
        z = tappe[0][1] + I["occhio_m"]
        # sguardo: direzione di marcia, con l'angolo (non il vettore) lisciato: a fine stanza la camera si gira con una panoramica
        av = max(1, int(round(0.8 / passo))); ang = []; prec = 0.0
        for i in range(n + 1):
            j = min(i + av, n); dx, dy = xs[j] - xs[i], ys[j] - ys[i]
            a_ = math.atan2(dy, dx) if math.hypot(dx, dy) > 1e-4 else prec
            while a_ - prec > math.pi: a_ -= 2 * math.pi
            while a_ - prec < -math.pi: a_ += 2 * math.pi
            ang.append(a_); prec = a_
        ang = liscia(ang, int(round(I["giro_sguardo_s"] * FPS / 2)))
        punti = [(x, y, z) for x, y in zip(xs, ys)]
        mire = [(x + 5 * math.cos(a_), y + 5 * math.sin(a_), z - 0.25) for x, y, a_ in zip(xs, ys, ang)]
        for kp in usate:
            o = scn.objects.get(porte[kp]["ob"])
            if o: o.hide_render = True; o.hide_viewport = True; o["porta_aperta"] = True
        deps.update()
        percorso(nome, "interni", punti, mire, I["focale_mm"], libero=I["spazio_libero_m"])
        PERCORSI[-1]["stanze"] = [vani[k]["nome"] for k in comp]; PERCORSI[-1]["porte_aperte"] = sorted(porte[kp]["ob"] for kp in usate)
        log(f"  {nome}: ingresso {porte[kp0]['ob']} ({porte[kp0]['larg']:.2f} m) → {stanze}; porte aperte {len(usate)}")
        for k in comp:                                                   # luce a soffitto, potenza per superficie
            v = vani[k]; ld = bpy.data.lights.new("Luce " + v["nome"], "AREA"); ld.shape = "DISK"; ld.size = 0.6
            ld.energy = I["luce_w_m2"] * v["pol"].area; ld.color = I["luce_colore"]
            lo = bpy.data.objects.new(f"Luce {v['nome']} v{villa}", ld); coll("Luci interni").objects.link(lo)
            lo.location = (v["centro"].x, v["centro"].y, v["z1"] - 0.15)

def voluto(tipo): return not SOLO or tipo in SOLO.split(",")
if voluto("drone"): drone()
if voluto("interni"): interni()
if voluto("strada"):
    assi = assi_strade()
    if not assi: log("strade: nessun asse DBGT vicino al lotto (lotto.json → dati.dbgt.assi)")
    for nome, asse in sorted(assi.items()): strada(nome, asse)

scn.render.fps = FPS
scn.frame_start = 1; scn.frame_end = max([p["fotogrammi"] for p in PERCORSI] or [1])
json.dump({"_nota": "percorsi di camera in coordinate locali del contesto (x Est, y Nord, z quota), un punto al secondo",
           "origine": O, "fps": FPS, "parametri": PAR, "percorsi": PERCORSI},
          open(os.path.join(USCITA, "percorsi.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(USCITA, "scena_percorsi.blend"))
log("salvato", os.path.join(USCITA, "scena_percorsi.blend"))

# ------------------------------------------------------------------------------------------------ anteprime
if "--render" in argv:
    motore = (opt("--motore", "EEVEE") or "EEVEE").upper(); passo = int(opt("--passo", "2"))
    if motore == "WORKBENCH":
        scn.render.engine = "BLENDER_WORKBENCH"; sh = scn.display.shading
        sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
        scn.view_settings.view_transform = "Standard"; scn.view_settings.look = "None"; scn.view_settings.exposure = 0
    elif opt("--samples"):
        try: scn.eevee.taa_render_samples = int(opt("--samples"))
        except Exception: pass
    scn.render.resolution_percentage = int(opt("--scala", "50"))
    scn.render.image_settings.file_format = "PNG"; scn.render.use_overwrite = False   # riprende dai fotogrammi fatti
    scn.frame_step = passo
    for p in PERCORSI:
        co = scn.objects[p["nome"]]; cart = os.path.join(USCITA, "anteprime", p["nome"])
        scn.camera = co; scn.render.resolution_x, scn.render.resolution_y = co["res"]
        scn.frame_start = 1; scn.frame_end = p["fotogrammi"]; scn.render.filepath = os.path.join(cart, "f_")
        if opt("--fotogrammi"):
            for fr in (int(x) for x in opt("--fotogrammi").split(",")):
                if fr > p["fotogrammi"]: continue
                scn.frame_set(fr); scn.render.filepath = os.path.join(cart, f"chiave_{fr:04d}.png")
                bpy.ops.render.render(write_still=True)
            log("immagini chiave", p["nome"], motore); continue
        bpy.ops.render.render(animation=True); log("render", p["nome"], motore)
        ff = shutil.which("ffmpeg")
        if not ff: log("FFmpeg non trovato: restano le immagini in", cart); continue
        # i file hanno il numero del fotogramma (1, 1+passo, ...): si leggono in ordine alfabetico alla cadenza ridotta
        elenco = os.path.join(cart, "elenco.txt")
        with open(elenco, "w", encoding="utf-8") as fl:
            for nome_f in sorted(x for x in os.listdir(cart) if x.startswith("f_") and x.endswith(".png")):
                fl.write(f"file '{nome_f}'\nduration {passo / FPS:.6f}\n")
        mp4 = os.path.join(USCITA, "anteprime", p["nome"] + ".mp4")
        r = subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", elenco,
                            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "20", "-r", str(FPS), mp4], capture_output=True, text=True)
        log("video", mp4 if r.returncode == 0 else "ERRORE FFmpeg: " + r.stderr.strip()[:300])
log("fine")
