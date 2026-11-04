# Protocollo di rilievo (modalità DESCRIVI)

## 0. Brief (chiedere o dedurre prima di iniziare)
- **Perimetro**: poligono o elenco di vie/civici; cosa sta dentro e cosa è "fondale".
- **Scopo**: inserimento ambientale, render, studio ombre, fotoinserimento, masterplan. Decide il LOD.
- **Viste di progetto**: da dove si guarderà il modello? I fronti visibili da lì vanno a LOD3.
- **Origine comune**: un punto lat/lng (spigolo del lotto, incrocio) usato da scheda, *Add Location*
  e script. Scriverlo nella scheda.

## 1. Livelli di dettaglio
| LOD | Edifici | Recinzioni / arredo / suolo |
|---|---|---|
| LOD1 | Volume estruso da impronta a quota gronda, tetto piano, un colore medio | Solo recinzioni continue come setti; nessun arredo; suolo unico |
| LOD2 | + forma copertura e manto, basamento, marcapiani e cornicione come fasce, colore per facciata, volumi tecnici | Recinzioni con tipologia e altezze; arredo principale (lampioni, panchine, alberi) come componenti semplici; pavimentazioni per zona |
| LOD3 | + aperture con ritmo, misure e profondità, serramenti e oscuranti, balconi, ringhiere, cornici, pluviali, insegne | Recinzioni con disegno della cancellata; arredo completo con modello/tipologia; cordoli, caditoie, segnaletica |

## 2. Sequenza
1. **Geometria da fonti aperte** (OSM/DBT/catasto): elenca gli edifici del perimetro e assegna gli
   ID in senso orario partendo da Nord-Ovest, isolato per isolato.
2. **Mappa annotata**: `gmaps.py static` + `annota.py mappa` con ID e numero delle riprese.
3. **Piano di riprese** (`templates/piano_riprese.json`):
   - almeno 1 ripresa frontale per ogni fronte LOD3 (pitch 0–15, fov 60–90, il più possibile
     perpendicolare: bersaglio = centro facciata);
   - 1 ripresa d'angolo (≈45°) per ogni edificio d'angolo, per leggere profondità e copertura;
   - riprese di dettaglio (fov 30–50) per basamenti, portoni, recinzioni, arredo;
   - riprese "di verifica" dalle stesse posizioni delle viste di progetto, se note.
   - Prima `sv-meta` (gratis) su tutti i punti: scarta pano interni, troppo lontani (> 25 m dal punto
     voluto) o con date incoerenti.
4. **Osservazione per elemento** (sotto) e compilazione della scheda.
5. **Satellitare e Earth** per coperture, cortili interni, retri non visibili da strada.
6. **Controllo di completezza** (§5).

## 3. Cosa osservare

### Edifici (E##)
- **Tipologia ed epoca** (palazzina anni '60, villino liberty, casa a schiera, capannone…):
  orienta tutte le ipotesi su ciò che non si vede.
- **Volumi**: piani fuori terra, piano attico/arretrato, sottotetto abitato (abbaini), volumi
  tecnici, corpi bassi, porticati, sbalzi.
- **Quote**: gronda e colmo (fonte e confidenza), quota del piano terra rispetto al marciapiede
  (gradini), altezza del basamento.
- **Copertura**: forma (piana, a capanna, a padiglione, a falda unica, shed, mansarda), pendenza
  stimata (tipico coppi 30–35%), manto e colore, sporto di gronda (cm), canali e pluviali,
  comignoli, lucernari, pannelli fotovoltaici, parapetti dei terrazzi.
- **Facciate per orientamento** (N, E, S, O o "fronte su via X"): materiale e finitura, colore
  (C##), partitura orizzontale (basamento, marcapiani, cornicione), verticale (lesene, angolari).
- **Aperture**: numero di assi e passo, allineamento verticale (sì/no), dimensioni tipo (L×H),
  quota davanzale, profondità della mazzetta, cornici/davanzali (materiale, sporgenza), serramento
  (materiale, colore, partizione), oscuranti (tipo, colore), vetrine al piano terra, portoni.
- **Aggetti**: balconi (sporgenza, lunghezza, spessore soletta), ringhiere/parapetti (tipo,
  colore), pensiline, tende da sole, insegne.
- **Impianti visibili**: split, antenne, canne fumarie: solo LOD3 e solo se caratterizzanti.

### Recinzioni (R##)
Tipo (muretto + cancellata, muro pieno, rete, grigliato, siepe, pannelli), altezza totale e del
muretto, copertina, materiale e colore di ogni parte, passo di pilastrini/montanti, cancelli e
passi carrai (larghezza, tipo, automazione), tracciato riferito al limite catastale.

### Arredo urbano (A##)
Per tipologia: lampioni (tipo, altezza indicativa, passo, lato), panchine, cestini, dissuasori,
fioriere, rastrelliere, pensiline, cassonetti, colonnine di ricarica, cabine, segnaletica verticale
e orizzontale rilevante (strisce, stalli). Posizione: distanza dal cordolo e dal civico più vicino;
per elementi in serie, inizio, fine e passo.

### Suolo e pavimentazioni (P##)
Carreggiata (materiale, larghezza, numero di corsie, sosta), marciapiedi (larghezza, materiale,
posa, cordolo e sua altezza, ≈ 15 cm), passi carrai, aiuole, rampe, chiusini caratterizzanti.

### Vegetazione (V##)
Specie o tipo (alberatura stradale, siepe, prato), altezza e diametro chioma stimati, sesto
d'impianto, caducifoglia/sempreverde (attenzione alla stagione della ripresa).

## 4. Stimare misure senza ricalcare
Si stimano per **riferimenti noti**, dichiarando il metodo:
- Interpiano: residenziale moderno 2,9–3,1 m; uffici 3,3–3,6 m; storico 3,5–4,5 m; piano terra
  commerciale 3,5–4,5 m.
- Elementi standard: porta 2,10–2,40 m; parapetto 1,00–1,10 m; davanzale 0,90 m; gradino 16–17 cm;
  cordolo ≈ 15 cm; automobile ≈ 1,45–1,55 m di altezza e ≈ 1,80 m di larghezza; posto auto
  2,50 × 5,00 m; cassonetto stradale ≈ 1,3–1,6 m.
- Larghezze e passi: dividere la lunghezza dell'impronta (fonte aperta) per il numero di assi.
- Altezza da conteggio: n. piani × interpiano + basamento + spessore cornicione. Confidenza media.
- Ripresa con pitch 0 e facciata perpendicolare minimizza la distorsione prospettica: usarla per i
  rapporti tra misure.
- Se due metodi divergono oltre il 10%, riportarli entrambi e motivare la scelta.

## 5. Controllo di completezza (prima della consegna)
- Ogni edificio del perimetro ha ID, LOD, quote con fonte, copertura, ogni facciata visibile
  descritta, almeno un riferimento a una ripresa.
- Ogni colore usato ha un C## in palette; ogni materiale ha la dimensione reale della texture.
- Fronti non visibili (retri, cortili): dichiarati come tali, con ipotesi marcata `bassa`.
- Elenco delle lacune e dei rischi in testa alla scheda.
