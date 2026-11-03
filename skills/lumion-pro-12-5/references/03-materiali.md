# Materiali

## Logica
Clicca sulla superficie in *Materials* → assegna dalla libreria (Indoor, Outdoor, Custom, Various). Le modifiche si applicano a tutte le superfici con lo stesso materiale sorgente.

## Materiale Standard – parametri chiave
| Parametro | Uso | Valori di partenza |
|---|---|---|
| Colorization | Tinta sulla texture | 0 se la texture è già corretta |
| Gloss | Intensità del riflesso | intonaco 0.1–0.3, legno lucidato 0.5–0.8, laccato 1.0+ |
| Reflectivity | Quantità di riflessione (Fresnel) | opachi 0.2–0.4, metalli 0.8–1 |
| Relief (Normal) | Profondità bump/normal | 0.5–1.2; mai esagerare sui muri |
| Scale | Dimensione texture (m) | verifica con un oggetto di riferimento (es. mattone 0.25 m) |
| Settings › Waxiness / Transparency / Emissive / Two-sided / Displacement | casi specifici | emissive per LED/insegne |
| Weathering | Sporco/usura (Lumion 11+) | 0.1–0.3 per realismo, mai 0 sugli esterni |

Le texture **PBR** (Albedo, Normal, Roughness→Gloss, Metallic, Displacement) si caricano nel materiale *Standard*: ricorda che Lumion usa *gloss*, quindi la roughness va **invertita** se non c'è opzione dedicata.

## Materiali speciali
- **Glass**: vetro architettonico con spessore. Reflectivity 0.6–0.9, Transparency alta, colore leggermente verde/azzurro. Per vetri singoli sottili: *Glass* + *Double sided*. Per vetro "freddo" usa *Frosted glass*.
- **Water / Waterfall / Ocean**: acqua da materiale su superficie modellata (piscine, vasche). Per vasche, modella la superficie leggermente sotto il bordo.
- **Landscape**: fonde una mesh importata con il terreno Lumion (erba inclusa).
- **Foliage**: per vegetazione importata (traslucenza e vento).
- **Invisible**: nasconde superfici (es. vetri interni che disturbano, piani di riferimento).
- **Billboard** / **Lightmap-free**: casi particolari (cartelloni, sfondi).
- **Fur / Carpet / Grass** sui materiali (Pro): moquette, tappeti, prati su mesh importate.
- **Decals / Surface decals** (introdotti con Lumion 12): adesivi di sporco/macchie/segnaletica sovrapposti senza toccare il modello.

## Buone pratiche
- Assegna prima i materiali "grandi" (facciate, pavimenti, vetri), poi il dettaglio.
- Controlla i materiali sotto luci diverse (mezzogiorno e golden hour): un gloss sbagliato emerge al tramonto.
- Salva set materiali (`.mts`) per libreria aziendale riutilizzabile.
- Evita bianco puro (RGB 255): usa ~230–240 per intonaci, altrimenti bruciature con *Exposure* alta.
