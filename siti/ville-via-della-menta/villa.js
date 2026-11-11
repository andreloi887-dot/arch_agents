/* Pagina di una villa: villa.html?id=villa-1 */
(function () {
  "use strict";
  var S = window.SITO, U = window.U, $ = U.$, el = U.el, vuoto = U.vuoto;

  var id = new URLSearchParams(location.search).get("id");
  var indice = S.ville.findIndex(function (v) { return v.id === id; });
  if (indice < 0) { location.replace("index.html#ville"); return; }
  var villa = S.ville[indice];
  var chiedi = "index.html?villa=" + encodeURIComponent(villa.id) + "#contatti";

  U.avviaPagina();
  document.title = villa.nome + " · " + S.progetto.nome;

  /* ---------- Copertina: percorso dentro la villa (lo avvia percorso.js) ---------- */
  $("villa-occhiello").textContent = "Villa " + (indice + 1) + " di " + S.ville.length + " · " + S.progetto.luogo;
  $("villa-nome").textContent = villa.nome;
  $("villa-sommario").textContent = villa.descrizione || S.progetto.motto;
  $("villa-stato").appendChild(U.etichettaStato(villa));
  $("villa-chiedi").href = chiedi;
  if (villa.stato === "venduta") $("villa-chiedi").hidden = true;

  var P = Object.assign({}, villa.percorso);
  if (!P.tappe) P.tappe = S.tappe_interni; // didascalie d'esempio finché non si scrivono quelle della villa
  if (!P.schermate) P.schermate = S.percorso.schermate;
  window.PERCORSO = { dati: P, ferma: villa.immagine };

  /* ---------- Numeri ---------- */
  $("villa-dati").appendChild(U.listaDati([
    ["Superficie", U.numero(villa.superficie_m2, "m²")],
    ["Giardino", U.numero(villa.giardino_m2, "m²")],
    ["Piani", U.numero(villa.piani)],
    ["Camere", U.numero(villa.camere)],
    ["Bagni", U.numero(villa.bagni)],
    ["Posti auto", U.numero(villa.posti_auto)],
    ["Classe energetica", U.numero(villa.classe_energetica)],
    ["Prezzo", "su richiesta"],
  ], "dati-grandi"));
  if (!vuoto(villa.descrizione)) $("villa-descrizione").textContent = villa.descrizione;

  /* ---------- Render e interni ---------- */
  var viste = (villa.galleria || []).filter(function (g) { return g && !vuoto(g.src); });
  var galleria = $("villa-galleria");
  if (viste.length) {
    viste.forEach(function (g) {
      var f = el("figure");
      f.appendChild(U.immagine(g.src, g.didascalia || villa.nome));
      if (!vuoto(g.didascalia)) f.appendChild(el("figcaption", null, g.didascalia));
      galleria.appendChild(f);
    });
  } else {
    ["Esterno in arrivo", "Zona giorno in arrivo", "Zona notte in arrivo"].forEach(function (t) {
      var f = el("figure");
      f.appendChild(el("div", "segnaposto", t));
      galleria.appendChild(f);
    });
  }

  /* ---------- Planimetrie ---------- */
  var piante = $("villa-planimetrie");
  if (villa.planimetrie && villa.planimetrie.length) {
    villa.planimetrie.forEach(function (p, i) {
      piante.appendChild(U.immagine(p, "Planimetria " + (i + 1) + " – " + villa.nome));
    });
  } else {
    piante.appendChild(el("div", "segnaposto", "Planimetria in arrivo"));
  }
  if (!vuoto(villa.scheda_pdf)) {
    var pdf = $("villa-pdf");
    pdf.href = villa.scheda_pdf; pdf.hidden = false;
  }

  /* ---------- Invito e altre ville ---------- */
  $("villa-chiedi-2").href = chiedi;
  $("villa-chiedi-2").textContent = "Chiedi informazioni su " + villa.nome;
  if (villa.stato === "venduta") {
    $("villa-chiedi-2").hidden = true;
    $("villa-invito").textContent = "Questa villa è venduta. Guarda le altre.";
  }
  S.ville.forEach(function (v) {
    if (v === villa) return;
    var a = el("a", "altra-villa");
    a.href = U.indirizzoVilla(v);
    a.appendChild(el("span", null, v.nome));
    a.appendChild(U.etichettaStato(v));
    $("altre-ville").appendChild(a);
  });

  U.comparsa(".sezione h2, .sezione .prosa, .dati-grandi li, .griglia-galleria figure, .villa-planimetrie > *, .altra-villa");
})();
