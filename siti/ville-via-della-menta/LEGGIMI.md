# Sito delle Ville di Via della Menta

Sito statico di presentazione e vendita: una pagina, nessun server, nessuna dipendenza esterna.
Si pubblica copiando la cartella su qualunque hosting (GitHub Pages, Netlify, spazio web con dominio).

| File | Cosa contiene |
|---|---|
| `dati.js` | **Tutti i contenuti che cambiano**: dati delle ville, stato, immagini, capitolato, contatti |
| `index.html` | Struttura e testi di presentazione |
| `stile.css` | Grafica |
| `script.js` | Costruisce schede, modulo e menu a partire da `dati.js` |
| `percorso.js` | Il percorso guidato dallo scorrimento in apertura |
| `prepara_percorso.sh` | Estrae dal video i fotogrammi del percorso (serve FFmpeg) |
| `immagini/`, `documenti/` | Render, planimetrie e PDF (da creare quando ci sono i file) |

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

## Il percorso dentro la casa
In apertura la scena resta ferma a tutto schermo e lo scorrimento fa avanzare la camera, con le didascalie
degli ambienti che compaiono lungo il cammino. Finché mancano i fotogrammi c'è un segnaposto animato.

**Cosa serve dalla filiera (Blender o Unreal):** un solo video continuo, senza tagli.
- Percorso: dalla strada al cancello, ingresso, zona giorno, cucina, zona notte, uscita in giardino.
- Durata 30–45 s, velocità costante, niente accelerazioni: la velocità la decide chi scorre.
- 1920 × 1080 a 30 fps. Soggetto al centro del quadro, perché sul telefono si vede solo la fascia
  centrale; meglio ancora un secondo video in verticale (1080 × 1920) sullo stesso percorso.
- Il primo fotogramma è la copertina del sito: deve essere l'immagine più forte.

**Preparazione:**
```
./prepara_percorso.sh percorso.mp4 180 [percorso_verticale.mp4]
```
Scrive i fotogrammi in `immagini/percorso/` e stampa i tre valori da copiare in `dati.js → percorso`.
Con 180 fotogrammi il peso atteso è di 10–20 MB per desktop e circa la metà per telefono; il sito carica
prima un fotogramma ogni 16 e poi infittisce, quindi il percorso è scorribile quasi subito.

**Didascalie:** in `dati.js → percorso.tappe`, ognuna con l'intervallo `da`–`a` (tra 0 e 1) in cui è
visibile. Vanno riposizionate guardando il video vero. `schermate` regola la lunghezza: più alto, più lento.

Chi ha impostato "riduci movimento" sul dispositivo vede una copertina ferma.

## Gallerie di render e interni
Ogni villa ha in `dati.js` una `galleria`: esterni e viste interne con didascalia, sfogliabili nella scheda.

## Prima di pubblicare
- [ ] Percorso di camera reso e preparato; didascalie riposizionate sul video.
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
