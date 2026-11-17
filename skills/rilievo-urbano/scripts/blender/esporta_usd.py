"""Export USD verso Unreal Engine (fine della fase 3, vedi PROCEDIMENTO.md).

  blender -b <modello>/uscita_blender/scena_percorsi.blend -P esporta_usd.py -- <cartella modello>
  python esporta_usd.py -- <cartella modello> --blend scena_percorsi.blend       (Blender come modulo)

Due file in <modello>/uscita_blender/usd/, così in Unreal la scena si importa una volta e le camere si possono
riesportare da sole dopo una modifica ai percorsi:
  scena.usdc    geometria, materiali (USD Preview Surface, texture copiate in textures/), sole; senza camere.
                Solo gli oggetti visibili in render: il contesto nascosto sotto il progetto non esce
  camere.usdc   le camere PERCORSO_* con l'animazione, un campione per fotogramma
Metri, asse Z in alto, nomi senza caratteri fuori ASCII (Unreal li rifiuta); framesPerSecond delle camere allineato al
fps della scena (Blender lo lascia a 24). Controllo finale: tipi riletti dai file nel log, e usd/riferimento.json con
luci, triangoli, materiali distinti, ingombro in cm (assi di Unreal), camere, fps e l'impronta della geometria
(cambia solo se cambia il risultato; dettaglio per mesh in usd/impronta_mesh.json). filiera.py lo confronta con Unreal.
"""
import bpy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comune import avvio

argv, opt, MOD, USCITA, log, scn = avvio("esporta_usd.log")
USD = os.path.join(USCITA, "usd"); os.makedirs(USD, exist_ok=True)
log("scena", bpy.data.filepath)

COMUNI = dict(evaluation_mode="RENDER", allow_unicode=False, root_prim_path="/scena", convert_scene_units="METERS",
              export_custom_properties=True, relative_paths=True)
percorsi = [o for o in scn.objects if o.type == "CAMERA" and o.name.startswith("PERCORSO_")]

f_scena = os.path.join(USD, "scena.usdc")
bpy.ops.wm.usd_export(filepath=f_scena, export_animation=False, export_cameras=False, export_lights=True,
                      export_materials=True, generate_preview_surface=True, export_textures_mode="NEW",
                      overwrite_textures=True, use_instancing=True, export_normals=True, export_uvmaps=True,
                      convert_world_material=False, export_subdivision="TESSELLATE", **COMUNI)
