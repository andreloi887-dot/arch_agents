"""Percorsi di camera generati dalle regole (fasi 3 e 4 della filiera, vedi PROCEDIMENTO.md).

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P percorsi_camera.py -- <cartella modello>
          [--render] [--motore EEVEE|WORKBENCH] [--scala 50] [--passo 2] [--samples 8] [--solo drone,strada]
  python percorsi_camera.py -- <cartella modello> --blend contesto.blend ...     (Blender come modulo: pip install bpy)

Percorsi (camere animate, un fotogramma chiave per fotogramma, velocità costante):
  PERCORSO_drone           giro completo attorno al lotto, in quota, sguardo sul lotto; parte dal lato del sole,
                           così le prime facciate inquadrate sono in luce
  PERCORSO_strada_<nome>   camminata ad altezza d'occhio lungo ogni strada che tocca il lotto (asse DBGT, spostato
                           sul lato opposto al lotto), sguardo in avanti che si gira verso il lotto quando è davanti
Avvicinamento all'ingresso e interni: da aggiungere con il progetto IFC (servono cancelli e vani).

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
def percorso(nome, tipo, punti, mire, focale):
    """camera animata: punti e mire = una posizione (x, y, z) per fotogramma."""
    cd = bpy.data.cameras.new(nome); cd.lens = focale; cd.sensor_width = 36; cd.clip_start = 0.1; cd.clip_end = 2000
    co = bpy.data.objects.new(nome, cd); coll("Percorsi").objects.link(co)
    co.rotation_mode = "XYZ"; prec = None
    for i, (p, m) in enumerate(zip(punti, mire)):
        e = (Vector(m) - Vector(p)).to_track_quat("-Z", "Y").to_euler("XYZ")
        if prec: e.make_compatible(prec)          # niente salti di 360° tra un fotogramma e il successivo
        prec = e.copy(); co.location = p; co.rotation_euler = e
        co.keyframe_insert("location", frame=i + 1); co.keyframe_insert("rotation_euler", frame=i + 1)
    lib = PAR["spazio_libero_m"]; avvisi = []
    for i, p in enumerate(punti):
        if i % 5: continue
        d = spazio(Vector(p), lib); z = terreno(p[0], p[1])
        if d < lib: avvisi.append({"fotogramma": i + 1, "ostacolo_a_m": round(d, 2)})
        elif z is not None and p[2] - z < 0.5: avvisi.append({"fotogramma": i + 1, "sul_terreno_m": round(p[2] - z, 2)})
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

def voluto(tipo): return not SOLO or tipo in SOLO.split(",")
if voluto("drone"): drone()
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
        bpy.ops.render.render(animation=True); log("render", p["nome"], motore)
        ff = shutil.which("ffmpeg")
        if not ff: log("FFmpeg non trovato: restano le immagini in", cart); continue
        # i file hanno il numero del fotogramma (1, 1+passo, ...): si leggono in ordine alfabetico alla cadenza ridotta
        elenco = os.path.join(cart, "elenco.txt")
        with open(elenco, "w", encoding="utf-8") as fl:
            for nome_f in sorted(x for x in os.listdir(cart) if x.endswith(".png")):
                fl.write(f"file '{nome_f}'\nduration {passo / FPS:.6f}\n")
        mp4 = os.path.join(USCITA, "anteprime", p["nome"] + ".mp4")
        r = subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", elenco,
                            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "20", "-r", str(FPS), mp4], capture_output=True, text=True)
        log("video", mp4 if r.returncode == 0 else "ERRORE FFmpeg: " + r.stderr.strip()[:300])
log("fine")
