# Rifiuti AGESP — integrazione Home Assistant

Integrazione personalizzata (`custom_components/rifiuti_agesp`) per la raccolta rifiuti
di AGESP a Busto Arsizio.

## Installazione (HACS)
1. HACS → menu ⋮ → **Repository personalizzati** → URL
   `https://github.com/ARComunicazione/ha-rifiuti-agesp`, tipo **Integrazione**.
2. Cerca "Rifiuti AGESP" in HACS → **Scarica** → riavvia Home Assistant.
3. Impostazioni → Dispositivi e servizi → **Aggiungi integrazione** → "Rifiuti AGESP".
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
```
Sono 30 casi di ricerca reali e non serve Home Assistant per eseguirli.

## Feature future
- **Fase 2 — calendario dei passaggi:** entità `calendar` più sensori "oggi" e "prossimo
  passaggio", da usare nel widget della home.
- **Assistente vocale:** rispondere a domande come *"dove butto il polistirolo?"* tramite
  Assist (frasi personalizzate + gestore d'intento che usa lo stesso motore di ricerca).
- Card Lovelace con la stessa ricerca, per poterla mettere in una dashboard (es. sul tablet in
  kiosk mode, dove la barra laterale è nascosta).
