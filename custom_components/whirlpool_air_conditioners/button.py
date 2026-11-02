"""Button platform for the Whirlpool Air Conditioners integration."""

from typing import override

from whirlpool.httpapi.aircon import SETTING_REBOOT_WIFI, Aircon as HttpAircon

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
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
    """Set up the button platform."""
    appliances_manager = config_entry.runtime_data
    # The reboot command is a raw setting that only units on the HTTP API expose.
    async_add_entities(
        WhirlpoolWifiRebootButton(aircon)
        for aircon in appliances_manager.aircons
        if isinstance(aircon, HttpAircon) and aircon.has_attribute(SETTING_REBOOT_WIFI)
    )


class WhirlpoolWifiRebootButton(WhirlpoolEntity, ButtonEntity):
    """Button to restart the Wi-Fi module of an air conditioner."""

    _appliance: HttpAircon

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "wifi_reboot"

    def __init__(self, appliance: HttpAircon) -> None:
        """Initialize the Wi-Fi reboot button."""
        super().__init__(appliance, unique_id_suffix="-wifi_reboot")

    @override
    async def async_press(self) -> None:
        """Restart the Wi-Fi module."""
        # The library defines the reboot setting but has no method for it.
        WhirlpoolWifiRebootButton._check_service_request(
            await self._appliance.send_attributes(
                {SETTING_REBOOT_WIFI: self._appliance.bool_to_attr_value(True)}
            )
        )
