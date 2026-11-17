---
name: arredo-da-riferimento
description: Modellare in Blender (e portare in Unreal) arredi interni identici alle immagini di riferimento di Andrea - forme, tessuti morbidi, materiali e consistenze. Usala quando Andrea manda foto di cucine, letti, armadi, divani, sedie, lampade da riprodurre, o quando un arredo della filiera sembra squadrato, finto o diverso dal riferimento.
---

# Arredo da riferimento

Rispondi in italiano. Codice: `skills/rilievo-urbano/scripts/blender/arredi_interni.py` (mobili), `tessili.py` (tessuti
simulati), texture CC0 in `libreria_materiali/` (fuori da git, si riscaricano con `strumenti/materiali/scarica_*.py`).
Riferimenti di Andrea: `rilievi/<zona>/modello/riferimenti_arredo/` (solo locali, fuori da git).

## Il giudizio di partenza (Andrea, 2026-11-16)
"L'arredo è totalmente lontano dalle immagini: i letti non hanno tessuti morbidi, è tutta roba squadrata". Tre cause:
1. **Forme**: parallelepipedi e smussi vanno bene per armadi, cucine, tavoli; mai per imbottiti e tessuti.
2. **Materiali**: tinte unite o formule procedurali non sembrano rovere, bouclé, lino, marmo.
3. **Controllo**: anteprime piccole (960 px, 32 campioni) che nascondono gli scalini; nessun confronto affiancato.

## Metodo, per ogni pezzo
1. **Leggi il riferimento** e scrivi in poche righe forma, proporzioni, materiali, dettagli (es. sedia: guscio unico a ferro
   di cavallo alto 0,80 dietro e basso sui fianchi, seduta a cuscino, gambe rastremate).
2. **Scegli la tecnica giusta**:
   | Cosa | Tecnica | Dove |
   |---|---|---|
   | mobili rigidi (armadi, cucine, tavoli, testate) | `Pezzo.scat` (scatole con smusso 4 mm) | `arredi_interni.py` |
   | imbottiti rigidi, gusci, forme organiche (sedie, lampade a ciottolo) | gabbia + suddivisione: `Pezzo.grezzo(..., "liscio")`, `scatola_liscia` con anelli di sostegno | `arredi_interni.py` |
   | piumoni, lenzuola, plaid | `tessili.telo`: telo che cade sugli ostacoli (simulazione dei tessuti) | `tessili.py` |
   | guanciali, cuscini decorativi | `tessili.cuscino` gonfiato con la pressione | `tessili.py` |
   | cuscini di divano | `tessili.cuscino(..., scatolato=True)`: parte alto, poca pressione, tessuto rigido | `tessili.py` |
   | cuscini in piedi (schienali, decorativi) | `tessili.cuscino(..., in_piedi=α)` con l'asse girato perché +perp(u) guardi lo schienale | `tessili.py` |
   | gambe inclinate, aste | `Pezzo.asta` (cilindro rastremato tra due punti) | `arredi_interni.py` |
3. **Materiali veri**: texture CC0 (Poly Haven, ambientCG) in `TEX` di `arredi_interni.py` (id, lato reale in m, contrasto,
   venatura). Il colore della foto si ritinge con la tinta del progetto (`ritinta`: luminanza × tinta, in lineare) in un file
   nuovo, così Blender, USD e Unreal vedono la stessa immagine. UV in metri / lato (in `Pezzo.fine`): legno con la fibra
   verticale sulle facce verticali e lungo il pezzo su quelle orizzontali. Scelte del 2026-11-16: rovere
   `washed_grey_oak_veneer`, bouclé `curly_teddy_natural`, biancheria e sedie `terlenka`, cuscini `rough_linen`, plaid
   `knitted_fleece`, gesso `white_stucco`, paraschizzi `Marble018`, piano `Marble025`. Si scelgono **guardando il mosaico
   delle anteprime**, mai dal nome (`wool_boucle` è uno scozzese, `marble_01` sono piastrelle).
4. **Banco di prova**: una vista ravvicinata per pezzo in `viste_controllo.txt` (`sedia`, `divano`, `letto_matrimoniale`,
   ...), resa con `filiera.py ... --da arredi --fino viste --viste <solo quelle> --scala 100 --campioni 64` (Full HD).
5. **Confronta col riferimento affiancato**: `python skills/arredo-da-riferimento/scripts/affianca.py <rif> <render> -o x.jpg`
   e guardalo. Elenca le differenze (forma, proporzioni, materiale, luce) e correggi. Si chiude solo quando a vista torna.
6. **Unreal**: poi la catena `--da unreal --fino render --taratura` e lo stesso confronto sui render di Unreal.

## Lezioni (errori fatti, da non ripetere)
- **Terna sinistrorsa** (2026-11-17): le scatole di collisione e i teli costruiti con assi (u, v) con u × v < 0 hanno le facce
  rovesciate: il materasso "attirava" il piumone, che si accartocciava, e lo spessore sul tessuto accartocciato faceva punte
  di metri. `tessili.py` ora rimette sempre v perché u × v > 0. `use_even_offset` dello spessore spento (punte sulle facce
  strette).
- **Due collisioni a pochi cm** (plaid sopra la copia del piumone, 4 cm sopra la scatola del materasso): il telo resta stretto
  tra le due e le attraversa. Meglio una scatola che le inviluppi; più il pavimento, per ciò che ricade.
- **Cuscini in piedi**: ruotarli attorno al centro li fa affondare per metà nella seduta; si alzano sul bordo (`in_piedi`).
- **Materiali e slot**: una parte con slot inutili veniva legata dall'export USD al primo slot (sedie e plaid in rovere in
  Unreal). `Pezzo.fine` assegna a ogni parte solo i materiali che usa.
- **Superfici lisce in USD**: `esporta_usd.py` usa `export_subdivision="TESSELLATE"`: Unreal riceve la forma già suddivisa.
- **Pezzi in due oggetti** (tavolo + sedie lisce): tutto ciò che cerca gli oggetti per tipo deve escludere `(liscio)` e
  `(tessili)` (era nato un lampadario in più).
- **Ville ferme**: ogni stile nuovo vale solo per le ville arredate (`VILLE_ARREDATE`); B, C, D restano com'erano.
- **Cosa non è stato fatto**: generazione 3D da immagine (TRELLIS, licenza MIT): su questo PC servono il toolkit CUDA e la
  compilazione di nvdiffrast/spconv; rimandata. Hunyuan3D è escluso: licenza non valida nell'Unione Europea.

## Ancora aperto
Grana fine dei tessuti a distanza (terlenka quasi invisibile), plaid ancora rigido, interni dell'armadio fumé, frange del plaid,
bordi cuciti dei cuscini, lampadario a ciottolo senza la texture irregolare del gesso in rilievo.
