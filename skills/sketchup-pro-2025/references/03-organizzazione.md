# Organizzazione: gruppi, componenti, tag, scene, stili, sezioni

## Gruppi vs componenti
| | Gruppo | Componente |
|---|---|---|
| Istanze collegate | No | Sì: modifichi una, cambiano tutte |
| Peso file | Ogni copia pesa | Definizione unica, istanze leggere |
| Uso tipico | Elementi unici (muro di un livello, solaio) | Ripetuti (finestre, pilastri, arredi, alberi) |
| Comportamento | — | *Glue to* / *Cut opening* / *Always face camera* |
- *Make Unique* per staccare un'istanza; *Reload* per aggiornare da un `.skp` esterno (lavoro in
  team).
- **Dynamic Components** per parametrici semplici; i **configurabili** di 3D Warehouse (asset
  configurabili nella content library) sono un'alternativa pronta: verificare la qualità della
  geometria.

## Tag
- **Regola d'oro**: geometria grezza su *Untagged*, tag solo sui contenitori.
- Cartelle di tag; *Color by tag* per controllare a colpo d'occhio; tratteggi per demolizioni e
  proiezioni.
- **Import IFC 2025**: crea tag per classe IFC in automatico. Utile per spegnere categorie, ma va
  riorganizzato (cartella dedicata) se il modello diventa la base di lavoro.

## Outliner
- Nominare gruppi e istanze. Struttura consigliata: `Edificio` › `Livello 0`, `Livello 1`… ›
  elementi; `Contesto`, `Terreno`, `Entourage` al livello radice.

## Scene
- Ogni scena salva camera, tag visibili, stile, sezioni attive, oggetti nascosti, ombre/nebbia,
  assi. Con *Update Scene* scegliere solo le proprietà volute.
- **Environment per scena** *(da verificare)*: controllare se l'environment attivo viene salvato
  con la scena o resta globale prima di affidarcisi per viste diverse (giorno/sera).
- Scene tecniche per LayOut: Parallel Projection + sezione attiva + stile tecnico (senza AO né
  Photoreal, così il Vector in LayOut resta pulito).
- Filtro di ricerca accanto alle tab delle scene.

## Stili (*Window › Styles*)
- Almeno 4 stili di studio:
  - **Tecnico**: spigoli neri, facce bianche, nessun AO, sfondo bianco;
  - **Presentazione**: texture, profili, ombre, **AO** leggero;
  - **Photoreal**: stile di faccia Photoreal Materials, environment attivo, spigoli spenti o molto
    leggeri, AO;
  - **Sezione**: Section Fill nero o grigio, linee di sezione spesse.
- **Ambient Occlusion** (dalla 2024): impostazione dello stile, con intensità e distanza
  regolabili. Ridurre la distanza nei modelli piccoli e aumentarla negli edifici *(nomi esatti dei
  parametri da verificare)*.
- *Edge Settings*: profili, estensioni, jitter. **Style Builder non esiste più nella 2025**: gli
  stili schizzati esistenti restano utilizzabili ma non se ne creano di nuovi.
- *Watermark* per carta, logo e sfondo.
- Lo stile modificato e non salvato va aggiornato (*Update Style with changes*), altrimenti scene e
  LayOut si comportano in modo inaspettato.

## Sezioni
- Una sezione per ogni contesto; nominare i piani (nome e simbolo in *Entity Info*).
- *Section Fill* richiede **solidi chiusi**.
- Piante in LayOut: sezione a 1,20–1,50 m dal piano finito, scena dedicata e stile Sezione.
