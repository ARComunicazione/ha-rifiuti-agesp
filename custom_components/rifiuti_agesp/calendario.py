"""Calendario della raccolta porta a porta: giorni fissi della settimana più eccezioni.

Usa solo la libreria standard: si può provare anche fuori da Home Assistant
(vedi tests/test_calendario.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# Frazioni raccolte porta a porta, nell'ordine in cui si mostrano
FRAZIONI = ("umido", "plastica", "carta", "vetro", "secco")
GIORNI_SETTIMANA = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
ANNULLATA = "annullata"

_RE_DATA = r"(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})"
_RE_ECCEZIONE = re.compile(rf"^{_RE_DATA}\s*>\s*({_RE_DATA}|{ANNULLATA})$", re.IGNORECASE)


class EccezioneNonValida(ValueError):
    """Riga delle eccezioni scritta in un formato non riconosciuto."""

    def __init__(self, riga: str) -> None:
        super().__init__(riga)
        self.riga = riga


@dataclass(frozen=True)
class Eccezione:
    """La raccolta del giorno `originale` si sposta a `nuova` (None = annullata)."""

    originale: date
    nuova: date | None


def _data(testo: str) -> date:
    if "/" in testo:
        return datetime.strptime(testo, "%d/%m/%Y").date()
    return date.fromisoformat(testo)


def leggi_eccezioni(testo: str) -> list[Eccezione]:
    """Una riga per eccezione: "26/12/2026 > 28/12/2026" oppure "26/12/2026 > annullata".

    Le righe vuote e il testo dopo "#" vengono ignorati.
    """
    eccezioni = []
    for grezza in (testo or "").splitlines():
        riga = grezza.split("#", 1)[0].strip()
        if not riga:
            continue
        m = _RE_ECCEZIONE.match(riga)
        if not m:
            raise EccezioneNonValida(grezza.strip())
        try:
            originale = _data(m.group(1))
            nuova = None if m.group(2).lower() == ANNULLATA else _data(m.group(2))
        except ValueError as err:
            raise EccezioneNonValida(grezza.strip()) from err
        eccezioni.append(Eccezione(originale, nuova))
    return eccezioni


class Calendario:
    """Quali frazioni vengono raccolte in un certo giorno."""

    def __init__(self, giorni: dict[str, list[int]], eccezioni: list[Eccezione] | None = None) -> None:
        # giorni: frazione -> giorni della settimana (0 = lunedì, come date.weekday())
        self._settimana: dict[int, list[str]] = {g: [] for g in range(7)}
        for frazione in FRAZIONI:
            for g in sorted(set(giorni.get(frazione, []))):
                self._settimana[g].append(frazione)
        self._tolte: set[date] = set()
        self._aggiunte: dict[date, list[tuple[str, date]]] = {}
        for e in eccezioni or []:
            self._tolte.add(e.originale)
            if e.nuova is not None:
                for frazione in self._settimana[e.originale.weekday()]:
                    self._aggiunte.setdefault(e.nuova, []).append((frazione, e.originale))

    @property
    def configurato(self) -> bool:
        return any(self._settimana.values())

    def raccolte(self, giorno: date) -> list[str]:
        """Frazioni raccolte in quel giorno, eccezioni comprese."""
        frazioni = [] if giorno in self._tolte else list(self._settimana[giorno.weekday()])
        for frazione, _ in self._aggiunte.get(giorno, []):
            if frazione not in frazioni:
                frazioni.append(frazione)
        return sorted(frazioni, key=FRAZIONI.index)

    def nota(self, giorno: date) -> str | None:
        """Spiega perché quel giorno è diverso dal solito (raccolta spostata)."""
        origini = sorted({orig for _, orig in self._aggiunte.get(giorno, [])})
        if not origini:
            return None
        return "Recupero della raccolta di " + ", ".join(
            f"{GIORNI_SETTIMANA[o.weekday()]} {o.strftime('%d/%m')}" for o in origini
        )

    def passaggi(self, da: date, giorni: int) -> list[tuple[date, list[str]]]:
        """Giorni con almeno una raccolta, da `da` incluso per `giorni` giorni."""
        risultato = []
        for i in range(giorni):
            g = da + timedelta(days=i)
            if frazioni := self.raccolte(g):
                risultato.append((g, frazioni))
        return risultato

    def prossima_raccolta(self, dopo: date, orizzonte: int = 60) -> tuple[date, list[str]] | None:
        """Primo giorno con raccolta dopo `dopo` (escluso)."""
        prossimi = self.passaggi(dopo + timedelta(days=1), orizzonte)
        return prossimi[0] if prossimi else None

    def prossimo_ritiro(self, frazione: str, da: date, orizzonte: int = 60) -> date | None:
        """Primo giorno, da `da` incluso, in cui passa quella frazione."""
        for i in range(orizzonte):
            g = da + timedelta(days=i)
            if frazione in self.raccolte(g):
                return g
        return None
