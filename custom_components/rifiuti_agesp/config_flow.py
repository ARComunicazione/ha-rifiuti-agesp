"""Configurazione dall'interfaccia: conferma e giorni della raccolta (modificabili da "Configura")."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .calendario import FRAZIONI, EccezioneNonValida, leggi_eccezioni
from .const import CONF_ECCEZIONI, DOMAIN, NOME_DISPOSITIVO

SELETTORE_GIORNI = SelectSelector(
    SelectSelectorConfig(
        options=[str(g) for g in range(7)],   # 0 = lunedì
        multiple=True,
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="giorno",
    )
)


def schema_calendario(valori: Mapping[str, Any]) -> vol.Schema:
    campi: dict[Any, Any] = {vol.Optional(f, default=list(valori.get(f, []))): SELETTORE_GIORNI for f in FRAZIONI}
    campi[vol.Optional(CONF_ECCEZIONI, default=valori.get(CONF_ECCEZIONI, ""))] = TextSelector(
        TextSelectorConfig(multiline=True)
    )
    return vol.Schema(campi)


def valida_calendario(dati: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """Errori del modulo e segnaposto per il messaggio (la riga sbagliata)."""
    try:
        leggi_eccezioni(dati.get(CONF_ECCEZIONI, ""))
    except EccezioneNonValida as err:
        return {CONF_ECCEZIONI: "eccezione_non_valida"}, {"riga": err.riga}
    return {}, {}


class RifiutiAgespConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RifiutiAgespOptionsFlow:
        return RifiutiAgespOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_calendario()
        return self.async_show_form(step_id="user")

    async def async_step_calendario(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errori: dict[str, str] = {}
        segnaposto: dict[str, str] = {}
        if user_input is not None:
            errori, segnaposto = valida_calendario(user_input)
            if not errori:
                return self.async_create_entry(title=NOME_DISPOSITIVO, data={}, options=user_input)
        return self.async_show_form(
            step_id="calendario",
            data_schema=schema_calendario(user_input or {}),
            errors=errori,
            description_placeholders=segnaposto,
        )


class RifiutiAgespOptionsFlow(OptionsFlowWithReload):
    """Modifica dei giorni di raccolta e delle eccezioni; al salvataggio l'integrazione si ricarica."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errori: dict[str, str] = {}
        segnaposto: dict[str, str] = {}
        if user_input is not None:
            errori, segnaposto = valida_calendario(user_input)
            if not errori:
                return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=schema_calendario(user_input or self.config_entry.options),
            errors=errori,
            description_placeholders=segnaposto,
        )
