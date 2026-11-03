# Render e realtà virtuale

## RTBIM (real-time integrato)
- Render in tempo reale collegato al modello: modifiche a materiali/oggetti si riflettono subito.
- Ordine: ubicazione e nord corretti → materiali (diffuso, rugosità, riflessione) → luci artificiali
  → camere → impostazioni qualità → output immagine/video/360.
- Usa il real-time per scegliere camera e luce, poi il render finale ad alta qualità.

## AIrBIM e render AI
- AIrBIM: rendering assistito da AI su base modello. Nelle ultime release c'è anche l'integrazione
  con il generatore di render AI di usBIM (codesign). Utile per concept e varianti di stile: controlla
  sempre che l'AI non inventi elementi architettonici non presenti nel progetto.
- Requisiti indicativi pubblicati da ACCA per RTBIM/AIrBIM: GPU ≥ ~20.000 punti PassMark (classe RTX
  4070 / RX 7800 XT), ≥16 GB RAM; GPU Intel ARC non compatibili con AIrBIM. Verifica la pagina
  requisiti aggiornata.

## VRiBIM
- Navigazione VR immersiva del modello per presentazioni al committente; verifica i visori supportati.

## Consigli
- Materiali con texture in scala reale; evita superfici coplanari (z-fighting).
- Alleggerisci oggetti ad alto numero di poligoni prima dei video.
