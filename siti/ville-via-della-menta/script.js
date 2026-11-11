/* Pagina principale. */
(function () {
  "use strict";
  var S = window.SITO, U = window.U, $ = U.$, el = U.el, vuoto = U.vuoto;

  U.avviaPagina();

  /* ---------- Copertina: percorso d'insieme (lo avvia percorso.js) ---------- */
  $("copertina-luogo").textContent = S.progetto.luogo;
  $("copertina-motto").textContent = S.progetto.motto;
  window.PERCORSO = { dati: S.percorso, ferma: S.progetto.immagine_copertina };

  /* ---------- Numeri ---------- */
  S.progetto.numeri.forEach(function (n) {
    var d = el("div");
    d.appendChild(el("dt", vuoto(n.valore) ? "vuoto" : null, vuoto(n.valore) ? "da definire" : n.valore));
    d.appendChild(el("dd", null, n.etichetta));
    $("numeri").appendChild(d);
  });

  /* ---------- Ville: ogni scheda porta alla pagina della villa ---------- */
  var interesse = $("interesse");
  interesse.appendChild(new Option("Non ho ancora deciso", "Nessuna preferenza"));

  S.ville.forEach(function (villa) {
    var a = el("a", "villa" + (villa.stato === "venduta" ? " venduta" : ""));
    a.href = U.indirizzoVilla(villa);
    var figura = el("div", "villa-figura");
    figura.appendChild(U.immagine(villa.immagine, villa.nome, "Render in arrivo"));
    figura.appendChild(U.etichettaStato(villa));
    var corpo = el("div", "villa-corpo");
    corpo.appendChild(el("h3", null, villa.nome));
    corpo.appendChild(U.listaDati([
      ["Superficie", U.numero(villa.superficie_m2, "m²")],
      ["Giardino", U.numero(villa.giardino_m2, "m²")],
      ["Camere", U.numero(villa.camere)],
      ["Bagni", U.numero(villa.bagni)],
    ]));
    corpo.appendChild(el("span", "villa-apri", "Entra nella villa"));
    a.appendChild(figura);
    a.appendChild(corpo);
    $("griglia-ville").appendChild(a);

    if (villa.stato !== "venduta") interesse.appendChild(new Option(villa.nome, villa.nome));
  });

  // Arrivo dalla pagina di una villa: index.html?villa=villa-2#contatti
  var chiesta = new URLSearchParams(location.search).get("villa");
  S.ville.forEach(function (v) {
    if (v.id === chiesta && v.stato !== "venduta") interesse.value = v.nome;
  });

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
    var li = el("li"), a = el("a", null, testo);
    a.href = href; li.appendChild(a);
    $("recapiti").appendChild(li);
  }
  if (!vuoto(K.telefono)) recapito(K.telefono, "tel:" + K.telefono.replace(/[^+\d]/g, ""));
  if (!vuoto(K.email)) recapito(K.email, "mailto:" + K.email);
  if (!vuoto(K.informativa_privacy)) {
    var pr = $("collegamento-privacy");
    pr.href = K.informativa_privacy; pr.hidden = false;
  }

  var modulo = $("modulo"), esito = $("esito");
  function messaggio(testo, classe) { esito.textContent = testo; esito.className = "esito " + (classe || ""); }

  modulo.addEventListener("submit", function (e) {
    e.preventDefault();
    var dati = new FormData(modulo);
    if (dati.get("sito_web")) return; // campo trappola compilato: è un automatismo

    var ok = true;
    ["nome", "email"].forEach(function (id) {
      var campo = $(id), valido = campo.checkValidity();
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

  U.comparsa(".sezione h2, .sezione .prosa, .numeri div, .villa, .planimetria, .modulo, .capitolato > div");
})();
