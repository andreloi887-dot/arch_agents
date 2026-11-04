# Materiali, colori e vocabolario

Usa termini precisi: l'agente SketchUp deve poter scegliere texture e dimensioni senza indovinare.

## Facciate
| Famiglia | Termini da usare | Cosa dichiarare |
|---|---|---|
| Intonaco | civile liscio, frattazzato fine/grosso, graffiato, a bugnato (liscio, rustico), a calce, tinteggiatura ai silicati, cappotto (spigoli vivi, nessuna modanatura) | colore C##, eventuale velatura/macchie, dimensione dei corsi del bugnato |
| Laterizio faccia vista | mattone pieno rosso/arancio/giallo paglierino, posa a correre, gotica, a fascia; giunto fugato, raso, arretrato; colore del giunto | formato (250×120×55 tipico, UNI 250×120×55 o "a mano"), modulo texture con giunto |
| Pietra | travertino, pietra serena, peperino, tufo, Luserna, Trani, granito, ciottoli; a opera incerta, a corsi, a lastre; bocciardata, levigata, a spacco | dimensione dei conci o lastre, giunti |
| Calcestruzzo | a vista, faccia a vista con fori dei distanziatori, cassero a tavole, prefabbricato a pannelli | modulo del cassero o del pannello |
| Rivestimenti | klinker, gres porcellanato, pannelli metallici (aggraffati, cassette), fibrocemento, legno a doghe, facciata ventilata | formato e passo dei giunti |
| Vetro | curtain wall a montanti e traversi, strutturale, vetro-mattone; riflettente, chiaro, satinato | passo dei montanti, colore dei profili |

## Coperture
Coppi, tegole marsigliesi, portoghesi, in cemento, ardesia, lamiera aggraffata/grecata (colore),
guaina ardesiata, terrazzo pavimentato, ghiaia, tetto verde. Lattonerie: rame, preverniciato,
zinco-titanio (colore). Dichiarare sempre lo sporto e se la gronda è a vista (travetti in legno)
o in cornicione.

## Aperture
- Serramenti: legno (naturale/verniciato), PVC, alluminio, ferro-finestra, legno-alluminio;
  partizioni (1, 2 ante, sopraluce, traversi).
- Oscuranti: persiane alla genovese (lamelle fisse/orientabili), alla romana, scuri interni o
  esterni, avvolgibili (cassonetto esterno/interno; colore del telo), frangisole, veneziane
  esterne, tende da sole (colore, a bracci o a caduta).
- Cornici: piatta, modanata, timpano, mostra in pietra; davanzale in pietra (sporgenza).

## Recinzioni
Muretto (cls, mattoni, pietra, intonacato) con copertina; cancellata in ferro battuto, a piatti, a
tondini, a grigliato elettrosaldato (maglia 62×132 tipica), pannelli in rete elettrosaldata
plastificata, rete a maglia sciolta con paletti a T, doghe in legno/composito, pannelli
frangivista, siepe (specie, altezza). Cancelli: a battente, scorrevoli; passo carraio.

## Arredo urbano
Lampioni (testa-palo, a frusta, a pastorale, storico in ghisa, a sospensione su fune), panchine
(seduta in legno/metallo, con o senza schienale), cestini, dissuasori (paletti in ghisa o acciaio,
panettoni in cls, archetti), fioriere, rastrelliere, pensiline bus, paline, segnaletica, cassonetti
e campane, colonnine di ricarica, armadi tecnici, idranti, chioschi, dehors.

## Pavimentazioni
Asfalto (nuovo nero / vecchio grigio con rappezzi), cubetti di porfido (posa ad archi contrastanti,
a coda di pavone), sampietrini/selci, lastre in pietra (Luserna, porfido a correre), masselli
autobloccanti, betonelle (40×40), calcestruzzo stampato o spazzolato, ghiaino lavato. Cordoli in
granito o cls, h ≈ 15 cm; scivoli; caditoie.

## Colore: campionamento
1. Scegli zone **in luce diffusa** (ombra portata uniforme o cielo coperto), lontane da riflessi e
   da macchie; evita il controluce.
2. Campiona la **mediana** su una finestra ampia (`annota.py campiona`) da almeno 2 riprese,
   meglio di date o ore diverse. Riporta `hex` (valore scelto) e `intervallo` (min/max).
3. Correzione: se nella stessa ripresa c'è un riferimento neutro affidabile (intonaco bianco già
   noto, cielo coperto), annota la dominante (calda/fredda) e correggi a giudizio; dichiaralo.
4. `ral_indicativo` solo come aiuto: le corrispondenze da foto sono approssimate. Un RAL certo
   richiede rilievo in sito con mazzetta.
5. Confidenza: alta = coerente su ≥ 2 riprese, luce diffusa; media = una sola ripresa buona o
   riprese discordi < ΔE 8; bassa = solo satellitare, controluce, distanza.

## Texture a scala reale (indicazioni per SketchUp)
Il `modulo_mm` della palette è la dimensione reale che la texture deve coprire in SketchUp:
- intonaco 1000×1000 (texture senza ripetizioni evidenti);
- mattone 250×55 + giunto 10 → modulo di una texture 4 corsi × 2 mattoni = 520×260;
- coppi ≈ 200 × 400 (passo sulla falda); marsigliesi ≈ 280 × 400;
- cubetti di porfido 8/10 ad archi: modulo dell'arco ≈ 1200;
- lastre: formato reale + giunto.
Il colore medio della texture deve stare vicino all'`hex` della palette (verificato in VERIFICA
con ΔE: vedi `05-verifica.md`).
