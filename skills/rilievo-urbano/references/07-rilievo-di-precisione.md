# Rilievo di precisione del contesto (obbligatorio per ogni lotto)

Obiettivo: un contesto **fedele elemento per elemento**, non "verosimile". Ogni edificio, ogni fronte su strada e ogni
balcone visibile va osservato, descritto in forma strutturata e poi controllato nel modello generato. Il motore
(`scripts/contesto/`) costruisce solo ciò che trova scritto: quello che il rilievo omette, nel modello manca.

## 1. Fonti, in quest'ordine
1. **DBGT regionale** (WFS `webgis.regione.sardegna.it/geoserver`, layer `dbu:dbgt_10k_22_v05_*`, scala 1:2000):
   sede stradale, assi con nome, **recinzioni** (`elemento_divisorio`), muri di sostegno, sagome degli edifici.
   È la geometria di riferimento. Il catasto è sfasato di 1–3 m e serve solo per il lotto e le particelle.
2. **DTM LiDAR 1 m** per le quote; le strade usano il profilo lisciato lungo gli assi DBGT.
3. **Street View**: le riprese di piano (`piano_riprese.json`) **più una ripresa mirata per ogni edificio**
   (`scripts/sv_edifici.py <modello>`), che riporta anche l'orientamento della facciata ripresa.
4. **Google Earth 3D** (browser) per coperture, retri, cortili, recinzioni interne, ordine delle altezze.
Le immagini Google servono solo a descrivere: mai ricalcare o misurare geometria.

## 2. Procedura per ogni edificio (nessuno escluso, anche quelli di sfondo `CTX`/`DB`)
Guarda **tutte** le immagini che lo inquadrano (ripresa mirata, riprese di piano, Earth da almeno due lati).
Prima di attribuire un dettaglio a un edificio, **verifica in pianta** quale edificio sta davvero dietro il
fronte ripreso: posizione del pano, heading, distanza (`manifest.json`). Gli errori più frequenti sono stati
proprio di attribuzione (un muro assegnato al vicino; un edificio scambiato con quello accanto in un'altra
ripresa). Se due immagini sono in contrasto, ne serve una terza; dichiaralo nella nota.

Compila, nella scheda (`E##`) o in `lotto.json → edifici.per_edificio.<ID>`:
- `piani`, `altezza` (gronda) e `colmo`, `copertura` (`piana`, `a padiglione`, `a capanna`), `pendenza_pct`,
  `manto`, `sporto_cm`, `fotovoltaico` (true/false), `volumi` (torrette, attici: lati, altezza in più).
- `facciate`: una voce per ogni fronte visibile, con `orientamento` (N, NE, E, SE, S, SO, O, NO: quello della
  normale della facciata, cioè heading della camera + 180°), `aperture.assi`, dimensioni tipo `l_m`/`h_m`,
  **`balconi_piani`** (elenco esplicito dei piani con balcone su quel fronte, 0 = piano terra) e
  `balcone_frazione` (quota della facciata occupata dal balcone, 0–1). Non lasciare i balconi in una frase.
- `fronte_strada`: `tipo`, `muro_h` (altezza del muro dal marciapiede), `materiale` (C##), `sopra`
  (`["ringhiera"|"doghe"|"rete", altezza, C##]`). Per gli edifici della scheda il fronte è il muro `R##` in
  `muri_contorno` (con `verso` NS/EO se il lotto ha due fronti, e `presso` + `raggio_m` per un tratto
  particolare, come un muro curvo sull'angolo).

## 3. Recinzioni e fronti su strada
- Percorri **ogni strada su entrambi i lati, tratto per tratto**, da incrocio a incrocio: per ogni tratto annota
  di chi è, tipo, altezza del muro e di ciò che c'è sopra, materiale e colore, cancelli e passi carrai.
- Gli angoli tra due strade (muri curvi, smussi) e i tratti dove il giardino è rialzato vanno descritti a parte.
- Il motore mette il muro sulla recinzione DBGT e, dove il DBGT non la disegna, sul bordo della sede stradale.
  Controlla nella pianta di verifica che **nessun fronte di lotto edificato resti senza muro** e che i confini
  interni (perpendicolari alla strada) non siano presi per muri su strada.

## 4. Strade, marciapiedi, arredo, verde
- Marciapiedi: larghezza per strada e lato, materiale, cordolo; strade: mezzeria, strisce pedonali (quali).
- Lampioni (passo, lato, altezza), segnaletica verticale, paline, armadi stradali (`vicino_a` un edificio).
- Alberi e palme per giardino (`giardino_di`, `n`, `forma`: `albero`, `palma`, `palma_alta`), siepi sui muri
  (`su_muri`), canneti (`dietro_muro`).

## 5. Controllo dopo la generazione (obbligatorio, fino a 3 cicli)
1. Pianta di verifica: muri colorati per origine (scheda, `fronte_strada`, confini interni, muri di sostegno)
   con l'altezza media di ogni tratto, sovrapposti alle recinzioni DBGT.
2. Viste del modello dagli stessi punti delle riprese (`export_verifica/SV-*.png`) affiancate alle foto:
   confronta **ogni** edificio e **ogni** fronte (numero di piani, balconi per piano, tipo e altezza della
   recinzione, forma del tetto).
3. `confronta.py`: ogni ❌ va spiegato (errore di modello, di scheda o di misura) e chiuso.
4. Ogni correzione va fatta nei dati (scheda o `lotto.json`) o nelle regole generali del motore, mai con
   eccezioni scritte a mano nel codice per quel lotto.
