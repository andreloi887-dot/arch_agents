# Preparazione del modello e import

> Fonte: Lumion Knowledge Base (support.lumion.com), articoli *Model import guidelines*, *Auto-Converted Materials*, *Why are your Lumion materials missing after re-importing*, *LiveSync with existing imported models (≤ 12.5)*, *Reduce the complexity of a model*, release notes 12.0/12.3/12.5. Verificato nov 2026.

## Regole di modellazione (a monte)
- **Origine 0,0,0**: il punto di inserimento in Lumion corrisponde all'origine del CAD (ArchiCAD: *Project Origin*; Rhino: 0,0,0 → se il CPlane è spostato, `_4View` due volte e `Move` all'origine; SketchUp: tasto destro sull'asse blu → *Reset*). Modelli lontani dall'origine = modello "sparito", ombre e superfici che sfarfallano (la GPU ha 8 cifre di precisione posizionale).
- **Unità**: OBJ e 3DS non salvano l'unità → Lumion 12 assume **1 unità = 1 m**.
- **Un materiale sorgente = una superficie in Lumion.** Lumion unisce sempre le superfici con lo stesso materiale CAD: per materiali diversi servono materiali diversi nel CAD *prima* dell'import. In Rhino il materiale può stare sul layer: oggetti/layer con lo stesso nome materiale vengono uniti; senza materiale finiscono in una superficie "catch-all".
- **Nomi materiali stabili**: Lumion riapplica i materiali al re-import tramite il **nome del materiale importato**. Se il nome cambia, i materiali Lumion spariscono. SketchUp: usa sempre `.SKP` (mai alternare SKP/DAE, i nomi non sono compatibili). ArchiCAD: esporta con **"Lumion Collada file (.DAE)"**, non il Collada generico. Revit: stessa versione del plugin su tutti i PC.
- **Facce invertite/invisibili (SketchUp)**: prima dell'export `Ctrl+A` → *Explode* ripetuto finché l'opzione è grigia.
- **Z-fighting**: separa le superfici complanari nel CAD; in Lumion c'è *Flicker Reduction* nel materiale ma va usato al minimo (vedi 03).
- **Alleggerire**: nascondi ciò che non si vede, dividi il modello in più file, LiveSync è più leggero del DAE. Revit: *Surface Smoothing* al minimo accettabile; Rhino: *File › Properties › Mesh › Custom › Density 0.0*; 3ds Max: *ProOptimizer*; SketchUp: Skimp, Material Resizer, CleanUp3.
- **Istanze**: importare 1 albero e piazzarlo 100 volte in Lumion è molto più efficiente che importare un file con 100 alberi (stessi 3D Points, ma meno memoria e più FPS).

## Formati e metodi consigliati (Lumion 12.x)
| Software | Metodo consigliato | Alternativa |
|---|---|---|
| SketchUp | LiveSync oppure `.SKP` diretto | — (DAE da SketchUp sconsigliato) |
| Revit | LiveSync (vista **3D prospettica** attiva) | Export DAE dal plugin (Revit LT: non supportato da LiveSync) |
| ArchiCAD | LiveSync (ArchiCAD 21+) | *Lumion Collada file (.DAE)* dal plugin |
| Rhino 6.10+ | LiveSync | Rhino 5: *Save As › Collada*; Rhino 4: *Save As › SKP* |
| AutoCAD | LiveSync / `.DWG` | DAE |
| FormIt 2022.1+ | LiveSync (novità Lumion 12) | DAE |
| Altri (3ds Max, Blender, C4D…) | FBX / DAE | OBJ, 3DS |

- Lumion 12.0 ha un **nuovo importer** per FBX, DAE, OBJ, 3DS; la 12.3 anche per **SKP e DWG**.
- Dalla 12.3: **drag & drop** di modelli e di file `.LS12` (per caricare o unire) direttamente in Build Mode.
- Nome modello 2–100 caratteri, nome cartella max 32 caratteri.
- **Non** disponibili nella 12.5 (arrivati dopo): import luci dal CAD (2024.3), glTF, sincronizzazione materiali PBR via LiveSync.

## Materiali convertiti automaticamente (fino a Lumion 12)
Solo **vetro e acqua**. Il nome del materiale CAD deve **iniziare** con la parola chiave seguita da spazio, e avere opacità ≤ 99%. In italiano: `Vetro …`, `Acqua …` (anche EN `Glass`/`Water`, DE, FR, ES ecc.). Revit: i tipi *Glazing, SolidGlass, Mirror, PrismTransparent* diventano Glass, *Water* diventa Water. Se il materiale ha una texture, la conversione non avviene. → Convenzione di naming consigliata: `Vetro facciata`, `Acqua piscina`.

## LiveSync (Lumion 12.5 e precedenti)
- Lumion riconosce il modello dal **nome file**. Stesso nome e percorso: basta *Start LiveSync* nel CAD.
- SketchUp/Revit con nome nuovo: se almeno **5 caratteri consecutivi** coincidono (es. `Casa_001` → `Casa_002`), Lumion propone *Re-connect to LiveSync* nel pannello oggetto. Se il nome è del tutto diverso o il percorso è cambiato: SketchUp → *re-import* del nuovo `.SKP`, poi Start LiveSync; Revit → salva il `.RVT`, esporta un DAE LiveSync con lo stesso nome e percorso, re-import in Lumion, poi Start LiveSync.
- La sincronizzazione della camera è opzionale (in 12.5 è stato corretto lo schermo rosso con camera sync Off).
- Revit + *Section Box*: i materiali possono sparire (le superfici tagliate cambiano). Vedi l'articolo KB dedicato.

## Import, aggiornamento, varianti
- *Re-import* aggiorna il modello mantenendo i materiali se i nomi sono invariati. Backup: **Save Material Set** (`.MTT`) prima di re-import importanti.
- **Variations** (Lumion 12): *Add Variation* crea un **duplicato unico** del modello importato (materiali indipendenti). Per sostituirlo con un altro file: `Alt` + *Re-Import* → *Re-import model from new file*. Fix 12.5: le varianti aggiunte in Material Mode non perdono i materiali, e cambiare variante aggiorna le ombre.
- Copia con `Alt`+trascina = **istanza**: stessi materiali dell'originale.
- **Place item on nodes**: importa box-proxy (un oggetto ciascuno, un solo materiale) e sostituiscili con oggetti della libreria (alberi, luci, arredi). Spot e Area Light in Lumion sono ruotate di 90° (puntano in basso): compensa la rotazione dei proxy nel CAD.

## Edificius (ACCA) → Lumion
Nessun LiveSync. Esporta **FBX** (preferibile) o DAE/OBJ, oppure IFC → Revit/ArchiCAD/SketchUp → LiveSync. Prima dell'export: modello vicino all'origine, materiali distinti per tipologia, nomi in italiano con prefisso `Vetro`/`Acqua` dove serve la conversione automatica. Con OBJ verifica la scala (Lumion assume metri).

## Checklist pre-import
- [ ] Modello vicino a 0,0,0, unità in metri
- [ ] Layer o oggetti inutili spenti (2D, quote, arredi non visibili)
- [ ] Un materiale CAD per ogni materiale Lumion desiderato, con nomi stabili e leggibili
- [ ] Vetri e acque con nome che inizia per `Vetro`/`Acqua` e opacità < 100%
- [ ] Facce corrette, nessuna superficie duplicata o complanare
- [ ] Modelli pesanti divisi in più file (edificio, arredi, contesto)
