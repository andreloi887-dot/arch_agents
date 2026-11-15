"""Import in Unreal Engine 5.8 della scena esportata da Blender (esporta_usd.py). Fase 5 di PROCEDIMENTO.md.
Provato sul PC di Andrea il 2026-11-15 (UE 5.8, da riga di comando); note in PROGRAMMA_INTERNI.md, sezione 10.

  UnrealEditor-Cmd.exe <progetto>.uproject -run=pythonscript -script="<repo>/skills/rilievo-urbano/scripts/unreal/importa_usd.py <modello>/uscita_blender/usd" -unattended -nosplash -nop4 -stdout -FullStdOutLogOutput
  (dentro l'editor: Output Log › Python:  py "<...>/importa_usd.py" "<cartella usd>")

Servono i plugin "USDImporter", "PythonScriptPlugin", "EditorScriptingUtilities" attivi nel progetto.

Cosa fa: cancella e rifà /Game/Progetto (si può rilanciare), livello nuovo /Game/Progetto/Scena, importa scena.usdc
e camere.usdc come asset veri (mesh, materiali, luci, camere; dalle camere animate una Level Sequence), così il livello
si riapre subito e materiali e mobili si possono sostituire. Usa il sole esportato da Blender come sole dell'atmosfera;
rende mobili tutte le luci (Lumen, niente illuminazione da calcolare); aggiunge atmosfera, luce del cielo, nebbia,
post-produzione con Lumen ed esposizione automatica. Salva tutto.
Controllo finale: righe "CONTROLLO" nel log e usd/controllo_unreal.json, che filiera.py confronta da sola con
usd/riferimento.json (scritto da esporta_usd.py).

Perché non lo USD Stage Actor (prima bozza): in commandlet non espone le mesh, gli asset restano transitori e il
livello si ricarica in 3-8 minuti a ogni apertura.
"""
import json, os, sys
import unreal

# -script="file cartella" spezza la cartella agli spazi (provato, 2026-11-15): si riuniscono gli argomenti
USD = " ".join(sys.argv[1:]).strip().strip('"')
RADICE = "/Game/Progetto"
LIVELLO = RADICE + "/Scena"
if not os.path.isfile(os.path.join(USD, "scena.usdc")): raise SystemExit(f"scena.usdc non trovato in {USD!r}")

asset_lib = unreal.EditorAssetLibrary
livelli = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
attori = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# rilancio (provato 2026-11-15): in commandlet il .umap cancellato resta su disco e new_level poi rifiuta il percorso.
# Quindi: il livello esistente si apre, si svuota e si salva; solo dopo, quando nessuno li usa più, gli asset importati
# (scena/, camere/) si cancellano e si rifanno (con il livello che li usa ancora, delete_directory li lascia).
if asset_lib.does_asset_exist(LIVELLO):
    if not livelli.load_level(LIVELLO): raise SystemExit(f"livello {LIVELLO} non aperto")
    for a in attori.get_all_level_actors(): attori.destroy_actor(a)
    livelli.save_current_level(); unreal.log(f"svuotato {LIVELLO}")
elif not livelli.new_level(LIVELLO): raise SystemExit(f"livello {LIVELLO} non creato")
for sotto in ("scena", "camere"):
    d = f"{RADICE}/{sotto}"
    if asset_lib.does_directory_exist(d):
        asset_lib.delete_directory(d)
        # in commandlet il registro continua a elencare gli asset cancellati: si controlla il disco
        disco = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()), d[len("/Game/"):])
        rimasti = [f for _, _, ff in os.walk(disco) for f in ff if f.endswith(".uasset")]
        if rimasti: raise SystemExit(f"non riesco a svuotare {d}: {len(rimasti)} file, es. {rimasti[:3]}")
        unreal.log(f"cancellato {d}")

