"""Rifiuti AGESP: dove buttare i rifiuti a Busto Arsizio e calendario della raccolta."""
from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_LIMITE,
    ATTR_TESTO,
    CARTELLA_FRONTEND,
    COMPONENTE_PANNELLO,
    DOMAIN,
    FILE_DIZIONARIO,
    FILE_PANNELLO,
    FILE_SINONIMI,
    ICONA_PANNELLO,
    LIMITE_MASSIMO,
    LIMITE_PREDEFINITO,
    SERVIZIO_CERCA,
    TITOLO_PANNELLO,
    URL_PANNELLO,
    URL_STATICI,
)
from .dati import DatiRifiuti, RifiutiConfigEntry, calendario_da_opzioni
from .search import MotoreRicerca

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SCHEMA_CERCA = vol.Schema(
    {
        vol.Required(ATTR_TESTO): cv.string,
        vol.Optional(ATTR_LIMITE, default=LIMITE_PREDEFINITO): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=LIMITE_MASSIMO)
        ),
    }
)


def _dati(hass: HomeAssistant) -> DatiRifiuti | None:
    return hass.data.get(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Registra file statici, comandi websocket e azione: una volta sola per avvio di HA."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_STATICI, str(CARTELLA_FRONTEND), cache_headers=False)]
    )
    websocket_api.async_register_command(hass, ws_cerca)
    websocket_api.async_register_command(hass, ws_info)
    websocket_api.async_register_command(hass, ws_calendario)

    async def cerca(call: ServiceCall) -> ServiceResponse:
        dati = _dati(hass)
        if dati is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="non_configurata")
        return dati.arricchisci(dati.motore.cerca(call.data[ATTR_TESTO], call.data[ATTR_LIMITE]))

    hass.services.async_register(
        DOMAIN, SERVIZIO_CERCA, cerca, schema=SCHEMA_CERCA, supports_response=SupportsResponse.ONLY
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RifiutiConfigEntry) -> bool:
    """Carica dizionario e calendario, crea le entità e la pagina "Rifiuti" nella barra laterale."""
    motore = await hass.async_add_executor_job(MotoreRicerca.da_file, FILE_DIZIONARIO, FILE_SINONIMI)
    dati = DatiRifiuti(motore, calendario_da_opzioni(entry.options))
    entry.runtime_data = dati
    hass.data[DOMAIN] = dati

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # l'impronta del file nell'URL obbliga browser e tablet a scaricare la versione nuova
    impronta = await hass.async_add_executor_job(
        lambda: hashlib.sha1((CARTELLA_FRONTEND / FILE_PANNELLO).read_bytes()).hexdigest()[:10]
    )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=URL_PANNELLO,
        webcomponent_name=COMPONENTE_PANNELLO,
        sidebar_title=TITOLO_PANNELLO,
        sidebar_icon=ICONA_PANNELLO,
        module_url=f"{URL_STATICI}/{FILE_PANNELLO}?v={impronta}",
        require_admin=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RifiutiConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    frontend.async_remove_panel(hass, URL_PANNELLO, warn_if_unknown=False)
    hass.data.pop(DOMAIN, None)
    return True


def _non_configurata(connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    connection.send_error(msg["id"], "non_configurata", "Integrazione Rifiuti AGESP non configurata")


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/cerca",
        vol.Required(ATTR_TESTO): str,
        vol.Optional(ATTR_LIMITE, default=15): vol.All(int, vol.Range(min=1, max=LIMITE_MASSIMO)),
    }
)
@callback
def ws_cerca(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (dati := _dati(hass)) is None:
        _non_configurata(connection, msg)
        return
    connection.send_result(msg["id"], dati.arricchisci(dati.motore.cerca(msg[ATTR_TESTO], msg[ATTR_LIMITE])))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/info"})
@callback
def ws_info(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (dati := _dati(hass)) is None:
        _non_configurata(connection, msg)
        return
    connection.send_result(msg["id"], dati.motore.info())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/calendario"})
@callback
def ws_calendario(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (dati := _dati(hass)) is None:
        _non_configurata(connection, msg)
        return
    connection.send_result(msg["id"], dati.stato_calendario())
