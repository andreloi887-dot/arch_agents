# Modello – lotto all'angolo Via Tamburino Sardo / Via della Menta e contorno

Modello generato da dati per SketchUp Pro 2022. Il lotto P03 (part. 4258) è a dettaglio alto; attorno ci
sono un contorno leggero (edifici LOD1, muri di cinta, strade e marciapiedi) su un'area di 150 × 150 m
centrata sull'incrocio.

## Come costruirlo in SketchUp 2022
1. Nuovo modello in metri. *File › Geo-location › Add Location*, centrato sull'incrocio (39.25240 N,
   9.11527 E), con terreno.
2. Copia l'intera cartella `modello/` sul PC: servono `contesto.json` e `texture/`.
3. *Window › Ruby Console*:
   ```ruby
   load 'C:/…/arch_agents/skills/rilievo-urbano/scripts/sketchup/costruisci_contesto.rb'
   RilievoUrbano::Contesto.costruisci('C:/…/modello/contesto.json')
   ```
   La console stampa lo scarto di 3 punti di controllo tra la nostra proiezione e quella di SketchUp.
   Sopra 5 cm dà un avviso, sopra 50 cm si ferma. Lo script si può rilanciare (sostituisce il contesto
   precedente) e un solo Ctrl+Z lo annulla.
4. Nascondi il terreno di Add Location (l'entità, non il tag) e la Location Snapshot.
5. Facoltativo, per la verifica: `scene_da_manifest.rb` (scene con le camere di Street View) e
   `inventario_modello.rb`. Da `rilievo-urbano`: `confronta.py`.

## Da dove vengono i dati
| Dato | Fonte | Precisione |
|---|---|---|
| Terreno, strade, quote dei lotti | **DTM LiDAR 1 m, Regione Autonoma della Sardegna** (`dtm_lidar_1m.tif`, WCS) | ±0,15 m in quota; il gradino dei muri è "spalmato" su ~1 m |
| Sagome di lotti, strade, edifici | Catasto AdE (WMS, CC BY 4.0), vettorializzato | sfasamento ≤ 1–2 m vicino all'incrocio, non ancora allineato |
| Altezza dei muri, posizione di arredo e palma, materiali e colori | Osservazione delle riprese Street View (scheda rev. 3) | stime, confidenza media/bassa |
| Fuori dal DTM | Copernicus GLO-30 (tendenza robusta) | ±2 m (non usato nell'area modellata) |
| Proiezione locale | Azimutale equidistante WGS84 centrata sull'incrocio | metri veri |

Nessuna geometria è stata ricavata da immagini Google: le riprese servono solo per descrivere e per
confrontare.

## Il lotto P03, come risulta dal DTM
- Non è una piattaforma piana: è un **rilevato** che sale dalla punta (≈ +0,5 m sull'incrocio) a
  **+3,8 m al centro**.
- Su Via della Menta è **a raso** con la strada: cordolo di ~0,2 m sotto la rete (SV-08).
- Su Via Tamburino Sardo e sulla punta c'è un **muro di sostegno in cls alto ~1,0–1,3 m**, con
  sopra una scarpata erbosa che in 2,5 m raggiunge il terreno interno.
- **Rete elettrosaldata** su paletti da ~24 m dall'incrocio verso N, con il blocco in cls con la
  scritta "ANO".
- Sull'angolo: **lampione**, **pilastrino con la targa** di Via della Menta e **cartello di divieto**.
- Dentro il lotto: **palma Phoenix giovane** senza fusto ed erbe spontanee alte ~1 m (aprile).

## Verifica
- **Camera-matched sulle 19 riprese.** Le immagini affiancate sono in `_rif_google/verifica_simulata/`,
  solo in locale. Le 4 viste del lotto (SV-08, 12, 16, 18) coincidono con le foto per muro, scarpata,
  rete, lampione, cartello e palma.
- **Verifica automatica simulata** (`verifica_simulata/report.md`). È calcolata da `contesto.json`, non
  ancora da SketchUp.
  - **P01, P02 e P03 sono ✅.** R06 è ⚠️: l'ingombro del contenitore include la pendenza di Via della
    Menta e la rete.
  - **Gli ❌ sul contorno sono attesi.** Gli edifici sono LOD1, quindi mancano tetti a falda,
    fotovoltaico e accenti. Alcuni elementi della scheda sono fuori dal perimetro modellato (R08,
    A03–A05, P04, V01).
  - Sui muri lunghi in pendenza, il criterio di `confronta.py` (ingombro verticale) include la
    pendenza. Le altezze stazione per stazione coincidono con la scheda.

## Limiti noti
- Catasto non allineato: va fatto in SketchUp su Add Location (`importa_catasto.rb`).
- Edifici LOD1, senza tetti a falda.
- Lo script Ruby è stato rivisto riga per riga da `sketchup-expert` (correzioni applicate: orientamento
  automatico dei muri, paletti per altezza, materiali per normale, scarti contati, arredo in
  sotto-gruppi, controllo delle texture), ma **non è ancora stato eseguito in SketchUp**: provalo su una
  copia del file. Tempo stimato: 10–60 s.
- In verifica daranno ❌ anche, per scelta di perimetro: i conteggi delle serie (A01 1 lampione su 6, A02
  2 su 6, V02 1 palma su 2) e le altezze degli edifici, perché senza tetti a falda l'estrusione si ferma
  alla gronda mentre la verifica confronta col colmo.

## Rigenerare i dati
I valori di questo lotto sono in `lotto.json`; gli script sono il motore generico in
`skills/rilievo-urbano/scripts/contesto/` (vedi il suo README). Dalla cartella del repository:
```
python skills/rilievo-urbano/scripts/contesto/terreno_tendenza.py rilievi/zona-cagliari-menta-tamburino/modello <Copernicus.tif>   # facoltativo
python skills/rilievo-urbano/scripts/contesto/contesto.py rilievi/zona-cagliari-menta-tamburino/modello   # scena.json + contesto.json
cd rilievi/zona-cagliari-menta-tamburino/modello
cd anteprima && CONTESTO=1 node render.js && node aerea.js
```
Servono numpy, shapely, triangle, pyproj, tifffile, imagecodecs e Pillow.