def importa(nome, sequenze):
    f = os.path.join(USD, nome + ".usdc")
    if not os.path.isfile(f): unreal.log_warning(f"manca {f}"); return
    op = unreal.UsdStageImportOptions()
    op.set_editor_property("import_actors", True)
    op.set_editor_property("import_geometry", True)
    op.set_editor_property("import_materials", True)
    op.set_editor_property("import_level_sequences", sequenze)
    op.set_editor_property("existing_actor_policy", unreal.ReplaceActorPolicy.REPLACE)
    op.set_editor_property("existing_asset_policy", unreal.ReplaceAssetPolicy.REPLACE)
    t = unreal.AssetImportTask()
    for k, v in (("filename", f), ("destination_path", f"{RADICE}/{nome}"), ("automated", True), ("save", True),
                 ("replace_existing", True), ("options", op)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    unreal.log(f"importato {f}: {len(t.get_editor_property('imported_object_paths') or [])} oggetti")

importa("scena", False)
importa("camere", True)

def metti(classe, nome, pos=(0, 0, 0), rot=(0, 0, 0)):
    a = attori.spawn_actor_from_class(classe, unreal.Vector(*pos), unreal.Rotator(*rot)); a.set_actor_label(nome); return a

# sole: quello di Blender (DistantLight → DirectionalLight) diventa il sole dell'atmosfera; uno solo
soli = [a for a in attori.get_all_level_actors() if a.get_component_by_class(unreal.DirectionalLightComponent)]
if not soli: soli = [metti(unreal.DirectionalLight, "Sole", rot=(-45, 140, 0))]; unreal.log_warning("sole non importato: aggiunto")
for i, a in enumerate(soli):
    a.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", i == 0)
# le luci arrivano "stazionarie": chiederebbero il calcolo dell'illuminazione e nell'editor la scena resta nera
# (visto il 2026-11-15). Con Lumen devono essere mobili.
n_mob = 0
for a in attori.get_all_level_actors():
    for c in a.get_components_by_class(unreal.LightComponentBase):
        c.set_mobility(unreal.ComponentMobility.MOVABLE); n_mob += 1
unreal.log(f"luci rese mobili: {n_mob}")
metti(unreal.SkyAtmosphere, "Atmosfera")
cielo = metti(unreal.SkyLight, "Luce del cielo")
cielo.get_component_by_class(unreal.SkyLightComponent).set_mobility(unreal.ComponentMobility.MOVABLE)
cielo.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
metti(unreal.ExponentialHeightFog, "Nebbia")
pp = metti(unreal.PostProcessVolume, "Post-produzione"); pp.set_editor_property("unbound", True)
s = pp.get_editor_property("settings")
for chiave, valore in (("override_dynamic_global_illumination_method", True), ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN),
                       ("override_reflection_method", True), ("reflection_method", unreal.ReflectionMethod.LUMEN),
                       # esposizione automatica: con quella manuale (ISO 100, 1/60, f/4) gli interni sono neri. Il valore
                       # fisso per i render si sceglie dopo, guardando la scena
                       ("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
                       ("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", -2.0),
                       ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", 14.0)):
    try: s.set_editor_property(chiave, valore)
    except Exception as e: unreal.log_warning(f"{chiave}: {e}")
pp.set_editor_property("settings", s)
livelli.save_current_level(); unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log("livello salvato: " + LIVELLO)

# ------------------------------------------------------------------------------------------------ controllo finale
tipi, comp, mat, lo, hi, tri = {}, {}, set(), [1e12] * 3, [-1e12] * 3, 0
for a in attori.get_all_level_actors():
    tipi[a.get_class().get_name()] = tipi.get(a.get_class().get_name(), 0) + 1
    for c in a.get_components_by_class(unreal.SceneComponent):
        n = c.get_class().get_name()
        if "Light" in n or n in ("StaticMeshComponent", "CineCameraComponent", "CameraComponent"): comp[n] = comp.get(n, 0) + 1
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if not sm: continue
        tri += sm.get_num_triangles(0)
        for i in range(c.get_num_materials()):
            m = c.get_material(i)
            if m: mat.add(m.get_path_name())
        o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
        for k, (oo, ee) in enumerate(((o.x, e.x), (o.y, e.y), (o.z, e.z))):
            lo[k] = min(lo[k], oo - ee); hi[k] = max(hi[k], oo + ee)
unreal.log(f"CONTROLLO attori {dict(sorted(tipi.items()))}")
unreal.log(f"CONTROLLO componenti {dict(sorted(comp.items()))}, materiali usati {len(mat)}, triangoli {tri}")
unreal.log(f"CONTROLLO ingombro mesh cm min ({lo[0]:.0f}, {lo[1]:.0f}, {lo[2]:.0f}) max ({hi[0]:.0f}, {hi[1]:.0f}, {hi[2]:.0f})")
seq = [d for d in asset_lib.list_assets(RADICE, True, False) if "LevelSequence" in str(asset_lib.find_asset_data(d).asset_class_path.asset_name)]
controllo = {"luci": {k[:-5]: v for k, v in tipi.items() if k in ("DirectionalLight", "SpotLight", "PointLight", "RectLight")},
             "mesh": comp.get("StaticMeshComponent", 0), "triangoli": tri, "materiali": len(mat),
             "ingombro_cm": [[round(v) for v in lo], [round(v) for v in hi]],
             "camere": tipi.get("CineCameraActor", 0) + tipi.get("CameraActor", 0)}
for d in seq:
    ls = unreal.EditorAssetLibrary.load_asset(d); r = ls.get_display_rate()
    controllo["fps"] = r.numerator / r.denominator; controllo["fotogrammi"] = [ls.get_playback_start(), ls.get_playback_end()]
    unreal.log(f"CONTROLLO level sequence {d}: {controllo['fps']:g} fps, fotogrammi {controllo['fotogrammi']}")
# letto da filiera.py e confrontato con usd/riferimento.json (scritto da esporta_usd.py)
json.dump(controllo, open(os.path.join(USD, "controllo_unreal.json"), "w", encoding="utf-8"), indent=1)
