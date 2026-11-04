#!/usr/bin/env python3
"""Accesso a Google Maps Platform (Geocoding, Street View Static, Maps Static) e OpenStreetMap.

Chiave: variabile d'ambiente GOOGLE_MAPS_API_KEY. Solo libreria standard.
Le immagini Google scaricate sono riferimento di lavoro locale: non importarle in SketchUp,
non usarle nei deliverable (vedi references/01-fonti-accesso.md).

Esempi:
  gmaps.py geocode "Via Garibaldi 10, Bergamo"
  gmaps.py sv-meta --lat 45.6942 --lng 9.6700
  gmaps.py sv-shots --piano piano_riprese.json --out zona/_rif_google [--dry-run]
  gmaps.py static --center 45.6942,9.6700 --zoom 19 --out zona/_rif_google/satellite.png
  gmaps.py osm-edifici --bbox 45.6935,9.6690,45.6950,9.6712 --out zona/geometria/osm.geojson
"""
import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://maps.googleapis.com/maps/api"
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = "rilievo-urbano/1.0"


def api_key():
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        sys.exit("Errore: imposta GOOGLE_MAPS_API_KEY (Street View Static, Maps Static, Geocoding abilitate).")
    return key


def build_url(path, params, with_key=True):
    p = dict(params)
    if with_key:
        p["key"] = api_key()
    return f"{BASE}/{path}?{urllib.parse.urlencode(p)}"


def redact(url):
    return url.split("&key=")[0] + "&key=***" if "&key=" in url else url


def http_get(url, data=None, tentativi=4):
    import time
    for i in range(tentativi):
        req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and i < tentativi - 1:
                time.sleep(2 ** (i + 1)); continue
            body = e.read()[:300].decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {e.code} su {redact(url)}: {body}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if i == tentativi - 1:
                raise
            time.sleep(2 ** (i + 1))


def get_json(url, data=None):
    body, _ = http_get(url, data)
    return json.loads(body)


# ---------------------------------------------------------------- geometria
def bearing(lat1, lng1, lat2, lng2):
    """Azimut iniziale da 1 a 2 in gradi (0 = Nord, orario)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def distance_m(lat1, lng1, lat2, lng2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- comandi
def cmd_geocode(a):
    res = get_json(build_url("geocode/json", {"address": a.indirizzo, "language": "it"}))
    if res.get("status") != "OK":
        sys.exit(f"Geocoding: {res.get('status')} {res.get('error_message', '')}")
    out = [{"indirizzo": r["formatted_address"], **r["geometry"]["location"],
            "tipo": r["geometry"].get("location_type")} for r in res["results"]]
    print(json.dumps(out, ensure_ascii=False, indent=2))


def sv_meta(lat=None, lng=None, pano=None, radius=50):
    params = {"source": "outdoor", "radius": radius}
    if pano:
        params["pano"] = pano
    else:
        params["location"] = f"{lat},{lng}"
    return get_json(build_url("streetview/metadata", params))


def is_ufficiale(meta):
    return meta.get("status") == "OK" and "google" in (meta.get("copyright") or "").lower()


def cerca_pano_ufficiale(lat, lng, raggio_max=20, passo=5):
    """Sonda (metadata gratuiti) una griglia attorno al punto e restituisce il pano Google ufficiale
    più vicino al punto richiesto, o None."""
    dlat = 1 / 111320.0
    dlng = 1 / (111320.0 * math.cos(math.radians(lat)))
    visti, migliore = set(), None
    for r in range(passo, raggio_max + 1, passo):
        for k in range(8):
            ang = math.radians(45 * k)
            m = sv_meta(lat + r * math.cos(ang) * dlat, lng + r * math.sin(ang) * dlng, radius=passo * 2)
            if not is_ufficiale(m) or m["pano_id"] in visti:
                continue
            visti.add(m["pano_id"])
            d = distance_m(lat, lng, m["location"]["lat"], m["location"]["lng"])
            if migliore is None or d < migliore[0]:
                migliore = (d, m)
        if migliore:
            return migliore[1]
    return None


def cmd_sv_meta(a):
    print(json.dumps(sv_meta(a.lat, a.lng, a.pano, a.radius), ensure_ascii=False, indent=2))


def cmd_sv_shots(a):
    with open(a.piano, encoding="utf-8") as f:
        piano = json.load(f)
    size = int(piano.get("size", 640))
    if size > 640:
        sys.exit("size massimo 640 (piani standard).")
    os.makedirs(a.out, exist_ok=True)
    manifest = {"size": size, "eye_height_m": 2.5, "riprese": [], "scartate": []}
    for s in piano["riprese"]:
        sid = s["id"]
        da = s.get("da", {})
        meta = sv_meta(da.get("lat"), da.get("lng"), s.get("pano"), s.get("radius", 50))
        if meta.get("status") != "OK":
            manifest["scartate"].append({"id": sid, "motivo": meta.get("status")})
            print(f"{sid}: nessun pano ({meta.get('status')})", file=sys.stderr)
            continue
        ufficiale = is_ufficiale(meta)
        if not ufficiale and not s.get("pano") and da and not s.get("consenti_pano_utente", False):
            alt = cerca_pano_ufficiale(da["lat"], da["lng"])
            if alt:
                print(f"{sid}: pano utente ({meta.get('copyright')}) sostituito con pano Google vicino", file=sys.stderr)
                meta, ufficiale = alt, True
        if not ufficiale and not s.get("consenti_pano_utente", False):
            manifest["scartate"].append({"id": sid, "motivo": f"pano utente ({meta.get('copyright')}): "
                                         "quota e posizione camera ignote; spostare il punto 'da' o "
                                         "impostare consenti_pano_utente (solo descrizione, no camera matching)"})
            print(f"{sid}: scartata, pano non Google ({meta.get('copyright')})", file=sys.stderr)
            continue
        plat, plng = meta["location"]["lat"], meta["location"]["lng"]
        scarto = distance_m(da["lat"], da["lng"], plat, plng) if da else 0.0
        if "bersaglio" in s:
            t = s["bersaglio"]
            heading = bearing(plat, plng, t["lat"], t["lng"])
            dist_t = distance_m(plat, plng, t["lat"], t["lng"])
        else:
            heading = float(s["heading"])
            dist_t = None
        rec = {
            "id": sid, "pano_id": meta["pano_id"], "lat": plat, "lng": plng,
            "data": meta.get("date"), "copyright": meta.get("copyright"),
            "heading": round(heading, 2), "pitch": float(s.get("pitch", 0)),
            "fov": float(s.get("fov", 90)), "size": size,
            "scarto_pano_m": round(scarto, 1),
            "distanza_bersaglio_m": round(dist_t, 1) if dist_t is not None else None,
            "inquadra": s.get("inquadra", ""), "file": f"{sid}.jpg", "pano_ufficiale": ufficiale,
        }
        if scarto > 25:
            print(f"{sid}: attenzione, pano a {scarto:.0f} m dal punto richiesto", file=sys.stderr)
        img_url = build_url("streetview", {
            "size": f"{size}x{size}", "pano": rec["pano_id"], "heading": rec["heading"],
            "pitch": rec["pitch"], "fov": rec["fov"], "return_error_code": "true"})
        if a.dry_run:
            rec["url"] = redact(img_url)
        else:
            body, ctype = http_get(img_url)
            if not ctype.startswith("image/"):
                raise RuntimeError(f"{sid}: risposta non immagine ({ctype})")
            with open(os.path.join(a.out, rec["file"]), "wb") as f:
                f.write(body)
        manifest["riprese"].append(rec)
        print(f"{sid}: pano {rec['data']} heading {rec['heading']}° -> {rec['file']}", file=sys.stderr)
    path = os.path.join(a.out, "manifest_riprese.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(path)


def cmd_static(a):
    lat, lng = (float(v) for v in a.center.split(","))
    params = {"center": f"{lat},{lng}", "zoom": a.zoom, "size": f"{a.size}x{a.size}",
              "scale": a.scale, "maptype": a.maptype}
    body, ctype = http_get(build_url("staticmap", params))
    if not ctype.startswith("image/"):
        sys.exit(f"Risposta non immagine: {body[:200]!r}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(body)
    meta = {"center": [lat, lng], "zoom": a.zoom, "size": a.size, "scale": a.scale, "maptype": a.maptype}
    with open(os.path.splitext(a.out)[0] + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(a.out)


def cmd_osm(a):
    s, w, n, e = (float(v) for v in a.bbox.split(","))
    q = f"""[out:json][timeout:60];
