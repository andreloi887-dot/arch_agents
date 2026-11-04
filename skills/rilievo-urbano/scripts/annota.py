#!/usr/bin/env python3
"""Annotazioni grafiche per la scheda di rilievo (richiede Pillow).

  annota.py mappa    --img satellite.png --etichette etichette.json [--geojson osm.geojson] --out mappa_annotata.png
      etichette.json: [{"id": "E01", "lat": .., "lng": ..}, {"id": "SV-01", "lat": .., "lng": .., "heading": 120}]
      (usa satellite.meta.json scritto da gmaps.py static)
  annota.py foto     --img SV-01.jpg --note note.json --out SV-01_annotata.png
      note.json: [{"id": "E01", "box": [x, y, w, h], "testo": "C01 intonaco ocra"}]
  annota.py palette  --scheda scheda.json --out palette.png
  annota.py campiona --img SV-01.jpg --box x,y,w,h      -> hex mediano e intervallo (5°-95° percentile)
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

COL_ID = {"E": (255, 214, 0), "R": (0, 200, 255), "A": (255, 120, 200), "P": (180, 255, 120),
          "V": (90, 230, 90), "S": (255, 80, 60)}


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def latlng_to_px(lat, lng, meta):
    """Web Mercator: lat/lng -> pixel dell'immagine Maps Static (center, zoom, size, scale)."""
    def world(la, ln):
        siny = min(max(math.sin(math.radians(la)), -0.9999), 0.9999)
        x = 256 * (0.5 + ln / 360.0)
        y = 256 * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi))
        return x * 2 ** meta["zoom"], y * 2 ** meta["zoom"]
    cx, cy = world(*meta["center"])
    x, y = world(lat, lng)
    s = meta.get("scale", 1)
    half = meta["size"] * s / 2
    return (x - cx) * s + half, (y - cy) * s + half


def label(draw, xy, text, color, f):
    x, y = xy
    l, t, r, b = draw.textbbox((0, 0), text, font=f)
    w, h = r - l, b - t
    draw.rectangle([x - w / 2 - 4, y - h / 2 - 4, x + w / 2 + 4, y + h / 2 + 4], fill=(0, 0, 0))
    draw.text((x - w / 2 - l, y - h / 2 - t), text, fill=color, font=f)


