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

## Regole fisse (dagli errori del 2026-11-16/17: valgono per ogni arredo nuovo)
1. **Guarda l'oggetto vero prima di modellarlo**: oltre al riferimento di Andrea, cerca foto dell'oggetto reale (browser:
   ricerca immagini) e scrivi i 3-4 tratti che lo fanno riconoscere (camicia: spalle piene sulla gruccia, colletto piegato
   con le punte, abbottonatura, maniche in parte dietro il busto). Le camicie fatte a memoria erano "fatte male".
2. **Un tessuto parte vicino alla sua forma finale**: la simulazione rifinisce, non inventa. Il plaid lasciato cadere si
   accartocciava; ora nasce steso sul piumone (`tessili.telo_appoggiato`). Il cuscino nasce a bordo cucito, la camicia a tubo.
   Ciò che il tessuto deve "ricordare" (pieghe, volume) va nella forma di partenza.
3. **Masse realistiche**: in Blender la massa è per vertice. Massa totale = massa × vertici: un cuscino 1-2 kg, un plaid
   1,5-20 kg "simulati", mai centinaia. `tessili` avvisa sopra 25 kg.
4. **Terne destrorse e normali verso fuori** per ogni involucro gonfiato (u × v > 0; t = d × su). `tessili` avvisa se il
   volume è negativo.
5. **Mai nascere dentro un ostacolo** (`_fuori`, ostacoli sottili ingrossati verso il muro). `tessili` conta i vertici dentro.
6. **Ogni regolazione entra nella chiave della cache** (`_chiave`: impostazioni, ostacoli con attrito e spessore, vertici
   fermati, `VERSIONE`). Se cambi il modo di simulare, alza `tessili.VERSIONE`.
7. **Prova in scena, nell'inquadratura del confronto** (`banco_scena.py`), con i materiali veri; poi Unreal giorno e sera.
8. **Leggi i controlli nel log** (`arredi_interni.log`: righe "AVVISO tessili" e "grinze"): un plaid disteso sta sotto 8-10°
   di grinze medie, uno accartocciato sopra 20°.
9. **Ricette condivise**: un valore buono trovato sul banco diventa il predefinito in `ricette_arredo.py`, mai un ritocco a
   mano nella scena.

## Metodo, per ogni pezzo
1. **Leggi il riferimento** e scrivi in poche righe forma, proporzioni, materiali, dettagli (es. sedia: guscio unico a ferro
   di cavallo alto 0,80 dietro e basso sui fianchi, seduta a cuscino, gambe rastremate).
2. **Scegli la tecnica giusta**:
   | Cosa | Tecnica | Dove |
   |---|---|---|
   | mobili rigidi (armadi, cucine, tavoli, testate) | `Pezzo.scat` (scatole con smusso 4 mm) | `arredi_interni.py` |
   | imbottiti rigidi, gusci, forme organiche (sedie, lampade a ciottolo) | gabbia + suddivisione: `Pezzo.grezzo(..., "liscio")`, `scatola_liscia` con anelli di sostegno | `arredi_interni.py` |
   | piumoni | `tessili.trapunta`: involucro chiuso gonfiato con la pressione che cade con la gravità (spessore 6 cm, pressione 1,5, grinze 2 mm: dal 2026-11-17, prima 2,5 e 7 mm facevano bozze) | `tessili.py`, `ricette_arredo.letto` |
   | plaid (dal 2026-11-17, secondo giro) | `tessili.telo_appoggiato`: nasce steso sul piumone simulato, i lembi pendono lungo i fianchi, la simulazione lo assesta (peso 0,006 per vertice, piega 1,0, attrito 4) | `tessili.py`, `ricette_arredo.letto` |
| lenzuola, plaid (vecchio) | `tessili.telo`: telo che cade; il plaid cade sul piumone stesso (`tessili.collisore`) da vicino (0,64 m sul pavimento), attrito 4, piega 1,0, 160 fotogrammi, spessore 1,5 cm (prima: da 0,80, attrito 12, piega 0,3 = lastra accartocciata) | `tessili.py`, `ricette_arredo.letto` |
   | guanciali, cuscini decorativi | `tessili.cuscino(..., coltello=True, maglia=0.02, pressione=1.1-1.3, morbido=2, seme, varia=1, assesta=40, ostacoli, via, massa_assesta=0.006)`: federa a bordo cucito gonfiata, ognuno diverso, poi lasciato cadere sugli appoggi veri | `tessili.py`, ricetta in `ricette_arredo.py` |
