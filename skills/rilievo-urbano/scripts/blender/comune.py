"""Funzioni comuni agli script Blender della filiera (importa_contesto.py, importa_progetto.py, allinea_ifc.py)."""
import os, sys


def argomenti():
    """argomenti dopo '--' e lettore delle opzioni '--nome valore'."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    def opt(nome, default=None):
        return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else default
    return argv, opt


def registro(percorso):
    """log su console e su file."""
    f = open(percorso, "w", encoding="utf-8")
    def log(*a):
        s = " ".join(str(x) for x in a); print(s); f.write(s + "\n"); f.flush()
    return log


def z_piano(q3, x, y):
    """quota nel punto (x, y) sul piano del triangolo q3 = [(x, y, z)] × 3 (anche fuori dal triangolo)."""
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = (tuple(v[:3]) for v in q3)
    d = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(d) < 1e-12: return z1
    l1 = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / d
    l2 = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / d
    return l1 * z1 + l2 * z2 + (1 - l1 - l2) * z3


def resa(scn, samples=16, ombre="1024"):
    """impostazioni di resa della filiera: EEVEE, AgX "Punchy" (regge il sole pieno e restituisce la saturazione delle
    foto), esposizione -0,2. Si applicano prima di salvare, così il .blend si apre già con la resa giusta."""
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: scn.render.engine = eng; break
        except Exception: pass
    for k, v in (("taa_render_samples", samples), ("shadow_pool_size", ombre)):
        try: setattr(scn.eevee, k, v)
        except Exception: pass
    try: scn.view_settings.view_transform = "AgX"
    except Exception: scn.view_settings.view_transform = "Filmic"
    for look in ("AgX - Punchy", "Punchy", "AgX - High Contrast"):
        try: scn.view_settings.look = look; break
        except Exception: pass
    scn.view_settings.exposure = -0.2


def rendi_camere(bpy, scn, cartella, solo=None, log=print):
    """rende le camere con la proprietà 'res' (riprese Street View e viste aeree); solo = 'SV-08,VISTA_angolo'."""
    os.makedirs(cartella, exist_ok=True)
    for co in [o for o in scn.objects if o.type == "CAMERA" and "res" in o]:
        if solo and not any(s in co.name for s in solo.split(",")): continue
        scn.camera = co; scn.render.resolution_x, scn.render.resolution_y = co["res"]
        scn.render.filepath = os.path.join(cartella, co.name + ".png")
        bpy.ops.render.render(write_still=True); log("render", co.name)
