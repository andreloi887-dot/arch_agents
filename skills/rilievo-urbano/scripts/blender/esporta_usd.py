"""Export USD verso Unreal Engine (fine della fase 3, vedi PROCEDIMENTO.md).

  blender -b <modello>/uscita_blender/scena_percorsi.blend -P esporta_usd.py -- <cartella modello>
  python esporta_usd.py -- <cartella modello> --blend scena_percorsi.blend       (Blender come modulo)

Due file in <modello>/uscita_blender/usd/, così in Unreal la scena si importa una volta e le camere si possono
riesportare da sole dopo una modifica ai percorsi:
  scena.usdc    geometria, materiali (USD Preview Surface, texture copiate in textures/), sole; senza camere.
                Solo gli oggetti visibili in render: il contesto nascosto sotto il progetto non esce
  camere.usdc   le camere PERCORSO_* con l'animazione, un campione per fotogramma
Metri, asse Z in alto, nomi senza caratteri fuori ASCII (Unreal li rifiuta). Controllo finale: numero di mesh,
materiali e camere riletti dai file, nel log.
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import argomenti, registro

argv, opt = argomenti()
MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender"))
if opt("--blend"): bpy.ops.wm.open_mainfile(filepath=os.path.join(USCITA, opt("--blend")))
USD = os.path.join(USCITA, "usd"); os.makedirs(USD, exist_ok=True)
log = registro(os.path.join(USCITA, "esporta_usd.log"))
scn = bpy.context.scene
log("scena", bpy.data.filepath)

COMUNI = dict(evaluation_mode="RENDER", allow_unicode=False, root_prim_path="/scena", convert_scene_units="METERS",
              export_custom_properties=True, relative_paths=True)
percorsi = [o for o in scn.objects if o.type == "CAMERA" and o.name.startswith("PERCORSO_")]

f_scena = os.path.join(USD, "scena.usdc")
bpy.ops.wm.usd_export(filepath=f_scena, export_animation=False, export_cameras=False, export_lights=True,
                      export_materials=True, generate_preview_surface=True, export_textures_mode="NEW",
                      overwrite_textures=True, use_instancing=True, export_normals=True, export_uvmaps=True,
                      convert_world_material=False, **COMUNI)
log("scritto", f_scena, f"{os.path.getsize(f_scena) / 1e6:.1f} MB")

f_camere = None
if percorsi:
    for o in scn.objects: o.select_set(False)
    for o in percorsi: o.select_set(True)
    scn.frame_start = 1; scn.frame_end = max(int(o.get("fotogrammi", 1)) for o in percorsi)
    f_camere = os.path.join(USD, "camere.usdc")
    bpy.ops.wm.usd_export(filepath=f_camere, selected_objects_only=True, export_animation=True, export_cameras=True,
                          export_lights=False, export_materials=False, export_meshes=False, **COMUNI)
    log("scritto", f_camere, f"{len(percorsi)} camere, fotogrammi 1-{scn.frame_end} a {scn.render.fps} fps")
else:
    log("nessuna camera PERCORSO_*: lanciare prima percorsi_camera.py")

try:
    from pxr import Usd, UsdGeom
    for f in filter(None, (f_scena, f_camere)):
        st = Usd.Stage.Open(f); tipi = {}
        for pr in st.Traverse(): tipi[pr.GetTypeName()] = tipi.get(pr.GetTypeName(), 0) + 1
        log(os.path.basename(f), "| asse", UsdGeom.GetStageUpAxis(st), "| metri per unità", UsdGeom.GetStageMetersPerUnit(st),
            "| fotogrammi", st.GetStartTimeCode(), "-", st.GetEndTimeCode(), "|",
            ", ".join(f"{k or 'senza tipo'} {v}" for k, v in sorted(tipi.items())))
except ImportError:
    log("controllo saltato: modulo pxr non disponibile in questo Python")
log("fine")
