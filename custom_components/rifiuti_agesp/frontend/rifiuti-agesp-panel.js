// Pagina "Rifiuti" dell'integrazione rifiuti_agesp: calendario della raccolta e ricerca nel dizionario AGESP.
// Web component senza dipendenze: usa i colori del tema attivo di Home Assistant.

const ESEMPI = ["polistirolo", "pile", "cartone della pizza", "olio fritto", "capsule caffè", "pannolini"];
const ATTESA_DIGITAZIONE = 120;
const ETICHETTE_ESITO = {
  cmr: "Portalo al",
  telefonare: "Non va nei bidoni: chiama il",
  tessili: "Mettilo nel contenitore",
  territorio: "Mettilo nei",
};

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// testo scuro sulle destinazioni chiare (plastica gialla), bianco sulle altre
const coloreTesto = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  const l = (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
  return l > 0.62 ? "#1f2937" : "#ffffff";
};

const normalizza = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

// date ISO "2026-10-17" lette come giorno locale, senza spostamenti di fuso orario
const dataLocale = (iso) => {
  const [a, m, g] = iso.split("-").map(Number);
  return new Date(a, m - 1, g);
};
const isoOggi = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const FORMATO_GIORNO = new Intl.DateTimeFormat("it-IT", { weekday: "long", day: "numeric", month: "long" });
const giornoEsteso = (iso) => FORMATO_GIORNO.format(dataLocale(iso));
const maiuscola = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const quando = (iso, mancanti) => (mancanti === 0 ? "oggi" : mancanti === 1 ? "domani" : giornoEsteso(iso));
const traQuanto = (mancanti) => (mancanti === 0 ? "oggi" : mancanti === 1 ? "domani" : `tra ${mancanti} giorni`);

// evidenzia nelle voci le parole cercate (stessa radice grezza usata dal motore di ricerca)
const evidenzia = (voce, testo) => {
  const radici = normalizza(testo)
    .split(/[^a-z0-9]+/)
    .filter((p) => p.length >= 3)
    .map((p) => (p.length > 3 ? p.replace(/[aeiou]+$/, "") : p))
    .filter((p) => p.length >= 3);
  if (!radici.length) return esc(voce);
  // la sottolineatura arriva fino alla fine della parola: "Polistirol" -> "Polistirolo"
  const re = new RegExp(`(${radici.map((r) => r.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})[a-z0-9]*`, "gi");
  const base = normalizza(voce);
  let out = "";
  let i = 0;
  for (const m of base.matchAll(re)) {
    out += esc(voce.slice(i, m.index)) + `<mark>${esc(voce.slice(m.index, m.index + m[0].length))}</mark>`;
    i = m.index + m[0].length;
  }
  return out + esc(voce.slice(i));
};

class RifiutiAgespPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._info = null;
    this._calendario = null;
    this._risposta = null;
    this._testo = "";
    this._richiesta = 0;
    this._timer = null;
  }

  set hass(hass) {
    const primo = !this._hass;
    this._hass = hass;
    if (primo) this._avvia();
    this._aggiornaMenu();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    this._aggiornaMenu();
  }

  set panel(_panel) {}
  set route(_route) {}

  connectedCallback() {
    // la pagina può restare aperta per giorni (tablet): a mezzanotte si aggiorna da sola
    this._controlloGiorno = setInterval(() => this._controllaGiorno(), 60000);
    this._suVisibilita = () => document.visibilityState === "visible" && this._controllaGiorno();
    document.addEventListener("visibilitychange", this._suVisibilita);
  }

  disconnectedCallback() {
    clearInterval(this._controlloGiorno);
    document.removeEventListener("visibilitychange", this._suVisibilita);
  }

  async _controllaGiorno() {
    if (!this._calendario || this._giornoCaricato === isoOggi()) return;
    await this._caricaCalendario();
    if (this._testo) this._cerca(this._testo);
    else this._disegnaRisultati();
  }

  async _caricaCalendario() {
    this._giornoCaricato = isoOggi();
    this._calendario = await this._hass.callWS({ type: "rifiuti_agesp/calendario" });
  }

  async _avvia() {
    this._disegnaStruttura();
    try {
      [this._info] = await Promise.all([
        this._hass.callWS({ type: "rifiuti_agesp/info" }),
        this._caricaCalendario(),
      ]);
    } catch (err) {
      this._mostraErrore(err);
      return;
    }
    const q = new URLSearchParams(location.search).get("q");
    if (q) {
      this._input.value = q;
      this._cerca(q);
    } else {
      this._disegnaRisultati();
    }
    if (matchMedia("(pointer: fine)").matches) this._input.focus();
  }

  _aggiornaMenu() {
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (!menu || !this._hass) return;
    menu.hass = this._hass;
    menu.narrow = this._narrow;
  }

  _disegnaStruttura() {
    this.shadowRoot.innerHTML = `
      <style>${STILE}</style>
      <div class="toolbar">
        <ha-menu-button></ha-menu-button>
        <div class="titolo">Rifiuti</div>
      </div>
      <main>
        <h1>Dove lo butto?</h1>
        <div class="ricerca">
          <ha-icon icon="mdi:magnify"></ha-icon>
          <input type="search" placeholder="Scrivi cosa devi buttare…" autocomplete="off" spellcheck="false"
                 aria-label="Cosa devi buttare">
          <button class="pulisci" aria-label="Cancella" hidden><ha-icon icon="mdi:close"></ha-icon></button>
        </div>
        <section class="risultati" aria-live="polite"></section>
        <footer></footer>
      </main>`;
    this._input = this.shadowRoot.querySelector("input");
    this._pulisci = this.shadowRoot.querySelector(".pulisci");
    this._risultati = this.shadowRoot.querySelector(".risultati");

    this._input.addEventListener("input", () => {
      clearTimeout(this._timer);
      this._timer = setTimeout(() => this._cerca(this._input.value), ATTESA_DIGITAZIONE);
    });
    this._input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this._imposta("");
    });
    this._pulisci.addEventListener("click", () => {
      this._imposta("");
      this._input.focus();
    });
    this._risultati.addEventListener("click", (e) => {
      const esempio = e.target.closest("[data-esempio]");
      if (esempio) this._imposta(esempio.dataset.esempio);
    });
    this._aggiornaMenu();
  }

  _imposta(testo) {
    this._input.value = testo;
    this._cerca(testo);
  }

  async _cerca(testo) {
    this._testo = testo.trim();
    this._pulisci.hidden = !this._testo;
    const url = new URL(location.href);
    if (this._testo) url.searchParams.set("q", this._testo);
    else url.searchParams.delete("q");
    history.replaceState(history.state, "", url);

    const numero = ++this._richiesta;
    if (!this._testo) {
      this._risposta = null;
      this._disegnaRisultati();
      return;
    }
    try {
      const risposta = await this._hass.callWS({ type: "rifiuti_agesp/cerca", testo: this._testo, limite: 20 });
      if (numero !== this._richiesta) return; // è già partita una ricerca più recente
      this._risposta = risposta;
      this._disegnaRisultati();
    } catch (err) {
      if (numero === this._richiesta) this._mostraErrore(err);
    }
  }

  _mostraErrore(err) {
    this.shadowRoot.querySelector(".risultati").innerHTML = `
      <div class="vetro avviso"><ha-icon icon="mdi:alert-circle-outline"></ha-icon>
      <div>Ricerca non disponibile: ${esc(err?.message || err)}</div></div>`;
  }

  // dettagli pratici di una destinazione: indirizzo, telefono, ecc.
  _dettaglio(d) {
    const c = this._info.contatti;
    const riga = (icona, testo) => `<ha-icon icon="${icona}"></ha-icon><span>${testo}</span>`;
    switch (d.id) {
      case "cmr":
        return riga("mdi:map-marker-outline", esc(c.cmr));
      case "telefonare":
        return riga(
          "mdi:phone-outline",
          `<a class="telefono" href="tel:${esc(c.numero_verde.replace(/\s/g, ""))}">${esc(c.numero_verde)}</a> · ${esc(c.orari_numero_verde)}`
        );
      case "territorio":
        return riga("mdi:information-outline", "Il dizionario non indica dove si trovano i contenitori");
      case "tessili":
        return riga("mdi:information-outline", esc(d.descrizione));
      default:
        if (!d.prossimo_ritiro) return riga("mdi:home-outline", "Raccolta porta a porta");
        return riga(
          "mdi:home-outline",
          `Porta a porta · prossimo ritiro <strong>${esc(quando(d.prossimo_ritiro, d.giorni_mancanti))}</strong>`
        );
    }
  }

  _pillola(d, grande = false) {
    return `<span class="pillola${grande ? " grande" : ""}" style="background:${d.colore};color:${coloreTesto(d.colore)}">
      <ha-icon icon="${esc(d.icona)}"></ha-icon>${esc(d.nome)}</span>`;
  }

  _destinazioni(r) {
    const sep = r.logica === "materiale" ? "o" : "oppure";
    return r.destinazioni.map((d) => this._pillola(d)).join(`<span class="sep">${sep}</span>`);
  }

  _riga(r) {
    const dettagli = r.destinazioni.length === 1 ? `<div class="dettaglio">${this._dettaglio(r.destinazioni[0])}</div>` : "";
    // per le alternative bastano le pillole con "oppure"; il materiale va spiegato
    const nota = r.logica === "materiale" ? `<div class="nota"><ha-icon icon="mdi:swap-horizontal"></ha-icon><span>${esc(r.nota)}</span></div>` : "";
    return `<li>
      <div class="voce">${evidenzia(r.voce, this._testo)}${nota}${dettagli}</div>
      <div class="destinazioni">${this._destinazioni(r)}</div>
    </li>`;
  }

  _disegnaRisultati() {
    if (!this._info) return;
    const info = this._info;
    this.shadowRoot.querySelector("footer").innerHTML =
      `${esc(info.fonte)} · ${info.numero_voci} voci · Servizio clienti ${esc(info.contatti.numero_verde)}`;

    const r = this._risposta;
    if (!r) {
      this._risultati.innerHTML = this._vuoto();
      return;
    }
    if (!r.trovato) {
      this._risultati.innerHTML = this._nonTrovato(r);
      return;
    }

    let html = "";
    if (r.esito_unico) {
      const colore = r.esito_unico[0].colore;
      html += `<div class="vetro esito" style="--accento:${colore}">
        <div class="etichetta">${r.esito_unico.length > 1 ? "Puoi scegliere tra" : ETICHETTE_ESITO[r.esito_unico[0].id] || "Va in"}</div>
        <div class="pillole">${r.esito_unico.map((d) => this._pillola(d, true)).join('<span class="sep">oppure</span>')}</div>
        ${r.esito_unico.map((d) => `<div class="dettaglio">${this._dettaglio(d)}</div>`).join("")}
      </div>`;
    }
    const titolo = r.esito_unico ? "Voci del dizionario" : `${r.totale} ${r.totale === 1 ? "voce trovata" : "voci trovate"}`;
    html += `<h2>${titolo}${r.totale > r.risultati.length ? ` <small>(le prime ${r.risultati.length})</small>` : ""}</h2>
      <ul class="vetro elenco">${r.risultati.map((x) => this._riga(x)).join("")}</ul>`;
    this._risultati.innerHTML = html;
  }

  _vuoto() {
    const legenda = Object.entries(this._info.destinazioni)
      .map(
        ([id, d]) => `<div class="legenda-voce">
          <span class="bollino" style="background:${d.colore};color:${coloreTesto(d.colore)}"><ha-icon icon="${esc(d.icona)}"></ha-icon></span>
          <div><strong>${esc(d.nome)}</strong><span>${esc(d.descrizione)}</span></div>
        </div>`
      )
      .join("");
    return `
      <div class="esempi">Prova con:
        ${ESEMPI.map((e) => `<button class="chip" data-esempio="${esc(e)}">${esc(e)}</button>`).join("")}
      </div>
      ${this._sezioneCalendario()}
      <h2>Dove vanno i rifiuti</h2>
      <div class="vetro legenda">${legenda}</div>`;
  }

  _sezioneCalendario() {
    const c = this._calendario;
    if (!c) return "";
    if (!c.configurato) {
      return `<div class="vetro avviso"><ha-icon icon="mdi:calendar-alert"></ha-icon>
        <div><strong>Calendario della raccolta non configurato.</strong>
        Impostazioni → Dispositivi e servizi → Rifiuti AGESP → Configura.</div></div>`;
    }
    const pillole = (g) =>
      g.frazioni.length
        ? `<div class="pillole">${g.frazioni.map((d) => this._pillola(d)).join("")}</div>`
        : `<div class="nessuna">Nessuna raccolta</div>`;
    const nota = (g) =>
      g.nota ? `<div class="nota"><ha-icon icon="mdi:calendar-sync"></ha-icon><span>${esc(g.nota)}</span></div>` : "";
    const { oggi, prossima } = c;
    const passaggi = c.passaggi
      .map(
        (g) => `<li>
          <div class="voce"><strong>${esc(maiuscola(giornoEsteso(g.data)))}</strong>
            ${g.giorni_mancanti <= 1 ? `<span class="tag">${traQuanto(g.giorni_mancanti)}</span>` : ""}${nota(g)}</div>
          <div class="destinazioni">${g.frazioni.map((d) => this._pillola(d)).join("")}</div>
        </li>`
      )
      .join("");
    return `
      <div class="raccolta">
        <div class="vetro giorno${oggi.frazioni.length ? " attivo" : ""}">
          <div class="etichetta">Oggi</div>
          <div class="quando">${esc(maiuscola(giornoEsteso(oggi.data)))}</div>
          ${pillole(oggi)}${nota(oggi)}
        </div>
        <div class="vetro giorno">
          <div class="etichetta">Prossima raccolta</div>
          ${
            prossima
              ? `<div class="quando">${esc(maiuscola(giornoEsteso(prossima.data)))} <small>· ${traQuanto(prossima.giorni_mancanti)}</small></div>
                 ${pillole(prossima)}${nota(prossima)}`
              : `<div class="nessuna">Nessuna nei prossimi 60 giorni</div>`
          }
        </div>
      </div>
      <h2>Prossimi passaggi</h2>
      <ul class="vetro elenco">${passaggi}</ul>`;
  }

  _nonTrovato(r) {
    const c = this._info.contatti;
    const simili = r.risultati.length
      ? `<h2>Forse cercavi</h2><ul class="vetro elenco">${r.risultati.slice(0, 8).map((x) => this._riga(x)).join("")}</ul>`
      : "";
    return `
      <div class="vetro avviso">
        <ha-icon icon="mdi:help-circle-outline"></ha-icon>
        <div><strong>«${esc(r.testo)}» non è nel dizionario.</strong>
          Chiedi al numero verde <a href="tel:${esc(c.numero_verde.replace(/\s/g, ""))}">${esc(c.numero_verde)}</a>
          (${esc(c.orari_numero_verde)}).</div>
      </div>${simili}`;
  }
}

