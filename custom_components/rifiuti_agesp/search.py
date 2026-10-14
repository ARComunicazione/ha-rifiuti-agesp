"""Motore di ricerca nel dizionario dei rifiuti AGESP.

Usa solo la libreria standard: si può provare anche fuori da Home Assistant
(vedi tests/test_search.py).
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# Parole che non aiutano a distinguere le voci, comprese quelle delle domande
# in linguaggio naturale ("dove butto il polistirolo?")
STOPWORDS = {
    "a", "ad", "al", "allo", "alla", "ai", "agli", "alle", "anche", "butto", "buttare",
    "che", "come", "con", "d", "da", "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "dei", "degli", "del", "dello", "della", "delle", "di", "dove", "e", "ed", "es",
    "etc", "ecc", "fra", "getto", "gettare", "gli", "i", "il", "in", "l", "la", "le",
    "lo", "metto", "mettere", "mi", "nei", "negli", "nel", "nello", "nella", "nelle",
    "o", "od", "per", "se", "si", "solo", "su", "sul", "sullo", "sulla", "sui",
    "sugli", "sulle", "tra", "un", "una", "uno", "va", "vanno",
}

PUNTEGGIO_ESATTO = 1.0
PUNTEGGIO_PREFISSO = 0.8     # parola scritta a metà: "polist" -> polistirolo
PUNTEGGIO_SIMILE = 0.7       # errori di battitura: "polisterolo"
PUNTEGGIO_CONTENUTO = 0.6    # parole composte: "panni" -> attaccapanni
SOGLIA_SIMILE = 0.82


def normalizza(testo: str) -> str:
    """Minuscole, senza accenti né punteggiatura."""
    t = unicodedata.normalize("NFKD", testo.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def radice(parola: str) -> str:
    """Radice grezza per l'italiano: unisce singolare e plurale (pila/pile, sacco/sacchi)."""
    if len(parola) <= 3 or parola.isdigit():
        return parola
    r = re.sub(r"[aeiou]+$", "", parola)
    if r.endswith(("ch", "gh")):
        r = r[:-1]
    return r if len(r) >= 3 else parola


def parole(testo: str) -> list[str]:
    return [radice(p) for p in normalizza(testo).split() if p not in STOPWORDS]


def _somiglianza(a: str, b: str) -> float:
    m = SequenceMatcher(None, a, b)
    if m.real_quick_ratio() < SOGLIA_SIMILE or m.quick_ratio() < SOGLIA_SIMILE:
        return 0.0
    return m.ratio()


def _corrispondenza(q: str, parole_voce: list[str]) -> float:
    """Quanto la parola cercata q corrisponde alla voce (0 = per niente)."""
    migliore = 0.0
    for p in parole_voce:
        if p == q:
            return PUNTEGGIO_ESATTO
        if len(q) >= 3 and p.startswith(q):
            migliore = max(migliore, PUNTEGGIO_PREFISSO)
        elif len(q) >= 4 and q in p:
            migliore = max(migliore, PUNTEGGIO_CONTENUTO)
        elif len(q) >= 4 and abs(len(p) - len(q)) <= 3 and _somiglianza(q, p) >= SOGLIA_SIMILE:
            migliore = max(migliore, PUNTEGGIO_SIMILE)
    return migliore


