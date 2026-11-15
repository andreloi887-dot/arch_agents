"""BOZZA NON PROVATA (scritta nel cloud il 2026-11-15, senza Unreal a disposizione): va provata e corretta sul PC con
Unreal Engine 5.8 prima di fidarsene. Fase 5 di PROCEDIMENTO.md.

Dentro l'editor di Unreal (Output Log › Cmd, oppure da riga di comando):
  py "<repo>/skills/rilievo-urbano/scripts/unreal/importa_usd.py" "<modello>/uscita_blender/usd"
  UnrealEditor-Cmd.exe <progetto>.uproject -run=pythonscript -script="importa_usd.py <cartella usd>"

Cosa fa: livello nuovo, scena.usdc e camere.usdc caricate come USD Stage (metri → centimetri li converte Unreal),
sole, cielo, luce diffusa del cielo, nebbia, volume di post-produzione con Lumen ed esposizione fissa. Salva il livello.
Servono i plugin "USD Importer" e "Python Editor Script Plugin" attivi nel progetto.
Da fare dopo, a mano o con altri script: materiali della libreria di studio al posto di quelli di anteprima, arredi
Fab/Megascans al posto dei mobili parametrici, Level Sequence dalle camere PERCORSO_*, Movie Render Queue.
"""
import os, sys
import unreal

USD = sys.argv[1] if len(sys.argv) > 1 else ""
LIVELLO = "/Game/Progetto/Scena"
if not os.path.isfile(os.path.join(USD, "scena.usdc")): raise SystemExit(f"scena.usdc non trovato in {USD!r}")

livelli = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
attori = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
livelli.new_level(LIVELLO)

def metti(classe, nome, pos=(0, 0, 0), rot=(0, 0, 0)):
    a = attori.spawn_actor_from_class(classe, unreal.Vector(*pos), unreal.Rotator(*rot)); a.set_actor_label(nome); return a

for nome in ("scena", "camere"):
    f = os.path.join(USD, nome + ".usdc")
    if not os.path.isfile(f): continue
    st = metti(unreal.UsdStageActor, "USD_" + nome)
    st.set_editor_property("root_layer", unreal.FilePath(f))
    unreal.log(f"caricato {f}")

# sole: la direzione vera è nel sole esportato da Blender dentro scena.usdc; questo è il sole di Unreal da allineargli
sole = metti(unreal.DirectionalLight, "Sole", rot=(-45, 140, 0))
sole.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
metti(unreal.SkyAtmosphere, "Atmosfera")
cielo = metti(unreal.SkyLight, "Luce del cielo")
cielo.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
metti(unreal.ExponentialHeightFog, "Nebbia")
pp = metti(unreal.PostProcessVolume, "Post-produzione"); pp.set_editor_property("unbound", True)
s = pp.get_editor_property("settings")
for chiave, valore in (("override_dynamic_global_illumination_method", True), ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.LUMEN),
                       ("override_reflection_method", True), ("reflection_method", unreal.ReflectionMethod.LUMEN),
                       ("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)):
    try: s.set_editor_property(chiave, valore)
    except Exception as e: unreal.log_warning(f"{chiave}: {e}")
pp.set_editor_property("settings", s)
livelli.save_current_level(); unreal.log("livello salvato: " + LIVELLO)