const STILE = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--lovelace-background, var(--primary-background-color));
    background-attachment: fixed;
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, inherit));
    --raggio: var(--ha-card-border-radius, 16px);
  }
  .toolbar {
    display: flex; align-items: center; gap: 4px;
    height: var(--header-height, 56px); padding: 0 12px;
    color: var(--app-header-text-color, var(--primary-text-color));
    background: var(--app-header-background-color, transparent);
    border-bottom: var(--app-header-border-bottom, none);
  }
  .titolo { font-size: 20px; margin-left: 8px; }
  main { max-width: 760px; margin: 0 auto; padding: 8px 16px 48px; box-sizing: border-box; }
  h1 { font-size: 28px; font-weight: 500; margin: 16px 4px 16px; }
  h2 { font-size: 15px; font-weight: 500; color: var(--secondary-text-color); margin: 24px 4px 8px; }
  h2 small { font-weight: 400; }
  .vetro {
    background: var(--ha-card-background, var(--card-background-color));
    -webkit-backdrop-filter: var(--ha-card-backdrop-filter, blur(14px));
    backdrop-filter: var(--ha-card-backdrop-filter, blur(14px));
    border: 1px solid var(--ha-card-border-color, var(--divider-color));
    border-radius: var(--raggio);
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .ricerca {
    display: flex; align-items: center; gap: 10px;
    padding: 0 8px 0 18px; height: 60px;
    background: var(--ha-card-background, var(--card-background-color));
    -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px);
    border: 1px solid var(--ha-card-border-color, var(--divider-color));
    border-radius: 30px;
  }
  .ricerca:focus-within { border-color: var(--primary-color); }
  .ricerca > ha-icon { color: var(--secondary-text-color); }
  input {
    flex: 1; min-width: 0; height: 100%;
    border: 0; outline: 0; background: transparent;
    color: var(--primary-text-color); font: inherit; font-size: 20px;
  }
  input::placeholder { color: var(--secondary-text-color); }
  input::-webkit-search-cancel-button { display: none; }
  button { font: inherit; cursor: pointer; }
  .pulisci {
    border: 0; background: transparent; color: var(--secondary-text-color);
    width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center;
  }
  .pulisci:hover { background: var(--divider-color); }
  .pulisci[hidden] { display: none; }
  .esempi { margin: 16px 4px 0; color: var(--secondary-text-color); line-height: 2.6; }
  .chip {
    margin-left: 6px; padding: 6px 14px; border-radius: 18px;
    border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color);
  }
  .chip:hover { border-color: var(--primary-color); }
  .legenda { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 4px; padding: 10px; }
  .legenda-voce { display: flex; align-items: center; gap: 12px; padding: 8px; }
  .legenda-voce strong { display: block; font-weight: 500; }
  .legenda-voce span { font-size: 13px; color: var(--secondary-text-color); }
  .bollino { flex: none; width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; }
  .raccolta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 20px; }
  .giorno { padding: 16px 18px; }
  .giorno.attivo { border-color: var(--primary-color); box-shadow: 0 0 22px -8px var(--primary-color), var(--ha-card-box-shadow, 0 0 0 transparent); }
  .giorno .quando { font-size: 18px; font-weight: 500; margin-top: 4px; }
  .giorno .quando small { font-size: 14px; font-weight: 400; color: var(--secondary-text-color); }
  .giorno .pillole { margin-bottom: 0; }
  .nessuna { color: var(--secondary-text-color); margin-top: 10px; }
  .tag {
    margin-left: 6px; padding: 1px 8px; border-radius: 10px; font-size: 12px;
    background: var(--primary-color); color: var(--text-primary-color, #fff);
  }
  .esito {
    margin-top: 20px; padding: 18px 20px;
    border-color: var(--accento);
    box-shadow: 0 0 24px -6px var(--accento), var(--ha-card-box-shadow, 0 0 0 transparent);
  }
  .etichetta { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--secondary-text-color); }
  .pillole { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 8px; }
  .pillola {
    display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;
    padding: 4px 12px 4px 8px; border-radius: 16px; font-size: 14px; font-weight: 500;
    --mdc-icon-size: 18px;
  }
  .pillola.grande { font-size: 22px; padding: 8px 18px 8px 12px; border-radius: 24px; --mdc-icon-size: 28px; gap: 10px; }
  .sep { color: var(--secondary-text-color); font-size: 13px; margin: 0 2px; }
  .elenco { list-style: none; margin: 0; padding: 4px 0; }
  .elenco li {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 12px 16px; border-top: 1px solid var(--divider-color);
  }
  .elenco li:first-child { border-top: 0; }
  .voce { min-width: 0; }
  .destinazioni { display: flex; flex-wrap: wrap; justify-content: flex-end; align-items: center; gap: 6px; flex: none; max-width: 55%; }
  mark { background: transparent; color: inherit; font-weight: 600; text-decoration: underline; text-decoration-color: var(--primary-color); text-underline-offset: 3px; }
  .dettaglio, .nota {
    display: flex; align-items: flex-start; gap: 6px; margin-top: 4px; line-height: 18px;
    font-size: 13px; color: var(--secondary-text-color); --mdc-icon-size: 16px;
  }
  .esito .dettaglio { font-size: 15px; --mdc-icon-size: 18px; }
  .dettaglio ha-icon, .nota ha-icon { flex: none; }
  .esito .dettaglio { line-height: 22px; }
  a { color: var(--primary-color); }
  .telefono { white-space: nowrap; }
  .avviso { display: flex; gap: 12px; align-items: flex-start; padding: 16px 18px; margin-top: 20px; line-height: 1.5; }
  .avviso > ha-icon { color: var(--warning-color, #f4b400); flex: none; }
  footer { margin: 32px 4px 0; font-size: 12px; color: var(--secondary-text-color); text-align: center; }
  @media (max-width: 600px) {
    h1 { font-size: 24px; }
    .elenco li { flex-direction: column; align-items: flex-start; }
    .destinazioni { justify-content: flex-start; max-width: none; }
    .legenda { grid-template-columns: 1fr; }
    .raccolta { grid-template-columns: 1fr; }
  }
`;

// dopo un aggiornamento dell'integrazione il browser già aperto carica di nuovo il modulo:
// il componente esiste già e la versione nuova arriva al prossimo ricaricamento della pagina
if (!customElements.get("rifiuti-agesp-panel")) customElements.define("rifiuti-agesp-panel", RifiutiAgespPanel);
