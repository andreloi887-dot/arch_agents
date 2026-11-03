# Build mode, navigazione e organizzazione

## Modalità principali
- **Build mode** (Edit): *Weather* (sole/nuvole), *Landscape* (terreno, acqua, oceano, erba, materiali landscape, OpenStreetMap), *Materials*, *Objects* (libreria: natura, persone/animali, trasporti, interni, esterni, luci e utilità, effetti speciali/particelle, suoni, importati).
- **Photo**, **Movie**, **360 Panorama**: ciascuna con stack di effetti proprio (copiabile tra modalità tramite *Save/Load effects* `.lfx`, o copia dello stack).

## Navigazione (tasti di base – verificare nella guida in-app con il tasto `?`/F1)
- `W A S D` movimento, `Q`/`E` su/giù, tasto destro mouse = orbita/guardo, rotella = zoom.
- `Shift` = veloce, `Spazio`/`Shift+Spazio` = più lento/molto veloce (varia).
- Tasto centrale (pan), `O` + tasto destro = orbita attorno a un punto.
- `Ctrl+1…0` salva posizione camera, `Shift+1…0` richiama.
- `F1–F4` qualità editor (F4 = massima; lavora a F2–F3 su scene pesanti).
- Durante lo spostamento oggetti: `M` sposta, `H` altezza, `R` ruota, `L` scala (tieni premuto e trascina), `Alt`+trascina = copia, `Ctrl`+trascina = selezione rettangolare, `Shift` = disattiva snapping al terreno.
- `Ctrl+F` / *Context menu › Transformation › Lock position* per bloccare oggetti.

## Layer
Fino a 20 layer: separa **Edificio / Contesto / Vegetazione / Persone / Auto / Luci / Varianti**. Nascondi i layer pesanti mentre lavori; la visibilità layer è animabile in Movie (effetto *Layer visibility*) → ottimo per varianti di progetto e cantierizzazione (anche *Animated phasing*).

## Posizionamento massivo
- *Mass placement* (Pro): distribuzione di oggetti lungo una linea/area con spaziatura e variazione random → filari, parcheggi, folle.
- *Cluster*: piazzamento casuale di un gruppo di oggetti.
- *Randomize* (menu contestuale): rotazione/scala casuale per naturalezza.

## Landscape
- Terreno: *Height* (brush raise/lower/flatten/smooth) – disattivabile per scene urbane (piano piatto).
- *Paint*: materiali del terreno; *Grass*: erba 3D (altezza, densità, varianti) – pesa sulla GPU.
- *OpenStreetMap*: importa edifici/strade del contesto reale (blocchi volumetrici, utili come massing).
- Per quote complesse o contesto: importa il terreno come mesh dal CAD/GIS e applica materiale *Landscape* per fonderlo con l'erba.

## Organizzazione del file
- Salva versioni incrementali (`Progetto_v01.ls12`…) — i file corrotti esistono.
- *File › Save as* scrive anche i modelli importati; per spostare su altro PC: **Export scene** o copia `Documents/Lumion 12.5/Library/Import` + file `.ls12`.
