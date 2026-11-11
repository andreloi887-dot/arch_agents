/* Funzioni condivise dalla pagina principale e dalle pagine delle ville. */
window.U = (function () {
  "use strict";
  var S = window.SITO;
  var STATI = { disponibile: "Disponibile", trattativa: "In trattativa", venduta: "Venduta" };

  function $(id) { return document.getElementById(id); }

  // Crea un elemento; il testo passa sempre da textContent, mai da innerHTML.
  function el(tag, classe, testo) {
    var e = document.createElement(tag);
    if (classe) e.className = classe;
    if (testo != null) e.textContent = testo;
    return e;
  }

  function vuoto(v) { return v == null || v === ""; }

  function numero(v, unita) {
    if (vuoto(v)) return null;
    var t = typeof v === "number" ? v.toLocaleString("it-IT") : String(v);
    return unita ? t + " " + unita : t;
  }

  function immagine(src, alt, etichetta) {
    if (vuoto(src)) return el("div", "segnaposto", etichetta);
    var i = el("img");
    i.src = src; i.alt = alt; i.loading = "lazy";
    return i;
  }

  function listaDati(voci, classe) {
    var ul = el("ul", "dati" + (classe ? " " + classe : ""));
    voci.forEach(function (v) {
      var li = el("li");
      li.appendChild(el("span", null, v[0]));
      li.appendChild(el("strong", vuoto(v[1]) ? "vuoto" : null, vuoto(v[1]) ? "da definire" : v[1]));
      ul.appendChild(li);
    });
    return ul;
  }

  function etichettaStato(villa) {
    var chiave = STATI[villa.stato] ? villa.stato : "disponibile";
    return el("span", "stato " + chiave, STATI[chiave]);
  }

  function indirizzoVilla(villa) { return "villa.html?id=" + encodeURIComponent(villa.id); }

  /* Parti uguali in tutte le pagine: fascia bozza, piede, menu, comparsa delle sezioni. */
  function avviaPagina() {
    if (S.bozza) {
      $("bozza").hidden = false;
      var robots = el("meta");
      robots.name = "robots"; robots.content = "noindex";
      document.head.appendChild(robots);
    }
    var K = S.contatti;
    var piede = [S.progetto.nome, K.venditore, K.partita_iva ? "P. IVA " + K.partita_iva : null];
    $("piede-venditore").textContent = piede.filter(function (x) { return !vuoto(x); }).join(" · ");

    var menu = $("menu"), apri = $("menu-apri");
    apri.addEventListener("click", function () {
      apri.setAttribute("aria-expanded", menu.classList.toggle("aperto"));
    });
    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") { menu.classList.remove("aperto"); apri.setAttribute("aria-expanded", "false"); }
    });
  }

  function comparsa(selettore) {
    if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var oss = new IntersectionObserver(function (voci) {
      voci.forEach(function (v) {
        if (v.isIntersecting) { v.target.classList.add("visibile"); oss.unobserve(v.target); }
      });
    }, { rootMargin: "0px 0px -12% 0px" });
    document.querySelectorAll(selettore).forEach(function (e, i) {
      e.classList.add("comparsa");
      e.style.transitionDelay = (i % 4) * 70 + "ms";
      oss.observe(e);
    });
  }

  return {
    $: $, el: el, vuoto: vuoto, numero: numero, immagine: immagine, listaDati: listaDati,
    etichettaStato: etichettaStato, indirizzoVilla: indirizzoVilla, avviaPagina: avviaPagina, comparsa: comparsa,
  };
})();
