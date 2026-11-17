"""Legno pitturato del soffitto (Andrea, 2026-11-17): "qualche nodino ... una venatura leggera leggera ... è legno pitturato con
una pittura molto grossa: la venatura si vede appena appena, con un nodino ogni tanto, nelle travi e nelle perline".

Genera due immagini ripetibili senza cuciture (solo numpy; le scrive Blender), in metri veri:
  fattore   grigio lineare: 0,5 = tinta della pittura invariata; venatura ±1,5-2 %, nodi fino a -13 % (con un velo più caldo
            della resina che affiora dalla pittura). Si moltiplica per 2 × tinta.
  normali   rilievo leggerissimo della fibra sotto la pittura e del nodo (OpenGL, +Y in alto).
La U dell'immagine è la fibra (lungo la doga o la trave). Lato U = LU m, lato V = 8 doghe: ogni doga dell'immagine ha la
sua venatura e i suoi nodi; i materiali (Blender e Unreal) spostano ogni fila di doghe lungo U di una quantità a caso
(hash della fila) perché i nodi non si ripetano allineati.

  import legno_dipinto; f, n = legno_dipinto.genera(cartella, doga_m=0.12)
"""
import os
import numpy as np

LU = 4.0          # m lungo la fibra
DP = 64           # pixel per doga (con doghe da 12 cm: 1,9 mm per pixel): le righe dell'immagine cadono sulle fughe vere


def _rumore(shape, scala_px, rnd):
    """rumore periodico (si ripete senza cuciture) con dettagli attorno a scala_px pixel."""
    h, w = shape
    f = np.fft.fft2(rnd.standard_normal(shape))
    ky = np.fft.fftfreq(h)[:, None]; kx = np.fft.fftfreq(w)[None, :]
    k = np.sqrt(kx ** 2 + ky ** 2) * scala_px
    r = np.real(np.fft.ifft2(f * np.exp(-k ** 2)))
    return (r - r.mean()) / (r.std() + 1e-9)


def _rumore_aniso(shape, sx, sy, rnd):
    """rumore periodico stirato: dettagli di sx pixel lungo x (fibra) e sy lungo y."""
    h, w = shape
    f = np.fft.fft2(rnd.standard_normal(shape))
    ky = np.fft.fftfreq(h)[:, None] * sy; kx = np.fft.fftfreq(w)[None, :] * sx
    r = np.real(np.fft.ifft2(f * np.exp(-(kx ** 2 + ky ** 2))))
    return (r - r.mean()) / (r.std() + 1e-9)


def calcola(doga_m=0.12, seme=5, nodi_per_m=0.35, venatura=0.035, nodo=0.13):
    """restituisce (fattore, altezza) come array float H × W; nodi_per_m = nodi per metro di doga."""
    rnd = np.random.default_rng(seme)
    PX_M = DP / doga_m; W = int(round(LU * PX_M)); dp = DP; H = 8 * dp
    y, x = np.mgrid[0:H, 0:W].astype(np.float64)
    fila = (y // dp).astype(int); yf = (y % dp) / PX_M                     # posizione di traverso dentro la doga, in m
    # fibra: linee lungo x, ondulate piano; ogni doga ha la sua fase e il suo passo (anelli tagliati a 1-3 mm)
    fase = rnd.uniform(0, 100, 8)[fila]; passo = rnd.uniform(0.0018, 0.0032, 8)[fila]
    curva = _rumore_aniso((H, W), 220, 18, rnd) * 0.004                      # ondulazione lenta delle fibre (m)
    t = (yf + curva) / passo + fase
    # nodi: posizioni a caso (periodiche), la fibra gira attorno al nodo
    n_nodi = max(1, int(round(nodi_per_m * LU * 8)))
    ix = rnd.uniform(0, W, n_nodi); dg = rnd.integers(0, 8, n_nodi); iy = dg * dp + rnd.uniform(0.25, 0.75, n_nodi) * dp
    rr = rnd.uniform(0.006, 0.013, n_nodi) * PX_M                            # raggio del nodo, 6-13 mm
    macchia = np.zeros((H, W)); spinta = np.zeros((H, W))
    for cx, cy, r in zip(ix, iy, rr):
        dx = (x - cx + W / 2) % W - W / 2; dy = (y - cy + H / 2) % H - H / 2
        d2 = (dx / 1.6) ** 2 + dy ** 2                                         # un po' allungato lungo la fibra
        macchia = np.maximum(macchia, np.exp(-d2 / (r * r)))
        spinta += np.sign(dy + 1e-6) * np.exp(-d2 / (2.5 * r) ** 2) * 1.5      # le fibre si aprono attorno al nodo
    t = t + spinta
    fibra = 0.5 + 0.5 * np.cos(2 * np.pi * t)                                  # 1 legno primaticcio, 0 tardivo
    fibra = fibra ** 3                                                         # linee tardive sottili
    lenta = _rumore((H, W), 60, rnd) * 0.3
    # sotto la pittura grossa la fibra si vede appena; il nodo affiora come macchia più scura e calda
    fatt = 1.0 - venatura * (fibra - fibra.mean() + lenta) - nodo * macchia ** 0.8
    alt = 0.4 * (fibra - fibra.mean()) + 0.15 * lenta + 1.2 * macchia            # rilievo relativo
    return fatt, alt, macchia


def genera(cartella, doga_m=0.12, seme=5, forza_normali=0.35):
    """scrive <cartella>/fattore_<doga>.png e normali_<doga>.png se non ci sono; restituisce i due percorsi e i lati (m)."""
    os.makedirs(cartella, exist_ok=True)
    tag = f"{doga_m:g}_{seme}_v2"
    f_f = os.path.join(cartella, f"fattore_{tag}.png"); f_n = os.path.join(cartella, f"normali_{tag}.png")
    lati = (LU, 8 * doga_m)
    if os.path.isfile(f_f) and os.path.isfile(f_n): return f_f, f_n, lati
    import bpy
    fatt, alt, macchia = calcola(doga_m, seme)
    H, W = fatt.shape
    # colore: fattore codificato t = 0,5 + (f - 1) × 4 (in 8 bit la venatura di ±1,6 % sarebbe stata 2 livelli di grigio, a
    # gradini); i materiali lo riportano a f = 0,875 + t / 4. Il nodo appena più caldo (resina): R 1, G 0,985, B 0,95
    fc = np.stack([fatt, fatt * (1 - 0.015 * macchia), fatt * (1 - 0.05 * macchia)], -1)
    rgb = np.clip(0.5 + (fc - 1.0) * 4.0, 0, 1)
    gy, gx = np.gradient(alt)
    nx, ny = -gx * forza_normali, gy * forza_normali                           # immagine con y verso il basso → +Y in alto
    nz = np.ones_like(nx); ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    nrm = np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], -1)
    for dati, f_ in ((rgb, f_f), (nrm, f_n)):
        im = bpy.data.images.new(os.path.basename(f_), W, H, float_buffer=False); im.colorspace_settings.name = "Non-Color"
        px = np.concatenate([dati[::-1], np.ones((H, W, 1))], -1).astype(np.float32)   # Blender: riga 0 in basso
        im.pixels.foreach_set(px.ravel()); im.filepath_raw = f_; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
    return f_f, f_n, lati
