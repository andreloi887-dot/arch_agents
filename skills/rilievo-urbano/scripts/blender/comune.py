"""Funzioni comuni agli script Blender della filiera: argomenti, log, quote, resa EEVEE (resa), Cycles su GPU (cycles),
render delle camere."""
import os, sys


def argomenti():
    """argomenti dopo '--' e lettore delle opzioni '--nome valore'."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    def opt(nome, default=None):
        return argv[argv.index(nome) + 1] if nome in argv and argv.index(nome) + 1 < len(argv) else default
    return argv, opt


def avvio(nome_log):
    """preambolo dei passi della filiera: argomenti, cartella modello e uscite, --blend (Blender come modulo, cloud),
    log. Restituisce argv, opt, MOD, USCITA, log, scn."""
    import bpy
    argv, opt = argomenti()
    MOD = os.path.abspath(argv[0]) if argv else os.getcwd()
    USCITA = os.path.join(MOD, opt("--uscita", "uscita_blender")); os.makedirs(USCITA, exist_ok=True)
    if opt("--blend"): bpy.ops.wm.open_mainfile(filepath=os.path.join(USCITA, opt("--blend")))
    log = registro(os.path.join(USCITA, nome_log))
    return argv, opt, MOD, USCITA, log, bpy.context.scene


def svuota(bpy, oggetti):
    """rilancio di un passo: toglie gli oggetti e subito i dati rimasti orfani (mesh, luci, materiali). Senza, i nuovi
    prendono i nomi con suffisso (.001) e al giro dopo li riperdono: nomi diversi a ogni rilancio, fino in Unreal."""
    for o in list(oggetti): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)


def registro(percorso):
    """log su console e su file."""
    f = open(percorso, "w", encoding="utf-8")
    def log(*a):
        s = " ".join(str(x) for x in a); print(s); f.write(s + "\n"); f.flush()
    return log


def lin(h):
    """colore "#RRGGBB" (sRGB) → [r, g, b, 1] lineari, come li vuole Blender."""
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


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


def cycles(bpy, scn, samples=32, cpu=False, log=print):
    """Cycles sulla scheda grafica se c'è (OptiX, poi CUDA, HIP, oneAPI, Metal), altrimenti CPU (sessione cloud).
    Senza attivare i dispositivi nelle preferenze, scn.cycles.device = 'GPU' resta sulla CPU: va fatto qui.
    cpu=True (o variabile d'ambiente FILIERA_CPU=1) forza la CPU. Restituisce la descrizione del dispositivo."""
    scn.render.engine = "CYCLES"; scn.cycles.samples = samples; scn.cycles.use_denoising = True
    scn.cycles.max_bounces = 6; scn.cycles.diffuse_bounces = 4
    usato = "CPU"
    if not cpu and os.environ.get("FILIERA_CPU") != "1":
        try:
            pr = bpy.context.preferences.addons["cycles"].preferences
            for tipo in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
                try: pr.compute_device_type = tipo
                except Exception: continue
                pr.refresh_devices()
                gpu = [d for d in pr.devices if d.type == tipo]
                if not gpu: continue
                for d in pr.devices: d.use = d.type == tipo
                scn.cycles.device = "GPU"; usato = f"{tipo}: " + ", ".join(d.name for d in gpu); break
        except Exception as e:
            log("AVVISO scheda grafica non attivata:", e)
    if usato == "CPU": scn.cycles.device = "CPU"
    if scn.cycles.device == "GPU":
        try: scn.cycles.denoiser = "OPTIX" if usato.startswith("OPTIX") else "OPENIMAGEDENOISE"
        except Exception: pass
    log("Cycles su", usato, "|", samples, "campioni")
    return usato


def rendi_camere(bpy, scn, cartella, solo=None, log=print):
    """rende le camere con la proprietà 'res' (riprese Street View e viste aeree); solo = 'SV-08,VISTA_angolo'."""
    os.makedirs(cartella, exist_ok=True)
    for co in [o for o in scn.objects if o.type == "CAMERA" and "res" in o]:
        if solo and not any(s in co.name for s in solo.split(",")): continue
        scn.camera = co; scn.render.resolution_x, scn.render.resolution_y = co["res"]
        scn.render.filepath = os.path.join(cartella, co.name + ".png")
        bpy.ops.render.render(write_still=True); log("render", co.name)
