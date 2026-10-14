"""Sensori della raccolta: oggi, domani, prossima raccolta e prossimo ritiro di ogni frazione."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .calendario import FRAZIONI, GIORNI_SETTIMANA
from .dati import RifiutiConfigEntry
from .entity import EntitaRifiuti


async def async_setup_entry(
    hass: HomeAssistant, entry: RifiutiConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(
        [
            SensoreGiorno(entry, "oggi", 0),
            SensoreGiorno(entry, "domani", 1),
            SensoreProssimaRaccolta(entry),
            *(SensoreProssimoRitiro(entry, f) for f in FRAZIONI),
        ]
    )


def _attributi_data(g: date, oggi: date) -> dict[str, Any]:
    return {"giorno": GIORNI_SETTIMANA[g.weekday()], "giorni_mancanti": (g - oggi).days}


class SensoreGiorno(EntitaRifiuti, SensorEntity):
    """Frazioni raccolte oggi o domani ("Nessuna raccolta" se non passa nessuno)."""

    def __init__(self, entry: RifiutiConfigEntry, chiave: str, scarto: int) -> None:
        super().__init__(entry, chiave)
        self._attr_translation_key = chiave
        self._scarto = scarto

    def _giorno(self) -> date:
        return self._dati.oggi() + timedelta(days=self._scarto)

    @property
    def native_value(self) -> str:
        frazioni = self._dati.calendario.raccolte(self._giorno())
        if not frazioni:
            return "Nessuna raccolta"
        return ", ".join(self._dati.frazione(f)["nome"] for f in frazioni)

    @property
    def icon(self) -> str:
        return "mdi:trash-can" if self._dati.calendario.raccolte(self._giorno()) else "mdi:trash-can-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        g = self._giorno()
        return {
            "data": g.isoformat(),
            "frazioni": self._dati.calendario.raccolte(g),
            "nota": self._dati.calendario.nota(g),
        }


class SensoreProssimaRaccolta(EntitaRifiuti, SensorEntity):
    """Data del primo passaggio dopo oggi, con le frazioni raccolte."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "prossima_raccolta"
    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, entry: RifiutiConfigEntry) -> None:
        super().__init__(entry, "prossima_raccolta")

    @property
    def native_value(self) -> date | None:
        prossima = self._dati.calendario.prossima_raccolta(self._dati.oggi())
        return prossima[0] if prossima else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        oggi = self._dati.oggi()
        if not (prossima := self._dati.calendario.prossima_raccolta(oggi)):
            return {}
        g, frazioni = prossima
        return {
            **_attributi_data(g, oggi),
            "frazioni": frazioni,
            "nomi": [self._dati.frazione(f)["nome"] for f in frazioni],
            "nota": self._dati.calendario.nota(g),
        }


class SensoreProssimoRitiro(EntitaRifiuti, SensorEntity):
    """Data del prossimo ritiro di una frazione (oggi compreso)."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "prossimo_ritiro"

    def __init__(self, entry: RifiutiConfigEntry, frazione: str) -> None:
        super().__init__(entry, f"prossimo_ritiro_{frazione}")
        self._frazione = frazione
        info = self._dati.frazione(frazione)
        self._attr_translation_placeholders = {"frazione": info["nome"]}
        self._attr_icon = info["icona"]

    @property
    def native_value(self) -> date | None:
        return self._dati.calendario.prossimo_ritiro(self._frazione, self._dati.oggi())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        g = self.native_value
        return _attributi_data(g, self._dati.oggi()) if g else {}
