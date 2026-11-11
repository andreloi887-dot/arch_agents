/*
 * DATI DEL SITO – l'unico file da modificare per aggiornare i contenuti.
 *
 * Regole:
 * - un valore lasciato a null compare sul sito come "da definire";
 * - finché bozza è true, in alto compare la fascia "Bozza" e il sito chiede
 *   ai motori di ricerca di non indicizzarlo;
 * - stato di una villa: "disponibile" | "trattativa" | "venduta";
 * - le immagini vanno in immagini/ e qui si scrive il percorso
 *   (es. "immagini/villa-1.jpg"); con null resta il segnaposto.
 */
window.SITO = {
  bozza: true,

  progetto: {
    nome: "Ville di Via della Menta",
    luogo: "Pirri · Cagliari",
    motto: "Quattro ville indipendenti, ognuna con il proprio ingresso e il proprio giardino.",
    immagine_copertina: null, // render principale, formato orizzontale, almeno 2400 px di larghezza
    consegna: null, // es. "primavera 2028"
    // Numeri in evidenza sotto la presentazione. Valore null = "da definire".
    numeri: [
      { valore: "4", etichetta: "ville indipendenti" },
      { valore: null, etichetta: "m² di superficie, da–a" },
      { valore: null, etichetta: "classe energetica di progetto" },
      { valore: null, etichetta: "consegna prevista" },
    ],
  },

  /*
   * Percorso guidato dallo scorrimento: la pagina resta ferma e lo scroll fa
   * avanzare la camera dentro la casa. I fotogrammi si preparano dal video
   * con prepara_percorso.sh (vedi LEGGIMI.md). Finché fotogrammi è 0 e bozza
   * è true compare un segnaposto animato.
   */
  percorso: {
    cartella: null, // es. "immagini/percorso/desktop"
    cartella_telefono: null, // es. "immagini/percorso/telefono" (facoltativa)
    fotogrammi: 0, // numero di file: 0001.webp … NNNN.webp
    estensione: "webp",
    schermate: 7, // lunghezza del percorso in altezze di schermo: più alto = più lento
    fine_titolo: 0.1, // punto del percorso (0–1) in cui il titolo iniziale è sparito
    // Didascalie lungo il cammino: da/a sono punti del percorso tra 0 e 1.
    // Vanno riscritte sul percorso di camera vero. lato: "sinistra" | "destra".
    tappe: [
      { da: 0.14, a: 0.28, titolo: "L'ingresso", testo: null, lato: "sinistra" },
      { da: 0.32, a: 0.46, titolo: "La zona giorno", testo: null, lato: "destra" },
      { da: 0.5, a: 0.64, titolo: "La cucina", testo: null, lato: "sinistra" },
      { da: 0.68, a: 0.82, titolo: "La zona notte", testo: null, lato: "destra" },
      { da: 0.86, a: 0.98, titolo: "Il giardino", testo: null, lato: "sinistra" },
    ],
  },

  ville: [
    {
      id: "villa-1",
      nome: "Villa 1",
      stato: "disponibile",
      descrizione: null, // 2–3 righe: cosa la distingue (esposizione, giardino, affaccio)
      superficie_m2: null, // superficie commerciale
      giardino_m2: null,
      piani: null,
      camere: null,
      bagni: null,
      posti_auto: null,
      classe_energetica: null, // es. "A4"
      immagine: null, // render della villa (immagine della scheda nell'elenco)
      // Galleria della scheda: esterni e viste interne, nell'ordine in cui si sfogliano.
      // Esempio: { src: "immagini/villa-1-soggiorno.jpg", didascalia: "Soggiorno" }
      galleria: [],
      planimetrie: [], // es. ["immagini/villa-1-piano-terra.png", "immagini/villa-1-piano-primo.png"]
      scheda_pdf: null, // es. "documenti/villa-1.pdf"
    },
    {
      id: "villa-2",
      nome: "Villa 2",
      stato: "disponibile",
      descrizione: null,
      superficie_m2: null,
      giardino_m2: null,
      piani: null,
      camere: null,
      bagni: null,
      posti_auto: null,
      classe_energetica: null,
      immagine: null,
      galleria: [],
      planimetrie: [],
      scheda_pdf: null,
    },
    {
      id: "villa-3",
      nome: "Villa 3",
      stato: "disponibile",
      descrizione: null,
      superficie_m2: null,
      giardino_m2: null,
      piani: null,
      camere: null,
      bagni: null,
      posti_auto: null,
      classe_energetica: null,
      immagine: null,
      galleria: [],
      planimetrie: [],
      scheda_pdf: null,
    },
    {
      id: "villa-4",
      nome: "Villa 4",
      stato: "disponibile",
      descrizione: null,
      superficie_m2: null,
      giardino_m2: null,
      piani: null,
      camere: null,
      bagni: null,
      posti_auto: null,
      classe_energetica: null,
      immagine: null,
      galleria: [],
      planimetrie: [],
      scheda_pdf: null,
    },
  ],

  // Capitolato: voci brevi e verificabili. Lista vuota = sezione nascosta.
  // Esempio di voce: { titolo: "Involucro", testo: "…" }
  capitolato: [],

  contatti: {
    venditore: null, // ragione sociale o nome di chi vende
    telefono: null,
    email: null, // se compilata, il modulo apre la posta dell'utente con il messaggio già scritto
    // In alternativa all'email: indirizzo di un servizio che riceve i moduli
    // (Formspree, Netlify Forms, Web3Forms…). Se compilato ha la precedenza.
    indirizzo_modulo: null,
    informativa_privacy: null, // percorso o indirizzo dell'informativa, obbligatoria prima di pubblicare
    partita_iva: null,
  },
};
