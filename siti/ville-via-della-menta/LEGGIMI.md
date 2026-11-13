# Sito delle Ville di Via della Menta

Sito statico di presentazione e vendita: una pagina, nessun server, nessuna dipendenza esterna.
Si pubblica copiando la cartella su qualunque hosting (GitHub Pages, Netlify, spazio web con dominio).

## Architettura
| Pagina | Indirizzo | Cosa mostra |
|---|---|---|
| Principale | `index.html` | Percorso d'insieme in apertura, progetto, elenco delle ville con stato, luogo, capitolato, contatti |
| Villa | `villa.html?id=villa-1` … `villa-4` | Percorso dentro la villa in apertura, dati, render e interni, planimetrie, richiesta di informazioni |

La pagina della villa è una sola e si riempie da `dati.js` in base all'`id`: aggiungere o togliere una villa
significa aggiungere o togliere una voce in `dati.js`, senza toccare altro. "Chiedi informazioni" riporta al
modulo della pagina principale con la villa già selezionata.

| File | Cosa contiene |
|---|---|
| `dati.js` | **Tutti i contenuti che cambiano**: dati delle ville, stato, immagini, percorsi, capitolato, contatti |
| `index.html`, `script.js` | Pagina principale |
| `villa.html`, `villa.js` | Pagina della villa |
| `comune.js` | Funzioni condivise dalle due pagine |
| `percorso.js` | Il percorso guidato dallo scorrimento, uguale per tutte le pagine |
| `stile.css` | Grafica |
| `prepara_percorso.sh` | Prepara i fotogrammi di un percorso (serve FFmpeg) |
| `immagini/`, `documenti/` | Render, planimetrie, fotogrammi e PDF (da creare quando ci sono i file) |

## Vederlo in locale
Si apre `index.html` con un doppio clic, oppure dalla cartella:
```
python -m http.server 8000
```
e poi `http://localhost:8000`.

## Aggiornare i contenuti
Si modifica solo `dati.js`. Un valore lasciato a `null` compare come "da definire".
- **Stato di una villa**: `"disponibile"`, `"trattativa"` o `"venduta"`. Una villa venduta resta visibile ma
  esce dall'elenco del modulo.
- **Immagini**: render in JPG a 2400 px di larghezza per la copertina e 1600 px per le ville, planimetrie in
  PNG o SVG. Si copiano in `immagini/` e si scrive il percorso in `dati.js`.
- **Capitolato**: la sezione compare da sola quando la lista ha almeno una voce.

## I percorsi guidati dallo scorrimento
In apertura di ogni pagina la scena resta ferma a tutto schermo e lo scorrimento fa avanzare la camera, con
le didascalie che compaiono lungo il cammino. I percorsi sono cinque: uno d'insieme sulla pagina principale
e uno dentro ogni villa. Ogni pagina carica solo il proprio.

Finché mancano i fotogrammi, in bozza c'è un segnaposto animato; fuori bozza resta una copertina ferma
(l'`immagine` della villa o `immagine_copertina`). Il percorso d'insieme è quindi facoltativo.

**Cosa serve dal programma di render**, per ogni percorso:
- Un movimento di camera continuo, senza tagli, a velocità costante: la velocità la decide chi scorre.
  - Insieme: avvicinamento da Via della Menta, i quattro ingressi, i giardini.
  - Villa: cancello, ingresso, zona giorno, cucina, zona notte, uscita in giardino.
- **Bastano 180–240 fotogrammi in tutto**, non un video a 30 fps: il sito ne mostra uno per volta. Conviene
  rendere direttamente la sequenza di immagini (PNG o JPG numerati), con molto meno tempo di calcolo.
- 1920 × 1080. Soggetto al centro del quadro, perché sul telefono si vede solo la fascia centrale; meglio
  ancora una seconda sequenza in verticale (1080 × 1920) sullo stesso percorso.
- Il primo fotogramma è la copertina della pagina: deve essere l'immagine più forte.

**Preparazione**, da un video oppure da una sequenza di immagini numerate:
```
./prepara_percorso.sh insieme percorso.mp4
./prepara_percorso.sh villa-1 "render/villa1_%04d.png" 180 "render/villa1_verticale_%04d.png"
```
Scrive i fotogrammi in `immagini/percorso/<nome>/` e stampa i tre valori da copiare in `dati.js`.
Con 180 fotogrammi il peso atteso è di 10–20 MB per desktop e circa la metà per telefono, per ogni percorso;
il sito carica prima un fotogramma ogni 16 e poi infittisce, quindi il percorso è scorribile quasi subito.

**Didascalie:** `tappe` in `dati.js`, ognuna con l'intervallo `da`–`a` (tra 0 e 1) in cui è visibile. Le ville
con `tappe: null` usano quelle d'esempio (`tappe_interni`). Vanno riposizionate guardando il percorso vero.
`percorso.schermate` regola la lunghezza: più alto, più lento.

Una tappa con `tipo: "cartello"` è un pannello a tutto schermo che sale e copre la scena, con numeri e titolo
("Saliamo al piano superiore"). Serve dove la camera non ha un passaggio continuo, come tra un piano e
l'altro: il percorso si può rendere in due tratti e unire le sequenze, con il cartello sopra il punto di giunzione.

Chi ha impostato "riduci movimento" sul dispositivo vede una copertina ferma.

## Render e interni
Ogni villa ha in `dati.js` una `galleria`: esterni e viste interne con didascalia, mostrati nella sua pagina.
La prima immagine e poi una ogni tre sono a tutta larghezza: conviene metterci le viste più ampie.

## Prima di pubblicare
- [ ] Percorsi di camera resi e preparati; didascalie riposizionate.
- [ ] Dati delle quattro ville compilati (superfici, locali, classe energetica di progetto).
- [ ] Render di copertina e delle ville, planimetrie.
- [ ] Contatti: venditore, telefono, email o indirizzo del servizio per il modulo.
- [ ] Informativa privacy collegata in `contatti.informativa_privacy`: il modulo raccoglie dati personali.
- [ ] Testi di `index.html` riletti: le frasi sulla zona e sui collegamenti vanno confermate.
- [ ] `bozza: false` in `dati.js`: toglie la fascia in alto e il blocco ai motori di ricerca.

## Il modulo di contatto
Un sito statico non può spedire email da solo. Due strade, entrambe in `dati.js → contatti`:
- `email`: il modulo apre il programma di posta del visitatore con il messaggio già scritto. Funziona
  subito, ma una parte dei visitatori non ha la posta configurata e la richiesta si perde.
- `indirizzo_modulo`: indirizzo di un servizio che riceve il modulo e lo inoltra (Formspree, Web3Forms,
  Netlify Forms). È la strada consigliata per la pubblicazione.

## La planimetria del lotto
Il contorno nella sezione "Il luogo" viene dal progetto
(`rilievi/zona-cagliari-menta-tamburino/modello/perimetro_progetto.json`), gli assi stradali dal DBGT.
Le sagome delle ville non ci sono: vanno aggiunte dalla planimetria generale di Edificius.
