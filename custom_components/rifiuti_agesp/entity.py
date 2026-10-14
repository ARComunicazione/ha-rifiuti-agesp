"""Base comune delle entità: dispositivo "Rifiuti AGESP" e aggiornamento a mezzanotte."""
from __future__ import annotations

from datetime import datetime

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN, NOME_DISPOSITIVO
from .dati import DatiRifiuti, RifiutiConfigEntry


class EntitaRifiuti(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: RifiutiConfigEntry, chiave: str) -> None:
        self._dati: DatiRifiuti = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{chiave}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NOME_DISPOSITIVO,
            manufacturer="AGESP Busto Arsizio",
            model="Raccolta porta a porta",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        # lo stato dipende solo dalla data: basta ricalcolarlo quando cambia il giorno
        self.async_on_remove(
            async_track_time_change(self.hass, self._nuovo_giorno, hour=0, minute=0, second=1)
        )

    @callback
    def _nuovo_giorno(self, _ora: datetime) -> None:
        self.async_write_ha_state()
