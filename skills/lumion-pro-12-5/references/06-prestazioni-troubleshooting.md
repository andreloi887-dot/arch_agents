# Prestazioni, file e troubleshooting (Lumion 12 / 12.5)

> Fonte: KB *What kind of computer does Lumion 12 need?*, *Which graphics card do you need for Lumion 12?*, *How can you improve performance within Lumion?*, *Reduce rendering times*, *Where are Projects and Imported Models saved*, *Backups*, *Transfer Projects to another PC*, *TdrDelay*, *NVIDIA driver 572.60+ known issue*, *Game-Ready or Studio drivers*, *Model invisible or black*, *Model far away*, *Model clipped in front of the camera*.

⚠️ **Lumion 12 non è più supportato ufficialmente** da Lumion: niente nuovi fix. Le soluzioni sono quelle documentate qui.

## Hardware (requisiti ufficiali Lumion 12)
- **Windows 10 1809+ o Windows 11 21H2+.** Consigliato Win10 2004+ con *Hardware-accelerated GPU scheduling* attivo. Il Mac non è supportato.
- **La GPU è il fattore principale**, poi la VRAM. Più schede in SLI o NVLink non accelerano: Lumion usa la GPU collegata al monitor su cui si apre. La grafica integrata non è supportata. Docking station ed eGPU non sono garantite.
- Livelli in punti PassMark G3D:

| Livello | PassMark GPU | VRAM | CPU single-thread | Esempi | Progetti |
|---|---|---|---|---|---|
| Minimo | ≥ 7.000 | 4 GB+ (6 GB per video 4K) | ≥ 2.000 | GTX 1660 Super, RTX 2060 | edificio singolo con contenuti Lumion, niente 3D Grass |
| Consigliato | ≥ 14.000 | 8 GB+ | ≥ 2.500 | RTX 3060/3070, RTX 2080, RX 6700 XT | casa grande con interni, parco o pezzo di città con OSM |
| High-end | ≥ 20.000 | 10 GB+ | ≥ 2.500 (meglio 3.500) | RTX 3080/3090, A5000/A6000 | città, interni multipiano dettagliati, Fine-detail Nature e 3D Grass |

- RAM: più ce n'è, più grandi sono le scene caricabili. SSD NVMe per progetti e libreria. Memoria virtuale (pagefile) **almeno 50 GB, 100–150 GB per progetti molto complessi**.
- Alimentatore adeguato alla GPU: spegnimenti o riavvii durante il render sono spesso colpa dell'alimentatore.

### Driver
- NVIDIA Game-Ready o Studio vanno bene entrambi, purché aggiornati.
- **RTX serie 5000 con Lumion 12**: interfaccia mostrata male con i driver dalla 572.60 in poi. **Risolto con il driver 576.52 o successivo.**
- AMD Navi: driver recenti. Alcune AMD serie 6000 hanno avuto problemi con certi oggetti.
- **TdrDelay**: se Windows chiude Lumion durante operazioni lunghe (texture 4K/8K, render pesanti), applica il fix di registro `TdrDelay_100.reg` della KB e riavvia.

## Ottimizzazione della scena
- Tieni d'occhio il **Performance Monitor** (in alto a destra: FPS, memoria, 3D Points, grafico dei tempi GPU e CPU). Arancione = smetti di aggiungere; rosso = intervieni subito.
- In editor:
  - *Editor Resolution* < 100% (`F7`);
  - qualità a 2–3 stelle;
  - **Use proxies** Auto oppure On;
  - alberi a bassa qualità (`F9`);
  - finestra o monitor a 1080p.
- Contenuti pesanti:
  - Fine-detail Nature solo dove la camera la vede;
  - spot e omni con ombre (preferisci Area o Fill dove basta);
  - 3D Grass e Foliage su aree grandi (meglio Landscape Grass);
  - texture 8–16K;
  - più di 5 video texture.
- Usa i **layer** per nascondere il pesante mentre lavori e riattivalo con *Layer Visibility* nelle foto.
- Progetti grandi: **file separati per interni ed esterni**; arredi interni solo dove si vedono.
- Durante il lavoro: anteprima delle Planar su None, *Preview spotlight GI* su Off.