# export_subdivision TESSELLATE (2026-11-16): le superfici lisce degli arredi (suddivisione come ultimo modificatore) escono
# già suddivise, la stessa forma che rende Blender, invece della gabbia da suddividere in Unreal
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
    from pxr import Usd, UsdGeom, UsdShade
    if f_camere:
        # Blender scrive timeCodesPerSecond ma lascia framesPerSecond a 24: Unreal legge questo e fa la Level Sequence
        # a 24 fps (provato in UE 5.8, 2026-11-15). Si allinea al fps della scena.
        st = Usd.Stage.Open(f_camere); st.SetFramesPerSecond(scn.render.fps / scn.render.fps_base)
        st.SetTimeCodesPerSecond(scn.render.fps / scn.render.fps_base); st.GetRootLayer().Save()
    # riferimento per il controllo in Unreal (importa_usd.py scrive controllo_unreal.json con le stesse voci)
    import hashlib, numpy as np
    st = Usd.Stage.Open(f_scena); rif = {"luci": {}, "mesh": 0, "triangoli": 0, "mesh_senza_uv": 0}; per_mesh = {}
    firme, mn, mx = set(), [1e12] * 3, [-1e12] * 3
    for pr in Usd.PrimRange.Stage(st, Usd.TraverseInstanceProxies()):
        t = pr.GetTypeName()
        if t.endswith("Light"):
            # Unreal: DistantLight → Directional, SphereLight con cono (ShapingAPI) → Spot, senza → Point
            from pxr import UsdLux
            k = {"DistantLight": "Directional", "RectLight": "Rect"}.get(t) or ("Spot" if pr.HasAPI(UsdLux.ShapingAPI) else "Point")
            rif["luci"][k] = rif["luci"].get(k, 0) + 1
        elif t == "Mesh" and UsdGeom.Imageable(pr).ComputeVisibility() != "invisible":
            m = UsdGeom.Mesh(pr); rif["mesh"] += 1
            # impronta della geometria: vertici al mm, trasformazione e materiale; cambia solo se cambia il risultato
            pts = np.asarray(m.GetPointsAttr().Get() or [], dtype=np.float64)
            mw = np.asarray(UsdGeom.Xformable(pr).ComputeLocalToWorldTransform(Usd.TimeCode.Default()), dtype=np.float64)
            mb, _ = UsdShade.MaterialBindingAPI(pr).ComputeBoundMaterial()
            h = hashlib.sha256(np.round(pts * 1000).astype(np.int64).tobytes() + np.round(mw * 1000).astype(np.int64).tobytes()
                               + str(mb.GetPath() if mb else "").encode()).hexdigest()[:12]
            per_mesh[str(pr.GetPath())] = h
            rif["triangoli"] += sum(max(n - 2, 0) for n in (m.GetFaceVertexCountsAttr().Get() or []))
            if not UsdGeom.PrimvarsAPI(pr).HasPrimvar("st"): rif["mesh_senza_uv"] += 1
    for pr in st.Traverse():
        if pr.GetTypeName() == "Material":     # Unreal accorpa i materiali uguali: si contano i contenuti distinti
            firme.add(tuple(tuple(sorted((a.GetName(), str(a.Get())) for a in d.GetAttributes()
                                         if a.GetName().startswith("inputs:") and not a.HasAuthoredConnections()))
                            for d in Usd.PrimRange(pr) if d.GetTypeName() == "Shader"))
    bb = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(st.GetPseudoRoot()).ComputeAlignedRange()
    # porte: nessuna può mancare in scena; le interne IFC sono nascoste solo perché rifatte con l'anta (sostituita)
    rif["porte_nascoste"] = sorted(o.name for o in scn.objects if o.get("ifc_classe") == "IfcDoor" and o.hide_render and not o.get("sostituita"))
    rif["porte"] = sum(1 for o in scn.objects if o.get("ifc_classe") == "IfcDoor")
    rif["materiali_distinti"] = len(firme); rif["impronta"] = hashlib.sha256((json.dumps(sorted(per_mesh.items())) + repr(sorted(firme))).encode()).hexdigest()[:16]   # l'export cambia l'ordine dei prim: si ordina
    # Unreal: centimetri e asse y ribaltato (mano sinistra)
    rif["ingombro_cm"] = [[round(bb.GetMin()[0] * 100), round(-bb.GetMax()[1] * 100), round(bb.GetMin()[2] * 100)],
                          [round(bb.GetMax()[0] * 100), round(-bb.GetMin()[1] * 100), round(bb.GetMax()[2] * 100)]]
    if f_camere:
        sc = Usd.Stage.Open(f_camere)
        rif["camere"] = len(percorsi); rif["fps"] = sc.GetFramesPerSecond()
        rif["fotogrammi"] = [int(sc.GetStartTimeCode()), int(sc.GetEndTimeCode())]
    json.dump(rif, open(os.path.join(USD, "riferimento.json"), "w", encoding="utf-8"), indent=1)
    # per capire cosa è cambiato quando l'impronta cambia: confrontare due copie di questo file
    json.dump(per_mesh, open(os.path.join(USD, "impronta_mesh.json"), "w", encoding="utf-8"), indent=0)
    for f in filter(None, (f_scena, f_camere)):
        s2 = Usd.Stage.Open(f); tipi = {}
        for pr in s2.Traverse(): tipi[pr.GetTypeName()] = tipi.get(pr.GetTypeName(), 0) + 1
        log(os.path.basename(f), "| asse", UsdGeom.GetStageUpAxis(s2), "| metri per unità", UsdGeom.GetStageMetersPerUnit(s2),
            "| fotogrammi", s2.GetStartTimeCode(), "-", s2.GetEndTimeCode(),
            "| fps", s2.GetFramesPerSecond(), "|", ", ".join(f"{k or 'senza tipo'} {v}" for k, v in sorted(tipi.items())))
    log("riferimento per Unreal", json.dumps(rif))
    if rif["mesh_senza_uv"]: log(f"AVVISO {rif['mesh_senza_uv']} mesh su {rif['mesh']} senza UV: in Unreal le texture non si applicano")
except ImportError:
    log("AVVISO controllo saltato: modulo pxr non disponibile, riferimento.json non scritto")
log("fine")
