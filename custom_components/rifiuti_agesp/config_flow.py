"""Configurazione dall'interfaccia: per ora nessuna opzione, solo conferma."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class RifiutiAgespConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="Rifiuti AGESP", data={})
        return self.async_show_form(step_id="user")