def cmd_mappa(a):
    img = Image.open(a.img).convert("RGB")
    with open(os.path.splitext(a.img)[0] + ".meta.json", encoding="utf-8") as fh:
        meta = json.load(fh)
    d = ImageDraw.Draw(img)
    f = font(max(14, img.width // 55))
    if a.geojson:
        with open(a.geojson, encoding="utf-8") as fh:
            gj = json.load(fh)
        for ft in gj["features"]:
            g = ft["geometry"]
            rings = g["coordinates"] if g["type"] == "Polygon" else [g["coordinates"]] if g["type"] == "LineString" else []
            for ring in rings:
                pts = [latlng_to_px(la, ln, meta) for ln, la in ring]
                d.line(pts, fill=(255, 255, 255), width=2)
    with open(a.etichette, encoding="utf-8") as fh:
        etichette = json.load(fh)
    for e in etichette:
        x, y = latlng_to_px(e["lat"], e["lng"], meta)
        col = COL_ID.get(e["id"][0], (255, 255, 255))
        if "heading" in e:  # ripresa: punto + freccia di direzione
            hd = math.radians(e["heading"])
            L = img.width / 18
            d.line([(x, y), (x + L * math.sin(hd), y - L * math.cos(hd))], fill=col, width=4)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col)
            label(d, (x, y + 22), e["id"], col, f)
        else:
            label(d, (x, y), e["id"], col, f)
    d.text((8, img.height - 22), "Riferimento di lavoro – immagine © Google, non per deliverable",
           fill=(255, 255, 255), font=font(14))
    img.save(a.out)
    print(a.out)


def cmd_foto(a):
    img = Image.open(a.img).convert("RGB")
    d = ImageDraw.Draw(img)
    f = font(max(13, img.width // 45))
    with open(a.note, encoding="utf-8") as fh:
        note = json.load(fh)
    for n in note:
        x, y, w, h = n["box"]
        col = COL_ID.get(n["id"][0], (255, 255, 255))
        d.rectangle([x, y, x + w, y + h], outline=col, width=3)
        txt = n["id"] + (f" · {n['testo']}" if n.get("testo") else "")
        l, t, r, b = d.textbbox((0, 0), txt, font=f)
        ty = y - (b - t) - 8 if y > (b - t) + 10 else y + 4
        d.rectangle([x, ty - 2, x + (r - l) + 8, ty + (b - t) + 6], fill=(0, 0, 0))
        d.text((x + 4 - l, ty + 2 - t), txt, fill=col, font=f)
    img.save(a.out)
    print(a.out)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cmd_palette(a):
    with open(a.scheda, encoding="utf-8") as fh:
        pal = json.load(fh)["palette"]
    cols, sw, pad = 4, 260, 20
    rows = math.ceil(len(pal) / cols)
    img = Image.new("RGB", (cols * (sw + pad) + pad, rows * (sw + 130) + pad), (255, 255, 255))
    d = ImageDraw.Draw(img)
    fb, fs = font(22), font(15)
    for i, c in enumerate(pal):
        x = pad + (i % cols) * (sw + pad)
        y = pad + (i // cols) * (sw + 130)
        d.rectangle([x, y, x + sw, y + sw - 60], fill=hex_to_rgb(c["hex"]), outline=(0, 0, 0))
        lo, hi = c.get("intervallo", [c["hex"], c["hex"]])
        d.rectangle([x, y + sw - 60, x + sw // 2, y + sw], fill=hex_to_rgb(lo), outline=(0, 0, 0))
        d.rectangle([x + sw // 2, y + sw - 60, x + sw, y + sw], fill=hex_to_rgb(hi), outline=(0, 0, 0))
        d.text((x, y + sw + 6), f"{c['id']}  {c['hex']}", fill=(0, 0, 0), font=fb)
        d.text((x, y + sw + 34), c["materiale"][:30], fill=(40, 40, 40), font=fs)
        d.text((x, y + sw + 54), c.get("finitura", "")[:30], fill=(40, 40, 40), font=fs)
        d.text((x, y + sw + 74), f"conf. {c.get('confidenza', '?')}  {c.get('ral_indicativo', '')}"[:30],
               fill=(90, 90, 90), font=fs)
    img.save(a.out)
    print(a.out)


def cmd_campiona(a):
    img = Image.open(a.img).convert("RGB")
    x, y, w, h = (int(v) for v in a.box.split(","))
    raw = img.crop((x, y, x + w, y + h)).tobytes()
    px = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    if not px:
        sys.exit("box vuoto")
    out = {}
    for i, ch in enumerate("rgb"):
        vals = sorted(p[i] for p in px)
        n = len(vals)
        out[ch] = (vals[n // 2], vals[int(n * 0.05)], vals[min(n - 1, int(n * 0.95))])
    med = "#%02X%02X%02X" % tuple(out[c][0] for c in "rgb")
    lo = "#%02X%02X%02X" % tuple(out[c][1] for c in "rgb")
    hi = "#%02X%02X%02X" % tuple(out[c][2] for c in "rgb")
    print(json.dumps({"hex": med, "intervallo": [lo, hi], "pixel": len(px)}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mappa"); m.add_argument("--img", required=True); m.add_argument("--etichette", required=True)
    m.add_argument("--geojson"); m.add_argument("--out", required=True); m.set_defaults(f=cmd_mappa)
    fo = sub.add_parser("foto"); fo.add_argument("--img", required=True); fo.add_argument("--note", required=True)
    fo.add_argument("--out", required=True); fo.set_defaults(f=cmd_foto)
    p = sub.add_parser("palette"); p.add_argument("--scheda", required=True); p.add_argument("--out", required=True)
    p.set_defaults(f=cmd_palette)
    c = sub.add_parser("campiona"); c.add_argument("--img", required=True); c.add_argument("--box", required=True)
    c.set_defaults(f=cmd_campiona)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
