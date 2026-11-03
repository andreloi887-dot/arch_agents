# Luce ed effetti

Gli effetti si aggiungono nella modalità Photo/Movie/Panorama (*FX* › categorie: Light and Shadow, Camera, Weather and Climate, Scene and Animation, Artistic, Sketch, Color, Various, Styles). L'**ordine** nello stack conta (gli effetti di colore/artistici in fondo).

## Partire da uno Style
I *Styles* (Realistic, Interior, Evening, Night, Daylight, Color Sketch, Watercolor…) sono stack pronti: buon punto di partenza, poi si rifinisce. Per fotorealismo: **Realistic** + regolazioni.

## Light and Shadow – i core
- **Sun**: altezza e azimut (o *Sun study* con località, data, ora – utile per studi di soleggiamento reali), intensità, *Sun disk size*. Partenza: intensità 1.5–2.5.
- **Shadow**: *Sun shadow range* (Small per interni/dettagli, Large per vedute), *Soft shadow* ON, *Coloring* leggero per ombre calde/fredde, *Omni shading* per riempire gli interni, *Interior/Exterior* switch.
- **Hyperlight** (Pro, Photo mode): rimbalzi indiretti di sole/cielo più accurati → aumenta realismo soprattutto in interni e sotto porticati. Costo di render elevato; usalo per still finali.
- **Global Illumination**: rimbalzo della luce del sole (e degli spotlight selezionati) – utile in interni.
- **Reflection**: aggiungi *Planar reflection* per pavimenti lucidi/acqua/vetri principali (max 10 piani: sceglili bene). *Speedray reflections* per qualità superiore.
- **Sky Light**: luce dalla cupola celeste – sempre ON per esterni (qualità *High* nel finale), riduce look "CG".
- **Volume light / Volumetric sunlight** (raggi, nebbia luminosa) – con parsimonia.
- **Real skies** (Pro): HDRI di cielo realistici con luce coerente: spesso il miglior upgrade singolo per un esterno.

## Luci artificiali
- *Objects › Lights and utilities*: Spotlight, Omni, Area/Line light, Fill light. Temperatura in **Kelvin** (novità di Lumion 12): 2700 K caldo residenziale, 3000–3500 K hospitality, 4000 K uffici.
- **Volumetric spotlight** (Lumion 12): coni di luce visibili in ambienti con foschia.
- Profili **IES** per spotlight: carica file del produttore per proiezioni realistiche.
- Shadow per spot: ON solo per le luci principali (pesano molto).

## Camera
- **Two-point perspective**: obbligatorio per architettura (verticali dritte).
- Focal length: 25–35 mm esterni, 18–24 mm interni (evitare < 16 mm distorto).
- **Depth of field**: leggero, per still di dettaglio.
- **Lens flare, Chromatic aberrations, Noise, Vignette**: dosi minime = più fotografico.
- **Exposure** con *Auto exposure* off per controllo coerente tra viste.

## Weather and Climate
- *Clouds / Fog / Rain / Snow / Wind*. Nebbia leggera (density 0.05–0.15) aumenta la profondità atmosferica.
- *Horizon cloud* per riempire skyline vuoti.

## Color / Finishing
- *Color correction* (temperatura, saturazione, contrasto, gamma), *Selective saturation*, *Bloom* leggero, *Sharpen* (0.4–0.6).
- Per output finale considera di uscire "neutro" e rifinire in Photoshop/Lightroom (esporta anche *Render pass*: depth, normal, material ID, lighting specular, sky alpha – utili per maschere).
