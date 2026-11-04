# Prestazioni e troubleshooting (2025)

## Motore grafico
- **Photoreal Materials, Environments o AO disattivati/grigi** → quasi sempre è attivo il
  **motore classico** (scelto a mano o per fallback automatico su hardware non supportato).
  *Preferences › Graphics*: attivare il nuovo motore e riavviare. Se torna al classico:
  aggiornare i driver GPU e, su un laptop, forzare la GPU dedicata per SketchUp.
- La grafica integrata Intel datata è la causa tipica dei problemi del nuovo motore (soprattutto su
  Mac Intel).
- Artefatti o crash grafici dopo un aggiornamento dei driver → provare il motore classico solo per
  diagnosi, poi tornare al nuovo.

## Modello lento
1. *Model Info › Statistics* e **Purge Unused**.
2. **Draft Mode** (*Preferences › Performance*) per navigare i modelli pesanti.
3. Stile di lavoro leggero: niente Photoreal, AO, ombre, profili né nebbia durante la modellazione;
   attivarli solo nelle scene di presentazione.
4. Cause tipiche: componenti 3D Warehouse ipermodellati, texture enormi (i materiali PBR hanno più
   mappe per materiale, quindi controllare il peso), gruppi copiati invece di componenti, DWG
   esplosi, terreni densi, environment HDRI a 8K.
5. Fix: componenti low-poly o proxy, texture a 2K, Skimp, entourage e contesto su tag spenti.

## Crash e instabilità
- Prima causa: **estensioni** (soprattutto quelle non aggiornate per Ruby 3.2). Usare la finestra
  di errore delle estensioni (2024+) oppure disattivarle tutte e riattivarle a blocchi.
- Recupero: `.skb`/auto-save (percorso in *Preferences › Files*); rinominare `.skb` → `.skp`.
- File corrotto: *Model Info › Statistics › Fix Problems*; altrimenti copiare la geometria in un file
  nuovo con *Paste in Place*.

## Materiali che cambiano aspetto dopo la migrazione
- Texture e colori diversi rispetto alla 2022/2024: il nuovo shading e la conversione automatica in
  PBR cambiano la resa. Controllare l'opzione di conversione automatica in *Preferences › Graphics*
  e lo stile di faccia (Photoreal o classico).
- Libreria materiali "nuova" e mancano i vecchi materiali: la libreria di default ora è PBR. I
  vecchi materiali si possono reimportare come collezione `.skm` dalla 2022 (cartella Materials
  della vecchia installazione).

## Facce che non si chiudono / buchi
- Spigoli non complanari: verificare con Orbit e X-ray, ridisegnare uno spigolo o usare *Make Faces*.
- Dettagli < 1 mm: **trucco della scala**.

## Z-fighting
- Facce sovrapposte complanari: eliminare i duplicati (CleanUp³) o separarle di 1–2 mm. Con AO e
  Photoreal lo sfarfallio si nota di più.

## Clipping della camera
- Geometria lontana dall'origine o oggetti persi: *Zoom Extents* per trovarli, spostare vicino
  all'origine, FOV moderato.

## Section Fill o Solid Tools che non funzionano
- Il gruppo non è un solido: Solid Inspector² per trovare spigoli liberi, facce interne e buchi.

## Texture distorte
- Tasto destro › *Texture › Position*; *Projected* per le superfici curve. Per i PBR verificare
  anche le dimensioni reali del materiale nell'editor (es. 600 × 600 mm per le piastrelle).

## Altro
- Tag che "non spegne": geometria grezza taggata → *Color by tag* + script "Untagged".
- Modifiche che si propagano: istanze dello stesso componente → *Make Unique*.
- Comando "sparito" dopo la migrazione (es. *Flip Along*): cercarlo con **Search** (Shift+S).
