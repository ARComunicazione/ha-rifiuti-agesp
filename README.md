# Rifiuti AGESP — integrazione Home Assistant

Integrazione personalizzata (`custom_components/rifiuti_agesp`) per la raccolta rifiuti
di AGESP a Busto Arsizio.

## Installazione (HACS)
1. HACS → menu ⋮ → **Repository personalizzati** → URL
   `https://github.com/ARComunicazione/ha-rifiuti-agesp`, tipo **Integrazione**.
2. Cerca "Rifiuti AGESP" in HACS → **Scarica** → riavvia Home Assistant.
3. Impostazioni → Dispositivi e servizi → **Aggiungi integrazione** → "Rifiuti AGESP", poi
   scegli i giorni di raccolta della tua zona (modificabili in seguito da **Configura**).
4. Nella barra laterale compare **Rifiuti**.

Senza HACS: copiare `custom_components/rifiuti_agesp` in `/config/custom_components/` e riavviare.

## Funzioni

### Ricerca "Dove lo butto?" (v0.1.0)
- Pagina dedicata **Rifiuti** nella barra laterale (`/rifiuti`), visibile anche agli utenti
  non amministratori. Si adatta al tema attivo, chiaro o scuro, e funziona anche da telefono.
- Risultati mentre scrivi, con tolleranza per gli errori di battitura (`polisterolo`,
  `bottilia`), le parole scritte a metà (`polist`), singolare e plurale (`pila` e `pile`) e le
  domande in linguaggio naturale (`dove butto il polistirolo?`).
- **Esito diretto** quando tutte le voci principali portano alla stessa destinazione
  (es. `pile` → Centro Multiraccolta oppure contenitori sul territorio). Altrimenti mostra
  l'elenco delle varianti (es. `bottiglia` → in vetro / in plastica).
- Dettagli pratici: indirizzo del Centro Multiraccolta, numero verde cliccabile con gli
  orari, regola del materiale per i flaconi (plastica o vetro).
- Se una parola non è nel dizionario, suggerisce le voci più vicine e il numero verde.
- Collegamento diretto a una ricerca: `/rifiuti?q=polistirolo`.
- Azione `rifiuti_agesp.cerca` (con risposta) da usare in script e automazioni:

  ```yaml
  action: rifiuti_agesp.cerca
  data:
    testo: polistirolo
    limite: 5
  response_variable: esito
  ```

### Calendario della raccolta (v0.2.0)
- **Giorni di raccolta** per frazione (umido, plastica, carta, vetro e lattine, secco), impostati
  dall'interfaccia: Impostazioni → Dispositivi e servizi → Rifiuti AGESP → **Configura**.
- **Eccezioni per le festività**, una per riga nello stesso modulo:

  ```
  26/12/2026 > 28/12/2026     # raccolta spostata
  06/01/2027 > annullata      # raccolta annullata
  ```

- Nella pagina **Rifiuti**: le schede "Oggi" e "Prossima raccolta" e i passaggi delle prossime tre
  settimane. Nei risultati della ricerca compare il prossimo ritiro delle frazioni porta a porta
  (es. *Plastica · prossimo ritiro sabato 17 ottobre*). Lo stesso dato arriva anche nella risposta
  dell'azione `rifiuti_agesp.cerca`.
- Entità (dispositivo "Rifiuti AGESP"), aggiornate a mezzanotte:

  | Entità | Stato | Attributi |
  |---|---|---|
  | `calendar.rifiuti_agesp` | evento di oggi o il prossimo | un evento per ogni giorno di raccolta |
  | `sensor.rifiuti_agesp_oggi` | `Umido, Carta, Vetro e lattine` / `Nessuna raccolta` | `frazioni`, `data`, `nota` |
  | `sensor.rifiuti_agesp_domani` | come sopra, per domani | `frazioni`, `data`, `nota` |
  | `sensor.rifiuti_agesp_prossima_raccolta` | data del primo passaggio dopo oggi | `frazioni`, `nomi`, `giorno`, `giorni_mancanti` |
  | `sensor.rifiuti_agesp_prossimo_ritiro_*` | data del prossimo ritiro di quella frazione (oggi compreso) | `giorno`, `giorni_mancanti` |

  Esempio di promemoria la sera prima:

  ```yaml
  alias: Promemoria rifiuti
  triggers:
    - trigger: time
      at: "20:00:00"
  conditions:
    - condition: template
      value_template: "{{ state_attr('sensor.rifiuti_agesp_domani', 'frazioni') | count > 0 }}"
  actions:
    - action: notify.notify
      data:
        message: "Stasera esponi: {{ states('sensor.rifiuti_agesp_domani') }}"
  ```

