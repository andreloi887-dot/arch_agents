# Materiali (Lumion 12 / 12.5)

> Fonte: KB *What do the properties of the Standard Material mean in Lumion 12?*, *How do Normal Maps work in Lumion 12?*, *Copy, paste, save and load Materials in Lumion 12*, *Add a texture to the standard Glass Material in Lumion 12.5 and older*, release notes 12.0/12.3/12.5.

## Logica
- All'import ogni superficie è un *Imported Material*, tranne vetro e acqua convertiti automaticamente. Per modificarla le assegni un **Standard Material** (si porta dietro la Color Map) o un materiale di libreria.
- Lumion 12 Pro ha 1.357 materiali (65 nuovi in Lumion 12, ad esempio mattoni, calcestruzzo, pietra, coperture in canna, lamiera ondulata, sughero, pavimento tattile).
- Lumion 12.5 usa ancora **Gloss** (più alto = riflesso più nitido). La *Roughness* arriva solo con Lumion 2023. Con texture PBR la **roughness va invertita** per ottenere la gloss map.

## Standard Material – mappe
- **Color Map**: albedo. Accetta anche un **MP4** come video texture (senza alfa; il processore ne gestisce al massimo circa 5 in contemporanea).
- **Normal Map**: caricando una Color Map, Lumion genera automaticamente Normal e Gloss. Puoi rigenerarla (*Create Normal Map from Color Map*) o caricarne una tua. *Flip Normal Map direction* se il rilievo risulta invertito: valutalo con il sole o uno spot sulla superficie.
- **Gloss Map**: slot separato (dalla 12.0 non serve più incorporare l'alfa in Photoshop). Resta supportato il metodo vecchio con l'alfa della Normal Map.
- **Alpha Clip Map**: maschera usata come Reflectivity, Clip (trasparenza ritagliata, attiva di default) o Emissive.
- **Displacement Map**: in scala di grigi (nero = 0, bianco = massimo spostamento). Lato divisibile per 4, meglio quadrata (2048×2048). Se è presente, la Normal viene generata dal displacement. I materiali di libreria con l'icona "D" ce l'hanno già. Le texture oltre 4.000 px pesano.

## Standard Material – slider
| Slider | Comportamento | Indicazioni |
|---|---|---|
| Colorization | 0–0,5 tinge la texture, 0,5–1 la sostituisce col colore | 0 se la texture è corretta |
| Gloss | 0 = riflesso sfocato, 1 = valore della gloss map, fino a 2 = mappa × 2 | intonaco 0,2–0,4; legno verniciato 0,6–1; laccati e metalli 1–1,5 |
| Reflectivity | 0–1 quantità di riflesso; **1–2 = riflessione metallica** (colorata dal materiale); vicino a 2 con gloss alto = specchio | opachi 0,2–0,5; metalli 1,2–1,8 |
| Relief | intensità della normal map | 0,5–1,2 |
| Displacement | intensità dello spostamento 3D | solo con mappa |
| Map Scale | **0 = usa le UV del CAD**; > 0 = mappatura a box; 1,0 con texture quadrata = 1×1 m | — |

**Altre impostazioni del pannello esteso**
- *Position/Orientation*: offset e rotazione, solo con Map Scale > 0.
- *Transparency*:
  - **Waxiness** (traslucenza): funziona solo con sole e luci Area/Line, non con Spot e Omni.
  - **Transparency**: dalla 12.3 regolabile indipendentemente dalla Waxiness. Nel render i livelli di trasparenza dipendono dalla qualità: 16 livelli a 4 stelle, 8 a 3, 4 a 2.
- *Settings*:
  - **Emissive**: agisce solo sulle aree della maschera.
  - **Saturation**.
  - **Specular**: potenzia i riflessi speculari, utile sui metalli.
  - **Flicker Reduction**: solo se ci sono superfici sovrapposte che sfarfallano. Regolalo con `Shift` di pochissimo: la soluzione vera è distanziare le superfici nel CAD.
- *Weathering*:
  - Preset: pietra, legno, pelle, acciaio spazzolato, argento/alluminio, oro, ferro, rame, plastica.
  - Valori: 0 = nuovo, 0–0,5 = invecchiato, 0,5–1 = anche sporco.
  - **Edges** arrotonda gli spigoli.
- *Foliage*: Spread, Leaves Size, Leaves Type (9 tipi), Spread Pattern Offset, Ground Level.

## Vetro
- **Glass** (standard): accetta una texture e l'**unica maschera di trasparenza a 256 livelli** (PNG/TGA/TIFF/BMP a 32 bit con alfa: nero = trasparente). Si usa con *Texture Influence* al massimo, poi si regolano Transparency e Reflectivity.
- **PureGlass**: vetro fisicamente più accurato, ma senza texture personalizzate. Al massimo 16 livelli di trasparenza.
- Limiti: Glass e PureGlass **non compaiono nelle Planar Reflections né nelle SpeedRay**. Il Depth of Field non sfoca bene Glass e PureGlass. Le ombre del vetro vanno attivate (vedi KB *How do you get glass to cast shadows?*).

## Altri materiali utili
- Water, Waterfall, Ocean.
- **Landscape**: fonde una mesh importata con il terreno.
- **3D Grass**: erba su mesh, pesante. Su aree grandi conviene Landscape Grass.
- **Foliage**: rampicanti e siepi su mesh. Usalo con parsimonia.
- **Fur**, **Billboard**, **Invisible**.
- **Surface Decals** (Pro, dalla 12.0): 142 decalcomanie (muschio, macchie d'acqua, mattoni a vista, segnaletica, buche...). Sono oggetti in *Effects › Decals* e prendono la texture e il rilievo del materiale sottostante. Dalla 12.3 si possono importare **decal personalizzate**.
- Materiali di libreria con slider propri (Nature, Brick...): i parametri estesi si copiano tra materiali dello stesso tipo.

## Copiare, salvare, riusare
- Ogni materiale ha un menu contestuale con *Copy/Paste* e *Save/Load* (file **`.LNM`**).
- *Save to Custom Materials* salva il materiale nella tua libreria personale.
- **Material Set** (`.MTT`) salva e carica tutti i materiali di un modello importato; l'abbinamento avviene per **nome del materiale CAD**. Salvalo prima di ogni re-import importante.
- Le texture assegnate nel CAD (icona triangolo giallo) non si possono salvare in un file materiale.
- Fix 12.5: il contorno giallo di selezione è sempre visibile, e le video texture MP4 vengono salvate una sola volta in `Documents\Lumion 12.5\Miscellaneous\Video Textures`.

## Buone pratiche
- Prima i materiali "grandi" (facciate, pavimenti, vetri), poi i dettagli. Controllali con il sole a mezzogiorno e radente: gloss e reflectivity sbagliati si vedono al tramonto.
- Evita il bianco puro: per gli intonaci usa RGB intorno a 230–240.
- Texture: 2K come standard, 4K solo in primo piano, 8–16K solo per mappe satellitari di terreni grandi. Il massimo supportato è 16.384 px.
