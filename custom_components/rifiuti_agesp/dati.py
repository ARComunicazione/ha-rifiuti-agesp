"""Dati dell'integrazione caricati in memoria: dizionario dei rifiuti e calendario della raccolta."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util

from .calendario import FRAZIONI, GIORNI_SETTIMANA, Calendario, EccezioneNonValida, leggi_eccezioni
from .const import CONF_ECCEZIONI, GIORNI_PASSAGGI
from .search import MotoreRicerca

_LOGGER = logging.getLogger(__name__)

type RifiutiConfigEntry = ConfigEntry[DatiRifiuti]


def calendario_da_opzioni(opzioni: Mapping[str, Any]) -> Calendario:
    giorni = {f: [int(g) for g in opzioni.get(f, [])] for f in FRAZIONI}
    try:
        eccezioni = leggi_eccezioni(opzioni.get(CONF_ECCEZIONI, ""))
    except EccezioneNonValida as err:
        # il modulo di configurazione le valida già: qui si arriva solo con dati modificati a mano
        _LOGGER.error("Eccezione del calendario non valida, eccezioni ignorate: %s", err.riga)
        eccezioni = []
    return Calendario(giorni, eccezioni)


@dataclass
class DatiRifiuti:
    motore: MotoreRicerca
    calendario: Calendario

    @staticmethod
    def oggi() -> date:
        return dt_util.now().date()

    def frazione(self, frazione: str) -> dict[str, Any]:
        return {"id": frazione, **self.motore.destinazioni[frazione]}

    def giorno(self, g: date) -> dict[str, Any]:
        """Un giorno del calendario con le frazioni raccolte, pronto per la pagina e i sensori."""
        return {
            "data": g.isoformat(),
            "giorno": GIORNI_SETTIMANA[g.weekday()],
            "giorni_mancanti": (g - self.oggi()).days,
            "frazioni": [self.frazione(f) for f in self.calendario.raccolte(g)],
            "nota": self.calendario.nota(g),
        }

    def stato_calendario(self) -> dict[str, Any]:
        oggi = self.oggi()
        prossima = self.calendario.prossima_raccolta(oggi)
        return {
            "configurato": self.calendario.configurato,
            "oggi": self.giorno(oggi),
            "domani": self.giorno(oggi + timedelta(days=1)),
            "prossima": self.giorno(prossima[0]) if prossima else None,
            "passaggi": [self.giorno(g) for g, _ in self.calendario.passaggi(oggi, GIORNI_PASSAGGI)],
        }

    def arricchisci(self, risposta: dict[str, Any]) -> dict[str, Any]:
        """Aggiunge ai risultati della ricerca il prossimo ritiro delle frazioni porta a porta."""
        if not self.calendario.configurato:
            return risposta
        oggi = self.oggi()
        destinazioni = [d for r in risposta["risultati"] for d in r["destinazioni"]]
        destinazioni += risposta["esito_unico"] or []
        for d in destinazioni:
            if d["id"] in FRAZIONI and (g := self.calendario.prossimo_ritiro(d["id"], oggi)):
                d["prossimo_ritiro"] = g.isoformat()
                d["giorni_mancanti"] = (g - oggi).days
        return risposta
