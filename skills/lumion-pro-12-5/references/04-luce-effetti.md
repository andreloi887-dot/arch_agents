# Luce ed effetti (Lumion 12 / 12.5)

> Fonte: KB *What are the changes in the Effects Categories for Lumion 12?*, *Planar / SpeedRay / Projected Reflections*, *Spotlight properties*, *Omni/Fill/Area Lights*, *Why are there no sun shadows?*, *Sun Effect with Real Skies*, *Render without sun shadows*, *Replace the sky with a photo*, release notes 12.0/12.3/12.5.

## Regole di base
- **Nello stack conta l'ordine: l'effetto più in alto ha la precedenza.** Esempio: per controllare il sole con Real Skies attivo, metti *Sun* **sopra** *Real Skies*. Attenzione però a non ritrovarti due soli nell'immagine.
- Gli stack si salvano e caricano dal menu contestuale del pulsante **+FX**. Non funzionano con progetti diversi nel caso delle animazioni di oggetti (Advanced Move).
- In Movie conviene mettere gli effetti comuni su *Entire Movie* e non sulle singole clip.
- Nella 12.5 il **ray tracing non c'è** (arriva con Lumion 2023): il motore è raster, con Hyperlight, Sky Light, GI e riflessioni SpeedRay o Planar.

## Categorie degli effetti in Lumion 12
- **Featured (Photo)**: Orthographic View, 2-Point Perspective, Depth of Field, Photo Matching, Real Skies, Sun, Shadow, Reflection, Hyperlight, Sky Light, Color Correction, Layer Visibility.
- **Concept**: Sketch, Outlines, Pastel Sketch.
- **Architectural**: Orthographic View, Blueprint, Styrofoam, Sun Study, Photo Matching, 2-Point Perspective.
- **Lighting**: Sun, Shadow, Sky Light, Hyperlight, Global Illumination, Real Skies, God Rays, Volumetric Sunlight, Volumetric Lights, Reflection.
- **Sky/Weather**: Sky and Clouds, Fog, Wind, Precipitation, Volume Clouds, Horizon Cloud, Moon, Autumn Colors, Aurora Borealis, Contrails.
- **Camera**: Depth of Field, Tilt Shift, Fish Eye, Lens Flare, Handheld Camera, Chromatic Aberrations, Exposure.
- **Animation**: Mass Move, Move, Advanced Move, Animate Light Colors, Animated Phasing, Fade in/out, Motion Blur, Titles, Time Warp.
- **Artistic**: Painting, Watercolor, Manga, Cartoon, Oil Painting.
- **Enhancements**: Color Correction, Sharpen, Bleach, Selective Saturation, Vignette, Bloom, Analog Color Lab, Noise.
- **Tools/Utilities**: Near Clip Plane, Print/Poster Enhancer, Image Overlay, Material Highlight, Layer Visibility, Variation Control, Water, Side by Side 3D Stereo, Sound.

Non disponibili nei panorami: Orthographic, 2-Point, DoF, Photo Matching, Hyperlight, Sky Light, Wind, gli effetti camera, Painting/Watercolor, Vignette, Print/Poster Enhancer, Image Overlay.

## Sole, cielo, ombre
- **Sun**: altezza, direzione, intensità. **Sun Study**: località (latitudine e longitudine), giorno, mese, anno, fuso orario e ora legale, ora. Si usa per studi di soleggiamento reali e si anima sull'ora.
- **Real Skies**: libreria di cieli reali (Cloudy, Evening, Morning, Overcast, Sunset, Clear, Night). ⚠️ **Nella 12.5 non si può caricare un HDRI personale** (è arrivato con la 2023.3). Se vuoi un tuo cielo: render con *Sky Alpha* e sostituzione in Photoshop.
- **Shadow**: range delle ombre del sole, soft shadow, colorazione, **OmniShadow** (occlusione ambientale), *Fine Detail Shadows*, modalità interior/exterior, Ultra Sharp.
- Per un render senza ombre nette (cielo coperto): stile Overcast o Sky and Clouds coperto, *Sun* sopra Real Skies con Brightness 0, Sky Light Off, OmniShadow 0, Fine Detail Shadows 0, poi compensa con Exposure.
- **Sky Light**: luce dalla volta celeste. Per i render Print e Poster usa la qualità **High**: Normal o Ultra, combinati con Real Skies, possono dare artefatti a quadretti.
- **Hyperlight** (Photo e Movie, non nei panorami): rimbalzo della luce più accurato. Nei video e nelle sequenze ha un raggio più corto, quindi **i video risultano più scuri delle foto**. Rimedi: GI, oppure luci Omni o Area rivolte verso il soffitto. Fix 12.5: i materiali trasparenti colpiti dal sole non "esplodono" più in luminosità nei render Print con Hyperlight.
- **Global Illumination**: sonde di luce riflessa da sole e spot selezionati. *Preview spotlight GI and shadows* va tenuto **Off** durante il lavoro (pesantissimo). Nei video con sole o oggetti animati fa sfarfallare la luce: render a 4 stelle e scena statica.

