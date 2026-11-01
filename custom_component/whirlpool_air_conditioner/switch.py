"""Switch platform for the Whirlpool Air Conditioner integration."""

from typing import Any, override

from whirlpool.aircon import Aircon

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WhirlpoolConfigEntry
from .entity import WhirlpoolEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: WhirlpoolConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Whirlpool custom toggles from a config entry."""
    appliances_manager = config_entry.runtime_data

    entities: list[SwitchEntity] = []
    for ac_device in appliances_manager.aircons:
        entities.append(WhirlpoolDisplaySwitch(ac_device))
        entities.append(WhirlpoolSuperSilentSwitch(ac_device))
        entities.append(WhirlpoolJetSwitch(ac_device))
        entities.append(WhirlpoolPowerSaveSwitch(ac_device))

    async_add_entities(entities)


class WhirlpoolDisplaySwitch(WhirlpoolEntity, SwitchEntity):
    """Representation of the Whirlpool Display panel switch."""

    _appliance: Aircon

    def __init__(self, appliance: Aircon) -> None:
        """Initialize the display panel switch."""
        super().__init__(appliance, unique_id_suffix="-display")
        self._attr_translation_key = "display"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if display panel is on."""
        return self._appliance.get_display_on()

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn display panel on."""
        WhirlpoolDisplaySwitch._check_service_request(
            await self._appliance.set_display_on(True)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn display panel off."""
        WhirlpoolDisplaySwitch._check_service_request(
            await self._appliance.set_display_on(False)
        )


class WhirlpoolJetSwitch(WhirlpoolEntity, SwitchEntity):
    """Representation of the Whirlpool Jet (turbo) mode switch."""

    _appliance: Aircon

    def __init__(self, appliance: Aircon) -> None:
        """Initialize the jet switch."""
        super().__init__(appliance, unique_id_suffix="-jet")
        self._attr_translation_key = "jet"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if jet (turbo) mode is on."""
        return self._appliance.get_turbo_mode()

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn jet mode on."""
        WhirlpoolJetSwitch._check_service_request(
            await self._appliance.set_turbo_mode(True)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn jet mode off."""
        WhirlpoolJetSwitch._check_service_request(
            await self._appliance.set_turbo_mode(False)
        )


class WhirlpoolPowerSaveSwitch(WhirlpoolEntity, SwitchEntity):
    """Representation of the Whirlpool Power save (eco) mode switch."""

    _appliance: Aircon

    def __init__(self, appliance: Aircon) -> None:
        """Initialize the power save switch."""
        super().__init__(appliance, unique_id_suffix="-power_save")
        self._attr_translation_key = "power_save"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if power save (eco) mode is on."""
        return self._appliance.get_eco_mode()

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn power save mode on."""
        WhirlpoolPowerSaveSwitch._check_service_request(
            await self._appliance.set_eco_mode(True)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn power save mode off."""
        WhirlpoolPowerSaveSwitch._check_service_request(
            await self._appliance.set_eco_mode(False)
        )


class WhirlpoolSuperSilentSwitch(WhirlpoolEntity, SwitchEntity):
    """Representation of the Whirlpool Super Silent (quiet) mode switch."""

    _appliance: Aircon

    def __init__(self, appliance: Aircon) -> None:
        """Initialize the super silent switch."""
        super().__init__(appliance, unique_id_suffix="-super_silent")
        self._attr_translation_key = "super_silent"

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if super silent (quiet) mode is on."""
        return self._appliance.get_quiet_mode()

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn super silent mode on."""
        WhirlpoolSuperSilentSwitch._check_service_request(
            await self._appliance.set_quiet_mode(True)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn super silent mode off."""
        WhirlpoolSuperSilentSwitch._check_service_request(
            await self._appliance.set_quiet_mode(False)
        )
