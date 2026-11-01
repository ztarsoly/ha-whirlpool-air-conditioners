"""Select platform for the Whirlpool Air Conditioners integration."""

from typing import Final, override

from whirlpool.aircon import (
    SETTING_SLEEP_MODE,
    SETVAL_SLEEP_MODE_ADULTS,
    SETVAL_SLEEP_MODE_CHILDREN,
    SETVAL_SLEEP_MODE_ELDERLY,
    SETVAL_SLEEP_MODE_OFF,
    SETVAL_SLEEP_MODE_TEENS,
    Aircon,
)

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity

PARALLEL_UPDATES = 1

SLEEP_MODES: Final[dict[str, str]] = {
    SETVAL_SLEEP_MODE_OFF: "off",
    SETVAL_SLEEP_MODE_ADULTS: "adults",
    SETVAL_SLEEP_MODE_ELDERLY: "elderly",
    SETVAL_SLEEP_MODE_TEENS: "teens",
    SETVAL_SLEEP_MODE_CHILDREN: "children",
}
OPTION_TO_SLEEP_MODE: Final = {v: k for k, v in SLEEP_MODES.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the select platform."""
    appliances_manager = config_entry.runtime_data
    async_add_entities(
        WhirlpoolSleepModeSelect(aircon)
        for aircon in appliances_manager.aircons
        if aircon.has_attribute(SETTING_SLEEP_MODE)
    )


class WhirlpoolSleepModeSelect(WhirlpoolEntity, SelectEntity):
    """Sleep mode of an air conditioner."""

    _appliance: Aircon

    _attr_options = list(SLEEP_MODES.values())
    _attr_translation_key = "sleep_mode"

    def __init__(self, appliance: Aircon) -> None:
        """Initialize the sleep mode select."""
        super().__init__(appliance, unique_id_suffix="-sleep_mode")

    @override
    @property
    def current_option(self) -> str | None:
        """Return the current sleep mode."""
        # The library defines the sleep mode setting but has no getter for it.
        return SLEEP_MODES.get(self._appliance._get_attribute(SETTING_SLEEP_MODE))  # noqa: SLF001

    @override
    async def async_select_option(self, option: str) -> None:
        """Set the sleep mode."""
        WhirlpoolSleepModeSelect._check_service_request(
            await self._appliance.send_attributes(
                {SETTING_SLEEP_MODE: OPTION_TO_SLEEP_MODE[option]}
            )
        )
