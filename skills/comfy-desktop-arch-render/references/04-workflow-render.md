# Pipeline tipo

Le catene sotto usano nodi nativi dove possibile. I nomi esatti dei nodi possono cambiare: in caso di dubbio
parti dal **template ufficiale** del modello e aggiungi i blocchi.

## A. Generazione da controllo (schizzo, linee, massing → render)
`Load Image (controllo)` → preprocessore (se serve) → applicazione ControlNet o patch → `KSampler` → `VAE Decode` → `Save`

- **SDXL / Flux (ControlNet classico):** `ControlNetLoader` + `Apply ControlNet` sulle condizioni.
  Parametri chiave: `strength`, `start_percent`, `end_percent`.
- **Qwen-Image / Z-Image (patch DiffSynth o Fun):** `ModelPatchLoader` (file in `models/model_patches`) +
  `QwenImageDiffsynthControlnet` (input: model, model_patch, vae, image, strength). La patch modifica il
  *modello*, non le condizioni.
- **Valori di partenza d'esperienza:**
  - depth 0.7–0.9 con end 0.7–0.8 (lasciare liberi gli ultimi step dà materiali più naturali);
  - linee o MLSD 0.4–0.7 con end 0.5–0.7;
  - schizzo libero (softedge) 0.5–0.65.
- Strength troppo alta produce un look "plastico" e cartoonesco con linee che diventano bordi neri; strength
  troppo bassa produce geometria inventata.

## B. Img2img su render esistente (Lumion o Edificius → più realismo)
`Load Image (render)` → `VAE Encode` → `KSampler (denoise < 1)` → …
- **Denoise 0.25–0.40:** stessa scena, materiali e vegetazione più credibili. Oltre 0.5 la geometria inizia a
  muoversi.
- Per spingere il denoise a 0.5–0.7 senza perdere la geometria, aggiungi la depth (dal pass Lumion) in
  ControlNet a 0.6–0.8.
- **Alternativa più moderna e spesso migliore:** il percorso C.

## C. Editing guidato da istruzione (Qwen-Image-Edit-2511, Flux Kontext)
`Load Image` → `TextEncodeQwenImageEdit(Plus)` con immagine e istruzione → `KSampler` → …
- Prompt come istruzioni da capocantiere: *"Sostituisci l'intonaco bianco con mattone faccia vista rosso
  scuro, mantieni invariati serramenti, geometria e inquadratura"* (in inglese il modello è più affidabile).
- **Una modifica per passaggio:** materiale, poi contesto, poi luce. Le modifiche cumulative in un solo
  prompt tendono a deformare.
- **Multi-reference:** immagine 1 = render, immagine 2 = campione di materiale o foto di riferimento
  ("applica il rivestimento dell'immagine 2 alla facciata dell'immagine 1").
- Per gli step e il CFG vedi `02-modelli-e-licenze.md` (CFG 4 senza Lightning; CFG 1 e 4–8 step con Lightning).

## D. Inpainting mirato (correggere una zona)
- Maschera da Material ID o Sky alpha (Lumion) oppure disegnata nel *Mask Editor*.
- Qwen e Z-Image: patch o Union con inpaint; SDXL: modello inpaint dedicato oppure `VAE Encode for Inpaint`.
- **Allarga la maschera di 8–24 px** (`GrowMask`) e sfumala: i bordi netti producono aloni.
- Tipici target: cielo, vegetazione, persone, vetri (riflessi credibili), cartellonistica.

## E. Coerenza tra più viste (serie di render dello stesso progetto)
- Stesso modello, stessi prompt di materiale, stesso seed di partenza; cambiano solo i controlli.
- Usa un render "master" approvato come **riferimento** (Qwen-Image-Edit multi-image o IP-Adapter su SDXL).
- Per materiali e brand di studio ricorrenti: una **LoRA di studio** addestrata su 20–40 render propri.
- Accetta che la coerenza perfetta non esista: per serie da 6+ viste di gara, la base resta il motore 3D e l'AI
  si usa per arricchire (percorso B o C a denoise basso).

## F. Upscaling per tavole e stampa
- **SeedVR2** (nativo, varianti 3B e 7B INT8): un passaggio, fedele all'originale. Tende a eccedere in contrasto e
  nitidezza, quindi controlla gli spigoli. Per fattori grandi fai 2× due volte.
- **Ultimate SD Upscale** (tile + diffusione a denoise 0.2–0.35, tile 1024, overlap 64–128): aggiunge dettaglio
  ma inventa di più. Su facciate ripetitive può duplicare elementi.
- Combinazione consigliata per la tavola finale: SeedVR2 2×, poi eventuali ritocchi locali in inpaint.
- Upscaler ESRGAN (4x-UltraSharp e simili): rapido, buono per anteprime.

## G. Video (solo se richiesto)
Dalle immagini di render si passa a modelli image-to-video (famiglie Wan e LTX). Per l'architettura servono
movimenti di camera lenti e controllati: la geometria tende a "nuotare". Fuori dal focus principale di questa
skill: verifica i modelli aggiornati sul web.
