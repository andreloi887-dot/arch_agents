# Fonti, accesso e termini d'uso

## 1. Chi fornisce cosa

| Dato | Fonte primaria | Uso consentito nel flusso |
|---|---|---|
| Impronte edifici | DBT/CTR regionale, catasto (WMS AdE), OpenStreetMap | Geometria del modello |
| Altezze | DBT (quota gronda/altezza, dove presente), LiDAR (nDSM = DSM − DTM), OSM `height`/`building:levels`, conteggio piani da Street View | Geometria (le prime tre); stima (l'ultima) |
| Terreno | *Add Location* di SketchUp, DTM regionale/LiDAR | Geometria |
| Materiali, colori, tipologie, ritmi, dettagli | **Street View**, Maps satellitare, Earth 3D | Descrizione testuale nella scheda |
| Arredo urbano, recinzioni | Street View (posizione indicativa), OSM (`amenity=bench`, `barrier=*`, `highway=street_lamp`) | Descrizione + posizione indicativa |
| Coperture (forma, falde, manto) | Satellitare (Maps/Earth) per lettura, DBT/LiDAR per quote | Descrizione + quote da fonti aperte |
| Confronto in VERIFICA | Street View con camera nota | Solo confronto, nessun contenuto derivato |

## 2. Termini d'uso Google (leggere prima di ogni lavoro)

- I Google Maps Platform Terms vietano di **creare contenuti basati sui contenuti Google**:
  ricalco, digitalizzazione, creazione di dataset derivati (impronte, contorni di edifici, modelli
  3D estratti da immagini oblique o dalle Photorealistic 3D Tiles). Vietato anche lo scraping e
  l'uso per addestrare modelli di IA. I termini sono stati aggiornati a giugno 2026: in caso di
  dubbio rileggere la versione vigente (cloud.google.com/maps-platform/terms e Service Specific
  Terms). Non sono un parere legale.
- Regole operative di questo skill:
  1. Nessuna impronta, quota o forma ricalcata da immagini Google. Se una geometria esiste solo su
     Google (es. un volume tecnico non in DBT/OSM), descrivila con una **stima dichiarata** a partire
     da riferimenti (conteggio piani, elementi standard) e marcala `confidenza: bassa`; non misurarla
     sull'immagine.
  2. Nessuna immagine Google importata in SketchUp come texture, underlay o *Match Photo*.
  3. Le immagini scaricate restano in una cartella locale di lavoro (`_rif_google/`, esclusa da git) e
     non finiscono in tavole, relazioni o pubblicazioni. Conservare l'attribuzione (`copyright` del
     metadata).
  4. Per le immagini nei deliverable usare: foto proprie, *Add Location* (imagery con licenza
     Trimble), ortofoto regionali con licenza aperta.

## 3. API Google Maps Platform (chiave dell'utente in `GOOGLE_MAPS_API_KEY`)