| camicie appese | `tessili.camicia`: busto e maniche come involucri chiusi, pieghe nella forma di riposo, fermati solo al centro della gruccia | `tessili.py`, `ricette_arredo.armadio` |
   | cuscini di divano | `tessili.cuscino(..., scatolato=True, morbido=1.6)` sedute (pressione 0,35); schienali non a scatola, pressione 4, `morbido=6` | `tessili.py` |
   | cuscini in piedi (schienali, decorativi) | `tessili.cuscino(..., in_piedi=α)` con l'asse girato perché +perp(u) guardi lo schienale | `tessili.py` |
   | gambe inclinate, aste | `Pezzo.asta` (cilindro rastremato tra due punti) | `arredi_interni.py` |
| paralumi, globi, catini, piedi torniti | `Pezzo.tornio(a, b, sezione chiusa [(r, z)], materiali per lato)`: solido di rotazione, parte "tondo" (liscia, senza smusso, spigoli vivi oltre 35°) | `arredi_interni.py` |
| mobili curvi (cassettiera del mobile TV) | `_contorno_tondo` + `_prismi`: contorno con l'angolo arrotondato, tagliato a file e colonne con fughe di 4 mm su un'anima scura | `arredi_interni.py` |
| asciugamani appesi | `tessili.asciugamano`: telo avvolto sulla barra già nella forma finale, fermo in cima, onde verticali di partenza | `tessili.py` |
| accessori del bagno | `accessori_wc`, `rubinetto_bidet` in `arredi_interni.py`: posizione dal lato del sanitario contro il muro (`_retro`), mai dentro doccia o accanto al bidet | `arredi_interni.py` |
| rivestimenti a parete (bagni) | lastre vere con fughe, fino a quota, più alte nella doccia, tagliate su porte e finestre e sotto il soffitto | `finiture_interni.py` (sezione rivestimento) |
3. **Materiali veri**: texture CC0 (Poly Haven, ambientCG) in `TEX` di `arredi_interni.py` (id, lato reale in m, contrasto,
   venatura). Il colore della foto si ritinge con la tinta del progetto (`ritinta`: luminanza × tinta, in lineare) in un file
   nuovo, così Blender, USD e Unreal vedono la stessa immagine. UV in metri / lato (in `Pezzo.fine`): legno con la fibra
   verticale sulle facce verticali e lungo il pezzo su quelle orizzontali. Scelte del 2026-11-16: rovere
   `oak_veneer_03` (dal 2026-11-17: contrasto 1,8 e ruvidità ritarata 0,70, vedi le lezioni), bouclé `curly_teddy_natural`, biancheria e sedie `terlenka`, cuscini `rough_linen`, plaid
   `knitted_fleece`, gesso `white_stucco`, paraschizzi `Marble018`, piano `Marble025`. Si scelgono **guardando il mosaico
   delle anteprime**, mai dal nome (`wool_boucle` è uno scozzese, `marble_01` sono piastrelle).
4. **Banco di prova in scena** (dal 2026-11-17, il preferito): `scripts/banco_scena.py` apre `contesto_progetto.blend`, rifà
   solo i tessili di un pezzo con **le stesse ricette della filiera** (`blender/ricette_arredo.py`: `letto`, `divano`, `armadio`)
   e i materiali veri (`blender/materiali_arredo.py`), e rende le viste di `viste_controllo.txt` o scritte per intero:
   `blender -b <...>/contesto_progetto.blend -P banco_scena.py -- pezzo=letto viste=letto_matrimoniale g_pr=1.1 g_ma=0.006`
   (8 s a vista, 20-30 s di simulazione). Quando una prova piace, il valore diventa il predefinito nella ricetta. La geometria
   del pezzo è nella proprietà `ricetta` dell'oggetto, scritta da `arredi_interni.py`.
   **Banco di prova da studio** (il vecchio metodo, per forme nuove): uno script che costruisce in una scena vuota solo il pezzo
   (letto, divano) con le stesse funzioni di `tessili.py` e lo rende in 1-2 minuti; si cambiano i parametri da riga di comando
   (`-- sp=0.06 pr=2.5 ...`) finché somiglia al riferimento, poi si portano i valori in `arredi_interni.py`. Andrea
   (2026-11-17): niente render inutili, solo quelli che servono al confronto.
5. **Viste di controllo**: una vista ravvicinata per pezzo in `viste_controllo.txt` (`sedia`, `divano`, `letto_matrimoniale`,
   ...), resa con `filiera.py ... --da arredi --fino viste --viste <solo quelle> --scala 100 --campioni 64` (Full HD).
6. **Confronta col riferimento affiancato**: `python skills/arredo-da-riferimento/scripts/affianca.py <rif> <render> -o x.jpg`
   e guardalo. Elenca le differenze (forma, proporzioni, materiale, luce) e correggi. Si chiude solo quando a vista torna.
