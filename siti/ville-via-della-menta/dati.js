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
   * Percorsi guidati dallo scorrimento: la pagina resta ferma e lo scroll fa
   * avanzare la camera. Ce n'è uno d'insieme in apertura del sito (qui sotto)
   * e uno dentro ogni villa, nella sua pagina (ville[].percorso).
   * I fotogrammi si preparano dal video con prepara_percorso.sh (vedi LEGGIMI.md).
   * Finché fotogrammi è 0 e bozza è true compare un segnaposto animato;
   * fuori bozza, senza fotogrammi, resta una copertina ferma.
   *
   * Didascalie (tappe): da/a sono punti del percorso tra 0 e 1 in cui la
   * didascalia è visibile; lato: "sinistra" | "destra". Vanno riposizionate
   * guardando il video vero.
   */
  percorso: {
    cartella: null, // es. "immagini/percorso/insieme/desktop"
    cartella_telefono: null, // es. "immagini/percorso/insieme/telefono" (facoltativa)
    fotogrammi: 0, // numero di file: 0001.webp … NNNN.webp
    estensione: "webp",
    schermate: 7, // lunghezza in altezze di schermo: più alto = più lento (vale anche per le ville)
    fine_titolo: 0.1, // punto del percorso in cui il titolo iniziale è sparito
    tappe: [
      { da: 0.2, a: 0.42, titolo: "L'arrivo da Via della Menta", testo: null, lato: "sinistra" },
      { da: 0.5, a: 0.72, titolo: "Quattro ingressi indipendenti", testo: null, lato: "destra" },
      { da: 0.8, a: 0.98, titolo: "I giardini", testo: null, lato: "sinistra" },
    ],
  },

  // Didascalie d'esempio per i percorsi delle ville che non hanno ancora le proprie.
  // tipo: "cartello" è un pannello a tutto schermo che copre la scena: serve nei
  // cambi di piano o di ambiente, dove la camera non ha un passaggio continuo.
  // Con numeri: "villa" mostra camere, bagni, piani e posti auto della villa;
  // in alternativa numeri: [{ valore: "3", etichetta: "camere" }, …].
  tappe_interni: [
    { da: 0.12, a: 0.22, titolo: "L'ingresso", testo: null, lato: "sinistra" },
    { da: 0.25, a: 0.36, titolo: "La zona giorno", testo: null, lato: "destra" },
    { da: 0.39, a: 0.5, titolo: "La cucina", testo: null, lato: "sinistra" },
    { da: 0.53, a: 0.67, tipo: "cartello", titolo: "Saliamo al piano superiore", testo: null, numeri: "villa" },
    { da: 0.7, a: 0.82, titolo: "La zona notte", testo: null, lato: "destra" },
    { da: 0.86, a: 0.98, titolo: "Il giardino", testo: null, lato: "sinistra" },
  ],

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
      immagine: null, // render della villa: scheda nell'elenco e copertina ferma della sua pagina
      // Galleria nella pagina della villa: esterni e viste interne, nell'ordine in cui compaiono.
      // Esempio: { src: "immagini/villa-1-soggiorno.jpg", didascalia: "Soggiorno" }
      galleria: [],
      // Percorso dentro la villa. tappe: null usa le didascalie d'esempio (tappe_interni).
      percorso: { cartella: null, cartella_telefono: null, fotogrammi: 0, estensione: "webp", tappe: null },
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
      percorso: { cartella: null, cartella_telefono: null, fotogrammi: 0, estensione: "webp", tappe: null },
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
      percorso: { cartella: null, cartella_telefono: null, fotogrammi: 0, estensione: "webp", tappe: null },
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
      percorso: { cartella: null, cartella_telefono: null, fotogrammi: 0, estensione: "webp", tappe: null },
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
