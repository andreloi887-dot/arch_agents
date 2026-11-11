# Sito delle Ville di Via della Menta

Sito statico di presentazione e vendita: una pagina, nessun server, nessuna dipendenza esterna.
Si pubblica copiando la cartella su qualunque hosting (GitHub Pages, Netlify, spazio web con dominio).

| File | Cosa contiene |
|---|---|
| `dati.js` | **Tutti i contenuti che cambiano**: dati delle ville, stato, immagini, capitolato, contatti |
| `index.html` | Struttura e testi di presentazione |
| `stile.css` | Grafica |
| `script.js` | Costruisce schede, modulo e menu a partire da `dati.js` |
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

## Prima di pubblicare
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
