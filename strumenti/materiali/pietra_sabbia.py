"""Pietra calcarea beige per il rivestimento dei bagni, ricavata dalla foto di Andrea (riferimenti_arredo/bagno.jpg).

Metodo usato (predefinito, "metodo=foto"): si toglie il gradiente della luce dalla lastra alta della foto (sopra la fuga,
lontano dall'angolo e dalla pianta), si puliscono i quadretti del JPEG e si ricuce una lastra ripetibile senza cuciture con
pezzetti della foto stessa (quilting: pezzi da 96 px, scelti a caso tra i migliori, ruotati e ribaltati), con l'istogramma della
foto e una grana fine alla risoluzione piena. Lato 1,5 m (2048 px). La "colore" è in grigio con la media a 0,5 e si ritinge
con la tinta del progetto (materiali_arredo.ritinta, contrasto 0,4 per il rivestimento: Andrea la voleva "più leggera").
Storia (2026-11-17): le texture CC0 scaricate e i generatori statistici (rumori frattali, spettro della foto: "metodo=rumore")
non somigliavano ("non è nemmeno vicino"); restano nel file per confronto.

  python strumenti/materiali/pietra_sabbia.py [metodo=foto|rumore] [--confronto <png>]
      → libreria_materiali/pietra_sabbia/{colore,normali,ruvidita}.png, info.json (svuota anche tinte/, la cache delle ritinte)
"""
import json, os, sys
import numpy as np
from PIL import Image

QUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(QUI, "..", ".."))
DEST = os.path.join(REPO, "libreria_materiali", "pietra_sabbia")
FOTO = os.path.join(REPO, "rilievi", "zona-cagliari-menta-tamburino", "modello", "riferimenti_arredo", "bagno.jpg")
N, LATO = 2048, 1.5                     # 1,5 m in 2048 px (0,73 mm per pixel)
P = {}                                  # regolazioni da riga di comando: chiave=valore


def p(k, d): return float(P.get(k, d))


def rumore(scala_m, rnd, n=N, lato=LATO):
    f = np.fft.fft2(rnd.standard_normal((n, n)))
    k = np.sqrt(np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2) * (scala_m / lato * n)
    r = np.real(np.fft.ifft2(f * np.exp(-k ** 2)))
    return (r - r.mean()) / (r.std() + 1e-9)


def frattale(rnd, scale):
    """somma di ottave (pesi decrescenti): bordi frastagliati invece delle nuvole gaussiane lisce."""
    t = sum((s / scale[0]) ** 0.6 * rumore(s, rnd) for s in scale)
    return (t - t.mean()) / t.std()


def liscio(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def foto_rel():
    """luminanza relativa della lastra nella foto (tolto il gradiente della luce): per l'istogramma e il confronto."""
    # solo la lastra alta: sopra la fuga orizzontale (riga 395 della foto), lontano dall'ombra dell'angolo e dalla pianta;
    # con la fuga dentro, il quilting copiava la riga scura come un segno della pietra (2026-11-17)
    im = np.asarray(Image.open(FOTO).convert("RGB"), float)[40:385, 150:600] / 255
    L = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4) @ [0.2126, 0.7152, 0.0722]
    k = np.ones(121) / 121
    b = np.apply_along_axis(lambda x: np.convolve(np.pad(x, 60, mode="edge"), k, "valid"), 0, L)
    b = np.apply_along_axis(lambda x: np.convolve(np.pad(x, 60, mode="edge"), k, "valid"), 1, b)
    return L / b


def spettro_foto():
    """ampiezza radiale dello spettro della lastra nella foto, in funzione della frequenza in cicli al metro (612 px/m)."""
    rel = foto_rel(); c = rel[22:278, 92:348]; c = (c - c.mean()) / c.mean()
    w = np.outer(np.hanning(256), np.hanning(256)); F = np.abs(np.fft.fft2(c * w)) ** 2
    fy, fx = np.meshgrid(np.fft.fftfreq(256), np.fft.fftfreq(256), indexing="ij"); fr = np.sqrt(fx ** 2 + fy ** 2) * 612.0
    bordi = np.linspace(0, 306, 60); med = [(bordi[i] + bordi[i + 1]) / 2 for i in range(59)]
    pot = [F[(fr >= bordi[i]) & (fr < bordi[i + 1])].mean() for i in range(59)]
    return np.array(med), np.array(pot)


