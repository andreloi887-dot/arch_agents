# Modellare il contesto da una scheda di rilievo urbano

Usare quando arriva un pacchetto dell'agente `rilievo-urbano` (`scheda.json`, `scheda.md`,
`manifest_riprese.json`, palette). Il contratto completo (nomi, tag, materiali, cosa restituire) è
in `skills/rilievo-urbano/references/06-consegna-sketchup.md`: va rispettato alla lettera, perché la
verifica è automatica.

## Procedura
1. **Leggi prima lacune, LOD e confidenze.** Le ipotesi a confidenza bassa si modellano come
   indicato e si elencano in `note_modellazione.md`.
2. **Georeferenzia**: *File › Geo-location › Add Location* sulla zona, poi origine degli assi su
   `zona.origine`. Il terreno di Add Location va su tag `60_Terreno`.
3. **Impronte dalle fonti aperte** della cartella `geometria/` su `00_Riferimenti`. Per i GeoJSON
   catastali: `RilievoUrbano::Catasto.importa` (`skills/rilievo-urbano/scripts/sketchup/importa_catasto.rb`),
   poi **allineare il gruppo intero** (Move + Rotate, mai deformare) su ≥ 3 spigoli riconoscibili
   nell'imagery di Add Location: il catasto è spesso sfasato di metri. `.report` dà dx/dy/rotazione da
   annotare. Bloccare il gruppo dopo l'allineamento. Mai ricalcare immagini Google.
4. **Palette prima della geometria**: crea un materiale per ogni C## chiamato `C##_descrizione`,
   colore = `hex`, texture con dimensione = `modulo_mm` (*Materials › Edit › Texture size*).
5. **Volumi** (LOD1): Push/Pull dell'impronta a quota gronda; un gruppo per ID `E## – indirizzo`
   su `10_Edifici`; base appoggiata al terreno (quota `piano_terra`).
6. **Coperture e fasce** (LOD2): falde con la pendenza della scheda (Protractor/VCB, es. 33% →
   arctan 0,33 ≈ 18,3°), sporti, basamento e marcapiani come Push/Pull di 4–6 cm o gruppi separati.
7. **Facciate** (LOD3): una finestra tipo per `codice` come componente *Cut opening* con
   mazzetta, cornice, serramento e oscurante con i rispettivi C##; Move/Copy con passo e numero di
   assi dalla VCB (es. `3,35` poi `*5`). Balconi e ringhiere come componenti.
8. **Recinzioni, arredo, vegetazione**: un componente per tipologia; istanze nominate con l'ID
   (`A01`), in numero pari a `n`; su `20_Recinzioni`, `30_Arredo`, `50_Vegetazione`.
9. **Pavimentazioni**: superfici sul terreno (Sandbox *Drape* o facce sollevate di 1–2 cm) con il
   C## e il modulo corretti; cordoli h 15 cm; tag `40_Pavimentazioni`.
10. **Controllo prima della consegna**: CleanUp³/Purge, nessun materiale senza prefisso C## sulle
    superfici visibili (`inventario.json › materiali_senza_prefisso` deve contenere solo materiali
    di servizio), geometria grezza su Untagged.

## Restituzione per la verifica
Eseguire su una copia del file, da *Window › Ruby Console*:
1. `load '…/skills/rilievo-urbano/scripts/sketchup/scene_da_manifest.rb'` → scene `SV-xx` e PNG in
   `export_verifica/`. Controllare la prima vista: se l'orizzonte non coincide con la foto il
   problema è di camera (origine, Nord, quota occhio), non di modello.
2. `load '…/skills/rilievo-urbano/scripts/sketchup/inventario_modello.rb'` → `inventario.json`.
3. Scrivere `note_modellazione.md` (ipotesi, elementi non modellati, dubbi sulla scheda).
