# Ricette (punti di partenza da regolare a vista)

Valori d'esperienza, non ufficiali. **Seed fisso** durante il tuning; cambia un parametro alla volta.
Per steps e CFG di ogni modello vedi `02-modelli-e-licenze.md`.

## 1. Schizzo a mano → render di concept
- Input: schizzo scansionato e pulito (vedi `03`). Preprocessore Lineart o Softedge.
- Modello: Z-Image Turbo + Fun Union (veloce) oppure SDXL + ControlNet lineart (8 GB).
- Controllo softedge 0.55–0.65, end 0.6. Lasciare libertà è il punto: lo schizzo non definisce i materiali.
- Prompt: tipo edilizio, materiali principali, ora e clima, obiettivo e focale ("architectural photography,
  35mm, overcast soft light"). Genera 8–16 varianti e scegli.

## 2. Massing grigio → render fotorealistico
- Input: depth dal 3D + MLSD o linee dalla stessa camera.
- Modello: Qwen-Image + DiffSynth depth (qualità) oppure Z-Image Turbo + Union (iterazione).
- Depth 0.8 (end 0.75) + MLSD 0.5 (end 0.6). Prompt molto descrittivo sui materiali per zona.
- Rifinitura: percorso C (Qwen-Image-Edit) per correggere materiali e dettagli, poi upscaling.

## 3. Render Lumion → fotorealismo spinto (il caso più frequente)
- **Opzione A (consigliata):** Qwen-Image-Edit-2511, istruzione *"make it photorealistic architectural
  photography, keep geometry, camera and materials unchanged, add realistic imperfections, natural vegetation"*.
  8 step con Lightning per le prove, poi 20–40 step senza Lightning per la finale.
- **Opzione B:** img2img a denoise 0.30–0.40 + depth pass Lumion a 0.6–0.7.
- Proteggi con maschere ciò che deve restare identico (loghi, insegne, elementi di progetto specifici).

## 4. Varianti di materiale per il cliente
- Base: render approvato. Qwen-Image-Edit, una variante per prompt ("replace the cladding with …").
- Multi-reference con la foto del campione reale del fornitore: risultati molto più credibili del solo testo.
- Impagina le varianti con lo stesso seed e la stessa camera: il confronto è leggibile solo se cambia
  solo il materiale.

## 5. Interno diurno
- Depth + Normal (interni con superfici inclinate) oppure Depth + MLSD.
- Focale 18–24 mm già nel 3D, verticali dritte. Prompt: "soft daylight from large windows, bounce light,
  natural materials, interior photography".
- Problemi tipici: lampade e arredi inventati, quindi riduci l'end del controllo depth solo se vuoi più libertà.

## 6. Notturno / blue hour da render diurno
- Qwen-Image-Edit: *"turn into blue hour, warm 2700K interior lights on, keep geometry"*.
- Se le luci accese escono nei punti sbagliati: maschera delle vetrate (Material ID) e inpaint solo lì.

## 7. Contesto e vegetazione
- Inpaint con maschera di terreno e sfondo (Material ID o Sky alpha). Specifica le essenze ("mature plane
  trees, Mediterranean shrubs") e la stagione.
- Le persone generate hanno spesso scala sbagliata: inseriscile nel 3D come sagome, poi chiedi all'AI di
  "renderle reali".

## 8. Cielo
- Maschera Sky alpha da Lumion → inpaint del solo cielo, oppure editing "replace the sky with …".
- Dopo la sostituzione verifica la **coerenza tra luce e ombre**: sole basso nel cielo e ombre corte in facciata è
  l'errore più comune.

## 9. Upscaling per tavola A1
- Generazione a ~1,6 MP (Qwen) → SeedVR2 2× → SeedVR2 2× (oppure USDU a denoise 0.25) → controllo degli
  spigoli. Per la stampa a 150 dpi su A1 servono circa 5000×3500 px.