def genera_spettro(seme=11):
    """rumore con lo stesso spettro della foto (fase a caso), oltre la risoluzione della foto prosegue con la stessa pendenza."""
    rnd = np.random.default_rng(seme)
    fm, pot = spettro_foto(); ok = pot > 0; lf, lp = np.log(fm[ok]), np.log(pot[ok])
    pend = np.polyfit(lf[-15:], lp[-15:], 1)                                  # pendenza delle frequenze alte
    fy, fx = np.meshgrid(np.fft.fftfreq(N), np.fft.fftfreq(N), indexing="ij"); fr = np.sqrt(fx ** 2 + fy ** 2) * (N / LATO)
    fr_ = np.maximum(fr, fm[0])
    lpot = np.where(fr_ <= fm[ok][-1], np.interp(np.log(fr_), lf, lp), np.polyval(pend, np.log(fr_)))
    amp = np.exp(lpot / 2); amp[0, 0] = 0
    # sopra 120 cicli/m (8 mm) la foto è rumore del JPEG e grana troppo forte: si smorza (2026-11-17, a vista)
    amp *= np.where(fr > p("fc", 120.0), p("fa", 0.45), 1.0)
    r = np.real(np.fft.ifft2(amp * np.exp(2j * np.pi * rnd.random((N, N)))))
    return (r - r.mean()) / r.std()


def genera(seme=11):
    rnd = np.random.default_rng(seme)
    F = frattale(rnd, [0.25, 0.10, 0.04, 0.016, 0.006])                     # macchie grandi, bordo frastagliato
    # bordi "arricciati" del calcare: il campo si deforma con un altro rumore (domain warping), ricci di qualche cm
    wa = p("warp", 0.03) / LATO * N; yy, xx = np.mgrid[0:N, 0:N]
    dx, dy = rumore(0.05, rnd) * wa, rumore(0.05, rnd) * wa
    F = F[(yy + dy).astype(int) % N, (xx + dx).astype(int) % N]
    G = frattale(rnd, [0.05, 0.02, 0.008])                                   # macchioline
    macchie = liscio(F, p("m0", 0.25), p("m1", 0.55))                        # zone più scure, bordo definito ma morbido
    contorni = np.exp(-((F - 0.4) / p("cl", 0.06)) ** 2)                     # linee curve sul bordo delle macchie
    piccole = liscio(G, 1.1, 1.5)
    chiari = liscio(frattale(rnd, [0.004, 0.002]), 2.2, 2.8)                 # puntini chiari
    grana = rumore(0.0012, rnd) * 0.6 + rnd.standard_normal((N, N)) * 0.4
    S = genera_spettro(seme)                                                 # mottle con lo spettro misurato sulla foto
    v = (p("ks", 1.0) * S - p("km", 0.0) * macchie - p("kc", 0.0) * contorni - p("kp", 0.3) * piccole + p("kl", 0.4) * chiari
         + p("kg", 0.0) * grana + p("kf", 0.0) * F)
    # istogramma della foto: stessa distribuzione dei valori (contrasto vero)
    ref = np.sort(foto_rel().ravel()); ordine = np.argsort(v.ravel()); out = np.empty(v.size)
    out[ordine] = ref[(np.arange(v.size) * (ref.size - 1) / (v.size - 1)).astype(int)]
    fatt = out.reshape(v.shape) / ref.mean()
    alt = -0.5 * macchie - 0.3 * contorni + 0.4 * grana
    return fatt, alt


