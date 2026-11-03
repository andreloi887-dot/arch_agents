# Organizzazione: gruppi, componenti, tag, scene, stili, sezioni

## Gruppi vs componenti
| | Gruppo | Componente |
|---|---|---|
| Istanze collegate | No (copie indipendenti) | Sì: modifichi una, cambiano tutte |
| Peso file | Ogni copia pesa | Definizione unica, istanze leggere |
| Uso tipico | Elementi unici (muro di un livello, solaio) | Ripetuti (finestre, pilastri, arredi, alberi) |
| Comportamento | — | *Glue to* / *Cut opening* / *Always face camera* |
- *Make Unique* per staccare un'istanza. *Reload* per aggiornare da un file `.skp` esterno; è un
  modo per lavorare in team su parti del progetto.
- I **Dynamic Components** (Pro: Component Attributes) servono per parametrici semplici
  (porte/finestre con larghezza variabile, scale). Meglio valutarli solo se riusati spesso, perché
  costano tempo di setup.
- **Live Components** (2021+, via Trimble Connect/3D Warehouse): parametrici configurabili.
  Utilità variabile, verificare la disponibilità.

## Tag (ex Layers)
- **Regola d'oro**: la geometria grezza (spigoli e facce) resta sempre su *Untagged*; i tag si
  assegnano al contenitore (gruppo/componente). Altrimenti spegnendo un tag restano "facce
  fantasma" o spigoli orfani.
- Cartelle di tag per macro-categorie; colori dei tag (*Color by tag*) per controllare a colpo
  d'occhio cosa è taggato male.
- Tratteggi dei tag (dashes, 2020+) per demolizioni, proiezioni e linee nascoste in pianta.
- I tag servono per la visibilità, non per l'organizzazione gerarchica: per quella c'è l'Outliner.

## Outliner
- Nominare gruppi e istanze. L'Outliner mostra la gerarchia ed è la mappa del modello.
- Struttura consigliata: `Edificio` › `Livello 0`, `Livello 1`… › elementi; `Contesto`, `Terreno`,
  `Entourage` separati al livello radice.
- Ricerca/filtro dell'Outliner per trovare istanze e nascondere/mostrare in modo rapido.

## Scene
- Ogni scena salva: camera, tag visibili, stile, sezioni attive, oggetti nascosti, ombre/nebbia,
  assi. Con *Update Scene* si sceglie esattamente cosa aggiornare (spuntare solo le proprietà
  volute).
- Scene "tecniche" per LayOut: pianta = camera Top + Parallel Projection + sezione orizzontale
  attiva + stile tecnico; prospetti = Parallel Projection + vista standard.
- Disattivare *Include in animation* per le scene tecniche se si esporta un video.
- Il **filtro scene** della 2022 aiuta quando le scene sono molte.

## Stili (*Window › Styles*)
- Almeno 3 stili di studio: **Tecnico** (spigoli neri, nessun profilo o profilo sottile, sfondo
  bianco, facce bianche/monocrome), **Presentazione** (texture, profili 2, ombre), **Sezione**
  (Section Fill nero o grigio, linee di sezione spesse).
- *Edit › Edge Settings*: profili, estensioni, jitter e linee schizzate per i concept.
- *Watermark* per carta, logo e sfondo grafico.
- Un warning sugli stili si risolve con *Update Style with changes*: se lo stile della scena è
  modificato e non salvato, LayOut e le scene si comportano in modo inaspettato.

## Sezioni
- Una sezione per ogni contesto; nominare i piani (nome e simbolo in *Entity Info*).
- *Section Fill* (Styles › Modeling) richiede **solidi chiusi**: se il riempimento non appare o
  "sbava", il gruppo non è un solido.
- Per piante in LayOut: sezione a 1,20–1,50 m dal piano finito, scena dedicata e stile Sezione.
