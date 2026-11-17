"""Affianca un'immagine di riferimento e un render (o più render) per il confronto a vista, alla stessa altezza.

  python skills/arredo-da-riferimento/scripts/affianca.py <riferimento> <render> [<render> ...] -o <uscita.jpg> [--alto 900]

Scrive un JPG con le immagini in fila, ognuna con il nome del file sopra. Serve al passo "confronta col riferimento" della
skill: guardare il risultato accanto alla foto che Andrea ha dato, non a memoria.
"""
import os, sys
from PIL import Image, ImageDraw


def affianca(file, uscita, alto=900):
    ims = [Image.open(f).convert("RGB") for f in file]
    ims = [im.resize((round(im.width * alto / im.height), alto)) for im in ims]
    W = sum(im.width for im in ims) + 10 * (len(ims) - 1); M = Image.new("RGB", (W, alto + 30), "white"); d = ImageDraw.Draw(M); x = 0
    for f, im in zip(file, ims):
        M.paste(im, (x, 30)); d.text((x + 6, 8), os.path.basename(f), fill="black"); x += im.width + 10
    M.save(uscita, quality=90); return uscita


if __name__ == "__main__":
    a = sys.argv[1:]; out = a[a.index("-o") + 1]; alto = int(a[a.index("--alto") + 1]) if "--alto" in a else 900
    file = [x for x in a if x not in ("-o", out, "--alto", str(alto))]
    print(affianca(file, out, alto))
