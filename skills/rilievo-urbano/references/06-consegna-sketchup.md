# Contratto di consegna con l'agente SketchUp

Questo file è letto da **entrambi** gli agenti. Le convenzioni servono a rendere la verifica
automatica: un nome sbagliato = un elemento "mancante" in VERIFICA.

## 1. Pacchetto consegnato dal rilievo
```
zona-<nome>/
  scheda.json              fonte di verità
  scheda.md                lettura umana, con immagini
  mappa_annotata.png       ID su base satellitare (solo riferimento di lavoro)
  palette.png              tavola dei C##
  manifest_riprese.json    riprese con pano, posizione, heading, pitch, fov, data
  geometria/               impronte e quote da fonti aperte (GeoJSON OSM, estratti DBT/catasto)
  _rif_google/             foto Street View (originali + annotate). Locale, fuori da git,
                           MAI importate in SketchUp né usate nelle tavole
```
Nel messaggio di consegna: zona, LOD, origine, elenco lacune, priorità (fronti delle viste di
progetto prima di tutto).

## 2. Cosa deve fare SketchUp (SketchUp Pro 2022)

### Georeferenziazione e origine
1. *File › Geo-location › Add Location* sulla zona; importare imagery e terreno.
2. Portare l'origine degli assi su `zona.origine` (lat/lng della scheda) e lasciare il Nord di
   *Add Location* (Solar North invariato). Senza questo passo le scene camera-matched non tornano.

### Struttura e nomi
- Un **gruppo o componente per ID**, nominato `ID – descrizione` (es. `E02 – Via Garibaldi 12`,
  `R01 – recinzione Via Verdi`). Per le serie (A##, V##): componente unico, istanze nominate `A01`.
- Nidificazione libera (es. `E02` › `Basamento`, `Piani`, `Copertura`), ma il contenitore con l'ID
  deve contenere tutto l'elemento.
- Tag sui contenitori (regola d'oro: geometria grezza su *Untagged*):
  `00_Riferimenti`, `10_Edifici`, `20_Recinzioni`, `30_Arredo`, `40_Pavimentazioni`,
  `50_Vegetazione`, `60_Terreno`.
- **Materiali nominati `C##_descrizione`** (es. `C01_intonaco_ocra`), colore = `hex` della palette,
  texture alla dimensione `modulo_mm`. Nessun materiale senza prefisso sulle superfici visibili.

### Livello di dettaglio
Rispettare il `lod` di ogni elemento: non aggiungere dettaglio non richiesto (peso del file, Lumion)
e non semplificare sotto il LOD. Dove la scheda dà confidenza bassa, modellare l'ipotesi indicata e
segnalarla nel messaggio di ritorno.

### Script da eseguire (in *Window › Ruby Console*, su una copia del file)
1. `scripts/sketchup/scene_da_manifest.rb` – chiede `manifest_riprese.json`, crea una scena
   `SV-xx` per ogni ripresa con la stessa camera di Street View (posizione del pano, quota occhio
   ≈ 2,5 m sul terreno, heading, pitch, fov, formato quadrato) ed esporta i PNG 1280×1280 in
   `export_verifica/`. Stile consigliato: texture e colori, spigoli sottili, ombre accese.
2. `scripts/sketchup/inventario_modello.rb` – esporta `inventario.json` accanto al `.skp`.

## 3. Pacchetto restituito per la VERIFICA
```
inventario.json
export_verifica/SV-01.png …
note_modellazione.md      ipotesi fatte, elementi non modellati e perché, dubbi sulla scheda
```

## 4. Orchestrazione
In Claude Code i subagent non si chiamano tra loro: coordina la sessione principale.
1. `rilievo-urbano` (DESCRIVI) → pacchetto in `zona-<nome>/`.
2. `sketchup-expert` → istruzioni passo-passo, script e verifiche per l'utente (o esecuzione via
   computer-use se disponibile) → pacchetto di ritorno.
3. `rilievo-urbano` (VERIFICA) → verbale; le correzioni tornano a `sketchup-expert`. Max 3 cicli.
