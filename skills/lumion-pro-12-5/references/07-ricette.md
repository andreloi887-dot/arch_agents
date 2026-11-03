# Ricette (punti di partenza da regolare a vista)

Valori costruiti sulle funzioni **realmente disponibili in Lumion 12.5 Pro**: niente ray tracing e niente HDRI personali. I numeri sono indicazioni d'esperienza, non dati ufficiali.

## Esterno diurno fotorealistico
1. Parti da uno *Style* realistico, poi personalizza lo stack.
2. **Real Skies** con un cielo coerente con l'ora (Clear o Cloudy). Se vuoi controllare il sole, metti *Sun* sopra Real Skies.
3. *Shadow*: soft shadow, OmniShadow moderato, Fine Detail Shadows attivo.
4. *Sky Light* su High, *Hyperlight* per la foto finale.
5. *Reflection*: SpeedRay attivo + Planar su vetrate e acqua principali (max 10 piani).
6. *2-Point Perspective*; focale ≈ 28–35 mm.
7. *Fog* leggera, Color Correction con saturazione −5/−10% e contrasto +5%, Sharpen leggero.
8. Contesto su più livelli: alberi alti, arbusti, Fine-detail Nature solo in primo piano, Landscape Grass, persone e auto. Decals (muschio, macchie d'acqua) sulle superfici troppo pulite.
9. Render Print + Print/Poster Enhancer.

## Golden hour
Sun Study con località reale e ora vicina al tramonto, oppure Real Sky Sunset. Sole radente sulla facciata principale; interni accesi con Spot e Area a **2.700–3.000 K** per il contrasto caldo/freddo; Volumetric Sunlight molto leggero; Exposure leggermente ridotta.

## Notturno / blue hour
Real Sky Night o Evening; luci con *Night activation* On o Random; emissive sulle vetrine; Volumetric Lights sugli spot principali con un filo di Fog; Bloom moderato; Exposure regolata senza bruciare le sorgenti. Nei video: Mass Move per auto e persone.

## Interno diurno
Style da interni; Shadow in modalità interior con OmniShadow; **Hyperlight** attivo; Global Illumination con gli spot principali selezionati (anteprima Off); Sky Light High; focale 18–24 mm con 2-Point Perspective; Planar sul pavimento lucido; Waxiness su tende e paralumi (funziona solo con sole e luci Area/Line). Se la luce filtra dagli spigoli: chiudi la geometria nel CAD.

## Interno in video
Stesso stack, ma ricorda che Hyperlight nei video è più scuro: aggiungi GI oppure Area Light rivolte verso il soffitto. Scena statica e 4 stelle se la GI sfarfalla.

## Vista aerea / masterplan
OpenStreetMap con Heightmap e mappa satellitare (Pro); progetto dentro l'area 2×2 km; Mass Placement per i filari; Fog per la profondità atmosferica; focale 35–50 mm; contesto OSM semitrasparente (*Buildings Alpha*) o in stile maquette.

## Studio di soleggiamento
*Sun Study*: latitudine e longitudine del sito, data (21/6, 21/12, equinozi), fuso orario e ora legale. Movie: anima l'*Hour* dall'alba al tramonto. Per tavole: foto alle 9, 12 e 15 con la stessa camera.

## Disegni tecnici renderizzati
*Orthographic View* (`F` per allinearti alla superficie) + *Clip Plane* con contorno per sezioni prospettiche (max 3 piani), oppure *Styrofoam* o *Blueprint* per l'effetto plastico.

## Concept / concorso artistico
Sopra uno stack realistico aggiungi *Sketch*, *Pastel Sketch*, *Watercolor*, *Painting* o *Outlines*. In alternativa: output realistico + render pass per una post-produzione mista.

## Animazione di cantiere / fasi
Componenti importati separatamente e allineati (*Align positions*) su layer distinti → *Animated Phasing* (preset di costruzione), oppure *Layer Visibility* animato, oppure *Advanced Move* sul Clip Plane. Camera orbitale lenta, Image Sequence, 30 fps.