7. **Unreal**: poi la catena `--da unreal --fino render --taratura` e lo stesso confronto sui render di Unreal.

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
- **Plaid staccato dal letto** (Andrea, 2026-11-17): cadeva su una scatola più alta del piumone. Ora cade sul piumone
  simulato (unico collisore vicino, più il pavimento): appoggia senza vuoti.
- **Tessuti duri** (Andrea, 2026-11-17): un telo con spessore resta una lastra; il piumone vero è un involucro gonfiato
  (`trapunta`), con una piccola irregolarità iniziale perché cadendo non resti piatto.
- **Mai rigenerare l'USD mentre Unreal importa o confronta**: il confronto con `riferimento.json` risulterebbe falsato.
- **Rovere**: `oak_veneer_03` (fibra dritta, fiamme leggere), contrasto 1,3; `washed_grey_oak_veneer` aveva la fibra ondulata.
- **Simulazioni non ripetibili** (2026-11-17): piumone e plaid uscivano un po' diversi a ogni giro e l'impronta della geometria
  cambiava sempre. Ora `tessili.py` salva ogni risultato in `uscita_blender/cache_tessili/` con una chiave (forma di partenza,
  parametri, ostacoli): a parità di ingressi si riusa (e `arredi` passa da 4 minuti a 11 secondi). In più la firma di ogni mesh
  in `esporta_usd.py` è robusta (ingombro, baricentro, scarto medio): un rumore di 1e-6 nella suddivisione non la cambia più.
  Per rifare una simulazione da capo basta cancellare la cartella della cache.
- **Ville ferme**: ogni stile nuovo vale solo per le ville arredate (`VILLE_ARREDATE`); B, C, D restano com'erano.
- **Cosa non è stato fatto**: generazione 3D da immagine (TRELLIS, licenza MIT): su questo PC servono il toolkit CUDA e la
  compilazione di nvdiffrast/spconv; rimandata. Hunyuan3D è escluso: licenza non valida nell'Unione Europea.