## File, salvataggi, migrazione
- Progetto: `.LS12`, salvato a mano con *File › Save / Save as*. **Un file salvato in 12.5 non si apre in versioni precedenti** (12.0–12.3.1 incluse). Fix 12.5: il pulsante Save non resta più grigio dopo *Save As*.
- Modelli importati: `Documents\Lumion 12.5\Library` (4 file per modello: `.LIB`, `.LIB.MTT`, `.LIB.INN`, `.LIB.TXX`). Per spostarli altrove bisogna reindirizzare la cartella Documenti di Windows.
- **Recovery**: se Lumion si chiude male, alla riapertura dal menu Start propone il ripristino. **Non premere Discard.** **QuickSave** (`.LQF`, icona orologio nella schermata Load) quando apri un altro progetto senza salvare: recuperalo subito con *Save As*, perché viene sovrascritto.
- Buone pratiche: *Save As* con versioni numerate (`Progetto_v07.ls12`), backup di `Documents\Lumion 12.5`, Material Set salvati.
- **Altro PC**: il `.LS12` contiene già modelli e materiali. Per avere anche librerie e preferiti copia `GroupLibrary`, `Library`, `Materials` (in `Materials\Custom`), `Recent` e `Settings[versione].ini`. I filmati usati come *Clip from movie file* vanno copiati a parte.
- 12.5 è un'installazione separata: non installarla nella cartella di una versione precedente e non disinstallare la vecchia finché non hai migrato. Le versioni 12.x condividono le cartelle Documenti di Lumion 12.

## Problemi frequenti
| Sintomo | Causa | Soluzione |
|---|---|---|
| Modello invisibile o nero dopo l'import | lontano da 0,0,0, oppure Lumion non riesce a scrivere in `Documents\Lumion 12.5\Library` (antivirus, permessi, OneDrive) | sposta il modello all'origine nel CAD; dai a Lumion l'accesso ai Documenti / aggiungi un'esclusione in Defender |
| Modello lontano dal punto di inserimento | coordinate CAD lontane dall'origine | correggi nel CAD e reimporta; in alternativa Type-In o un gruppo con pivot spostato |
| Solo linee gialle, nessun modello | geometria assente, solo bordi | verifica l'export (facce, non solo linee) |
| Superfici capovolte o invisibili (SketchUp) | componenti annidati | *Explode* completo prima dell'export |
| Non riesci a selezionare una parte del modello | stesso materiale CAD | materiale distinto nel CAD e re-import |
| Materiali Lumion persi dopo il re-import | nomi dei materiali CAD cambiati, SKP/DAE alternati, DAE ArchiCAD sbagliato | ricarica un Material Set (`.MTT`) da una versione intatta |
| Ombre e superfici che tremano | distanza dall'origine o z-fighting | modello verso 0,0,0, superfici distanziate, *Flicker Reduction* minimo |
| Camera che taglia il modello | Near Clip automatico con camera alta sul terreno | alza il terreno sotto il modello, oppure effetto *Near Clip Plane* |
| Niente ombre del sole in editor | qualità 1 stella | `F2`–`F4` |
| Niente ombre degli spot | anteprima limitata | seleziona le luci (max 5) o tieni premuto `F8`; nel render ci sono |
| Luce che "passa" attraverso i muri | Fill o Area senza ombre | usa Spot oppure Omni con ombre |
| Erba non visibile in lontananza | fuori dall'area 2×2 km | progetto dentro il riquadro giallo |
| Crash o freeze al render | progetto troppo complesso per la VRAM, TDR | riduci contenuti ed effetti, TdrDelay, pagefile 100–150 GB, chiudi le altre app che usano la GPU |
| PC che si riavvia durante il render | alimentatore o temperatura | verifica alimentatore e raffreddamento |
| Video più scuro della foto | Hyperlight ridotto nei video | GI o luci di riempimento |
| Interfaccia corrotta con RTX 50xx | driver | NVIDIA 576.52 o successivo |
| Pixel quadrati in Print/Poster | render a tasselli + Sky Light/Real Skies | vedi 05 |

## Diagnostica
- Test con un progetto vuoto: se funziona, il problema è nel contenuto. Reimporta il modello a pezzi per isolare quello difettoso.
- Per il supporto: Diagnostics Report di Lumion, log errori e importer, msinfo32, HWiNFO (articoli KB in *Troubleshooting*).
