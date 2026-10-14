"""Calendario della raccolta: un evento di un giorno intero per ogni passaggio."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .dati import RifiutiConfigEntry
from .entity import EntitaRifiuti

MAX_GIORNI = 400   # limite per le richieste di intervalli molto lunghi


async def async_setup_entry(
    hass: HomeAssistant, entry: RifiutiConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([CalendarioRifiuti(entry)])


class CalendarioRifiuti(EntitaRifiuti, CalendarEntity):
    _attr_name = None   # prende il nome del dispositivo: calendar.rifiuti_agesp
    _attr_icon = "mdi:calendar-blank"

    def __init__(self, entry: RifiutiConfigEntry) -> None:
        super().__init__(entry, "calendario")

    def _evento(self, g: date) -> CalendarEvent | None:
        frazioni = self._dati.calendario.raccolte(g)
        if not frazioni:
            return None
        nomi = ", ".join(self._dati.frazione(f)["nome"] for f in frazioni)
        return CalendarEvent(
            start=g,
            end=g + timedelta(days=1),
            summary=f"Rifiuti: {nomi}",
            description=self._dati.calendario.nota(g) or "Raccolta porta a porta AGESP",
            uid=f"rifiuti_agesp_{g.isoformat()}",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """L'evento di oggi, altrimenti il prossimo."""
        oggi = self._dati.oggi()
        if evento := self._evento(oggi):
            return evento
        prossima = self._dati.calendario.prossima_raccolta(oggi)
        return self._evento(prossima[0]) if prossima else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        primo = dt_util.as_local(start_date).date()
        ultimo = min(dt_util.as_local(end_date).date(), primo + timedelta(days=MAX_GIORNI))
        eventi = []
        g = primo
        while g <= ultimo:
            # evento di un giorno intero: conta se si sovrappone all'intervallo richiesto
            if (evento := self._evento(g)) and dt_util.start_of_local_day(g) < end_date:
                eventi.append(evento)
            g += timedelta(days=1)
        return eventi
