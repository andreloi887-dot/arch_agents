# Consegna a sketchup-expert – zona Via della Menta / Via Tamburino Sardo (rev. 2)

**Pacchetto:** `scheda.json` (fonte di verità), `scheda.md`, `palette.png`,
`_rif_google/manifest_riprese.json` (19 riprese per le scene di verifica). Le foto in `_rif_google/`
sono solo riferimento locale: non importarle in SketchUp.
Il contratto (nomi, tag, materiali) è in `skills/rilievo-urbano/references/06-consegna-sketchup.md`.

**Prima di modellare (bloccante):**
1. *Add Location* centrato su 39.25240 N, 9.11527 E, con terreno; origine sull'incrocio.
2. `RilievoUrbano::Catasto.importa` (`skills/rilievo-urbano/scripts/sketchup/importa_catasto.rb`) con
   `geometria/catasto_fabbricati.geojson` e `geometria/catasto_strade_particelle.geojson`.
3. **Allineare il gruppo CATASTO intero** con Move/Rotate sugli spigoli di E06, E02, E10 ed E01, che hanno
   la forma coerente. Lo sfasamento atteso è 0–5 m, non uniforme. Non deformare le singole sagome.
4. `RilievoUrbano::Catasto.report` e trascrivere dx, dy e rotazione in `note_modellazione.md`.
5. E03, E08 ed E09: la sagoma catastale è incompleta. Integrare i corpi mancanti leggendoli
   sull'imagery di *Add Location* e sulle riprese della scheda, e segnalarli come ipotesi.

**Priorità (dalle viste dell'incrocio):**
1. **Muri e recinzioni R01 e R02, in LOD3.** Il fronte stradale è fatto di muri. R01 è a gradoni, va
   seguito sul terreno e ha la copertina in cotto C02.
2. E09 (LOD3), poi E06 (LOD3).
3. Marciapiedi P02 (marmette 400×400 a scacchiera C17/C18, cordolo h 15 cm) e carreggiate P01.
4. Gli altri edifici in LOD2, E04 ed E07 in LOD1, poi arredo e verde.

**Attenzione:**
- Tutte le altezze sono stime. Le quote nella scheda per E08 ed E09 sono misurate **dal marciapiede**:
  il terreno interno ai lotti è rialzato di 1,0 m (E09) e 2,5 m (E08).
- Non scurire i materiali per imitare l'ombra: gli hex sono valori in luce.

**Da restituire per la verifica:** `inventario.json`, `export_verifica/SV-xx.png` (generati da
`scene_da_manifest.rb`), `note_modellazione.md`.
