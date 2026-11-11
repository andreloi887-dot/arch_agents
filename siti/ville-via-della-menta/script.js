(function () {
  "use strict";
  var S = window.SITO;
  var $ = function (id) { return document.getElementById(id); };

  var STATI = { disponibile: "Disponibile", trattativa: "In trattativa", venduta: "Venduta" };

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

  function listaDati(voci) {
    var ul = el("ul", "dati");
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

  /* ---------- Bozza e copertina ---------- */
  if (S.bozza) {
    $("bozza").hidden = false;
    var robots = el("meta");
    robots.name = "robots"; robots.content = "noindex";
    document.head.appendChild(robots);
  }
  $("copertina-luogo").textContent = S.progetto.luogo;
  $("copertina-motto").textContent = S.progetto.motto;
  if (!vuoto(S.progetto.immagine_copertina)) {
    var c = $("copertina-immagine");
    c.style.backgroundImage = 'url("' + encodeURI(S.progetto.immagine_copertina) + '")';
    c.classList.add("con-foto");
  }

  /* ---------- Numeri ---------- */
  S.progetto.numeri.forEach(function (n) {
    var d = el("div");
    d.appendChild(el("dt", vuoto(n.valore) ? "vuoto" : null, vuoto(n.valore) ? "da definire" : n.valore));
    d.appendChild(el("dd", null, n.etichetta));
    $("numeri").appendChild(d);
  });

  /* ---------- Ville ---------- */
  var scheda = $("scheda");
  var interesse = $("interesse");
  interesse.appendChild(new Option("Non ho ancora deciso", "Nessuna preferenza"));

  S.ville.forEach(function (villa) {
    var b = el("button", "villa" + (villa.stato === "venduta" ? " venduta" : ""));
    b.type = "button";
    var figura = el("div", "villa-figura");
    figura.appendChild(immagine(villa.immagine, villa.nome, "Render in arrivo"));
    figura.appendChild(etichettaStato(villa));
    var corpo = el("div", "villa-corpo");
    corpo.appendChild(el("h3", null, villa.nome));
    corpo.appendChild(listaDati([
      ["Superficie", numero(villa.superficie_m2, "m²")],
      ["Giardino", numero(villa.giardino_m2, "m²")],
      ["Camere", numero(villa.camere)],
      ["Bagni", numero(villa.bagni)],
    ]));
    corpo.appendChild(el("span", "villa-apri", "Apri la scheda"));
    b.appendChild(figura);
    b.appendChild(corpo);
    b.addEventListener("click", function () { apriScheda(villa); });
    $("griglia-ville").appendChild(b);

    if (villa.stato !== "venduta") interesse.appendChild(new Option(villa.nome, villa.nome));
  });

  function apriScheda(villa) {
    var dentro = $("scheda-contenuto");
    dentro.replaceChildren();

    var figura = el("div", "scheda-figura");
    figura.appendChild(immagine(villa.immagine, villa.nome, "Render in arrivo"));
    figura.appendChild(etichettaStato(villa));
    dentro.appendChild(figura);

    var corpo = el("div", "scheda-corpo");
    var titolo = el("h2", null, villa.nome);
    titolo.id = "scheda-titolo";
    corpo.appendChild(titolo);
    if (!vuoto(villa.descrizione)) corpo.appendChild(el("p", null, villa.descrizione));
    corpo.appendChild(listaDati([
      ["Superficie", numero(villa.superficie_m2, "m²")],
      ["Giardino", numero(villa.giardino_m2, "m²")],
      ["Piani", numero(villa.piani)],
      ["Camere", numero(villa.camere)],
      ["Bagni", numero(villa.bagni)],
      ["Posti auto", numero(villa.posti_auto)],
      ["Classe energetica", numero(villa.classe_energetica)],
      ["Prezzo", "su richiesta"],
    ]));

    var piante = el("div", "scheda-planimetrie");
    if (villa.planimetrie && villa.planimetrie.length) {
      villa.planimetrie.forEach(function (p, i) {
        piante.appendChild(immagine(p, "Planimetria " + (i + 1) + " – " + villa.nome));
      });
    } else {
      piante.appendChild(el("div", "segnaposto", "Planimetria in arrivo"));
    }
    corpo.appendChild(piante);

    var azioni = el("div", "scheda-azioni");
    if (villa.stato !== "venduta") {
      var chiedi = el("a", "bottone", "Chiedi informazioni su " + villa.nome);
      chiedi.href = "#contatti";
      chiedi.addEventListener("click", function () {
        interesse.value = villa.nome;
        scheda.close();
      });
      azioni.appendChild(chiedi);
    }
    if (!vuoto(villa.scheda_pdf)) {
      var pdf = el("a", "bottone bottone-chiaro", "Scarica la scheda (PDF)");
      pdf.href = villa.scheda_pdf; pdf.target = "_blank"; pdf.rel = "noopener";
      azioni.appendChild(pdf);
    }
    corpo.appendChild(azioni);
    dentro.appendChild(corpo);

    scheda.showModal();
    dentro.scrollTop = 0;
  }

  $("scheda-chiudi").addEventListener("click", function () { scheda.close(); });
  scheda.addEventListener("click", function (e) { if (e.target === scheda) scheda.close(); });

  /* ---------- Capitolato ---------- */
  if (S.capitolato && S.capitolato.length) {
    $("capitolato").hidden = false;
    S.capitolato.forEach(function (v) {
      var d = el("div");
      d.appendChild(el("h3", null, v.titolo));
      d.appendChild(el("p", null, v.testo));
      $("voci-capitolato").appendChild(d);
    });
  } else {
    $("voce-capitolato").hidden = true;
  }

  /* ---------- Contatti ---------- */
  var K = S.contatti;
  function recapito(testo, href) {
    var li = el("li");
    if (href) { var a = el("a", null, testo); a.href = href; li.appendChild(a); }
    else li.textContent = testo;
    $("recapiti").appendChild(li);
  }
  if (!vuoto(K.telefono)) recapito(K.telefono, "tel:" + K.telefono.replace(/[^+\d]/g, ""));
  if (!vuoto(K.email)) recapito(K.email, "mailto:" + K.email);
  if (!vuoto(K.informativa_privacy)) {
    var pr = $("collegamento-privacy");
    pr.href = K.informativa_privacy; pr.hidden = false;
  }
  var piede = [S.progetto.nome, K.venditore, K.partita_iva ? "P. IVA " + K.partita_iva : null];
  $("piede-venditore").textContent = piede.filter(function (x) { return !vuoto(x); }).join(" · ");

  var modulo = $("modulo");
  var esito = $("esito");
  function messaggio(testo, classe) { esito.textContent = testo; esito.className = "esito " + (classe || ""); }

  modulo.addEventListener("submit", function (e) {
    e.preventDefault();
    var dati = new FormData(modulo);
    if (dati.get("sito_web")) return; // campo trappola compilato: è un automatismo

    var ok = true;
    ["nome", "email"].forEach(function (id) {
      var campo = $(id);
      var valido = campo.checkValidity();
      campo.classList.toggle("non-valido", !valido);
      if (!valido) ok = false;
    });
    if (!ok) return messaggio("Controlla nome ed email.", "errore");
    if (!$("consenso").checked) return messaggio("Serve il consenso al trattamento dei dati.", "errore");

    if (!vuoto(K.indirizzo_modulo)) {
      dati.delete("sito_web");
      messaggio("Invio in corso…");
      fetch(K.indirizzo_modulo, { method: "POST", body: dati, headers: { Accept: "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          modulo.reset();
          messaggio("Richiesta inviata. Ti rispondiamo al più presto.", "riuscito");
        })
        .catch(function () {
          messaggio("Invio non riuscito. Riprova tra poco" + (vuoto(K.telefono) ? "." : " o chiamaci al " + K.telefono + "."), "errore");
        });
    } else if (!vuoto(K.email)) {
      var corpo = [
        "Nome: " + dati.get("nome"),
        "Email: " + dati.get("email"),
        "Telefono: " + (dati.get("telefono") || "-"),
        "Villa di interesse: " + dati.get("interesse"),
        "",
        dati.get("messaggio") || "",
      ].join("\n");
      location.href = "mailto:" + K.email +
        "?subject=" + encodeURIComponent("Richiesta informazioni – " + S.progetto.nome) +
        "&body=" + encodeURIComponent(corpo);
      messaggio("Si è aperto il tuo programma di posta: premi Invia per completare.", "riuscito");
    } else {
      messaggio("Modulo non ancora collegato: compila contatti in dati.js.", "errore");
    }
  });

  /* ---------- Menu su schermi stretti ---------- */
  var menu = $("menu"), apri = $("menu-apri");
  apri.addEventListener("click", function () {
    var aperto = menu.classList.toggle("aperto");
    apri.setAttribute("aria-expanded", aperto);
  });
  menu.addEventListener("click", function (e) {
    if (e.target.tagName === "A") { menu.classList.remove("aperto"); apri.setAttribute("aria-expanded", "false"); }
  });
})();