## Luci artificiali (Lumion 12)
| Tipo | Ombre | Uso |
|---|---|---|
| **Spotlight** | sì (Medium Static 512 px, High Static 1024 px, **Dynamic** che si aggiorna a ogni frame ed è lento) | luci principali; profili **IES** (solo simmetrici); *Target Light* punta su una superficie |
| **Omni Light** | sì (dalla 11.3) + *Shadow Exclusion Zone* | lampade, sorgenti puntiformi |
| **Area / Line Light** | no (veloci) | strisce LED, plafoniere, riempimento |
| **Fill Light** | no, illumina tutte le superfici | riempimento lontano dalla camera |

- **Temperatura in Kelvin** (novità della 12): da 3.000 K caldo a 7.000 K freddo, per Spot, Omni e Area/Line. Il selettore colore è ora quadrato (tonalità e saturazione); la luminosità si regola solo con lo slider.
- *Night activation*: On, oppure Random (accensione casuale quando il sole è vicino all'orizzonte).
- Ombre Dynamic solo se ci sono oggetti animati nel cono. Ogni spot Dynamic rallenta molto il render.
- **Volumetric Lights** (Pro): dalla 12.0 per gli spot, dalla 12.3 anche per le Omni. Coni di luce visibili, ideali con nebbia, Real Sky atmosferico o precipitazioni.
- **Animate Light Colors**: animazione di colore e intensità delle luci.
- I valori fisici in lumen e nit della KB valgono **dalla 2023 in poi**. Nella 12.5 la luminosità degli slider si tara a vista.

## Riflessioni (pipeline raster)
| Tipo | Precisione | Costo | Note |
|---|---|---|---|
| Projected (predefinita) | bassa | minimo | panorama a 360° dal *Reflection Control*; nelle foto viene generato dalla posizione della camera; `U` aggiorna l'anteprima |
| **SpeedRay** (Pro) | buona su ogni superficie | basso | riflette solo ciò che è visibile a schermo; non riflette vetri, acqua, oceano, fumo, fuoco e nebbia |
| **Planar** | massima sui piani | alto (ogni piano = un render in più della scena) | **massimo 10 piani** per foto o clip; pulsante di rilevamento automatico; *Plane Margins*; durante il lavoro anteprima su None |

Le Planar non mostrano Glass e PureGlass, OmniShadow, Hyperlight, GI, Sky Light, lens flare, fumo, fuoco e nebbia. La nitidezza del riflesso dipende dalla **Gloss** del materiale.

## Camera e post-produzione
- **2-Point Perspective**: obbligatoria per l'architettura (verticali parallele).
- **Orthographic View**: piante, prospetti e sezioni (insieme a Clip Plane con contorno). `F` allinea la camera alla superficie al centro della vista.
- **Photo Matching**: inserimento del progetto in una foto. L'immagine deve essere in **16:9**, altrimenti l'allineamento salta.
- **Near Clip Plane**: se la camera taglia il modello (modelli molto alti sul terreno).
- **Depth of Field**, **Exposure**, **Color Correction**, **Sharpen**, **Bloom**, **Vignette**, **Noise**, **Chromatic Aberrations**: dosi minime per un risultato fotografico.
- **Print/Poster Enhancer**: sempre attivo per i render Print e Poster.
- **Autumn Colors**: preset autunno, primavera ed estate; può agire su tutti i layer.
