# Procedimento unico: dal progetto Edificius al video fotorealistico

Decisione del 2026-11-06. È la linea da seguire per ogni progetto, salvo diversa indicazione di Andrea.

**Obiettivo.** Prendere il progetto BIM fatto in Edificius e inserirlo nel contesto reale del lotto.
Poi produrre video fotorealistici di interni ed esterni con movimenti di camera cinematografici.
Andrea deve intervenire il meno possibile.

## La filiera

**Edificius → Contesto (Python) → Blender (assemblaggio) → Unreal Engine 5 (video) → montaggio automatico**

| Fase | Strumento | Chi | Ingresso → uscita |
|---|---|---|---|
| 1. Progetto BIM | Edificius | **Andrea** | progetto → `edificius/progetto.ifc`, con il punto base concordato |
| 2. Contesto del lotto | Motore Python (`skills/rilievo-urbano/`) | agenti | `lotto.json` → `contesto.json` + verifica |
| 3. Assemblaggio | Blender + Bonsai, senza interfaccia (`blender -b -P`) | agenti | IFC + `contesto.json` → scena `.blend` ed export USD |
| 4. Anteprima | Blender EEVEE | agenti → **Andrea approva** | immagini chiave e percorsi di camera in bassa qualità |
| 5. Render video | Unreal Engine 5: Lumen, Sequencer, Movie Render Queue | agenti | USD → sequenze EXR/PNG |
| 6. Montaggio | FFmpeg | agenti | sequenze → MP4 H.264, con titoli, dissolvenze e musica |

**Interventi di Andrea:**
1. export IFC da Edificius;
2. approvazione delle anteprime;
3. visione del video finale.

## Cosa fa ogni fase

### 1. Edificius (Andrea)
- Alla creazione del progetto: impostare come **punto base** l'origine indicata dagli agenti per quel lotto.
  È la scelta più difficile da cambiare dopo.
- Gli arredi degli interni vanno messi come **ingombri semplici**, con la classe IFC corretta
  (IfcFurniture ecc.). Gli agenti li sostituiscono con modelli di qualità presi dalle librerie.
- Export IFC4: classi corrette, materiali con nomi chiari, piani con quote reali.

### 2. Contesto (agenti)
- Ingresso: `lotto.json` con coordinate, foglio/particella, raggio dell'area e livello di dettaglio.
- Fonti per la Sardegna:
  - DTM e DSM LiDAR 1 m della Regione;
  - catasto AdE (WMS);
  - Database Geotopografico regionale (*da verificare*);
  - riprese Street View solo per descrivere e confrontare, mai per ricavare geometria.
- Altezze degli edifici: DSM − DTM sulla sagoma, con tetti approssimati.
- Dettaglio per distanza: alto per il lotto e i fronti visibili, LOD1 neutro per lo sfondo.
- Nessuna eccezione scritta a mano per il singolo lotto. Le regole sono generali: marciapiedi,
  muri di confine, raccordi agli angoli tra strade a pendenza diversa.
- Uscita indipendente dal software: `contesto.json`, più gli esportatori (IFC verso Edificius, se serve
  il contesto anche lì; Blender; SketchUp solo per controlli).

### 3. Assemblaggio in Blender (agenti)
- Importa l'IFC di Edificius con Bonsai, mantenendo classi e piani.
- Costruisce il contesto da `contesto.json`, nella stessa origine.
- Materiali PBR dalla **libreria materiali di studio**, assegnati per classe IFC e nome del materiale.
- Vegetazione con Geometry Nodes, luci degli interni, sole reale (posizione georeferenziata, data e ora
  scelte).
- Percorsi di camera generati in automatico:
  - camminata ad altezza d'occhio lungo le strade;
  - giro con il drone attorno al lotto;
  - avvicinamento all'ingresso;
  - percorsi negli interni stanza per stanza.
- Export **USD** verso Unreal.

### 4. Anteprima (agenti → Andrea)
- EEVEE: immagini chiave e video dei percorsi in bassa qualità, pochi secondi per fotogramma.
- Gli agenti fanno un primo controllo da soli: compenetrazioni, buchi, materiali mancanti, camere
  dentro i muri.
- Andrea approva o chiede modifiche ai percorsi e ai materiali.

### 5. Video in Unreal Engine 5 (agenti)
- Import USD, Lumen con ray tracing hardware (Quadro RTX 6000, 24 GB), sole e cielo reali.
- Sequencer con i percorsi approvati: fuoco, motion blur, velocità costanti.
- Movie Render Queue avviata da riga di comando, uscita in sequenza di immagini: se il calcolo
  si interrompe, riparte dall'ultimo fotogramma.
- Path tracer solo per singole immagini fisse di altissima qualità.
- Librerie: Fab/Megascans per arredi, vegetazione e materiali fotografici.

### 6. Montaggio (agenti)
- FFmpeg: sequenze → MP4 H.264, con dissolvenze, titoli e musica.

## Esclusi, e perché
| Software | Motivo |
|---|---|
| SketchUp | Usato nel test di Via della Menta, non serve nella filiera. Lo script resta per controlli rapidi |
| 3ds Max, V-Ray, Corona | Ottimi per le immagini fisse, troppo lenti per i video, con licenze in più |
| Lumion, Enscape | Si usano a mano, senza automazione: contrario all'obiettivo |
| ComfyUI (`skills/comfy-desktop-arch-render/`) | Nei video cambia i dettagli tra un fotogramma e l'altro e non rispetta fedelmente il progetto. Al massimo ritocco di immagini fisse |

## Da preparare una volta sola
- [x] Installare Blender con Bonsai (5.2 + 0.9.0), Unreal Engine 5 (5.8; licenza da verificare in base al
      fatturato dello studio) e FFmpeg.
- [x] In Blender: *Preferences › System › Cycles Render Devices › OptiX*, con la Quadro spuntata.
- [ ] Libreria materiali di studio: pavimenti, legni, intonaci, metalli, tessuti, con la corrispondenza
      materiale Edificius → materiale PBR.
- [x] Generalizzare il motore del contesto (2026-11-07): gli script sono in `skills/rilievo-urbano/scripts/contesto/`,
      i valori del singolo lotto in `lotto.json` nella cartella del modello. Su Via della Menta dà geometria identica.
- [x] Dati di un lotto nuovo in automatico (2026-11-07): `prepara_lotto.py` scarica catasto e DTM e scrive `lotto.json`.
      La scheda (altezze, materiali, arredo) la completa l'agente rilievo-urbano.
- [ ] Prova del motore su un secondo lotto.
- [ ] Scrivere gli agenti e le skill per l'assemblaggio in Blender e per i video in Unreal.
- [ ] Prova completa su un progetto vero.

## Stato
- Fase 2 provata su Via della Menta / Via Tamburino Sardo (Cagliari). La pipeline funziona in SketchUp
  2025; il motore è generico e legge `lotto.json`, ma non è ancora stato provato su un secondo lotto.
- Installati: Blender 5.2 + Bonsai 0.9.0, Unreal Engine 5.8, FFmpeg.
- Fasi 3–6 ancora da costruire.