def quilting(seme=5, blocco=96, sovr=24, candidati=500, tra=0.12):
    """lastra ripetibile (toroidale) cucita con pezzetti della foto stessa (tolta la luce): la stessa pietra della foto, non
    un'imitazione statistica (2026-11-17: rumori e spettri non ci arrivavano). Ogni pezzo nuovo si sceglie tra 'candidati' a
    caso quello che meglio combacia con quanto già posato (anche oltre il bordo: la lastra si ripete senza cuciture), poi si
    sfuma nella sovrapposizione."""
    rnd = np.random.default_rng(seme); src = foto_rel(); src = src / src.mean()
    # via i quadretti del JPEG (8 px) e il rumore: la lastra sembrava "spixelata" da vicino (Andrea, 2026-11-17)
    from PIL import ImageFilter
    src = np.asarray(Image.fromarray(np.clip(src * 127, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1)), float) / 127
    sh, sw = src.shape; n = int(round(612 * LATO)); passo = blocco - sovr; k = int(np.ceil(n / passo)); n = k * passo
    out = np.zeros((n, n)); peso = np.zeros((n, n))
    rampa = np.ones(blocco); rampa[:sovr] = np.linspace(0, 1, sovr + 2)[1:-1]; rampa[-sovr:] = rampa[:sovr][::-1]
    W2 = np.outer(rampa, rampa)
    for i in range(k):
        for j in range(k):
            ys = (np.arange(blocco) + i * passo) % n; xs = (np.arange(blocco) + j * passo) % n
            gia = peso[np.ix_(ys, xs)] > 0; att = np.where(gia, out[np.ix_(ys, xs)] / np.maximum(peso[np.ix_(ys, xs)], 1e-9), 0)
            prove = []
            for _ in range(candidati):
                y0, x0 = rnd.integers(0, sh - blocco), rnd.integers(0, sw - blocco); pz = src[y0:y0 + blocco, x0:x0 + blocco]
                pz = np.rot90(pz, rnd.integers(0, 4)); pz = pz[:, ::-1] if rnd.random() < 0.5 else pz       # la pietra non ha un verso
                prove.append((((pz - att) ** 2)[gia].sum() if gia.any() else 0.0, pz))
            # a caso tra i migliori (il solo migliore era sempre un pezzo liscio: lastra piatta)
            prove.sort(key=lambda t: t[0]); meglio = prove[rnd.integers(0, max(1, int(tra * candidati)))][1]
            out[np.ix_(ys, xs)] += meglio * W2; peso[np.ix_(ys, xs)] += W2
    t = out / np.maximum(peso, 1e-9)
    # contrasto della foto: la sfumatura delle sovrapposizioni lo abbassa; si riporta l'istogramma su quello della foto
    ref = np.sort(src.ravel()); o_ = np.argsort(t.ravel()); t2 = np.empty(t.size)
    t2[o_] = ref[(np.arange(t.size) * (ref.size - 1) / (t.size - 1)).astype(int)]; t = t2.reshape(t.shape)
    big = Image.fromarray(np.clip(t * 127, 0, 255).astype(np.uint8)).resize((N, N), Image.LANCZOS)
    fatt = np.asarray(big, float) / 127
    # grana fine alla risoluzione piena (0,7 mm): la foto non arriva sotto 1,6 mm e ingrandita sembrava sfocata o a quadretti
    g_ = np.random.default_rng(seme + 1); fine = g_.standard_normal((N, N))
    fine = np.asarray(Image.fromarray(np.clip(fine * 40 + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), float) / 40 - 3.2
    fatt = fatt + fine * 0.010
    alt = (fatt - fatt.mean()) / fatt.std()
    return fatt / fatt.mean(), alt


def scrivi():
    os.makedirs(DEST, exist_ok=True)
    import shutil
    shutil.rmtree(os.path.join(DEST, "tinte"), ignore_errors=True)    # versioni ritinte e ritarate vecchie (cache di materiali_arredo)
    fatt, alt = quilting() if P.get("metodo", "foto") == "foto" else genera()          # "rumore": il vecchio generatore statistico
    grigio = np.clip(fatt * 0.5, 0, 1)
    Image.fromarray((grigio * 255).astype(np.uint8), "L").convert("RGB").save(os.path.join(DEST, "colore.png"))
    gy, gx = np.gradient(alt); forza = 0.25
    nx, ny, nz = -gx * forza, gy * forza, np.ones_like(gx); ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    Image.fromarray(((np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(os.path.join(DEST, "normali.png"))
    ruv = np.clip(0.78 + 0.03 * alt / (alt.std() + 1e-9), 0, 1)
    Image.fromarray((ruv * 255).astype(np.uint8), "L").convert("RGB").save(os.path.join(DEST, "ruvidita.png"))
    json.dump({"id": "pietra_sabbia", "nome": "Pietra calcarea beige (generata sulla foto bagno.jpg)", "licenza": "generata da questo script",
               "dimensioni_mm": [LATO * 1000, LATO * 1000], "regolazioni": P,
               "mappe": {"colore": "colore.png", "normali": "normali.png", "ruvidita": "ruvidita.png"}},
              open(os.path.join(DEST, "info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("scritto", DEST)
    return fatt


def confronto(fatt, uscita, tinta="#C9B597"):
    """foto | generata, alla stessa scala (612 px/m) e con la stessa tinta media."""
    from PIL import ImageDraw
    rel = foto_rel(); h, w = rel.shape
    gen = Image.fromarray(np.clip(fatt * 127, 0, 255).astype(np.uint8)).resize((round(612 * LATO),) * 2, Image.LANCZOS)
    gen = np.asarray(gen, float)[:h, :w] / 127
    t = np.array([int(tinta[i:i + 2], 16) for i in (1, 3, 5)]) / 255; tl = np.where(t <= 0.04045, t / 12.92, ((t + 0.055) / 1.055) ** 2.4)
    def rgb(r): o = np.clip(r[..., None] * tl, 0, 1); return (np.where(o <= 0.0031308, o * 12.92, 1.055 * o ** (1 / 2.4) - 0.055) * 255).astype(np.uint8)
    a, b = Image.fromarray(rgb(rel / rel.mean())), Image.fromarray(rgb(gen / gen.mean()))
    M = Image.new("RGB", (w * 2 + 10, h + 20), "white"); M.paste(a, (0, 20)); M.paste(b, (w + 10, 20)); d = ImageDraw.Draw(M)
    d.text((4, 4), "foto (luce tolta)", fill="black"); d.text((w + 14, 4), "pietra_sabbia generata", fill="black")
    M.resize((M.width * 2, M.height * 2), Image.LANCZOS).save(uscita); print("confronto", uscita)


if __name__ == "__main__":
    P.update(dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a))
    f = scrivi()
    if "--confronto" in sys.argv: confronto(f, sys.argv[sys.argv.index("--confronto") + 1])