### Street View Static API
- Immagine: `https://maps.googleapis.com/maps/api/streetview?size=640x640&location=LAT,LNG&heading=H&pitch=P&fov=F&source=outdoor&return_error_code=true&key=…`
  - `size` max 640×640 nei piani standard. Lavora **quadrato** (semplifica il camera matching).
  - `heading` 0–360°, 0 = Nord, in senso orario. Se omesso punta verso `location` dalla posizione del pano.
  - `pitch` −90…+90°, 0 = orizzontale. Default 0. Per facciate alte: +10/+20.
  - `fov` 1…120°, default 90. 90 per contesto, 50–60 per dettaglio, 30 per elementi lontani.
  - `source=outdoor` esclude i pano interni; `radius` (default 50 m) raggio di ricerca del pano.
  - **Pano degli utenti** (photosphere, `copyright` ≠ "© Google"): `source=outdoor` NON li esclude e
    nei centri storici sono spesso i più vicini (anche dall'alto di torri e terrazze). Quota e posizione
    della camera sono ignote, quindi niente camera matching. `gmaps.py sv-shots` li scarta e cerca il
    pano Google ufficiale più vicino entro 20 m (metadata gratuiti); per usarli comunque solo come
    riferimento descrittivo: `"consenti_pano_utente": true` nella ripresa.
  - Si può usare `pano=ID` invece di `location` per bloccare una ripresa specifica.
- Metadata: `…/streetview/metadata?location=…&key=…` → `status`, `pano_id`, `location` (posizione
  **reale** del pano, diversa dal punto richiesto), `date` (AAAA-MM), `copyright`. **Gratuito**, non
  consuma quota: usarlo sempre prima di scaricare.
- Camera: altezza ≈ 2,5 m dal suolo per le riprese da auto (indicativo; i pano Trekker sono più
  bassi). In VERIFICA si regola guardando la linea d'orizzonte.

### Maps Static API
- `https://maps.googleapis.com/maps/api/staticmap?center=LAT,LNG&zoom=Z&size=640x640&scale=2&maptype=satellite&key=…`
- `zoom` 18–20 per un isolato; `scale=2` raddoppia la risoluzione. I `markers` hanno etichette di un
  solo carattere: per gli ID usa `annota.py mappa`, che proietta lat/lng in pixel (Web Mercator).

### Altre API utili
- **Geocoding API**: indirizzo ↔ coordinate. Se la chiave ha una restrizione di applicazione (siti
  web/IP) il Geocoding risponde `REQUEST_DENIED`: usare solo la restrizione per API o una chiave dedicata.
- **Elevation API**: quota del terreno in un punto (solo controllo, il terreno del modello viene da
  *Add Location*/DTM).
- **Map Tiles API – Photorealistic 3D Tiles**: visione obliqua 3D (es. in un visualizzatore
  Cesium). Solo osservazione: niente estrazione di mesh o misure.
- **Solar API (buildingInsights)**: falde con pendenza e orientamento. Copertura in Italia da
  verificare caso per caso; anche qui solo come controllo descrittivo.

## 4. Google Earth
- **Earth Pro (desktop, gratuito)**: *Storico immagini* (orologio) per datare interventi, edifici 3D
  per leggere volumi e coperture, Street View integrato. Strumento Righello solo per orientarsi.
- **Earth Web**: vista 3D e misura; stesse regole.
- Con computer-use: screenshot frequenti, annota coordinate e data immagini (in basso).

## 5. Fonti aperte italiane per la geometria
- **OpenStreetMap** (ODbL, citare "© OpenStreetMap contributors"): `building`, `building:levels`,
  `height`, `roof:shape`, `roof:levels`, `building:material`, `barrier`, `amenity`. Qualità
  variabile: verificare con il catasto. `gmaps.py osm-edifici` scarica via Overpass.
- **DBT / CTR regionali** (geoportali regionali, WMS/WFS, spesso CC-BY): impronte a 1:1000–1:5000
  in ambito urbano, spesso con quota gronda o altezza volume. È la fonte migliore per le altezze.
- **Cartografia catastale** (Agenzia delle Entrate, servizio WMS gratuito, CC-BY 4.0): particelle e
  sagome dei fabbricati; ottima per i limiti di proprietà (dove corrono le recinzioni).
- **Catasto sfasato: allineare prima di usare.** Le mappe catastali sono spesso traslate e ruotate
  rispetto alla realtà, di solito di qualche metro e a volte di più di 10 m: dipende dalle origini locali
  Cassini-Soldner, dalla trasformazione verso WGS84 e dai fogli di impianto storico. Inoltre le sagome
  non sono sempre aggiornate. Procedura:
  1. trattare le sagome come **forma**, non come **posizione**;
  2. scegliere ≥ 3 punti di controllo ben distribuiti (spigoli di edifici, angoli di recinzione) su una
     base con licenza: *Add Location* di SketchUp, ortofoto regionale, LiDAR. Mai su imagery Google;
  3. applicare una **rototraslazione rigida** (eventualmente con scala uniforme), non una
     deformazione: le sagome restano congruenti tra loro;
  4. dichiarare nella scheda lo spostamento applicato (dx, dy, rotazione) e lo scarto residuo per
     punto. Con residui > 1 m su un edificio, quell'impronta va a confidenza bassa: probabilmente la
     sagoma è obsoleta (ampliamenti, demolizioni);
  5. confrontare il numero e la forma dei corpi con Street View: edifici nuovi non accatastati (o
     accatastati male) vanno in `lacune`.
- **LiDAR** (Piano Straordinario di Telerilevamento del MASE e LiDAR regionali): DTM/DSM 1–2 m;
  nDSM = DSM − DTM dà le altezze degli edifici con precisione ±0,5 m.
- **SketchUp *Add Location*** (Pro): imagery e terreno georeferenziati, base del modello e dell'origine
  comune con la scheda.
- **Ortofoto AGEA/regionali**: per le tavole al posto delle immagini Google.
