# Prestazioni e troubleshooting

## Modello lento
1. *Model Info › Statistics*: conteggio di facce, spigoli e componenti; poi **Purge Unused**.
2. Cause tipiche: componenti 3D Warehouse ipermodellati (auto, alberi, arredi da 50k+ facce),
   texture enormi (>4K), gruppi copiati invece di componenti, DWG importati esplosi, terreno troppo
   denso.
3. Fix: sostituire con componenti low-poly o proxy (alberi 2D *Always face camera*), ridurre
   le texture (2K), Skimp per decimare, tenere entourage e contesto su tag spenti durante la
   modellazione.
4. Visualizzazione: profili OFF, ombre OFF, nebbia OFF, stile semplice durante il lavoro; scene di
   lavoro con tag pesanti nascosti.
5. *Preferences › Graphics*: driver della GPU aggiornati; su laptop forzare la GPU dedicata per
   `SketchUp.exe`.

## Crash e instabilità
- Prima causa: **estensioni**. Test: disattivarle tutte in *Extension Manager*, riavviare e
  riattivarle a blocchi.
- Recupero: file `.skb` (backup) o file di auto-save (Windows:
  `%LocalAppData%\Temp\SketchUp` o percorso in *Preferences › Files*). Rinominare `.skb` → `.skp`.
- File corrotto: *Window › Model Info › Statistics › Fix Problems*; altrimenti copiare la
  geometria in un file nuovo (Ctrl+C/Edit › *Paste in Place*).

## Facce che non si chiudono / buchi
- Gli spigoli non sono complanari: verificare con *Orbit* e X-ray. Ridisegnare uno spigolo per
  forzare la faccia oppure usare *Make Faces*.
- Dettagli < 1 mm: **trucco della scala** (gruppo → Scale x100 → modellare → Scale /100).
- Curve importate con troppi micro-segmenti: semplificare in CAD o con estensioni.

## Z-fighting (facce che "sfarfallano")
- Facce sovrapposte complanari: eliminare i duplicati (CleanUp³) o spostarle di 1–2 mm.
- Spesso deriva da gruppi copiati due volte nello stesso punto: controllare l'Outliner.

## Clipping della camera (la vista "taglia" il modello)
- Geometria lontanissima dall'origine (DWG georeferenziato) o modello enorme insieme a un
  dettaglio minuscolo. Fix: spostare vicino all'origine, rimuovere gli oggetti persi lontani
  (*Zoom Extents* rivela i punti lontani), con prospettiva FOV moderato.
- In una scena interna: *Camera › Field of View* oppure nascondere il contesto esterno.

## Section Fill o Solid Tools che non funzionano
- Il gruppo non è un solido: Solid Inspector² mostra spigoli liberi, facce interne e buchi.
- Gruppi annidati: Solid Tools vuole un solo livello di geometria per solido.

## Texture distorte o storte
- Tasto destro sulla faccia › *Texture › Position* (pin di spostamento/scala/rotazione);
  *Projected* per superfici curve (campionare con Alt+Paint Bucket su una faccia piana proiettata).
- Per i render: tile reale corretto in *Materials › Edit* (es. 600 × 600 mm per piastrelle).

## Altro
- Tag che "non spegne": geometria grezza taggata o contenitore su un altro tag. Usare *Color by
  tag* e lo script "Untagged" in `06-estensioni-ruby.md`.
- Modifiche che si propagano "da sole": sono istanze dello stesso componente → *Make Unique*.
- Oggetti che si incollano: geometria grezza a contatto con altra geometria grezza → raggruppare
  sempre.
