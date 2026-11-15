# Programma degli interni: dall'IFC di Edificius alle immagini di anteprima

Scritto il 2026-11-15 sulla villa A di Via della Menta. È la parte "interni" delle fasi 3 e 4 di
[PROCEDIMENTO.md](PROCEDIMENTO.md): chi riprende il lavoro parte da qui.

**Stato.** La villa A è completa come anteprima: finiture, porte, controsoffitto, arredi, viste con luce vera.
Ville B, C, D: ferme per scelta di Andrea (2026-11-15), si riprendono quando la A è approvata.

## 1. Cosa serve da Andrea

| Cosa | Dove va | Note |
|---|---|---|
| IFC4 di Edificius con i vani (IfcSpace) nominati | `rilievi/<zona>/edificius/progetto.ifc` | porte e finestre comprese; gli arredi non servono |
| Planimetria PDF **vettoriale** con gli ingombri degli arredi colorati | allegata in chat | giallo e arancio pieni; un rettangolo per mobile |
| Risposte alle domande sotto | `lotto.json → progetto_ifc → finiture`, `arredi.json` | una volta per progetto |

Domande da fare subito, tutte insieme (sulla villa A sono arrivate una alla volta e ogni risposta ha richiesto un giro):
1. **Soffitti**: piani o a falde? Struttura a vista? Sezioni e passo di travi e travetti, colore.
2. **Pavimenti**: prodotto, formato, direzione di posa, fughe; uguale in tutte le stanze? Sempre continuo tra le stanze.
3. **Battiscopa**: materiale, altezza, vani esclusi.
4. **Porte interne**: stile, colore, coprifilo; ci sono scorrevoli a scomparsa?
5. **Controsoffitti e impianti a vista**: dove, a che quota, faretti, griglie, bocchette, split.
6. **Arredi**: stile in tre parole; pezzi obbligati; dove va il tavolo e per quanti posti; cosa non deve stare davanti alle porte.
7. **Cucina**: elettrodomestici voluti, a vista o a scomparsa.

## 2. Ambiente (sessione cloud)

```bash
pip install bpy==5.2.4 ifcopenshell shapely usd-core matplotlib
```

```bash
apt-get install -y libegl1 libgl1-mesa-dri libegl-mesa0 libgles2 poppler-utils
```