class MotoreRicerca:
    """Dizionario caricato in memoria con indice per la ricerca."""

    def __init__(self, dizionario: dict[str, Any], sinonimi: dict[str, str]) -> None:
        self.fonte: str = dizionario["fonte"]
        self.contatti: dict[str, str] = dizionario["contatti"]
        self.destinazioni: dict[str, dict[str, str]] = dizionario["destinazioni"]
        self.voci: list[dict[str, Any]] = dizionario["voci"]
        self._indice = [parole(v["voce"]) for v in self.voci]
        self._sinonimi = sorted(
            ((normalizza(k), normalizza(v)) for k, v in sinonimi.items() if not k.startswith("_")),
            key=lambda kv: -len(kv[0]),
        )

    @classmethod
    def da_file(cls, dizionario: Path, sinonimi: Path) -> MotoreRicerca:
        return cls(
            json.loads(dizionario.read_text(encoding="utf-8")),
            json.loads(sinonimi.read_text(encoding="utf-8")),
        )

    def info(self) -> dict[str, Any]:
        return {
            "fonte": self.fonte,
            "contatti": self.contatti,
            "destinazioni": self.destinazioni,
            "numero_voci": len(self.voci),
        }

    def _varianti(self, testo: str) -> list[tuple[str, float]]:
        """La ricerca originale più quelle ottenute dai sinonimi, ciascuna col suo peso."""
        norm = normalizza(testo)
        varianti = [(norm, 1.0)]
        for chiave, valore in self._sinonimi:
            if re.search(rf"\b{re.escape(chiave)}\b", norm):
                varianti.append((re.sub(rf"\b{re.escape(chiave)}\b", valore, norm), 1.0))
            elif len(norm) >= 4 and chiave.startswith(norm):
                # sinonimo scritto a metà ("cartone della pizz"): pesa meno dei risultati diretti
                varianti.append((valore, 0.9))
        return varianti

    def _punteggi(self, testo: str) -> dict[int, tuple[bool, bool, float]]:
        """Per ogni voce trovata: (tutte le parole trovate, la voce inizia con una di esse, punteggio)."""
        cercate = list(dict.fromkeys(parole(testo)))
        if not cercate:
            return {}
        corrisp = [[_corrispondenza(q, pv) for pv in self._indice] for q in cercate]
        # le parole rare pesano di più: in "cartone pizza" conta soprattutto "pizza"
        n = len(self.voci)
        pesi = [math.log(1 + n / (1 + sum(1 for c in col if c > 0))) for col in corrisp]
        totale_pesi = sum(pesi)
        risultato = {}
        for i, pv in enumerate(self._indice):
            valori = [col[i] for col in corrisp]
            if not any(valori):
                continue
            punteggio = sum(p * v for p, v in zip(pesi, valori)) / totale_pesi
            # leggera preferenza per le voci brevi, più vicine a ciò che si è scritto
            punteggio -= 0.01 * max(0, len(pv) - len(cercate))
            # "Pile esaurite" conta più di "Blister ... per pile"
            testa = any(_corrispondenza(q, pv[:1]) for q in cercate)
            risultato[i] = (all(valori), testa, punteggio)
        return risultato

    def _risultato(self, i: int, punteggio: float) -> dict[str, Any]:
        v = self.voci[i]
        r = {
            "voce": v["voce"],
            "destinazioni": [{"id": d, **self.destinazioni[d]} for d in v["destinazioni"]],
            "punteggio": round(punteggio, 3),
            "pagina": v["pagina"],
        }
        if "logica" in v:
            r["logica"] = v["logica"]
            r["nota"] = v["nota"]
        return r

    def cerca(self, testo: str, limite: int = 15) -> dict[str, Any]:
        migliori: dict[int, tuple[bool, bool, float]] = {}
        for variante, fattore in self._varianti(testo):
            for i, (completa, testa, punteggio) in self._punteggi(variante).items():
                valore = (completa, testa and fattore == 1.0, punteggio * fattore)
                if i not in migliori or valore > migliori[i]:
                    migliori[i] = valore

        ordinati = sorted(
            migliori.items(),
            key=lambda kv: (not kv[1][0], not kv[1][1], -kv[1][2], len(self.voci[kv[0]]["voce"])),
        )
        complete = [(i, p) for i, (c, _, p) in ordinati if c]
        # senza corrispondenze complete si propongono le voci più vicine, per punteggio
        vicine = sorted(((i, p) for i, (_, _, p) in migliori.items() if p >= 0.5), key=lambda ip: -ip[1])
        scelti = complete or vicine
        risultati = [self._risultato(i, p) for i, p in scelti[:limite]]

        # esito unico: le voci che iniziano con la parola cercata portano tutte alla stessa destinazione
        esito = None
        principali = [i for i, (c, t, _) in ordinati if c and t]
        insiemi = {tuple(self.voci[i]["destinazioni"]) for i in principali}
        if len(insiemi) == 1:
            esito = [{"id": d, **self.destinazioni[d]} for d in insiemi.pop()]

        return {
            "testo": testo,
            "trovato": bool(complete),
            "esito_unico": esito,
            "totale": len(scelti),
            "risultati": risultati,
        }
