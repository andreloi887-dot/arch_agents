# Impostazione del progetto

## Checklist iniziale
1. **Dati generali**: committente, ubicazione (serve a TerMus e al sole nei render), orientamento nord.
2. **Unità**: metri/centimetri coerenti con i collaboratori; precisione quote.
3. **Piani (livelli)**: crea tutti i piani con quota di riferimento e altezza d'interpiano reali
   (es. P.T. ±0.00, P1 +3.10). Piani interrati e copertura inclusi. Le altezze di muri e pilastri si
   agganciano ai piani: cambiare un interpiano dopo aggiorna tutto, *se* gli oggetti sono vincolati.
4. **Fili fissi / griglia** se c'è una maglia strutturale (agevola il passaggio a EdiLus).
5. **Stili/tipologie** (muri, solai, coperture, infissi) con stratigrafia e materiali reali: sono la
   base di computo (PriMus) e trasmittanze (TerMus). Nomi parlanti: `MU_EST_TamponamentoCappotto_42`.
6. **Template di studio**: salva un file vuoto con piani tipo, stili, cartigli e impostazioni di stampa.

## Organizzazione
- Un file per edificio; più edifici o grandi lotti → valuta file separati collegati via IFC/usBIM.
- Stato di fatto vs progetto: usa l'ambiente **Gialli e Rossi** (demolisci, ricostruisci, trasforma
  oggetti da esistenti a nuovi, confronto dinamico tra i modelli e tavole di confronto) invece di
  duplicare file.
- Tempi: l'ambiente **4D-Gantt** associa la proprietà tempo agli oggetti (WBS, attività, timeline in 3D).
- Salvataggi versionati e backup automatico attivo; per il lavoro di gruppo usa la modalità
  collaborativa "classic for usBIM" (semaforo verde/giallo/rosso, vedi 00-versione-novita.md).
  Pianifica chi modella scale, tetti e rampe: sono operazioni esclusive, bloccate in giallo.

## Errori da evitare
- Modellare tutto sul piano terra spostando gli oggetti in Z a mano.
- Stili generici "Muro 30" senza stratigrafia: abachi e computo inutilizzabili.
- Importare DWG enormi come base senza pulirli (layer inutili, blocchi annidati, coordinate lontane).
