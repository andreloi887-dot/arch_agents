# Visualizzazione nella 2025: Photoreal Materials, Environments, AO

Tutto questo richiede il **nuovo motore grafico** (*Preferences › Graphics*). Non sostituisce un
motore di render (niente luci artificiali fisiche, GI completa o caustiche), ma basta per concept,
revisioni con il cliente e immagini di studio di qualità.

## Photoreal Materials (PBR)
- Si attivano come **stile di faccia** (pannello Styles / toolbar Styles): finché lo stile non è
  Photoreal, i materiali PBR si vedono come classici.
- Mappe tipiche: base color, normal (rilievo), roughness (ruvidità), metallic, ambient occlusion.
  Logica: la **roughness** governa il riflesso. Bassa (0,05–0,2) per vetro, metallo lucido e
  laccati; media (0,4–0,6) per legni trattati e ceramiche satinate; alta (0,8–1) per intonaco,
  cemento e tessuti *(nomi dei cursori nell'editor da verificare)*.
- Le librerie di default sono PBR; altri materiali curati sono su 3D Warehouse.
- **Dimensione reale**: impostarla sempre nell'editor (piastrella 600 × 600, doga 1200 × 180…).
  Con il normal map un errore di scala salta all'occhio.
- **Generate Textures**: dall'editor dei materiali, parte da un'immagine o da un materiale classico
  e genera un PBR piastrellabile. Serve la connessione (elaborazione online). Utile per
  materiali di studio e campioni fotografati dal fornitore; controllare la ripetizione su superfici
  grandi.
- Conversione automatica dei materiali in PBR: opzione in *Preferences › Graphics*. Disattivarla se
  il modello deve restare "classico" (export verso software che non leggono i PBR).

## Environments
- Pannello **Environments**: immagini 360° (HDRI equirettangolari) che illuminano i materiali PBR e
  producono i riflessi; si possono mostrare come sfondo (sky dome) o usare solo per la luce.
- Sorgenti: 3D Warehouse (collezioni curate) o file propri (fino a 8K). HDRI a 4K bastano quasi
  sempre e pesano molto meno.
- Regolazioni da cercare nel pannello: rotazione (allineare il sole dell'HDRI alle ombre di
  SketchUp), esposizione/intensità, visibilità come sfondo *(nomi esatti da verificare)*.
- Coerenza: se le ombre di SketchUp sono attive, la loro direzione deve coincidere con il sole
  dell'HDRI, altrimenti l'immagine "non torna". Si regola la data/ora (o la rotazione dell'HDRI)
  finché non coincidono.

## Ambient Occlusion (dal 2024)
- Impostazione di stile: scurisce gli incontri tra le facce e dà profondità anche agli stili non
  fotorealistici (ottima per le assonometrie di concept).
- Dosaggio: leggero nelle viste di presentazione; spento negli stili tecnici destinati al Vector di
  LayOut.

## Ricetta: immagine photoreal esterna
1. Stile di lavoro → duplicarlo in `STY_Photoreal`: faccia Photoreal, spigoli OFF (o profili molto
   sottili), AO ON leggero.
2. Materiali: PBR da libreria o *Generate Textures*; dimensioni reali; vetri con roughness bassa.
3. Environment: HDRI diurno, ruotato in modo che il sole coincida con le ombre (*Shadows* ON,
   data/ora dalla Geo-location).
4. Camera: *Two-Point Perspective*, FOV 35–50°, altezza occhio 1,60 m o vista rialzata.
5. Scena dedicata (salva stile, camera e ombre).
6. *File › Export › 2D Graphic*: 4000 px, anti-alias. Post-produzione leggera (contrasto,
   bilanciamento del bianco).

## Ricetta: interno
- HDRI di interno o esterno luminoso; ombre ON con il sole che entra dalle finestre; PBR su
  pavimento (roughness media) e legni; AO medio.
- Limite: le luci artificiali non illuminano davvero. Per i notturni o le luci d'atmosfera servono
  Lumion, Enscape o V-Ray.

## Quando passare a Lumion
- Vegetazione realistica, persone animate, video, notturni, materiali avanzati (acqua, vetro con
  rifrazione), contesto ricco: Lumion. Vedi `05-interoperabilita.md` per la compatibilità dei file
  con Lumion 12.5.
