# Render e output (Lumion 12 / 12.5)

> Fonte: KB *Output Quality setting in Movie and 360 Panorama Modes*, *Render all Photos in one go*, *Image Sequence*, *Higher resolution than Poster*, *Motion Blur in Print/Poster*, *Movies darker than Photos*, *Shadows/lighting flicker*, *Panorama render settings*, *Square Pixels artifacts*, *DPI*, *MyLumion Phasing Out*, release notes 12.0/12.3/12.5.

## Photo Mode
- Risoluzioni (16:9): **Email** 1280×720, **Desktop** 1920×1080, **Print** 3840×2160, **Poster** 7680×4320. Gli altri formati (verticale, 1:1, 3:2...) sono nativi solo dalla 2023: nella 12.5 si fa il **crop in post-produzione**.
- Fino a 10 viste per set (`Ctrl+1…0`) e più **Photo Set**. **Dalla 12.3 / 12.3.1 si possono renderizzare più set o una selezione di foto in un colpo solo** (Select Current, Select All, spunta per singola foto): è il batch notturno.
- Render pass in uscita: profondità, normali, sky alpha, material ID, illuminazione e riflessioni. Sono utili per le maschere in Photoshop (sostituzione del cielo, correzioni selettive).
- Il DPI non si imposta in Lumion: calcola i pixel necessari (A4 o Letter a 300 DPI ≈ 2550×3300) e imposta il DPI in post.
- **Oltre il Poster**: render PNG o BMP non compresso, con Print/Poster Enhancer, poi upscaling esterno (Topaz Gigapixel, PhotoZoom, SmillaEnlarger).
- **Pixel quadrati** nei render Print e Poster (succede nel render a tasselli, soprattutto con Sky Light e Real Skies insieme). Possibili rimedi:
  - Print/Poster Enhancer;
  - Sky Light su **High**;
  - Hyperlight più basso ed Exposure più alta;
  - SpeedRay spente;
  - Sky and Clouds al posto di Volume Clouds;
  - render 4K da Movie Mode con Image Sequence;
  - render 1080p e upscaling.

## Movie Mode
- **Output Quality (Lumion 12)**:
  - 1 stella: tutto attivo, senza antialiasing;
  - 2 stelle: AA 4×;
  - 3 stelle: AA 8×;
  - 4 stelle: AA 16×.
  Le trasparenze hanno rispettivamente 4, 8 e 16 livelli.
- Risoluzioni video: 640×360, 1280×720, 1920×1080, 2560×1440, 3840×2160. Il 4K richiede almeno 6 GB di VRAM.
- Ease In/Ease Out è lineare di default dalla 12.0. La lunghezza delle clip è arrotondata al secondo. `Spazio` sulla timeline = anteprima.
- **Image Sequence**: *Render Clip/Movie › Image Sequence › Frame Range*. È consigliata per render lunghi: se si blocca, riprendi dal frame. Serve anche per estrarre un fotogramma 4K con Motion Blur, che **non funziona in Print e Poster**.
- Più foto come fotogrammi chiave: si renderizzano i keyframe come immagini (30 clip per set, fino a 99 keyframe per clip).
- **FPS**: 30 dimezza i tempi rispetto a 60. 60 serve solo per panoramiche veloci. Alternativa: render a metà durata e interpolazione con AI (Flowframes, RIFE).
- **Animazioni**:
  - *Move*, *Advanced Move* (interfaccia nuova in Lumion 12, keyframe trascinabili; fix 12.5: niente loop quando è attivo *Use clip length*);
  - *Mass Move* (percorsi per auto e persone);
  - *Animated Phasing* (preset per la costruzione dell'edificio);
  - *Layer Visibility* animato;
  - *Sun / Sun Study* animati sull'ora;
  - *Advanced Move* sul **Clip Plane** per sezioni che avanzano.
- **Camminata a livello occhi**: *Set eye level* posiziona la camera a 1,60 m sul modello o sul terreno.

### Sfarfallio nei video
- **Ombre che tremano**: il modello è lontano da 0,0,0. Raggruppa e sposta il gruppo verso l'origine, o meglio correggi nel CAD.
- **Luce che pulsa**: Global Illumination con sole o oggetti animati. Usa 4 stelle, scena statica e Wind basso.
- **Video più scuri delle foto**: Hyperlight ha un raggio ridotto nei video. Aggiungi GI o luci di riempimento.

## 360 Panorama
- Lumion 8–12: *Target Device* **Generic** (equirettangolare, per la maggior parte dei visori e delle app, incluso Oculus TV) oppure **GearVR/Oculus** (cubico side-by-side).
- **Stereoscopic**: due render (occhio sinistro e destro), tempi circa doppi. L'IPD si cambia solo per i bambini.
- **Horizontal Slices**: più fette = qualità e tempi maggiori. Con oggetti vicini alla camera tieni le fette alte, altrimenti compaiono giunte.
- Camera a circa 1,6 m. Hyperlight e Sky Light non sono disponibili nei panorami.
- ⚠️ **MyLumion viene dismesso: chiude a dicembre 2026** e da Lumion 2026 non è più accessibile. Non usarlo per consegne nuove: esporta i panorami e pubblicali con un viewer 360° proprio o di terze parti.

## Tempi di render: cosa pesa
In ordine di impatto:
- numero e peso dei modelli (3D Points);
- texture grandi;
- **Sky Light e Hyperlight**;
- numero di piani Planar (e Sky Light attivo nelle Planar);
- spot con ombre **Dynamic**;
- spot selezionati nella GI;
- superfici grandi con 3D Grass o Foliage;
- video texture.

Leve in uscita: qualità più bassa, FPS più bassi, risoluzione più bassa con upscaling.

## Specifiche consigliate
| Uso | Impostazione |
|---|---|
| Test e iterazioni | Desktop, oppure Email a 1–2 stelle |
| Tavola A1 o concorso | Print con Enhancer + upscaling, Poster solo con molta VRAM (≥ 10–12 GB) |
| Web e social | Desktop + crop (1080×1350, 1:1) |
| Video presentazione | 1920×1080, 30 fps, 3–4 stelle, Image Sequence |
| VR | panorama Generic, stereo se serve la profondità |