(way["building"]({s},{w},{n},{e});relation["building"]({s},{w},{n},{e});
 way["barrier"]({s},{w},{n},{e});node["highway"="street_lamp"]({s},{w},{n},{e});
 node["amenity"~"bench|waste_basket|bicycle_parking"]({s},{w},{n},{e});node["natural"="tree"]({s},{w},{n},{e}););
out geom tags;"""
    res = get_json(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode())
    feats = []
    for el in res.get("elements", []):
        tags = el.get("tags", {})
        if el["type"] == "node":
            geom = {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
        elif el["type"] == "way" and "geometry" in el:
            coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
            closed = len(coords) > 3 and coords[0] == coords[-1]
            geom = ({"type": "Polygon", "coordinates": [coords]} if closed and "building" in tags
                    else {"type": "LineString", "coordinates": coords})
        else:
            continue  # relation multipolygon: verificare a mano
        feats.append({"type": "Feature", "id": f"{el['type']}/{el['id']}", "properties": tags, "geometry": geom})
    gj = {"type": "FeatureCollection", "attribution": "© OpenStreetMap contributors (ODbL)", "features": feats}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, indent=1)
    nb = sum(1 for x in feats if "building" in x["properties"])
    print(f"{a.out}: {len(feats)} elementi ({nb} edifici)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("geocode"); g.add_argument("indirizzo"); g.set_defaults(f=cmd_geocode)
    m = sub.add_parser("sv-meta"); m.add_argument("--lat", type=float); m.add_argument("--lng", type=float)
    m.add_argument("--pano"); m.add_argument("--radius", type=int, default=50); m.set_defaults(f=cmd_sv_meta)
    s = sub.add_parser("sv-shots"); s.add_argument("--piano", required=True); s.add_argument("--out", required=True)
    s.add_argument("--dry-run", action="store_true"); s.set_defaults(f=cmd_sv_shots)
    st = sub.add_parser("static"); st.add_argument("--center", required=True); st.add_argument("--zoom", type=int, default=19)
    st.add_argument("--size", type=int, default=640); st.add_argument("--scale", type=int, default=2)
    st.add_argument("--maptype", default="satellite"); st.add_argument("--out", required=True); st.set_defaults(f=cmd_static)
    o = sub.add_parser("osm-edifici"); o.add_argument("--bbox", required=True, help="sud,ovest,nord,est")
    o.add_argument("--out", required=True); o.set_defaults(f=cmd_osm)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
