/*
 * Percorso guidato dallo scorrimento.
 * La scena resta ferma a tutto schermo mentre la sezione scorre: l'avanzamento
 * (0–1) sceglie il fotogramma da disegnare sulla tela e le didascalie da mostrare.
 * Si usano fotogrammi singoli e non un video perché lo spostamento a mano dentro
 * un video è a scatti su molti telefoni.
 */
(function () {
  "use strict";
  var S = window.SITO;
  var C = window.PERCORSO || {}; // la pagina dice quale percorso mostrare: { dati, ferma }
  var P = C.dati || {};
  var $ = function (id) { return document.getElementById(id); };
  var sezione = $("percorso"), tela = $("percorso-tela");
  var ctx = tela.getContext("2d");

  var N = P.fotogrammi > 0 && P.cartella ? P.fotogrammi : 0;
  var ridotto = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var telefono = !!P.cartella_telefono && matchMedia("(max-width: 50rem)").matches;
  var cartella = telefono ? P.cartella_telefono : P.cartella;

  function indirizzo(i) {
    return cartella + "/" + String(i + 1).padStart(4, "0") + "." + (P.estensione || "webp");
  }
  function limita(v, a, b) { return Math.min(b, Math.max(a, v)); }

  /* ---------- Copertina ferma: niente fotogrammi fuori bozza, o movimento ridotto ---------- */
  if (ridotto || (!N && !S.bozza)) {
    sezione.classList.add("fermo");
    var fermo = C.ferma || (N ? indirizzo(0) : null);
    if (fermo) tela.style.backgroundImage = 'url("' + encodeURI(fermo) + '")';
    else tela.classList.add("vuota");
    return;
  }

  sezione.style.setProperty("--schermate", P.schermate || 7);
  $("percorso-invito").hidden = false;
  $("percorso-salta").hidden = false;
  if (!N) $("percorso-nota").hidden = false;

  /* ---------- Didascalie ---------- */
  var tappe = (P.tappe || []).map(function (t, i) {
    var d = document.createElement("div");
    var cartello = t.tipo === "cartello"; // pannello a tutto schermo che sale e copre la scena
    d.className = cartello ? "cartello" : "tappa" + (t.lato === "destra" ? " destra" : "");
    if (cartello && t.numeri && t.numeri.length) {
      var dl = document.createElement("dl");
      t.numeri.forEach(function (x) {
        var c = document.createElement("div"), dt = document.createElement("dt"), dd = document.createElement("dd");
        dt.textContent = x.valore == null || x.valore === "" ? "–" : x.valore;
        dd.textContent = x.etichetta;
        c.appendChild(dt); c.appendChild(dd); dl.appendChild(c);
      });
      d.appendChild(dl);
    }
    if (!cartello) {
      var n = document.createElement("p");
      n.className = "tappa-numero";
      n.textContent = String(i + 1).padStart(2, "0") + " / " + String(P.tappe.length).padStart(2, "0");
      d.appendChild(n);
    }
    var h = document.createElement("h2");
    h.textContent = t.titolo;
    d.appendChild(h);
    if (t.testo) { var p = document.createElement("p"); p.textContent = t.testo; d.appendChild(p); }
    $("tappe").appendChild(d);
    return { da: t.da, a: t.a, nodo: d, cartello: cartello };
  });
  var titolo = $("copertina-testo"), barra = $("percorso-avanzamento");

  function aggiornaTesti(p) {
    var fine = P.fine_titolo || 0.1;
    var o = limita(1 - p / fine, 0, 1);
    titolo.style.opacity = o;
    titolo.style.transform = "translateY(" + (-(1 - o) * 40) + "px)";
    titolo.style.visibility = o === 0 ? "hidden" : "visible"; // i bottoni spariti non devono restare cliccabili
    tappe.forEach(function (t) {
      var sfuma = Math.min(t.cartello ? 0.05 : 0.035, (t.a - t.da) / 3);
      var v = limita(Math.min((p - t.da) / sfuma, (t.a - p) / sfuma), 0, 1);
      if (t.cartello) {
        // sale dal basso, resta, poi prosegue verso l'alto e scopre la scena successiva
        var y = p < (t.da + t.a) / 2 ? (1 - v) * 100 : -(1 - v) * 100;
        t.nodo.style.transform = "translateY(" + y + "%)";
        t.nodo.style.visibility = v === 0 ? "hidden" : "visible";
        return;
      }
      t.nodo.style.opacity = v;
      t.nodo.style.transform = "translateY(" + (p < (t.da + t.a) / 2 ? (1 - v) * 30 : -(1 - v) * 30) + "px)";
    });
    barra.style.transform = "scaleX(" + p + ")";
  }

  /* ---------- Fotogrammi ---------- */
  var immagini = new Array(N), pronte = new Array(N);
  function caricaTutti() {
    // Prima una passata rada (1 su 16), poi via via più fitta: il percorso
    // è scorribile quasi subito e si raffina mentre il resto arriva.
    var ordine = [], visti = {};
    [16, 8, 4, 2, 1].forEach(function (passo) {
      for (var i = 0; i < N; i += passo) if (!visti[i]) { visti[i] = true; ordine.push(i); }
    });
    var prossimo = 0, insieme = 6;
    function avanti() {
      if (prossimo >= ordine.length) return;
      var i = ordine[prossimo++], im = new Image();
      im.decoding = "async";
      im.onload = function () { pronte[i] = true; ridisegna = true; avvia(); avanti(); };
      im.onerror = avanti;
      im.src = indirizzo(i);
      immagini[i] = im;
    }
    for (var k = 0; k < insieme; k++) avanti();
  }
  function piuVicino(i) {
    for (var d = 0; d < N; d++) {
      if (pronte[i - d]) return immagini[i - d];
      if (pronte[i + d]) return immagini[i + d];
    }
    return null;
  }
  function disegnaFotogramma(p, w, h) {
    var im = piuVicino(Math.round(p * (N - 1)));
    if (!im) return;
    var s = Math.max(w / im.naturalWidth, h / im.naturalHeight); // riempie la tela, come object-fit: cover
    var lw = im.naturalWidth * s, lh = im.naturalHeight * s;
    ctx.drawImage(im, (w - lw) / 2, (h - lh) / 2, lw, lh);
  }

  /* ---------- Segnaposto: una fuga di stanze in prospettiva ---------- */
  function disegnaSegnaposto(p, w, h) {
    var cielo = ctx.createLinearGradient(0, 0, 0, h);
    cielo.addColorStop(0, "rgb(" + Math.round(201 - 150 * p) + "," + Math.round(143 - 80 * p) + "," + Math.round(107 - 50 * p) + ")");
    cielo.addColorStop(1, "#1f3329");
    ctx.fillStyle = cielo;
    ctx.fillRect(0, 0, w, h);

    var passo = 5, lungo = 60, cam = p * (lungo - 12);
    var f = Math.max(w, h) * 0.55;
    var cx = w / 2 + Math.sin(p * 9) * w * 0.05, cy = h * 0.5 + Math.cos(p * 7) * h * 0.02;
    function telaio(z) {
      var s = f / Math.max(z - cam, 0.25);
      return { s: s, x0: cx - 3.6 * s, x1: cx + 3.6 * s, y0: cy - 1.4 * s, y1: cy + 1.6 * s };
    }
    ctx.lineWidth = Math.max(1, w / 900);
    var prima = null;
    for (var z = Math.floor(cam / passo) * passo; z <= lungo; z += passo) {
      var t = telaio(z), lontano = limita(1 - (z - cam) / 34, 0, 1);
      if (z - cam > 0.25) {
        ctx.strokeStyle = "rgba(169, 201, 180," + 0.85 * lontano + ")";
        ctx.strokeRect(t.x0, t.y0, t.x1 - t.x0, t.y1 - t.y0);
        // una porta su un lato, alternata, per dare il senso degli ambienti
        var lato = (z / passo) % 2 ? t.x0 : t.x1 - 1.1 * t.s;
        ctx.fillStyle = "rgba(233, 201, 160," + 0.16 * lontano + ")";
        ctx.fillRect(lato, t.y1 - 2.2 * t.s, 1.1 * t.s, 2.2 * t.s);
      }
      if (prima) {
        ctx.strokeStyle = "rgba(169, 201, 180," + 0.45 * lontano + ")";
        ctx.beginPath();
        [["x0", "y0"], ["x1", "y0"], ["x0", "y1"], ["x1", "y1"]].forEach(function (c) {
          ctx.moveTo(prima[c[0]], prima[c[1]]); ctx.lineTo(t[c[0]], t[c[1]]);
        });
        ctx.stroke();
      }
      prima = t;
    }
    // fughe del pavimento
    for (var g = Math.ceil(cam + 0.3); g <= lungo; g++) {
      var q = telaio(g);
      ctx.strokeStyle = "rgba(246, 241, 231," + 0.14 * limita(1 - (g - cam) / 22, 0, 1) + ")";
      ctx.beginPath(); ctx.moveTo(q.x0, q.y1); ctx.lineTo(q.x1, q.y1); ctx.stroke();
    }
  }

  /* ---------- Ciclo: lo scorrimento fissa la meta, il disegno la insegue ---------- */
  var meta = 0, attuale = 0, ridisegna = true, inCorso = false, larg = 0, alt = 0;

  function misura() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = Math.round(tela.clientWidth * dpr), h = Math.round(tela.clientHeight * dpr);
    if (w !== larg || h !== alt) { tela.width = larg = w; tela.height = alt = h; ridisegna = true; }
  }
  function leggiScorrimento() {
    var r = sezione.getBoundingClientRect();
    var corsa = r.height - window.innerHeight;
    meta = corsa > 0 ? limita(-r.top / corsa, 0, 1) : 0;
    avvia();
  }
  function passo() {
    var diff = meta - attuale;
    if (Math.abs(diff) > 0.0004) { attuale += diff * 0.14; ridisegna = true; }
    else if (attuale !== meta) { attuale = meta; ridisegna = true; }
    if (ridisegna) {
      ridisegna = false;
      if (N) disegnaFotogramma(attuale, larg, alt); else disegnaSegnaposto(attuale, larg, alt);
      aggiornaTesti(attuale);
    }
    if (attuale !== meta) requestAnimationFrame(passo); else inCorso = false;
  }
  function avvia() { if (!inCorso) { inCorso = true; requestAnimationFrame(passo); } }

  addEventListener("scroll", leggiScorrimento, { passive: true });
  addEventListener("resize", function () { misura(); leggiScorrimento(); });
  misura();
  if (N) caricaTutti();
  leggiScorrimento();
})();