Blender gira come modulo Python, senza interfaccia. EEVEE su CPU non calcola le ombre: per giudicare un interno si
usa **Cycles su CPU** (circa 55 s per un'immagine 960×540 a 32–40 campioni). Unreal e la scheda grafica sono solo sul
PC di Andrea.

## 3. Sequenza

`S=skills/rilievo-urbano/scripts/blender`, `M=rilievi/<zona>/modello`. Ogni script scrive un log in `$M/uscita_blender/`.

| # | Comando | Cosa fa | Tempo |
|---|---|---|---|
| 1 | `python $S/controlli/apri.py $M/uscita_blender/contesto.blend $S/importa_progetto.py -- $M` | IFC nella scena del contesto: elementi, vani nascosti, dati delle porte (verso di apertura) | 20 s |
| 2 | `python $S/finiture_interni.py -- $M --blend contesto_progetto.blend` | pavimento, battiscopa, porte, controsoffitto, perlinato e orditura | 10 s |
| 3 | `python $S/controlli/arredi_da_pdf.py planimetria.svg $M <villa> bozza.json` | ingombri dalla planimetria (prima: `pdftocairo -svg`) | 5 s |
| 4 | completare `arredi.json`: tipo di ogni ingombro, stile, zona giorno | a mano, leggendo misure e posizione | – |
| 5 | `python $S/arredi_interni.py -- $M --blend contesto_progetto.blend` | mobili parametrici, cucina a moduli, divano e tavolo | 3 s |
| 6 | `python $S/percorsi_camera.py -- $M --blend contesto_progetto.blend --solo interni --villa 1` | percorso stanza per stanza e luci → `scena_percorsi.blend` | 5 s |
| 7 | `python $S/controlli/pianta_arredi.py $M/uscita_blender/contesto_progetto.blend 1 pianta.png` | pianta con arredi, porte e battute delle ante | 3 s |
| 8 | `python $S/controlli/viste.py $M/uscita_blender/scena_percorsi.blend <cartella> 32 nome:x,y,h,tx,ty,th[,focale] ...` | viste Cycles da un punto verso un bersaglio (h = altezza sul pavimento) | 55 s l'una |
| 9 | `python $S/esporta_usd.py -- $M --blend scena_percorsi.blend` | USD per Unreal | 30 s |

I passi 2, 5 e 6 si possono rilanciare: cancellano e rifanno le proprie collezioni (`PRG_Finiture`, `PRG_Arredi`).
Dopo il passo 1 vanno rifatti tutti.

## 4. Dove stanno i valori

- **`lotto.json → progetto_ifc → finiture`**: `soffitto` (colore, doga, `travetti`: sezione, interasse, trave d'incontro,
  arretro sopra gli infissi), `pavimento` (colore, formato, fuga, `per_vano`), `battiscopa`, `porte`, `controsoffitto`.
  I predefiniti sono in `PRED` dentro `finiture_interni.py`.
- **`arredi.json`**: `stile` (colori), `arredi` (un ingombro per mobile, con `tipo`), voce `zona_giorno`
  (`posti_tavolo`, `distanza_porte_m`, `tavolo_contro_vano`).
- Nessun valore del singolo progetto dentro gli script.

## 5. Regole fissate da Andrea (villa A, 2026-11-15)

**Tetto in legno a vista**
- Una trave lungo ogni colmo, displuvio e compluvio; i travetti delle due falde vi arrivano nello stesso punto, alla
  stessa quota (incastro a coda di rondine).
- Passo e sezione dei travetti identici ovunque (70 cm, 10×16; travi d'incontro 14×22). La differenza di misura va in
  un solo campo di compensazione, al centro di ogni campata.
- Un travetto non appoggia mai sopra un infisso: si ferma 25 cm prima su una trave perpendicolare della stessa
  sezione, che scarica sui travetti ai due lati.
- Perlinato e travi avorio chiaro (#EFE8D6).

**Pavimento e battiscopa**
- Marazzi Room Beige 100×100, fughe parallele ai muri, mai in diagonale.
- Una superficie continua in tutta la casa: nessuna soglia o riga sotto le porte.
- Battiscopa dello stesso gres, 7 cm, ovunque tranne nei bagni.

**Porte**
- Moderne, anta liscia, coprifilo discreto (5 cm, piatto).
- Versi di apertura come in planimetria. Stanno nell'IFC: l'anta apre verso +y locale, cerniera a x = larghezza,
  oppure a x = 0 se `IFC_Pset_Geometria → Inverti (dx/sx)` è vero (verificato su 9 porte).
- In cucina doppia scorrevole a scomparsa.
- Le ante si vedono, aperte: non si nascondono per far passare la camera.

**Disimpegno e clima**
- Controsoffitto in cartongesso a 2,40 m con faretti LED tondi a incasso e griglie di ripresa: sopra c'è la macchina.
- Una bocchetta di immissione in ogni stanza, sopra la porta. *Ipotesi da confermare*: quota 2,45–2,60 m, bagni esclusi.

**Arredi**
- Stile caldo, naturale, minimale: rovere chiaro, laccato avorio, lino, un accento terracotta.
- Ingombri dalla planimetria; il resto (divano, tavolino, tavolo, sedie) lo dispone lo script.
- Tavolo da 4 allungabile, addossato al muro tra soggiorno e camera singola; parete TV, divano e tavolino spostati
  verso la vetrata di quanto serve. Passaggio libero davanti alla porta del disimpegno.
- Cucina: frigo, colonna forno e microonde, lavello, lavastoviglie, piano cottura con cappa, pensili.

## 6. Controlli prima di mostrare qualcosa ad Andrea

1. Log senza `AVVISO` nuovi (`finiture_interni.log`, `arredi_interni.log`, `percorsi.log`).
2. Pianta arredi: nessun mobile nelle battute delle ante, tavolo e divano dove chiesto.
3. Una vista Cycles per stanza, guardata davvero: porte, battiscopa, soffitto, mobili che non bucano muri o tetto.
4. Le immagini si mandano con l'elenco di ciò che non va ancora. Mai dire "fatto" senza averle guardate.

## 7. Limiti noti

- **Tetto**: nell'IFC sette linee d'incontro della villa A non sono a 45° con falde di pari pendenza. Lì passo costante
  e incontro esatto dei travetti non stanno insieme: va corretto il tetto in Edificius.
- **Muri interni**: alcuni non arrivano al tetto; sopra la porta della cucina si vede il vano accanto.
- **Pensili della cucina**: alti fino a 2,15 m, non controllano la quota della falda.
- **Mobili**: volumi parametrici. Vanno bene armadi, cucina e parete TV; divano, sedie, letti e tessili sono da
  sostituire con modelli di libreria (Poly Haven ha poco di moderno: Fab/Megascans in Unreal).
- **Materiali**: procedurali di Blender; in Unreal vanno rifatti dalla libreria di studio. Il gres esce troppo chiaro.
- **Percorso di camera**: nato per le stanze vuote. Controlla gli ostacoli solo ad altezza d'occhio, guarda spesso
  un muro, e ha 12 avvisi di passaggio stretto. Le viste fisse del passo 8 rendono meglio.
- **Video interno**: non rifatto dopo arredi e porte. In Cycles su CPU sono circa 30 ore: va fatto in Unreal.

## 8. Prossimi passi, in ordine

1. Giudizio di Andrea sulle viste della villa A; correzioni.
2. Percorso interno ripensato sui mobili: una o due inquadrature per stanza, movimenti lenti tra punti scelti.
3. Tarare esposizione e colori su una foto di riferimento del gres e del legno.
4. Correzione del tetto in Edificius (Andrea) e nuovo IFC.
5. Ville B, C, D: stesse regole, più ingressi e scale.
6. Unreal sul PC di Andrea: import USD, materiali e arredi di libreria, Sequencer, Movie Render Queue.
7. Contesto esterno dalle foto del sopralluogo.
8. Trasformare questo programma in una skill con il suo agente.

## 9. Livello di modello

Decisioni su regole, disposizioni e letture dell'IFC: sessione principale. Rilanci, estrazioni e controlli di log:
direttamente, sono compiti piccoli. Niente livello 0 sui contenuti tecnici.