### Card per le dashboard (v0.3.0)
La stessa interfaccia della pagina Rifiuti è disponibile come card, da mettere in una vista
della dashboard (con lo sfondo, la barra di navigazione e lo stile della dashboard). Il file è
caricato dall'integrazione: non serve aggiungere risorse a mano.

```yaml
type: custom:rifiuti-agesp-card
mostra: tutto        # tutto | ricerca | calendario
titolo: false        # true mostra "Dove lo butto?" sopra la ricerca
```

La card ha sfondo trasparente; i riquadri interni usano il tema di Home Assistant oppure, se
definite (per esempio con card-mod), queste variabili:

```yaml
card_mod:
  style: |
    ha-card {
      --rifiuti-vetro-sfondo: rgba(15, 23, 42, 0.55);
      --rifiuti-vetro-sfocatura: blur(14px);
      --rifiuti-vetro-bordo: rgba(148, 163, 184, 0.25);
      --rifiuti-vetro-raggio: 22px;
      --rifiuti-vetro-ombra: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
```

## Dati
- `custom_components/rifiuti_agesp/data/dizionario_agesp.json`: 555 voci estratte dal
  *Dizionario dei rifiuti* AGESP, edizione gennaio 2024 (il PDF si scarica da
  [agesp.it](https://www.agesp.it) e non è incluso nel repository).
- `custom_components/rifiuti_agesp/data/sinonimi.json`: parole comuni che nel dizionario non
  compaiono (`scottex`, `tetrapak`, `cicca`…). Puntano sempre a voci ufficiali e non
  aggiungono regole nuove. Si può modificare a mano, poi va ricaricata l'integrazione.
- Nuova edizione del dizionario: rigenerare il file con

  ```bash
  python3 strumenti/estrai_dizionario.py NUOVO.pdf custom_components/rifiuti_agesp/data/dizionario_agesp.json
  ```

  Richiede `poppler` (`pdftoppm`, `pdftotext`) e Pillow. Lo script segnala le voci in cui non
  riconosce l'icona.

### Particolarità del dizionario (riportate così come sono)
- 13 voci hanno due destinazioni: i **flaconi vuoti** vanno nella plastica o nel vetro
  *a seconda del materiale*; **farmaci, pile, olio alimentare** vanno al Centro Multiraccolta
  *oppure* nei contenitori sul territorio; il **polistirolo grande** va nel secco *oppure* al
  Centro Multiraccolta.
- Incoerenze dell'originale: agenda e calendario plastificati → carta, mentre carta
  plastificata → secco. Terracotta in piccole quantità → Centro Multiraccolta, mentre i cocci di
  terracotta in piccole quantità → secco. Pannolini → numero verde, mentre gli assorbenti →
  secco.
- Il dizionario non dice dove si trovano i "contenitori distribuiti sul territorio".

## Prove
```bash
python3 tests/test_search.py
python3 tests/test_calendario.py
```
Ci sono 30 casi di ricerca reali e le prove del calendario, eccezioni comprese. Per eseguirli non
serve Home Assistant. Per provare l'integrazione completa c'è l'istanza Docker in `../HA-Test`.

## Feature future
- **Widget per la home** (dashboard AD Home): prossimo passaggio e raccolta del giorno, usando i
  sensori qui sopra.
- **Assistente vocale:** rispondere a domande come *"dove butto il polistirolo?"* tramite
  Assist (frasi personalizzate + gestore d'intento che usa lo stesso motore di ricerca).
