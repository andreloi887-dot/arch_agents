# Lezioni apprese (Via della Menta, novembre 2026)

Errori trovati confrontando il contesto generato con foto, Google Earth, ortofoto e DSM, e regola adottata per non
ripeterli. Ogni regola è già nel motore (`scripts/contesto/`) o nei controlli (`verifica_contesto.py`); qui c'è il
perché, da leggere prima di lavorare su un lotto nuovo.

## Fonti e geometria
| Errore | Causa | Regola |
|---|---|---|
| Particella più piccola di ~2 % e frustoli mancanti | il catasto WMS è un'immagine: i contorni passano per i centri dei pixel, dentro la linea; scartati i pezzi < 20 m² | allargare di 1,5 px fino alla mezzeria della linea; soglia 5 m² |
| Indici delle particelle cambiati dopo una nuova vettorializzazione | l'ordine dei contorni dipende dai parametri | indicare particelle e lotto con un **punto [lat, lng]**, mai con l'indice |
| Recinzioni e marciapiedi sbagliati | il catasto è sfasato di 1–3 m e la sua sede stradale non è quella reale | **DBGT regionale** come geometria di riferimento (sede, assi, recinzioni, muri, edifici); catasto solo per il lotto |
| Marciapiedi "inventati" | il DBGT non disegna i marciapiedi: la sede va da recinzione a recinzione | marciapiede = fascia interna alla sede (larghezza da rilievo), controllata sull'ortofoto |
| Dossi in carreggiata | la quota presa dal DTM punto per punto risente di muri e recinzioni ai bordi | profilo stradale lisciato lungo gli assi DBGT + pendenza trasversale; raccordo lungo (8 m) agli innesti |
| Muri su strada alti 4 m | il DTM vicino ai muri "spalma" il salto del giardino | il muro supera l'altezza del rilievo di 0,3 m al massimo |
| Fronte di un lotto senza muro | il confine catastale stava metri indietro rispetto alla sede DBGT | ogni tratto di bordo stradale va alla **particella edificata più vicina** (6 m) e, se ci sono più edifici nella stessa particella, all'**edificio più vicino** |
| Confini interni presi per muri su strada | un tratto vicino alla strada ma perpendicolare | "su strada" solo se vicino (2 m) **e parallelo** (±30°) al bordo della sede |
| Muretto in mezzo all'incrocio | un muro di sostegno DBGT disegnato sul marciapiede | i muri di sostegno DBGT non possono stare sulla sede né sul fronte del lotto |
| Altezze stimate male (±2 m) | conteggio dei piani da foto | **DSM LiDAR regionale** (solo edifici): gronda = 35° percentile della fascia perimetrale, colmo = 97° percentile; tetto piano se il dislivello < 0,6 m |
| Edifici moderni senza misura | costruiti dopo il volo del DSM | riconosciuti in automatico (copertura < 60 %) e lasciati alle stime da foto, segnalati in `quote_fonte` |
| Alberi che non esistono più | il DSM è del 2008 | albero tenuto solo se nell'ortofoto 2022 la chioma è scura e verde (luminosità ≤ 115, indice di verde ≥ 0,085) |

## Rilievo da foto
| Errore | Causa | Regola |
|---|---|---|
| Muro attribuito all'edificio sbagliato (R05 fra E03 ed E04, due volte) | foto guardata senza verificare chi sta dietro il fronte | per ogni fronte: posizione del pano, heading e pianta; almeno tre viste per edificio (`sv_edifici.py`) |
| Tetto piano/a falde invertito (E07, E11) | una sola ripresa che inquadrava il volume vicino | mai cambiare la scheda per una sola foto: serve una seconda vista o il DSM |
| Etichette sbagliate nel piano di riprese | il campo `inquadra` era una previsione, non una verifica | l'etichetta va riscritta dopo aver visto la foto |
| Balconi mancanti | descritti a parole o non rilevati sugli edifici di sfondo | `balconi_piani` esplicito per ogni facciata visibile, anche per CTX/DB |
| Strisce pedonali dove non ci sono | regola generica a tutti gli incroci; assi DBGT doppi | strisce solo dove rilevate (`strada`, `lato`, `incrocio`); dedup dei doppioni |
| Cartelli in carreggiata | posizione calcolata dal bordo sbagliato | ogni arredo viene riportato sul marciapiede (0,4 m dal cordolo); controllo automatico |

## Ambiente e strumenti
- SketchUp è solo un **visualizzatore di controllo**: non investire nella sua resa; la qualità finale è in Blender.
- Un backup `.skb` a 0 byte lasciato da un'esecuzione interrotta blocca `model.save` senza errori: la pipeline lo
  elimina prima di salvare. Non chiudere SketchUp a forza durante il salvataggio.
- Nel costruttore Ruby i materiali hanno nomi rinominati (`C20_acciaio_zincato`): usare solo nomi generici
  definiti in `contesto.json` (es. `PALO_LUCE`) o quelli già rinominati.
- Il verso delle facce generate non è garantito: stesso materiale su fronte e retro (niente facce azzurre).
- Chiave Google Maps: progetto `rilievo-urbano`, account in prova gratuita: **non** fare l'upgrade.
- Google Earth 3D e Street View servono a descrivere, mai a ricavare geometria; ortofoto e DSM regionali sono dati
  aperti e se ne può ricavare geometria.

## Ciclo di lavoro che ha funzionato
1. `prepara_lotto.py` (catasto, DTM, DBGT, DSM, ortofoto) → `contesto.py` → `verifica_contesto.py`.
2. Rilievo di precisione (`07-rilievo-di-precisione.md`) con tre viste per edificio.
3. Rigenerazione, viste dagli stessi punti delle riprese, confronto affiancato edificio per edificio.
4. Ogni differenza corretta nei dati o in una regola generale, mai con eccezioni nel codice per il singolo lotto.
