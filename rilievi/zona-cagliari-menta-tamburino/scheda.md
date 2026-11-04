# Scheda di rilievo – Cagliari (Pirri), incrocio Via della Menta / Via Tamburino Sardo

| | |
|---|---|
| Zona | Incrocio a Y Via Tamburino Sardo (NO–SE) × Via della Menta (verso NNE), con l'innesto di Via A. Moravia (verso E); raggio ~70 m |
| Origine | 39.25240 N, 9.11527 E – baricentro dell'incrocio (stessa origine per SketchUp) |
| Scopo | Rilievo di prova del flusso; contesto per inserimento ambientale |
| LOD | LOD2 di default; **LOD3 per E06, E09, R01, R02** (i fronti visti dall'incrocio) |
| Immagini | 19 riprese Street View Google, **aprile 2026**; satellitare Airbus/Maxar 2026 |
| Revisione | 1 – 04/11/2026 |
| Fonti geometria | **nessuna ancora** (vedi lacune) |

## ⚠️ Lacune e rischi (leggere prima di modellare)
1. **Impronte e quote non provengono da fonti aperte.** OpenStreetMap e Geoportale Sardegna non erano
   raggiungibili dall'ambiente di lavoro. Tutte le altezze sono **stime da conteggio dei piani**
   (confidenza media o bassa). Prima di modellare servono le sagome da **catasto (WMS AdE)** o dal **DBMP
   della Regione Sardegna**. Non ricalcare il satellitare Google.
2. **Terreno in pendenza.** Via Moravia sale sensibilmente verso E e Via Tamburino Sardo scende
   leggermente verso SE. Per questo molti muri di cinta sono **muri di sostegno**: i lotti a E (E08, E09,
   E06) stanno 1–2,5 m sopra il marciapiede. Usare il terreno di *Add Location* o il DTM regionale.
3. Retri e fronti interni (E03, E07, E08, E09 lato giardino) non sono visibili: ipotesi.
4. Il sole pieno sovraespone bianchi e marciapiedi: i colori C05, C17, C18 e C19 hanno confidenza bassa.
5. Le falde di E05, E08 ed E09 sono in gran parte coperte da fotovoltaico.
6. E04 ed E07 sono visti solo da satellite: solo volumi (LOD1).

## Carattere della zona
Periferia residenziale a bassa densità di Pirri: villini e palazzine da 1 a 3 piani **arretrati nei
lotti**, di epoche diverse, dalle case anni '80–'90 con tetti a padiglione in tegole alle palazzine
contemporanee bianche a tetto piano con fotovoltaico. **Il fronte stradale è fatto quasi solo di muri di
cinta e di sostegno**, molto vari per materiale (intonaci gialli, salmone, bianchi; blocchi di cls a
vista; cls grezzo), sormontati da ringhiere o recinzioni a doghe bianche. Strade in asfalto con
marciapiedi stretti (~1,5 m) in **marmette di cls a scacchiera rosa e beige** e cordolo in cls. Due lotti
incolti, all'angolo N e a SO, e palme come elemento verde caratterizzante.
**Per il modello conta più la corretta resa dei muri che il dettaglio delle facciate.**

Riferimenti grafici: `palette.png` (deliverable); `_rif_google/mappa_annotata.png` e
`_rif_google/SV-xx_annotata.png` (solo riferimento di lavoro locale, © Google).

## Edifici

| ID | Dove | Piani | Gronda / colmo (m) | Copertura | Facciata | LOD | Riprese |
|---|---|---|---|---|---|---|---|
| E01 | Tamburino Sardo O, a NO (civ. ~120) | 3 | 9,0 m / 10,8 m | capanna, C03 | intonaco beige C14 | 2 | SV-11 |
| E02 | Tamburino Sardo O | 2 (+ corpo di 3) | 6,5 m / 8,3 m | padiglione, C03 | intonaco crema C13 | 2 | SV-10 |
| E03 | angolo NE Menta/Moravia | 2 | 6,5 m / 8,3 m | padiglioni multipli, C03 | intonaco pesca C08 | 2 | SV-09, SV-16 |
| E04 | Menta E, a N di E03 | 1 | 3,5 m | piana | bianco C04 | 1 | (satellitare) |
| E05 | Moravia S, civ. 52 | 2 | 7,0 m | piana + fotovoltaico | bianco C04 + pietra C12 | 2 | SV-07 |
| E06 | Moravia S | 3 | 10,0 m | piana + fotovoltaico + pergola | bianco C04 + grigio C11 | **3** | SV-06, SV-19 |
| E07 | Moravia S, interno | 2 | 6,5 m / 8,3 m | padiglione + fotovoltaico | C08 (ipotesi) | 1 | (satellitare) |
| E08 | Tamburino Sardo E, civ. 67A | 1 su basamento | 6,5 m / 8,0 m dal marciapiede | padiglione basso + fotovoltaico | bianco C04 | 2 | SV-02, 03, 14 |
| E09 | Tamburino Sardo civ. 69, angolo Moravia | 2 + torretta di 3 | 6,8 m / 10,5 m | padiglioni + fotovoltaico, C03 | **giallo C01** | **3** | SV-01, 13, 15, 17 |
| E10 | Tamburino Sardo O, a S | 3 | 9,3 m / 10,8 m | padiglione, C03 | pesca C08 + vetrata blu C22 | 2 | SV-05, SV-17 |
| E11 | Tamburino Sardo O, di fronte a E09 | 1–2 | 6,5 m | piana | bianco C04 + cornici C23 | 2 | SV-04 |

**E09 – complesso a schiera all'angolo (LOD3, priorità massima).** È l'edificio più visibile
dall'incrocio. Si tratta di 3–4 unità affiancate lungo Via Tamburino Sardo, su un giardino rialzato di
~1,0 m rispetto al marciapiede.
- **Volumi:** corpi a 2 piani con portici e logge al piano terra, archi ribassati su pilastri e colonne
  bianchi (C04), più una **torretta a 3 piani** con tetto a padiglione (colmo ~10,5 m, stima media).
- **Facciate:** intonaco giallo paglierino C01, cornici di finestre e spigoli bianchi C04, sottogronda e
  gronde in cotto C02 con sporto di ~50 cm, pluviali in rame.
- **Aperture:** portefinestre 1,2 × 2,4 m su balconi con ringhiera in acciaio grigio C06 a montanti
  verticali; finestre 0,9 × 1,3 m. Tende a cappottina grigie, fotovoltaico sulle falde S/O.
- Le palme V01 nel giardino d'angolo fanno parte della sua immagine.

**E06 – palazzina contemporanea (LOD3).** Volumi cubici bianchi C04 sfalsati, con setti verticali
sporgenti. Al 1° piano c'è un riquadro arretrato grigio C11 con una finestra a nastro. Terrazzi con
parapetti in vetro o metallo, tenda da sole grigia al piano terra, pergola in copertura. Il vicino a E
(E05) riprende lo stesso linguaggio, con una fascia verticale in pietra a opera incerta scura C12.

**E08 – villa su basamento.** Un piano con cornicione bianco spesso, su un terrazzamento ~2,5 m sopra
il marciapiede. Dalla strada si vedono solo il cornicione e la recinzione a doghe: il volume conta poco,
il muro R02 molto.

**E10 – palazzina a 3 piani.** Intonaco pesca C08 e **vano scala vetrato blu C22 a tutta altezza**
sullo spigolo NE: è l'elemento riconoscibile verso S. Finestre con avvolgibili, inferriate al piano terra.

**E01, E02, E03, E11.** Case anni '80–'90 a 2–3 piani con intonaci tenui (C14, C13, C08), persiane in
legno marrone e tetti in tegole C03. E11 si vede appena oltre il muro R09: ha cornici e pilastri angolari
rosso mattone C23.

## Recinzioni e muri (elemento dominante)

| ID | Dove | Composizione | H (m) | Materiali | LOD |
|---|---|---|---|---|---|
| **R01** | E09: Tamburino Sardo + curva d'angolo (raggio ~6 m) + Moravia | muro **a gradoni** che segue la pendenza; tratti pieni (+0,5 m) alternati a tratti con ringhiera a montanti tubolari (h 1,0, passo ~12 cm); copertina in cotto spessa 4 cm e sporgente 3 cm; cancelletto pedonale 1,1 × 2,0 m in lamiera e barre; nicchie dei contatori | muro 1,4–2,0 + ringhiera 1,0 | C01, C02, C06 | **3** |
| **R02** | E08: Tamburino Sardo | muro di sostegno liscio + recinzione a doghe orizzontali bianche (doghe da 15 cm, montanti ogni ~2 m); cancello carrabile a doghe su rampa | 2,5 + 1,2 | C04, C05 | **3** |
| R03 | E06: Moravia | muretto in salita + ringhiera grigia; posto auto chiuso da rete elettrosaldata zincata h 1,8 | 1,0–1,4 + 0,8 | C04, C06, C20 | 2 |
| R04 | E05: Moravia | muretto 0,6 + recinzione e cancelli a lamelle orizzontali | 1,9 | C04, C05 | 2 |
| R05 | E03: Menta | muro in **blocchi di cls a vista** con pilastrini ogni ~3 m; base degradata | 2,5 | C10 | 2 |
| R06 | lotto P03: angolo N e Via della Menta | muro di sostegno in cls a vista (graffiti, targa Via della Menta) + rete elettrosaldata su paletti e cancello tubolare | 0,6–1,5 | C15, C20 | 2 |
| R07 | E02: Tamburino Sardo | tratti in blocchi di cls a vista + tratti intonacati | 1,4 | C10, C13 | 2 |
| R08 | E01: Tamburino Sardo | muro intonacato + cancello in ferro; pilastri con cappello in coppi | 1,6 | C14, C06, C03 | 2 |
| R09 | E11: Tamburino Sardo | muro pieno intonacato salmone | 2,5 | C07 | 2 |
| R10 | E10: Tamburino Sardo | muro rustico grigio + cancello; prosegue con muretti rosa | 1,8 | C09, C06, C07 | 2 |
| R11 | Moravia N + angolo Menta | muro di sostegno intonacato con capperi ricadenti; graffiti all'angolo | 2,5 | C04 | 2 |

## Arredo urbano

| ID | Tipo | Dove | N | Materiale |
|---|---|---|---|---|
| A01 | lampione testa-palo, palo cilindrico zincato h ~8 m, armatura LED a sbraccio corto | marciapiedi, ~0,5 m dal cordolo, passo 25–30 m | ~6 | C20 |
| A02 | segnaletica verticale: divieto di sosta 0-24 con rimozione, frecce di direzione, targhe via, attraversamento pedonale | incrocio e Tamburino Sardo E | ~6 | C20 |
| A03 | palina della fermata bus | davanti al civ. 69 | 1 | C20 |
| A04 | armadio stradale grigio | Moravia, davanti a E06 | 1 | C06 |
| A05 | caditoie in ghisa a bordo carreggiata, chiusini in mezzeria | lungo i cordoli | – | – |

## Pavimentazioni e verde

| ID | Descrizione | Materiali |
|---|---|---|
| P01 | carreggiate in asfalto usurato, mezzeria bianca, strisce pedonali zebrate sull'incrocio (Tamburino Sardo e Menta) | C16 |
| P02 | marciapiedi ~1,5 m in **marmette di cls 40×40 a scacchiera** rosa salmone e beige, cordolo in cls h ~15 cm | C17, C18, C19 |
| P03 | lotto incolto all'angolo N, rialzato di ~1 m, prato secco e arbusti | – |
| P04 | terreno incolto a SO (fondale) | – |
| V01 | 2 palme a ventaglio (*Washingtonia*) h ~7 m nel giardino d'angolo di E09 | – |
| V02 | 2 palme da dattero (*Phoenix canariensis*) h ~4,5 m all'angolo di Via della Menta | – |
| V03 | canneto (*Arundo donax*) h ~3,5 m dietro R07 | – |
| V04 | olivi e agrumi nei giardini (E03, E09, E10) | – |
| V05 | siepi e rampicanti sulla sommità dei muri; bouganville su E05 | – |

## Palette (23 materiali-colore)
Vedi `palette.png` e `scheda.json › palette`. Riepilogo:

| C## | Materiale | Hex | Conf. | | C## | Materiale | Hex | Conf. |
|---|---|---|---|---|---|---|---|---|
| C01 | intonaco giallo paglierino | #F2D9AE | media | | C13 | intonaco crema | #E2DBC9 | media |
| C02 | cotto, copertine e gronde | #BF7E52 | media | | C14 | intonaco beige | #D4C3AA | media |
| C03 | tegole/coppi | #BE7B73 | bassa | | C15 | cls a vista | #B5A187 | bassa |
| C04 | intonaco bianco | #ECE5DA | alta | | C16 | asfalto | #AFA698 | media |
| C05 | alluminio bianco, doghe | #FAFAFA | media | | C17 | marmetta rosa | #E5C7B1 | bassa |
| C06 | acciaio grigio | #64696D | media | | C18 | marmetta beige | #F8E5C5 | bassa |
| C07 | intonaco salmone | #AE8260 | media | | C19 | cordolo cls | #D8D0C0 | bassa |
| C08 | intonaco pesca | #E5CDAF | media | | C20 | acciaio zincato | #ACB0B3 | media |
| C09 | intonaco rustico grigio | #796E5E | media | | C21 | fotovoltaico | #394A63 | media |
| C10 | blocchi cls a vista | #7E7463 | alta | | C22 | vetrata blu | #343B52 | bassa |
| C11 | grigio d'accento | #767771 | media | | C23 | rosso mattone | #68312E | bassa |
| C12 | pietra a opera incerta | #545252 | media | | | | | |

Nota: i colori sono campionati in **sole pieno**, quindi sono valori in luce. In ombra C01 vira a #C7A678
e C04 a #A7A9AB: non scurire i materiali in SketchUp per "imitare" l'ombra.

## Indice delle riprese
`_rif_google/manifest_riprese.json`: 19 riprese, tutte da pano Google ufficiali di aprile 2026, con
posizione, heading, pitch e fov per le scene di verifica in SketchUp.
SV-01 incrocio → E09 · SV-02/03/14 → E08/R02 · SV-04 → E11/R09 · SV-05 → E10/R10 · SV-06 → E06/R03 ·
SV-07 → E05/R04 · SV-08 → P03/R06 · SV-09 → E03/R05 · SV-10 → E02/R07 · SV-11 → E01/R08 ·
SV-12 → P03 + incrocio · SV-13 → dettaglio R01 · SV-15 → E09 · SV-16/17/18/19 → viste lungo le quattro
strade (Menta N, Tamburino SE, Tamburino NO, Moravia E).
