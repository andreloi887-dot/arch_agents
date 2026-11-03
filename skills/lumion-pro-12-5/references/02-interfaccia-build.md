# Build Mode, navigazione, scorciatoie, organizzazione

> Fonte: KB *Is there a list of all the keyboard shortcuts in Lumion 12?* (le scorciatoie **non sono personalizzabili**), *How do Layers work?*, *Terrains in Lumion 12*, *OpenStreetMap in Lumion 12 Pro*, release notes 12.0/12.3/12.5.

## Navigazione
| Tasto | Azione |
|---|---|
| `W A S D` / frecce | avanti, sinistra, indietro, destra |
| `Q` / `E` | su / giù |
| `Spazio` + movimento | molto lento |
| `Shift` + movimento | veloce |
| `Shift+Spazio` + movimento | molto veloce |
| Tasto destro + mouse | guarda intorno |
| Tasto centrale + mouse | pan (con Spazio/Shift: lento/veloce) |
| Rotella | avanti / indietro |
| `O` + tasto destro | orbita attorno al punto nel mirino |
| `Ctrl+H` | rimette la camera orizzontale (pitch 0) |
| Doppio clic destro su un modello | teletrasporto in quel punto |
| Doppio clic sinistro su un modello | avvicina la camera al modello |

## Qualità editor e varie
| Tasto | Azione |
|---|---|
| `F1` | 1 stella: nessuna ombra, niente emissive |
| `F2` | 2 stelle: senza ombre del landscape e senza OmniShadow |
| `F3` | 3 stelle: senza ombre del landscape |
| `F4` | 4 stelle: tutto attivo |
| `F6` | anteprima HQ automatica/manuale |
| `F7` | cicla l'**Editor Resolution** (50% Performance, 59% Balanced, 67% Quality, 77% Ultra, 100% Native; upsampling GPU introdotto in Lumion 12) |
| `F8` (tenuto premuto) | mostra le ombre di Spotlight/Omni |
| `F9` | alberi e piante a bassa/alta qualità |
| `F11` | Theater Mode (nasconde l'interfaccia) |
| Doppio clic su uno slider | digitare il valore; `Shift` mentre trascini = regolazione fine |

Le ombre del sole compaiono solo a 2–4 stelle. Le ombre delle luci artificiali non sono visibili in editor (solo selezionandole, max 5 alla volta, o con F8), ma vengono **sempre** calcolate nel render.

## Piazzare, selezionare, trasformare
| Tasto | Azione |
|---|---|
| Clic sinistro (Place) | piazza l'oggetto selezionato in libreria |
| `V` + clic | piazza con scala casuale ±0–50% |
| `Ctrl` + clic (Cluster) | piazza 10 copie in posizioni casuali (`Ctrl+V` + clic: anche con scala casuale) |
| Mass Placement: `Ctrl`+clic / clic destro / `Invio` | aggiungi punto / rimuovi punto / chiudi la linea e ne inizia un'altra |
| `M` | strumento Select (per il Type-In delle coordinate) |
| `Ctrl` + trascina | selezione rettangolare (`Ctrl+Shift`: aggiunge alla selezione) |
| `Ctrl` + clic su un'icona / sul vuoto | aggiungi o togli dalla selezione / deseleziona tutto |
| `Alt` + trascina | duplica (crea istanze) |
| `H` + trascina | sposta in altezza |
| `X` / `Z` + trascina | vincola il movimento all'asse X / Z (vale anche in Move e Advanced Move) |
| `G` + trascina | aggancia solo al terreno Lumion, ignorando gli altri oggetti |
| `F` + trascina | orienta l'oggetto secondo la superficie sottostante |
| `Shift` + trascina | spostamento orizzontale senza snap |
| `R` + trascina | ruota (heading); `Shift` disattiva lo snap a 45° |
| `K` + rotazione | tutti gli oggetti selezionati si girano verso il cursore |
| `L` + trascina | scala |
| Icone sovrapposte: cursore sopra + `W`/`S` | scorre tra gli oggetti allineati |

Photo/Movie: `Ctrl+1…0` salva fino a 10 viste (Photo Set 1), `Shift+1…0` le richiama. Movie: `Spazio` con il cursore sulla timeline = play/stop; `Ctrl` durante il render = mostra gli FPS.

## Layer
- Un progetto nuovo ha 5 layer. In Lumion 12.0 si arriva a 20, **dalla 12.3 a 32**.
- Doppio clic per rinominare. Il layer attivo (bianco) non si può nascondere. La freccia seleziona tutti gli oggetti del layer (deseleziona prima, per non spostare oggetti per errore). Gli oggetti si assegnano dal menu Layer nel pannello opzioni oggetto.
- Dalla 12.0 la barra dei layer è disponibile anche in Move, Advanced Move, Mass Move e Global Illumination.
- Fix 12.5: i layer nascosti restano nascosti alla prima apertura del progetto, e Paint Placement piazza sul layer attivo.
- Schema consigliato: Edificio, Contesto, Vegetazione alta, Vegetazione bassa/erba, Persone, Auto, Luci, Varianti A/B, Cantiere.

## Gruppi, posizionamento, utilità
- **Groups**: categoria propria nella libreria, includono anche oggetti effetto e Character Billboard. Fix 12.5: gli effetti raggruppati mantengono la posizione relativa e *Edit Group* evidenzia il singolo oggetto.
- **Mass Placement**: diretto (si clicca e si disegna il percorso), supporta i gruppi, la direzione ha snap a −180/−90/0/90/180.
- **Space Objects Evenly**: distanza impostabile. **Randomize** posizione e dimensione.
- **Clip Plane**: fino a 3 per progetto, con contorno opzionale sul taglio (sezioni prospettiche).
- **Character Billboard** (Utilities): texture personalizzata sempre rivolta alla camera (persone 2D, sagome).
- **Collections** e **Object Tags** nella libreria: il tag `L12` filtra i contenuti nuovi di Lumion 12.
- Coordinate esatte: *Select* (`M`) → *Type In* → X/Y/Z.

## Landscape e terreno (12.x)
- Terreno Lumion: area ad **alta definizione 2×2 km** (contorno giallo) dentro un'area a bassa definizione di **10×10 km** (contorno rosso), centrate su 0,0,0. L'erba del landscape compare **solo nei 2×2 km**: tieni lì il progetto.
- **Heightmap**: 1024×1024 px (si usano i 1000×1000 centrali), 1 px = 2×2 m, nero = 0 m, bianco = 200 m (0,78125 m per livello di grigio).
- Terreno importato: assegna il materiale **Landscape** per fonderlo col terreno Lumion (stesse texture, anche l'erba). Piscine e interrati: usa il *Landscape Cutter*, oppure modella nel CAD un bordo di terreno attorno, a cui dare il materiale Landscape.
- I modelli vengono mostrati entro **35 km** dalla camera.
- NVIDIA: lascia *Anisotropic Filtering* su *Application Controlled*, altrimenti le texture del terreno peggiorano.

## OpenStreetMap (Pro, beta)
*Landscape › OpenStreetMap › On* → *Pick GPS Coordinate* (anche incollando le coordinate) → OSM Range e Orientation → opzioni *Download Heightmaps*, *Clamp Heightmaps* (punto più basso a 0 m), *Download satellite maps* → *Start Download*. Poi: *Hide Buildings*, preset di stile, filtri (acqua, terreno, edifici, uso del suolo, strade), altezza minima o casuale degli edifici, *Buildings Alpha* (trasparenza).
⚠️ Il modello OSM sta su un layer speciale. Se lo spegni prima di salvare, **non viene salvato nel .LS12**. Per eliminare il rilievo scaricato: *Height › Flatten Landscape map*.