- **Cuscini rigidi e tutti uguali** (Andrea, 2026-11-17): erano palloncini senza gravità né appoggi, e a parità di misure
  nascevano dalla stessa forma, quindi la cache li rendeva identici. Ora: federa a bordo cucito (`coltello=True`), maglia di
  2 cm, `seme`/`varia` (misure ±4 %, pressione ±15 %, rotazione ±5°, un'ammaccatura), poi `assesta`: gravità e appoggi veri.
- **La massa del tessuto è per vertice**: con 0,35 kg un guanciale di 1700 vertici pesava 600 kg e crollava. Per l'assestamento
  0,006 kg.
- **Un tessuto non deve nascere dentro un ostacolo**: esplode o lo attraversa (guanciali dentro la testata). `_fuori` lo sposta
  fuori prima di simulare; gli ostacoli sottili (testata da 5 cm) vanno ingrossati verso il muro.
- **Pressione, non volume obiettivo**: con `use_pressure_volume` il cuscino raggiunge il volume ma si stringe in pianta (sacco
  alto e stretto). La pressione ha una soglia netta: 1,0 piatto (7 cm), 1,1 guanciale vero (20 cm), 2 pallone. Le rughe non si
  fanno indebolendo la compressione (il tessuto si accorcia invece di piegarsi).
- **Il tessuto ricorda la forma da cui parte**: una camicia che parte piatta e verticale, fermata sulle spalle, resta un pannello.
  Le pieghe vanno messe nella forma di riposo (onde di 10-18 cm più ampie verso l'orlo), e si ferma solo il centro della gruccia.
- **Camicie accartocciate nell'armadio**: la terna (d, su, perp(d)) era sinistrorsa, le facce rovesciate e la pressione le
  schiacciava (ora t = d × su e normali ricalcolate). Viste di taglio le pieghe sembrano carta: grucce girate tutte di ~16°.
  Niente vetro e schiena come ostacoli se le camicie ci stanno: le maniche ci strisciavano e si stropicciavano.
- **Il banco cancellava il materasso**: la parte morbida di un mobile si chiama anch'essa "<pezzo> (tessili)"; il banco toglie
  solo i tessili delle ricette.
- **Ogni regolazione nuova del tessuto entra nella chiave della cache** (`_chiave`), altrimenti si rilegge un risultato vecchio.
- **Legno "di plastica"** (Andrea, 2026-11-17): la ruvidità della foto del rovere aveva media 0,48 (laminato lucido). Ora
  `RUV_TEX` la ritara a 0,70 nel file (così anche USD e Unreal), contrasto 1,8 e normali piene (la mappa è debolissima). La
  fibra va lungo il lato lungo della faccia: verticale sulle ante, orizzontale su fascia del letto, testata e cassetti.

- **Plaid prefigurato che esplodeva** (2026-11-17, secondo giro): appoggiato sulla superficie lisciata del piumone ma con la
  gabbia (più sporgente) come ostacolo nasceva dentro; e il piumone simulato ha strati che si incrociano, quindi nessun "fuori"
  pulito. Regola: un telo prefigurato urta **la superficie su cui è stato appoggiato** (copia abbassata lungo le normali), non
  l'oggetto sotto. Risultato: grinze da 30° a 13°.
- **Involucri gonfiati: il peso fa da contrappeso alla pressione** (piumone leggero = pallone). Il controllo della massa vale
  solo per i teli; nel controllo "dentro un ostacolo" le normali si riorientano solo per le forme chiuse.
- **I controlli hanno trovato difetti vecchi**: i cuscini decorativi del divano nascevano fino a 254 vertici dentro gli
  schienali (`_fuori` guardava solo le scatole). Ora esce anche dagli oggetti con la collisione: lungo `via`, o in su se sta
  sotto una seduta.
- **Sostituzioni di testo nel codice**: un rimpiazzo uguale in due funzioni ha cambiato anche `_guanciale` (NameError a metà
  filiera). Prima di sostituire, contare le occorrenze (`assert s.count(a) == 1`).

- **Pezzi che sostituiscono blocchi IFC** (lavabo dei bagni, 2026-11-17): si dichiarano in `arredi.json` (`tipo`, `anello`,
  `sostituisce`); il blocco IFC resta nel file nascosto (`sostituita`, come le porte), così la filiera si può rilanciare.
- **Nomi dei materiali e Unreal**: `prepara_render.py` cambia i materiali per prefisso (legno, rovere, marmo, led, lampadina,
  vetro_fume, lume_dentro, paralume) e trasforma in vetro chiaro ogni `MI_` con opacità tra 0 e 1. Un materiale nuovo non deve
  cominciare con quei nomi se non vuole quel trattamento; il tipo "lampada" viene scambiato con la plafoniera di libreria.

- **Rifinire un blocco IFC senza rifarlo** (doccia, 2026-11-17): dividere la mesh in parti connesse e riconoscerle dalla forma
  (lastra = scatola di 12-13 facce, sottile e alta; telaio = sottile ma con più facce; piatto = basso e largo). Con la sola
  soglia di spessore il telaio diventava vetro e una lastra stretta acciaio a specchio.
- **Viste di controllo**: le camere si mettono verificando il punto dentro il poligono del vano (le prime erano nei muri).

- **Texture che non somiglia** (rivestimento dei bagni, 2026-11-17): `beige_wall_002` era un intonaco a onde, non la pietra
  liscia della foto. Si confronta la texture ritinta **accanto al ritaglio della foto** alla stessa scala prima di usarla; se
  nessuna CC0 somiglia, **si ricava dalla foto**: `strumenti/materiali/pietra_sabbia.py` toglie il gradiente della luce e
  ricuce una lastra ripetibile con pezzetti della foto stessa (quilting: pezzi da 96 px, scelti a caso tra i migliori, ruotati e
  ribaltati, istogramma della foto). Rumori e spettri "statistici" non ci arrivavano (Andrea: "non è nemmeno vicino"). La zona
  sorgente non deve contenere fughe, ombre d'angolo o oggetti (la fuga veniva copiata come un segno). Dopo aver rigenerato una
  texture si svuota la sua cartella `tinte/` (cache delle versioni ritinte), altrimenti si usa quella vecchia.
- **Rivestimento che mancava su un muro**: il taglio delle aperture prendeva anche porte vicine e muri perpendicolari. Un'apertura
  taglia solo il muro a cui è parallela e che attraversa (almeno 10 cm); le porte rifatte si tagliano sul filo del coprifilo.

## Ancora aperto
- **Grucce girate** (`tessili.camicia(ruota=…)`): per un errore di modifica la rotazione non è mai stata applicata; le camicie
  verificate sono perpendicolari all'asta e il predefinito è 0. Da provare con `banco_scena.py pezzo=armadio ruota=16`.
- **Render finali di stasera interrotti** (Andrea ha spento il PC): gli ultimi ritocchi dei bagni (leva del bidet davanti,
  rotolo vero, maniglie in un pezzo, pietra più leggera) sono verificati solo in Blender; manca il giro Unreal giorno e sera.
- Le maniche delle camicie sono ancora un po' piatte in cima, e c'è il decoro da fare (piante, quadri, tende). Nota: con il
  plaid leggero (peso 0,05 per vertice) si accartocciava di più.
Prima del 2026-11-17:
Grana fine dei tessuti a distanza (terlenka quasi invisibile), plaid ancora rigido, interni dell'armadio fumé, frange del plaid,
bordi cuciti dei cuscini, lampadario a ciottolo senza la texture irregolare del gesso in rilievo.
