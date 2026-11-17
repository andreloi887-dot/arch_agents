"""Banco di prova IN SCENA (2026-11-17): rifà solo i tessili di un pezzo dentro la scena vera della filiera (stanza, luci,
materiali con le texture, inquadrature di viste_controllo.txt) e lo rende con Cycles. Usa le stesse ricette della filiera
(blender/ricette_arredo.py), quindi ciò che si vede qui è ciò che esce dalla filiera con le stesse regolazioni.
Non salva il .blend. I risultati delle simulazioni finiscono nella cache dei tessili della filiera: se poi la filiera usa
le stesse regolazioni, li riprende senza rifarli.

  blender -b <modello>/uscita_blender/contesto_progetto.blend -P banco_scena.py -- pezzo=letto viste=letto_matrimoniale
          [nome=<parte del nome del pezzo>] [campioni=48] [scala=50] [out=<cartella>] [chiave=valore ...]

  pezzo     letto | divano | armadio  (il pezzo con la proprietà "ricetta" scritta da arredi_interni.py)
  nome      per scegliere tra più pezzi dello stesso tipo (predefinito: "Matrimoniale" per il letto)
  viste     nomi di viste_controllo.txt separati da virgola, oppure viste scritte per intero (nome:x,y,h,tx,ty,th[,focale])
            separate da ';'
  legno=1   rifà anche i materiali del legno (prova delle finiture) prima di rendere
  chiave=valore  regolazioni della ricetta (vedi ricette_arredo.py: g_pr, g_morb, pium_pr, plaid_piega, d_pr, varia, ...)
"""
import bpy, json, os, sys, time
QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(QUI, "..", "..", "rilievo-urbano", "scripts", "blender")))
from mathutils import Vector
from comune import cycles
import tessili, materiali_arredo as MA, ricette_arredo

P = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a)
pezzo = P.pop("pezzo", "letto"); viste = P.pop("viste", ""); campioni = int(P.pop("campioni", 48)); scala = int(P.pop("scala", 50))
nome_f = P.pop("nome", "" if pezzo == "divano" else "Matrimoniale"); legno = P.pop("legno", "0") == "1"
USCITA = os.path.dirname(bpy.data.filepath); MOD = os.path.dirname(USCITA)
out = P.pop("out", os.path.join(USCITA, "banco")); os.makedirs(out, exist_ok=True); etich = P.pop("etichetta", "prova")
O = {}
for k, v in P.items():
    try: O[k] = float(v)
    except ValueError: O[k] = v
scn = bpy.context.scene
tessili.CACHE = os.path.join(USCITA, "cache_tessili")
MA.configura(json.load(open(os.path.join(MOD, "arredi.json"), encoding="utf-8")).get("stile", {}))

cand = [o for o in bpy.data.objects if "ricetta" in o.keys() and json.loads(o["ricetta"])["tipo"] == pezzo and nome_f.lower() in o.name.lower()]
if not cand: sys.exit(f"nessun pezzo '{pezzo}' con la ricetta (nome con '{nome_f}'): rilancia la filiera da 'arredi'")
ob_p = cand[0]; R = json.loads(ob_p["ricetta"]); print("PEZZO", ob_p.name, "| regolazioni", O)
prefisso = f"Divano v{R['villa']} " if pezzo == "divano" else R["nome"] + " "
# solo i tessili delle ricette: la parte "morbida" del mobile stesso (materasso, base del divano) si chiama "<pezzo> (tessili)"
# e va lasciata (2026-11-17: il banco cancellava il materasso e i cuscini sembravano sospesi)
vecchi = [o for o in bpy.data.objects if o.name.startswith(prefisso) and o.name.endswith("(tessili)") and o.name != ob_p.name + " (tessili)"]
coll = vecchi[0].users_collection[0] if vecchi else scn.collection
for o in vecchi: bpy.data.objects.remove(o, do_unlink=True)
if legno: MA.MATS.clear()
t0 = time.time()
fatti, righe = getattr(ricette_arredo, pezzo)(scn, R, O)
for o in fatti:
    for c_ in list(o.users_collection): c_.objects.unlink(o)
    coll.objects.link(o)
for r_ in righe: print(r_)
print("SIMULAZIONE", round(time.time() - t0, 1), "s")
if legno:                                 # i materiali si rifanno in posto (stesso nome "Arredo k"): gli oggetti li vedono già
    for k in ("rovere", "legno"): MA.mat(k)

cycles(bpy, scn, campioni)
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080; scn.render.resolution_percentage = scala
scn.render.image_settings.file_format = "PNG"; scn.view_settings.exposure = float(os.environ.get("ESP", 0.6))
bg = next((n for n in scn.world.node_tree.nodes if n.type == "BACKGROUND"), None)
if bg: bg.inputs["Strength"].default_value = 1.0
z0 = min((o.matrix_world @ v.co).z for o in scn.objects if o.get("villa") == R.get("villa", 1) and str(o.get("vano", "")).startswith("Soggiorno") for v in o.data.vertices)
tutte = {}
for r_ in open(os.path.join(MOD, "viste_controllo.txt"), encoding="utf-8"):
    r_ = r_.strip()
    if r_ and not r_.startswith("#") and ":" in r_: tutte[r_.split(":")[0]] = r_.split(":")[1]
scelte = [(x, tutte[x]) for x in viste.split(",") if x in tutte] if ":" not in viste else [tuple(x.split(":")) for x in viste.split(";")]
cd = bpy.data.cameras.new("banco"); co = bpy.data.objects.new("banco", cd); scn.collection.objects.link(co); scn.camera = co; cd.clip_start = 0.05
for nome, val in scelte:
    n = [float(x) for x in val.split(",")]; cd.lens = n[6] if len(n) > 6 else 16
    p = Vector((n[0], n[1], z0 + n[2])); t = Vector((n[3], n[4], z0 + n[5])); co.location = p
    co.rotation_euler = (t - p).to_track_quat("-Z", "Y").to_euler()
    scn.render.filepath = os.path.join(out, f"{etich}_{nome}.png"); t1 = time.time(); bpy.ops.render.render(write_still=True)
    print("FATTO", scn.render.filepath, round(time.time() - t1, 1), "s")
