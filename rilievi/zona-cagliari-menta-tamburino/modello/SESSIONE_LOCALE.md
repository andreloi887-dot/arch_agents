# Lanciare il modello in SketchUp da una sessione Claude sul tuo PC

## Preparazione (una volta sola, circa 10 minuti)
1. **Claude sul PC.** Installa l'app Claude Desktop (claude.ai/download) e accedi con lo stesso
   account. In alternativa: Claude Code da terminale.
2. **Repository sul PC.** Da un terminale (con Git installato):
   ```
   git clone https://github.com/andreloi887-dot/arch_agents.git
   cd arch_agents
   git checkout claude/determined-carson-ka9dsw
   ```
3. **Modello base georeferenziato.** È l'unico passo manuale: Add Location richiede l'interfaccia e
   l'accesso Trimble.
   - Apri SketchUp 2022 e crea un modello nuovo con il modello di base in **metri**.
   - *File › Geo-location › Add Location*, cerca `39.25240, 9.11527`, seleziona un riquadro di circa
     250 × 250 m centrato sull'incrocio e importa (terreno incluso).
   - *File › Save As* → `arch_agents\rilievi\zona-cagliari-menta-tamburino\modello\base_georef.skp`.
   - Chiudi SketchUp.
   **Con SketchUp 2025** (provato il 2026-11-04, build 25.0.575): dopo la ricerca delle coordinate la
   posizione è già impostata. *Add Context* apre la scelta del contesto: per importare la mappa serve un
   abbonamento, ma **non è necessario**. Basta annullare e salvare, perché gli script usano solo la
   georeferenziazione e il terreno lo costruiscono dal DTM LiDAR. L'eseguibile è
   `C:\Program Files\SketchUp\SketchUp 2025\SketchUp\SketchUp.exe`. Conviene passare anche il modello
   base come ultimo argomento della riga di comando, così si apre direttamente.
4. **Facoltativo, per il confronto con le foto:** imposta la variabile d'ambiente utente
   `GOOGLE_MAPS_API_KEY` sul PC (la stessa chiave della sessione cloud).

## Avvio
Apri una sessione di Claude Code nella cartella `arch_agents` (app Desktop › Code › apri la cartella,
oppure `claude` dal terminale nella cartella) e incolla il prompt qui sotto. Approva i comandi che
chiede di eseguire.

```
Siamo nel repository arch_agents, branch claude/determined-carson-ka9dsw. Leggi
rilievi/zona-cagliari-menta-tamburino/modello/README.md e questo file (SESSIONE_LOCALE.md).
Obiettivo: costruire in SketchUp Pro 2022 il modello del lotto all'angolo Via Tamburino Sardo / Via
della Menta (Cagliari) e verificarlo.

1. Controlla che esistano SketchUp 2022 (di solito C:\Program Files\SketchUp\SketchUp 2022\SketchUp.exe)
   e il modello base rilievi\zona-cagliari-menta-tamburino\modello\base_georef.skp. Se manca, fermati e
   dimmelo.
2. Lancia la pipeline senza dialoghi: imposta la variabile RILIEVO_CONFIG al percorso assoluto di
   rilievi\zona-cagliari-menta-tamburino\modello\pipeline.json e avvia
   "SketchUp.exe" -RubyStartup "<repo>\skills\rilievo-urbano\scripts\sketchup\pipeline_contesto.rb".
   Attendi la comparsa di modello\uscita_sketchup\esito_pipeline.json (al massimo 10 minuti) e leggi
   esito_pipeline.json e pipeline.log.
3. Se ci sono errori: analizzali, correggi gli script (costruisci_contesto.rb, pipeline_contesto.rb) o i
   dati (lotto.json, poi `python skills/rilievo-urbano/scripts/contesto/contesto.py <cartella modello>` → contesto.json), chiudi SketchUp e rilancia. Al massimo 3 tentativi.
4. Guarda le viste esportate (uscita_sketchup\vista_*.png ed export_verifica\SV-*.png) e descrivi cosa
   vedi: facce rovesciate, buchi, muri, terreno del lotto, posizione di lampione, palma e rete.
5. Verifica: se GOOGLE_MAPS_API_KEY è impostata, scarica le riprese con
   python skills\rilievo-urbano\scripts\gmaps.py sv-shots --piano rilievi\zona-cagliari-menta-tamburino\piano_riprese.json --out rilievi\zona-cagliari-menta-tamburino\_rif_google
   poi lancia confronta.py (scheda.json, uscita_sketchup\inventario.json, _rif_google,
   uscita_sketchup\export_verifica) e confronta le viste SV-08, SV-12, SV-16, SV-18 con le foto.
   I criteri sono in skills\rilievo-urbano\references\05-verifica.md; i ❌ attesi sul contorno sono
   elencati nel README del modello.
6. Fai commit e push delle sole correzioni agli script e ai dati, non di uscita_sketchup né di
   _rif_google. Poi scrivimi un riepilogo: esito, tempi, problemi trovati e correzioni fatte.
```

## Cosa produce
`modello\uscita_sketchup\`:
- `contesto_generato.skp`
- `pipeline.log` ed `esito_pipeline.json`
- `inventario.json`
- `export_verifica\SV-01…19.png` (stesse camere di Street View)
- `vista_aerea_SO.png`, `vista_aerea_NE.png`, `vista_angolo.png`
